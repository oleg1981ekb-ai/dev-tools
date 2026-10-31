import pytest

from compare.pdf_reader import extract_from_pages


class FakePage:
    def __init__(self, table, fallback_only=False):
        self.table = table
        self.fallback_only = fallback_only

    def extract_table(self, table_settings=None):
        if self.fallback_only and table_settings is None:
            return None
        return self.table


def test_skips_repeated_header_and_joins_pages():
    pages = [
        FakePage([["A", "B"], ["1", "2"], ["3", "4"]]),
        FakePage([["A", "B"], ["5", "6"]]),
    ]
    headers, rows = extract_from_pages(pages)
    assert headers == ["A", "B"]
    assert rows == [["1", "2"], ["3", "4"], ["5", "6"]]


def test_missing_table_produces_warning():
    warnings = []
    pages = [FakePage(None)]
    with pytest.raises(ValueError):
        extract_from_pages(pages, warnings)
    assert "Страница 1: таблица не найдена." in warnings


def test_empty_rows_are_skipped():
    pages = [FakePage([["A", "B"], ["", ""], ["1", "2"]])]
    _, rows = extract_from_pages(pages)
    assert rows == [["1", "2"]]


def test_ragged_rows_are_padded_and_headers_extended():
    warnings = []
    pages = [
        FakePage(
            [
                ["A", "B"],
                ["1", "2", "3"],
                ["4"],
            ]
        )
    ]
    headers, rows = extract_from_pages(pages, warnings)
    assert headers == ["A", "B", "Колонка 3"]
    assert rows == [["1", "2", "3"], ["4", None, None]]
    assert any("Таблица шире шапки" in warning for warning in warnings)


def test_text_settings_fallback_is_used():
    pages = [FakePage([["A"], ["1"]], fallback_only=True)]
    headers, rows = extract_from_pages(pages)
    assert headers == ["A"]
    assert rows == [["1"]]


def test_header_only_pdf_is_rejected():
    pages = [FakePage([["A", "B"]])]
    with pytest.raises(ValueError, match="только шапка"):
        extract_from_pages(pages)


def test_header_like_row_after_empty_page_is_dropped():
    pages = [
        FakePage([["A", "B"], ["1", "2"]]),
        FakePage(None),
        FakePage([["A", "B"], ["3", "4"]]),
    ]
    warnings = []
    headers, rows = extract_from_pages(pages, warnings)
    assert headers == ["A", "B"]
    assert rows == [["1", "2"], ["3", "4"]]
    assert any("Страница 2" in warning for warning in warnings)
