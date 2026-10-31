from decimal import Decimal

import pytest

from compare.normalize import (
    format_value,
    is_empty,
    normalize_header,
    normalize_text,
    numbers_equal,
    parse_number,
)


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        (None, True),
        ("", True),
        ("   ", True),
        ("0", False),
        (0, False),
        (float("nan"), True),
    ],
)
def test_is_empty(value, expected):
    assert is_empty(value) is expected


def test_normalize_text_collapses_spaces_case_and_yo():
    assert normalize_text("  Стена\u00a0из  газобетона Ё ") == "стена из газобетона е"


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("1 234,56", Decimal("1234.56")),
        ("1\u00a0234,5", Decimal("1234.5")),
        ("1,234", Decimal("1.234")),
        ("1.234,56", Decimal("1234.56")),
        ("(1 000)", Decimal("-1000")),
        ("−12,5", Decimal("-12.5")),
        (100, Decimal("100")),
        (12.5, Decimal("12.5")),
    ],
)
def test_parse_number(value, expected):
    assert parse_number(value) == expected


@pytest.mark.parametrize("value", ["12 шт", "12%", "нет данных", "1.2.3-", None, True])
def test_parse_number_rejects_non_numbers(value):
    assert parse_number(value) is None


def test_numbers_equal_uses_absolute_tolerance():
    assert numbers_equal(
        Decimal("1.0"),
        Decimal("1.0000000001"),
        Decimal("1e-9"),
        Decimal("0"),
    )


def test_numbers_equal_uses_relative_tolerance():
    assert numbers_equal(
        Decimal("1000000"),
        Decimal("1000000.5"),
        Decimal("1e-9"),
        Decimal("1e-6"),
    )


def test_numbers_not_equal_outside_tolerance():
    assert not numbers_equal(
        Decimal("1"),
        Decimal("1.1"),
        Decimal("1e-9"),
        Decimal("1e-6"),
    )


def test_normalize_header_removes_punctuation():
    assert normalize_header(" № поз. ") == "поз"
    assert normalize_header("Наименование, ед.") == "наименование ед"


def test_format_value_handles_lists_and_decimals():
    assert format_value([1, None, "a"]) == "1 |  | a"
    assert format_value(Decimal("1.2300")) == "1.2300"
