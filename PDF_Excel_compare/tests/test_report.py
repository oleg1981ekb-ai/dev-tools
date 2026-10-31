import pandas as pd

from compare.comparer import compare_tables
from compare.models import TableData
from compare.report import (
    DIFFERENCES_SHEET,
    ONLY_EXCEL_SHEET,
    ONLY_PDF_SHEET,
    SUMMARY_SHEET,
    write_report,
)


def make_table(headers, rows, source="test"):
    return TableData(source=source, headers=list(headers), rows=[list(row) for row in rows])


def test_report_contains_difference_and_summary(tmp_path):
    excel = make_table(["Наименование", "Количество"], [["Кирпич", "100"], ["Песок", "5"]])
    pdf = make_table(["Наименование", "Количество"], [["Кирпич", "100"], ["Песок", "6"]])
    result = compare_tables(excel, pdf)
    report = tmp_path / "report.xlsx"

    write_report(result, report)

    with pd.ExcelFile(report) as book:
        assert set(book.sheet_names) == {
            SUMMARY_SHEET,
            DIFFERENCES_SHEET,
            "Columns",
            ONLY_EXCEL_SHEET,
            ONLY_PDF_SHEET,
        }
        differences = pd.read_excel(book, sheet_name=DIFFERENCES_SHEET)
        summary = pd.read_excel(book, sheet_name=SUMMARY_SHEET)

    assert len(differences) == 1
    assert differences.iloc[0]["Тип"] == "Число"
    assert differences.iloc[0]["Строка Excel"] == 2
    verdict = summary.loc[summary["Параметр"] == "Вердикт", "Значение"].iloc[0]
    assert verdict == "Найдено расхождений: 1"


def test_report_without_differences_still_written(tmp_path):
    table = make_table(["A"], [["1"]])
    result = compare_tables(table, table)
    report = tmp_path / "report.xlsx"

    write_report(result, report)

    with pd.ExcelFile(report) as book:
        differences = pd.read_excel(book, sheet_name=DIFFERENCES_SHEET)
        summary = pd.read_excel(book, sheet_name=SUMMARY_SHEET)

    assert differences.empty
    verdict = summary.loc[summary["Параметр"] == "Вердикт", "Значение"].iloc[0]
    assert verdict == "Расхождений не найдено"


def test_only_in_excel_and_pdf_sheets(tmp_path):
    excel = make_table(["A"], [["1"], ["2"]])
    pdf = make_table(["A"], [["1"], ["3"]])
    result = compare_tables(excel, pdf)
    report = tmp_path / "report.xlsx"

    write_report(result, report)

    with pd.ExcelFile(report) as book:
        only_excel = pd.read_excel(book, sheet_name=ONLY_EXCEL_SHEET)
        only_pdf = pd.read_excel(book, sheet_name=ONLY_PDF_SHEET)

    assert only_excel.empty
    assert only_pdf.empty
