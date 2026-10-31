"""Нормализация значений перед сравнением.

Числа сравниваются через Decimal с настраиваемым допуском, текст — после
приведения пробелов, регистра и буквы «ё» к единому виду.
"""

from __future__ import annotations

import math
import re
from decimal import Decimal, InvalidOperation
from typing import Any

_SPACE_RE = re.compile(r"\s+")
_HEADER_RE = re.compile(r"[^\w]+", re.UNICODE)
_NUMBER_RE = re.compile(r"^[+-]?\d[\d.,]*$|^[+-]?[.,]\d+$")

_MINUS_TRANSLATION = str.maketrans({"−": "-", "–": "-", "—": "-"})
_SPACE_TRANSLATION = str.maketrans(
    {
        "\u00a0": " ",
        "\u202f": " ",
        "\u2009": " ",
        "\u2007": " ",
    }
)


def is_empty(value: Any) -> bool:
    """Пустое ли значение (None, NaN, строка из пробелов)."""
    if value is None:
        return True
    if isinstance(value, float) and math.isnan(value):
        return True
    if isinstance(value, str):
        return not value.strip()
    try:
        return bool(value != value)
    except (TypeError, ValueError):
        return False


def normalize_text(value: Any) -> str:
    """Нормализованное текстовое представление для сравнения."""
    if is_empty(value):
        return ""
    text = str(value).translate(_SPACE_TRANSLATION).translate(_MINUS_TRANSLATION)
    text = text.replace("ё", "е").replace("Ё", "Е")
    text = _SPACE_RE.sub(" ", text).strip()
    return text.casefold()


def normalize_header(value: Any) -> str:
    """Ключ для сопоставления заголовков колонок."""
    text = normalize_text(value)
    text = _HEADER_RE.sub(" ", text)
    return _SPACE_RE.sub(" ", text).strip()


def _normalize_separators(text: str) -> str:
    """Приводит запятые и точки к десятичной точке."""
    has_comma = "," in text
    has_dot = "." in text

    if has_comma and has_dot:
        if text.rfind(",") > text.rfind("."):
            return text.replace(".", "").replace(",", ".")
        return text.replace(",", "")

    if has_comma:
        parts = text.split(",")
        if len(parts) == 2:
            return f"{parts[0]}.{parts[1]}"
        return text.replace(",", "")

    if has_dot and text.count(".") > 1:
        return text.replace(".", "")

    return text


def parse_number(value: Any) -> Decimal | None:
    """Разбирает число с учётом русской локали и скобок для отрицательных.

    Возвращает None, если значение не является числом целиком (например,
    «12 шт» или «12%»).
    """
    if is_empty(value) or isinstance(value, bool):
        return None

    if isinstance(value, int):
        return Decimal(value)
    if isinstance(value, Decimal):
        return None if value.is_nan() else value
    if isinstance(value, float):
        if math.isnan(value) or math.isinf(value):
            return None
        return Decimal(str(value))

    text = str(value).translate(_SPACE_TRANSLATION).translate(_MINUS_TRANSLATION)
    text = text.strip().replace(" ", "")

    negative = False
    if text.startswith("(") and text.endswith(")"):
        negative = True
        text = text[1:-1].strip()

    if not text or not _NUMBER_RE.fullmatch(text):
        return None

    text = _normalize_separators(text)
    try:
        number = Decimal(text)
    except InvalidOperation:
        return None

    return -number if negative else number


def numbers_equal(
    left: Decimal,
    right: Decimal,
    abs_tolerance: Decimal,
    rel_tolerance: Decimal,
) -> bool:
    """Сравнивает числа с абсолютным и относительным допуском."""
    difference = abs(left - right)
    if difference <= abs_tolerance:
        return True
    scale = max(abs(left), abs(right))
    return difference <= rel_tolerance * scale


def format_value(value: Any) -> str:
    """Представление значения для отчёта."""
    if is_empty(value):
        return ""
    if isinstance(value, (list, tuple)):
        return " | ".join(format_value(item) for item in value)
    if isinstance(value, Decimal):
        return format(value, "f")
    return str(value)
