"""Формирование Excel-отчёта о расхождениях."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any

import pandas as pd
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter

from .models import ComparisonResult, Difference, DifferenceType
from .normalize import format_value

SUMMARY_SHEET = "Summary"
DIFFERENCES_SHEET = "Differences"
COLUMNS_SHEET = "Columns"
ONLY_EXCEL_SHEET = "Only in Excel"
ONLY_PDF_SHEET = "Only in PDF"

TYPE_LABELS = {
    DifferenceType.NUMBER: "Число",
    DifferenceType.TEXT: "Текст",
    DifferenceType.EMPTY_VS_VALUE: "Пусто / значение",
    DifferenceType.MISSING_COLUMN: "Нет колонки",
    DifferenceType.MISSING_ROW: "Нет строки",
}

DIFFERENCE_COLUMNS = [
    "Тип",
    "Строка Excel",
    "Строка PDF",
    "Колонка Excel",
    "Колонка PDF",
    "Значение Excel",
    "Значение PDF",
    "Комментарий",
]

COLUMN_COLUMNS = [
    "Колонка Excel",
    "Колонка PDF",
    "Метод",
    "Сходство",
]

ONLY_COLUMNS = ["Тип", "Строка", "Колонка", "Значение"]


def _row_number(value: int | None) -> int | None:
    return value


def _difference_row(difference: Difference) -> dict[str, Any]:
    return {
        "Тип": TYPE_LABELS[difference.type],
        "Строка Excel": _row_number(difference.row_excel),
        "Строка PDF": _row_number(difference.row_pdf),
        "Колонка Excel": difference.column_name_excel,
        "Колонка PDF": difference.column_name_pdf,
        "Значение Excel": format_value(difference.value_excel),
        "Значение PDF": format_value(difference.value_pdf),
        "Комментарий": difference.comment,
    }


def _summary_rows(result: ComparisonResult) -> list[tuple[str, Any]]:
    counts = result.count_by_type()
    total = len(result.differences)
    verdict = "Расхождений не найдено" if total == 0 else f"Найдено расхождений: {total}"

    return [
        ("Дата отчёта", datetime.now().strftime("%Y-%m-%d %H:%M:%S")),
        ("Файл Excel", result.excel.source),
        ("Лист Excel", result.excel.metadata.get("sheet", "")),
        ("Файл PDF", result.pdf.source),
        ("Страниц в PDF", result.pdf.metadata.get("pages", "")),
        ("Строк Excel", result.excel.height),
        ("Строк PDF", result.pdf.height),
        ("Колонок Excel", result.excel.width),
        ("Колонок PDF", result.pdf.width),
        ("Сопоставлено колонок", len(result.column_pairs)),
        ("Колонок только в Excel", len(result.unmatched_excel_columns)),
        ("Колонок только в PDF", len(result.unmatched_pdf_columns)),
        ("Абсолютный допуск", str(result.abs_tolerance)),
        ("Относительный допуск", str(result.rel_tolerance)),
        ("Всего расхождений", total),
        ("Числовых", counts[DifferenceType.NUMBER]),
        ("Текстовых", counts[DifferenceType.TEXT]),
        ("Пусто / значение", counts[DifferenceType.EMPTY_VS_VALUE]),
        ("Нет колонки", counts[DifferenceType.MISSING_COLUMN]),
        ("Нет строки", counts[DifferenceType.MISSING_ROW]),
        ("Вердикт", verdict),
    ]


def _only_in_excel(result: ComparisonResult) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for difference in result.differences:
        if difference.type == DifferenceType.MISSING_ROW and difference.row_excel:
            rows.append(
                {
                    "Тип": "Строка",
                    "Строка": difference.row_excel,
                    "Колонка": "",
                    "Значение": format_value(difference.value_excel),
                }
            )
    for index in result.unmatched_excel_columns:
        rows.append(
            {
                "Тип": "Колонка",
                "Строка": "",
                "Колонка": result.excel.headers[index],
                "Значение": result.excel.headers[index],
            }
        )
    return rows


def _only_in_pdf(result: ComparisonResult) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for difference in result.differences:
        if difference.type == DifferenceType.MISSING_ROW and difference.row_pdf:
            rows.append(
                {
                    "Тип": "Строка",
                    "Строка": difference.row_pdf,
                    "Колонка": "",
                    "Значение": format_value(difference.value_pdf),
                }
            )
    for index in result.unmatched_pdf_columns:
        rows.append(
            {
                "Тип": "Колонка",
                "Строка": "",
                "Колонка": result.pdf.headers[index],
                "Значение": result.pdf.headers[index],
            }
        )
    return rows


def _columns_rows(result: ComparisonResult) -> list[dict[str, Any]]:
    return [
        {
            "Колонка Excel": pair.excel_name,
            "Колонка PDF": pair.pdf_name,
            "Метод": pair.method,
            "Сходство": pair.score if pair.method == "fuzzy" else "",
        }
        for pair in result.column_pairs
    ]


def _style_sheet(worksheet: Any, autofilter: bool = True) -> None:
    header_fill = PatternFill("solid", fgColor="DDEBF7")
    for cell in worksheet[1]:
        cell.font = Font(bold=True)
        cell.fill = header_fill
        cell.alignment = Alignment(vertical="center", wrap_text=True)

    worksheet.freeze_panes = "A2"
    if autofilter and worksheet.max_row >= 1:
        worksheet.auto_filter.ref = worksheet.dimensions

    for cells in worksheet.columns:
        max_length = 0
        for cell in cells:
            if cell.value is not None:
                max_length = max(max_length, len(str(cell.value)))
        column_letter = get_column_letter(cells[0].column)
        worksheet.column_dimensions[column_letter].width = min(max(12, max_length + 2), 70)


def write_report(result: ComparisonResult, path: str | Path) -> Path:
    """Сохраняет отчёт и возвращает путь к нему."""
    report_path = Path(path).expanduser()
    report_path.parent.mkdir(parents=True, exist_ok=True)

    summary = pd.DataFrame(_summary_rows(result), columns=["Параметр", "Значение"])
    differences = pd.DataFrame(
        [_difference_row(item) for item in result.differences],
        columns=DIFFERENCE_COLUMNS,
    )
    columns = pd.DataFrame(_columns_rows(result), columns=COLUMN_COLUMNS)
    only_excel = pd.DataFrame(_only_in_excel(result), columns=ONLY_COLUMNS)
    only_pdf = pd.DataFrame(_only_in_pdf(result), columns=ONLY_COLUMNS)

    with pd.ExcelWriter(report_path, engine="openpyxl") as writer:
        summary.to_excel(writer, sheet_name=SUMMARY_SHEET, index=False)
        differences.to_excel(writer, sheet_name=DIFFERENCES_SHEET, index=False)
        columns.to_excel(writer, sheet_name=COLUMNS_SHEET, index=False)
        only_excel.to_excel(writer, sheet_name=ONLY_EXCEL_SHEET, index=False)
        only_pdf.to_excel(writer, sheet_name=ONLY_PDF_SHEET, index=False)

        for name, worksheet in writer.sheets.items():
            _style_sheet(worksheet, autofilter=name != SUMMARY_SHEET)

    return report_path
