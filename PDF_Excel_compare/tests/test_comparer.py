from decimal import Decimal

import pytest

from compare.comparer import align_columns, compare_tables
from compare.models import DifferenceType, TableData


def make_table(headers, rows, source="test"):
    return TableData(source=source, headers=list(headers), rows=[list(row) for row in rows])


def test_equal_tables_have_no_differences():
    table = make_table(["A", "B"], [["Стена", "10"], ["Пол", "20"]])
    result = compare_tables(table, table)
    assert result.has_differences is False
    assert result.differences == []


def test_text_comparison_ignores_case_spaces_and_yo():
    excel = make_table(["A"], [["Стена Ё"]])
    pdf = make_table(["A"], [["  стена е  "]])
    assert compare_tables(excel, pdf).has_differences is False


def test_number_tolerance():
    excel = make_table(["A"], [["1.0"]])
    pdf = make_table(["A"], [["1.0000005"]])
    assert compare_tables(excel, pdf).has_differences is False


def test_number_difference():
    excel = make_table(["A"], [["1.0"]])
    pdf = make_table(["A"], [["1.1"]])
    result = compare_tables(excel, pdf)
    assert len(result.differences) == 1
    assert result.differences[0].type == DifferenceType.NUMBER


def test_empty_vs_value():
    excel = make_table(["A"], [[None]])
    pdf = make_table(["A"], [["10"]])
    result = compare_tables(excel, pdf)
    assert result.differences[0].type == DifferenceType.EMPTY_VS_VALUE


def test_extra_rows_are_reported():
    excel = make_table(["A"], [["1"], ["2"], ["3"]])
    pdf = make_table(["A"], [["1"]])
    result = compare_tables(excel, pdf)
    missing = [d for d in result.differences if d.type == DifferenceType.MISSING_ROW]
    assert len(missing) == 2
    assert missing[0].row_excel == 2
    assert missing[1].row_excel == 3


def test_fuzzy_column_matching():
    excel = make_table(["Наименование"], [["Кирпич"]])
    pdf = make_table(["Наименования"], [["Кирпич"]])
    result = compare_tables(excel, pdf)
    assert result.differences == []
    assert result.column_pairs[0].method == "fuzzy"


def test_positional_column_matching_when_headers_differ():
    excel = make_table(["A", "B"], [["1", "2"]])
    pdf = make_table(["X", "Y"], [["1", "2"]])
    result = compare_tables(excel, pdf)
    assert result.differences == []
    assert [pair.method for pair in result.column_pairs] == ["positional", "positional"]
    assert result.warnings


def test_duplicate_headers_are_paired_by_order():
    excel = make_table(["A", "A"], [["1", "2"]])
    pdf = make_table(["A", "A"], [["1", "2"]])
    pairs, unmatched_excel, unmatched_pdf, _ = align_columns(
        excel.headers, pdf.headers
    )
    assert len(pairs) == 2
    assert [pair.pdf_index for pair in pairs] == [0, 1]
    assert unmatched_excel == []
    assert unmatched_pdf == []


def test_missing_column_is_reported():
    excel = make_table(["A", "B", "C"], [["1", "2", "3"]])
    pdf = make_table(["A", "B"], [["1", "2"]])
    result = compare_tables(excel, pdf)
    assert result.unmatched_excel_columns == [2]
    missing = [d for d in result.differences if d.type == DifferenceType.MISSING_COLUMN]
    assert len(missing) == 1
    assert missing[0].column_name_excel == "C"


def test_negative_tolerance_is_rejected():
    table = make_table(["A"], [["1"]])
    with pytest.raises(ValueError):
        compare_tables(table, table, abs_tolerance=Decimal("-1"))
