"""Чтение таблиц из PDF через pdfplumber + OCR fallback."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Iterable, Sequence

import pdfplumber
import pytesseract
from PIL import Image

from .header import trim_signature_rows
from .models import TableData
from .normalize import is_empty, normalize_header

TEXT_TABLE_SETTINGS = {
    "vertical_strategy": "text",
    "horizontal_strategy": "text",
}


def _ocr_cell_image(page: Any, bbox: tuple[float, float, float, float]) -> tuple[str, float]:
    """Распознаёт текст в области ячейки через Tesseract OCR.
    
    Args:
        page: pdfplumber page object
        bbox: (x0, y0, x1, y1) координаты области в PDF points
        
    Returns:
        tuple: (recognized_text, confidence_score)
    """
    try:
        # Render page region to image
        x0, y0, x1, y1 = bbox
        # pdfplumber uses points (1/72 inch), we need pixels for OCR
        # Scale to ~300 DPI for better OCR quality
        scale = 300 / 72
        im = page.to_image(resolution=300)
        pil_image = im.original
        
        # Crop to bbox (in points, converted to pixels)
        crop_bbox = (x0 * scale, y0 * scale, x1 * scale, y1 * scale)
        cell_image = pil_image.crop(crop_bbox)
        
        # OCR with Tesseract
        data = pytesseract.image_to_data(
            cell_image, 
            lang='rus+eng',
            output_type=pytesseract.Output.DICT
        )
        
        # Combine text and calculate average confidence
        texts = [t for t in data['text'] if t.strip()]
        confidences = [int(c) for c in data['conf'] if c != '-1']
        
        combined_text = " ".join(texts).strip()
        avg_confidence = sum(confidences) / len(confidences) / 100.0 if confidences else 0.0
        
        return combined_text, avg_confidence
    except Exception:
        return "", 0.0


def _enhance_cell_with_ocr(
    rows: list[list[str | None]], 
    page: Any,
    page_number: int,
    headers: list[str]
) -> tuple[list[list[str | None]], list[str]]:
    """Enhances empty/suspicious cells with OCR fallback.
    
    Args:
        rows: Current extracted rows
        page: pdfplumber page object
        page_number: Page number for logging
        headers: Column headers for context
        
    Returns:
        tuple: (enhanced_rows, warnings)
    """
    warnings = []
    enhanced_rows = []
    
    # Get table bbox on page
    try:
        tables = page.find_tables()
        if not tables:
            return rows, warnings
        table_bbox = tables[0].bbox  # (x0, top, x1, bottom)
    except Exception:
        return rows, warnings
    
    x0, top, x1, bottom = table_bbox
    row_height = (bottom - top) / max(len(rows), 1)
    col_width = (x1 - x0) / max(len(headers), 1)
    
    for row_idx, row in enumerate(rows):
        enhanced_row = list(row)
        for col_idx, cell in enumerate(row):
            if is_empty(cell):
                # Calculate cell bbox
                cell_x0 = x0 + col_idx * col_width
                cell_y0 = top + row_idx * row_height
                cell_x1 = cell_x0 + col_width
                cell_y1 = cell_y0 + row_height
                
                ocr_text, confidence = _ocr_cell_image(page, (cell_x0, cell_y0, cell_x1, cell_y1))
                
                if ocr_text and confidence > 0.5:
                    enhanced_row[col_idx] = ocr_text
                    warnings.append(
                        f"Страница {page_number}: ячейка [{row_idx},{col_idx}] "
                        f"заполнена через OCR (confidence={confidence:.2f}): '{ocr_text[:50]}'"
                    )
        
        enhanced_rows.append(enhanced_row)
    
    return enhanced_rows, warnings


def _clean_cell(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).replace("\u00a0", " ").replace("\u202f", " ").replace("\u2009", " ")
    text = " ".join(text.split())
    return text or None


def _is_document_header_row(row: Sequence[Any]) -> bool:
    """Проверяет, является ли первая строка документа-заголовком (склеенной ячейки)."""
    non_empty = [cell for cell in row if cell is not None and str(cell).strip()]
    if not non_empty:
        return False
    if len(row) >= 8 and len(non_empty) <= 2:
        return True
    text = str(non_empty[0])
    if len(non_empty) == 1 and len(text) > 100:
        return True
    return False


def _has_sequential_number_row(rows: list[list[Any]]) -> bool:
    """Проверяет, есть ли строка с последовательными числами 1, 2, 3... (номера колонок)."""
    for row in rows:
        numbers = []
        for cell in row:
            if cell is not None:
                try:
                    n = int(str(cell).strip())
                    if n > 0:
                        numbers.append(n)
                except ValueError:
                    continue
        if len(numbers) >= 3 and numbers == list(range(1, len(numbers) + 1)):
            return True
    return False


def _clean_table(table: Sequence[Sequence[Any]] | None) -> list[list[str | None]]:
    if not table:
        return []

    cleaned: list[list[str | None]] = []
    for row in table:
        if row is None:
            continue
        cells = [_clean_cell(cell) for cell in row]
        if any(not is_empty(cell) for cell in cells):
            cleaned.append(cells)
    return cleaned


def _looks_like_header(row: Sequence[Any], headers: Sequence[str]) -> bool:
    left = [normalize_header(cell) for cell in row]
    right = [normalize_header(cell) for cell in headers]
    width = max(len(left), len(right))
    if width == 0:
        return False

    non_empty = sum(1 for cell in left if cell)
    if non_empty == 0:
        return False

    matches = sum(
        1
        for index in range(width)
        if index < len(left)
        and index < len(right)
        and left[index]
        and left[index] == right[index]
    )
    return matches / non_empty >= 0.6


def _extract_page_table(page: Any) -> list[list[Any]] | None:
    try:
        return page.extract_table()
    except Exception:
        return None


def _extract_page_table_with_text_settings(page: Any) -> list[list[Any]] | None:
    try:
        return page.extract_table(TEXT_TABLE_SETTINGS)
    except TypeError:
        try:
            return page.extract_table()
        except Exception:
            return None
    except Exception:
        return None


def _extend_headers(
    headers: list[str],
    row: Sequence[Any],
    warnings: list[str],
) -> None:
    if len(row) <= len(headers):
        return
    added = len(row) - len(headers)
    warnings.append(
        f"Таблица шире шапки: добавлено колонок {added} (до {len(row)})."
    )
    for index in range(len(headers), len(row)):
        headers.append(f"Колонка {index + 1}")


def _find_column_number_row(rows: list[list[Any]]) -> int | None:
    """Ищет строку нумерации колонок (1, 2, 3, ...).

    Требует не менее пяти последовательных чисел, чтобы не путать с
    ordinary data rows (например, «1», «2» или «1», «2», «3»).
    """
    for index, row in enumerate(rows):
        numbers = []
        for cell in row:
            if cell is None:
                continue
            try:
                n = int(str(cell).strip())
                if n > 0:
                    numbers.append(n)
            except ValueError:
                continue
        if len(numbers) >= 5 and numbers == list(range(1, len(numbers) + 1)):
            return index
    return None


def _combine_header_values(values: Sequence[Any]) -> str:
    """Склеивает многострочный заголовок колонки без повторов."""
    parts: list[str] = []
    for value in values:
        text = _clean_cell(value)
        if not text:
            continue
        if not parts or normalize_header(parts[-1]) != normalize_header(text):
            parts.append(text)
    return " / ".join(parts)


def _build_headers(header_rows: list[list[Any]], width: int) -> list[str]:
    """Строит заголовки колонок из нескольких строк шапки."""
    return [
        _combine_header_values(
            [row[column] if column < len(row) else None for row in header_rows]
        )
        for column in range(width)
    ]


def extract_from_pages(
    pages: Iterable[Any],
    warnings: list[str] | None = None,
    ocr: str = "none",
) -> tuple[list[str], list[list[Any]]]:
    """Извлекает и склеивает таблицы со страниц.

    Поддерживает многострочную шапку: строку с нумерацией колонок (1, 2, ...)
    отбрасывается, предшествующие строки формируют заголовки.
    """
    if warnings is None:
        warnings = []

    headers: list[str] | None = None
    rows: list[list[Any]] = []
    header_row_count: int = 0

    for page_number, page in enumerate(pages, start=1):
        table = _clean_table(_extract_page_table(page))
        if not table:
            table = _clean_table(_extract_page_table_with_text_settings(page))

        if not table:
            warnings.append(f"Страница {page_number}: таблица не найдена.")
            continue

        # Пропускаем строку-документ (гигантская склеенная ячейка в начале)
        if headers is None and _is_document_header_row(table[0]):
            table = table[1:]
            if not table:
                warnings.append(f"Страница {page_number}: таблица не найдена.")
                continue

        if headers is None:
            # Ищем строку с нумерацией колонок (1, 2, 3, ...)
            col_number_index = _find_column_number_row(table)
            if col_number_index is not None:
                header_rows = table[:col_number_index]
                width = max(len(row) for row in header_rows)
                headers = _build_headers(header_rows, width)
                header_row_count = col_number_index + 1
                data_rows = table[col_number_index + 1:]
            else:
                headers = [str(cell) if cell is not None else "" for cell in table[0]]
                header_row_count = 1
                data_rows = table[1:]
        elif _looks_like_header(table[0], headers):
            data_rows = table[1:]
        else:
            data_rows = table

        for row in data_rows:
            _extend_headers(headers, row, warnings)
            rows.append(list(row) + [None] * (len(headers) - len(row)))

        # OCR fallback: only when explicitly enabled
        if ocr != "none" and rows:
            rows, ocr_warnings = _enhance_cell_with_ocr(rows, page, page_number, headers)
            warnings.extend(ocr_warnings)

    if headers is None:
        raise ValueError("Не удалось извлечь ни одной таблицы из PDF.")

    if not rows:
        raise ValueError("В PDF найдена только шапка таблицы без данных.")

    # Отбрасываем строки подписей (в конце документа: «Сдал...», «Принял...», «Наблюдатель...»)
    rows, trimmed = trim_signature_rows(rows)
    if trimmed:
        warnings.append(f"Строки подписей отброшены: {trimmed}.")

    return headers, rows


def read_pdf(
    path: str | Path, 
    warnings: list[str] | None = None,
    ocr: str = "none",  # none / paddle / full
) -> TableData:
    """Читает все таблицы PDF и возвращает единую таблицу."""
    pdf_path = Path(path).expanduser()
    page_warnings: list[str] = warnings if warnings is not None else []

    with pdfplumber.open(pdf_path) as pdf:
        page_count = len(pdf.pages)
        headers, rows = extract_from_pages(pdf.pages, page_warnings, ocr=ocr)

    return TableData(
        source=str(pdf_path),
        headers=headers,
        rows=rows,
        metadata={"pages": page_count, "warnings": page_warnings},
    )
