"""Формирование Excel-отчёта о расхождениях."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any

import pandas as pd
from openpyxl.styles import (
    Alignment,
    Font,
    PatternFill,
    Side,
    Border,
    numbers,
)
from openpyxl.utils import get_column_letter
from openpyxl.formatting.rule import CellIsRule, FormulaRule, DataBarRule

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

# Color coding for difference types
TYPE_COLORS = {
    DifferenceType.NUMBER: PatternFill("solid", fgColor="FFF2CC"),  # Желтый
    DifferenceType.TEXT: PatternFill("solid", fgColor="DDEBF7"),  # Синий-облетен
    DifferenceType.EMPTY_VS_VALUE: PatternFill("solid", fgColor="FCE4EC"),  # Розовый
    DifferenceType.MISSING_COLUMN: PatternFill("solid", fgColor="E8E8E8"),  # Серый
    DifferenceType.MISSING_ROW: PatternFill("solid", fgColor="E3F2FD"),  # Голубой
}

# Column-specific fills for Differences sheet
COLUMN_COLORS = {
    "Тип": PatternFill("solid", fgColor="DDEBF7"),
    "Значение Excel": PatternFill("solid", fgColor="F0F0F0"),
    "Значение PDF": PatternFill("solid", fgColor="F0F0F0"),
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


# Per-sheet header styles
SHEET_HEADER_STYLES = {
    SUMMARY_SHEET: PatternFill("solid", fgColor="1F4E79"),  # Тёмно-синий
    DIFFERENCES_SHEET: PatternFill("solid", fgColor="C00000"),  # Красный
    COLUMNS_SHEET: PatternFill("solid", fgColor="2E75B6"),  # Средний синий
    ONLY_EXCEL_SHEET: PatternFill("solid", fgColor="548235"),  # Зелёный
    ONLY_PDF_SHEET: PatternFill("solid", fgColor="BF8F00"),  # Оранжевый
}

SHEET_TITLE_FONT = Font(bold=True, color="FFFFFF", size=12)
SHEET_HEADER_FONT = Font(bold=True, color="FFFFFF", size=10)


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


def _apply_header_style(worksheet: Any, fill: PatternFill) -> None:
    header_font = Font(bold=True, color="FFFFFF", size=10)
    for cell in worksheet[1]:
        cell.font = header_font
        cell.fill = fill
        cell.alignment = Alignment(vertical="center", wrap_text=True, horizontal="center")


def _style_summary(worksheet: Any) -> None:
    """Styling for Summary sheet with colored key metrics."""
    _apply_header_style(worksheet, SHEET_HEADER_STYLES[SUMMARY_SHEET])
    thin = Side(style="thin", color="BFBFBF")
    border = Border(left=thin, right=thin, top=thin, bottom=thin)

    total_differences_row = None
    for row_idx, row in enumerate(worksheet.iter_rows(min_row=2), start=2):
        label_cell = row[0]
        value_cell = row[1]
        label_cell.alignment = Alignment(vertical="center", wrap_text=True)
        value_cell.alignment = Alignment(vertical="center", wrap_text=True)

        for cell in row:
            cell.border = border
            cell.fill = PatternFill("solid", fgColor="FFFFFF" if row_idx % 2 else "F2F2F2")

        if label_cell.value == "Всего расхождений":
            total_differences_row = row_idx
            value_cell.font = Font(bold=True, color="C00000", size=12)
            value_cell.fill = PatternFill("solid", fgColor="FFF2CC")
        elif label_cell.value == "Вердикт":
            if value_cell.value and "не найдено" in str(value_cell.value):
                value_cell.font = Font(bold=True, color="548235", size=11)
                value_cell.fill = PatternFill("solid", fgColor="E2EFDA")
            else:
                value_cell.font = Font(bold=True, color="C00000", size=11)
                value_cell.fill = PatternFill("solid", fgColor="FFC7CE")

        # Bold labels
        label_cell.font = Font(bold=True)

    worksheet.column_dimensions["A"].width = 45
    worksheet.column_dimensions["B"].width = 60


def _style_differences(worksheet: Any) -> None:
    """Styling for Differences sheet with type color coding."""
    _apply_header_style(worksheet, SHEET_HEADER_STYLES[DIFFERENCES_SHEET])

    thin = Side(style="thin", color="BFBFBF")
    border = Border(left=thin, right=thin, top=thin, bottom=thin)

    type_col_index = None
    for col_idx, cell in enumerate(worksheet[1], start=1):
        if cell.value == "Тип":
            type_col_index = col_idx

    for row_idx, row in enumerate(worksheet.iter_rows(min_row=2), start=2):
        for cell in row:
            cell.border = border
            cell.alignment = Alignment(vertical="center", wrap_text=True)

        if type_col_index is not None:
            type_cell = row[type_col_index - 1]
            type_label = str(type_cell.value) if type_cell.value else ""
            row_color = None
            for diff_type, label in TYPE_LABELS.items():
                if label == type_label:
                    row_color = TYPE_COLORS[diff_type]
                    break
            if row_color:
                type_cell.fill = row_color

        for cell in row:
            cell.fill = row_color if row_color else PatternFill("solid", fgColor="FFFFFF")

    # Conditional formatting: highlight mismatched value cells
    if worksheet.max_row >= 2:
        value_cols = []
        for col_idx, cell in enumerate(worksheet[1], start=1):
            header = str(cell.value) if cell.value else ""
            if header in ("Значение Excel", "Значение PDF"):
                value_cols.append(get_column_letter(col_idx))

        for col_letter in value_cols:
            last_row = worksheet.max_row
            range_str = f"{col_letter}2:{col_letter}{last_row}"
            worksheet.conditional_formatting.add(
                range_str,
                CellIsRule(
                    operator="notEqual",
                    formula=[f'$B{2}'],
                    fill=PatternFill("solid", fgColor="FF9999"),
                    font=Font(color="C00000"),
                ),
            )


def _style_columns(worksheet: Any) -> None:
    """Styling for Columns sheet."""
    _apply_header_style(worksheet, SHEET_HEADER_STYLES[COLUMNS_SHEET])

    thin = Side(style="thin", color="BFBFBF")
    border = Border(left=thin, right=thin, top=thin, bottom=thin)

    for row_idx, row in enumerate(worksheet.iter_rows(min_row=2), start=2):
        for cell in row:
            cell.border = border
            cell.alignment = Alignment(vertical="center", wrap_text=True)

        if row_idx % 2 == 0:
            for cell in row:
                cell.fill = PatternFill("solid", fgColor="F2F2F2")

    # Data bar rule for similarity score
    last_row = worksheet.max_row
    if last_row >= 2:
        score_col = None
        for col_idx, cell in enumerate(worksheet[1], start=1):
            if cell.value == "Сходство":
                score_col = col_idx
                break
        if score_col:
            score_letter = get_column_letter(score_col)
            range_str = f"{score_letter}2:{score_letter}{last_row}"
            worksheet.conditional_formatting.add(
                range_str,
                DataBarRule(start_type="num", start_value=0, end_type="num", end_value=1,
                            color="63BE7B", showValue=True),
            )

    for col_idx, header_cell in enumerate(worksheet[1], start=1):
        col_letter = get_column_letter(col_idx)
        width = max(len(str(header_cell.value)) + 2, 30)
        worksheet.column_dimensions[col_letter].width = min(width, 70)


def _style_only_sheet(worksheet: Any, sheet_name: str) -> None:
    """Styling for Only in Excel / Only in PDF sheets."""
    fill = SHEET_HEADER_STYLES.get(sheet_name, PatternFill("solid", fgColor="808080"))
    _apply_header_style(worksheet, fill)

    thin = Side(style="thin", color="BFBFBF")
    border = Border(left=thin, right=thin, top=thin, bottom=thin)

    for row_idx, row in enumerate(worksheet.iter_rows(min_row=2), start=2):
        for cell in row:
            cell.border = border
            cell.alignment = Alignment(vertical="center", wrap_text=True)
        if row_idx % 2 == 0:
            for cell in row:
                cell.fill = PatternFill("solid", fgColor="F2F2F2")

    for col_idx, header_cell in enumerate(worksheet[1], start=1):
        col_letter = get_column_letter(col_idx)
        worksheet.column_dimensions[col_letter].width = max(len(str(header_cell.value)) + 2, 20)


def _freeze_and_filter(worksheet: Any, autofilter: bool) -> None:
    worksheet.freeze_panes = "A2"
    if autofilter and worksheet.max_row >= 1:
        worksheet.auto_filter.ref = worksheet.dimensions


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

        sheets = {
            SUMMARY_SHEET: lambda ws: _style_summary(ws),
            DIFFERENCES_SHEET: lambda ws: _style_differences(ws),
            COLUMNS_SHEET: lambda ws: _style_columns(ws),
            ONLY_EXCEL_SHEET: lambda ws: _style_only_sheet(ws, ONLY_EXCEL_SHEET),
            ONLY_PDF_SHEET: lambda ws: _style_only_sheet(ws, ONLY_PDF_SHEET),
        }

        for name, worksheet in writer.sheets.items():
            _freeze_and_filter(worksheet, autofilter=name != SUMMARY_SHEET)
            if name in sheets:
                sheets[name](worksheet)

    return report_path
