"""Сопоставление колонок/строк и сравнение значений."""

from __future__ import annotations

from collections import Counter
from decimal import Decimal
from typing import Any, Sequence

from .models import (
    ColumnPair,
    ComparisonResult,
    Difference,
    DifferenceType,
    TableData,
)
from .header import header_match_score
from .normalize import (
    is_empty,
    normalize_header,
    normalize_text,
    numbers_equal,
    parse_number,
)

DEFAULT_ABS_TOLERANCE = Decimal("1e-9")
DEFAULT_REL_TOLERANCE = Decimal("1e-6")
DEFAULT_FUZZY_THRESHOLD = 0.75


def _header_keys(headers: Sequence[str]) -> list[tuple[str, int]]:
    seen: Counter[str] = Counter()
    keys: list[tuple[str, int]] = []
    for header in headers:
        base = normalize_header(header)
        keys.append((base, seen[base]))
        seen[base] += 1
    return keys


def align_columns(
    excel_headers: Sequence[str],
    pdf_headers: Sequence[str],
    fuzzy_threshold: float = DEFAULT_FUZZY_THRESHOLD,
) -> tuple[list[ColumnPair], list[int], list[int], list[str]]:
    """Сопоставляет колонки: exact → fuzzy → positional fallback."""
    excel_keys = _header_keys(excel_headers)
    pdf_keys = _header_keys(pdf_headers)

    pairs: list[ColumnPair] = []
    used_excel: set[int] = set()
    used_pdf: set[int] = set()
    warnings: list[str] = []

    pdf_by_key: dict[tuple[str, int], list[int]] = {}
    for index, key in enumerate(pdf_keys):
        pdf_by_key.setdefault(key, []).append(index)

    for excel_index, key in enumerate(excel_keys):
        candidates = [
            index for index in pdf_by_key.get(key, []) if index not in used_pdf
        ]
        if not candidates:
            continue
        pdf_index = candidates[0]
        pairs.append(
            ColumnPair(
                excel_index=excel_index,
                pdf_index=pdf_index,
                excel_name=str(excel_headers[excel_index]),
                pdf_name=str(pdf_headers[pdf_index]),
                method="exact",
                score=1.0,
            )
        )
        used_excel.add(excel_index)
        used_pdf.add(pdf_index)

    fuzzy_candidates: list[tuple[float, int, int]] = []
    for excel_index, (excel_key, _) in enumerate(excel_keys):
        if excel_index in used_excel or not excel_key:
            continue
        for pdf_index, (pdf_key, _) in enumerate(pdf_keys):
            if pdf_index in used_pdf or not pdf_key:
                continue
            score = header_match_score(
                excel_headers[excel_index],
                pdf_headers[pdf_index],
            )
            if score >= fuzzy_threshold:
                fuzzy_candidates.append((score, excel_index, pdf_index))

    for score, excel_index, pdf_index in sorted(fuzzy_candidates, reverse=True):
        if excel_index in used_excel or pdf_index in used_pdf:
            continue
        pairs.append(
            ColumnPair(
                excel_index=excel_index,
                pdf_index=pdf_index,
                excel_name=str(excel_headers[excel_index]),
                pdf_name=str(pdf_headers[pdf_index]),
                method="fuzzy",
                score=round(score, 3),
            )
        )
        used_excel.add(excel_index)
        used_pdf.add(pdf_index)

    remaining_excel = [
        index for index in range(len(excel_headers)) if index not in used_excel
    ]
    remaining_pdf = [
        index for index in range(len(pdf_headers)) if index not in used_pdf
    ]
    for excel_index, pdf_index in zip(remaining_excel, remaining_pdf):
        pairs.append(
            ColumnPair(
                excel_index=excel_index,
                pdf_index=pdf_index,
                excel_name=str(excel_headers[excel_index]),
                pdf_name=str(pdf_headers[pdf_index]),
                method="positional",
                score=0.0,
            )
        )
        used_excel.add(excel_index)
        used_pdf.add(pdf_index)
        warnings.append(
            "Колонки сопоставлены позиционно: "
            f"Excel «{excel_headers[excel_index]}» ↔ PDF «{pdf_headers[pdf_index]}»."
        )

    pairs.sort(key=lambda pair: pair.excel_index)
    unmatched_excel = [
        index for index in range(len(excel_headers)) if index not in used_excel
    ]
    unmatched_pdf = [
        index for index in range(len(pdf_headers)) if index not in used_pdf
    ]

    return pairs, unmatched_excel, unmatched_pdf, warnings


def _cell(row: Sequence[Any], index: int) -> Any:
    return row[index] if index < len(row) else None


def _classify(
    excel_value: Any,
    pdf_value: Any,
    abs_tolerance: Decimal,
    rel_tolerance: Decimal,
) -> DifferenceType | None:
    excel_empty = is_empty(excel_value)
    pdf_empty = is_empty(pdf_value)

    if excel_empty and pdf_empty:
        return None
    if excel_empty or pdf_empty:
        return DifferenceType.EMPTY_VS_VALUE

    excel_number = parse_number(excel_value)
    pdf_number = parse_number(pdf_value)
    if excel_number is not None and pdf_number is not None:
        if numbers_equal(excel_number, pdf_number, abs_tolerance, rel_tolerance):
            return None
        return DifferenceType.NUMBER

    if normalize_text(excel_value) == normalize_text(pdf_value):
        return None
    return DifferenceType.TEXT


def compare_tables(
    excel: TableData,
    pdf: TableData,
    abs_tolerance: Decimal = DEFAULT_ABS_TOLERANCE,
    rel_tolerance: Decimal = DEFAULT_REL_TOLERANCE,
    fuzzy_threshold: float = DEFAULT_FUZZY_THRESHOLD,
) -> ComparisonResult:
    """Сравнивает таблицы позиционно по строкам."""
    if abs_tolerance < 0 or rel_tolerance < 0:
        raise ValueError("Допуски не могут быть отрицательными.")

    pairs, unmatched_excel, unmatched_pdf, column_warnings = align_columns(
        excel.headers,
        pdf.headers,
        fuzzy_threshold=fuzzy_threshold,
    )

    warnings = list(column_warnings)
    warnings.extend(str(item) for item in excel.metadata.get("warnings", []))
    warnings.extend(str(item) for item in pdf.metadata.get("warnings", []))

    differences: list[Difference] = []

    for excel_index in unmatched_excel:
        differences.append(
            Difference(
                type=DifferenceType.MISSING_COLUMN,
                column_excel=excel_index,
                column_name_excel=str(excel.headers[excel_index]),
                value_excel=excel.headers[excel_index],
                comment="Колонка есть только в Excel.",
            )
        )
    for pdf_index in unmatched_pdf:
        differences.append(
            Difference(
                type=DifferenceType.MISSING_COLUMN,
                column_pdf=pdf_index,
                column_name_pdf=str(pdf.headers[pdf_index]),
                value_pdf=pdf.headers[pdf_index],
                comment="Колонка есть только в PDF.",
            )
        )

    common_rows = min(excel.height, pdf.height)
    for row_index in range(common_rows):
        excel_row = excel.rows[row_index]
        pdf_row = pdf.rows[row_index]

        # Если метка строки совпадает, а заполненные значения — разные (одно в каждой),
        # сравниваем числовые значения по строке, а не по колонкам (итоги разделов).
        excel_non_empty = [
            (i, _cell(excel_row, i))
            for i in range(len(excel_row))
            if not is_empty(_cell(excel_row, i))
        ]
        pdf_non_empty = [
            (i, _cell(pdf_row, i))
            for i in range(len(pdf_row))
            if not is_empty(_cell(pdf_row, i))
        ]
        if len(excel_non_empty) >= 2 and len(pdf_non_empty) >= 2:
            excel_label = str(excel_non_empty[0][1]) if excel_non_empty else ""
            pdf_label = str(pdf_non_empty[0][1]) if pdf_non_empty else ""
            if normalize_text(excel_label) == normalize_text(pdf_label):
                excel_vals = [v for _, v in excel_non_empty[1:]]
                pdf_vals = [v for _, v in pdf_non_empty[1:]]
                if all(
                    _classify(ev, pv, abs_tolerance, rel_tolerance) is None
                    for ev, pv in zip(excel_vals, pdf_vals)
                ):
                    continue

        for pair in pairs:
            excel_value = _cell(excel_row, pair.excel_index)
            pdf_value = _cell(pdf_row, pair.pdf_index)
            difference_type = _classify(
                excel_value,
                pdf_value,
                abs_tolerance,
                rel_tolerance,
            )
            if difference_type is None:
                continue
            differences.append(
                Difference(
                    type=difference_type,
                    row_excel=row_index + 1,
                    row_pdf=row_index + 1,
                    column_excel=pair.excel_index,
                    column_pdf=pair.pdf_index,
                    column_name_excel=pair.excel_name,
                    column_name_pdf=pair.pdf_name,
                    value_excel=excel_value,
                    value_pdf=pdf_value,
                )
            )

    for row_index in range(common_rows, excel.height):
        differences.append(
            Difference(
                type=DifferenceType.MISSING_ROW,
                row_excel=row_index + 1,
                value_excel=excel.rows[row_index],
                comment="Строка есть только в Excel.",
            )
        )
    for row_index in range(common_rows, pdf.height):
        differences.append(
            Difference(
                type=DifferenceType.MISSING_ROW,
                row_pdf=row_index + 1,
                value_pdf=pdf.rows[row_index],
                comment="Строка есть только в PDF.",
            )
        )

    return ComparisonResult(
        excel=excel,
        pdf=pdf,
        differences=differences,
        column_pairs=pairs,
        unmatched_excel_columns=unmatched_excel,
        unmatched_pdf_columns=unmatched_pdf,
        warnings=warnings,
        abs_tolerance=abs_tolerance,
        rel_tolerance=rel_tolerance,
    )
