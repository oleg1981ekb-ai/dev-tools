"""Определение шапки таблицы и служебных строк."""

from __future__ import annotations

from difflib import SequenceMatcher
from typing import Any, Sequence

from .normalize import is_empty, normalize_header, normalize_text

HEADER_MARKERS = (
    "№ п/п",
    "наименование",
    "единица измерения",
    "количество",
    "сметная стоимость",
)
HEADER_SCAN_ROWS = 100
HEADER_MAX_ROWS = 12
SIGNATURE_MARKERS = ("сдал", "принял", "наблюдатель")


def cell_text(value: Any) -> str:
    """Текст ячейки с нормализованными пробелами."""
    if is_empty(value):
        return ""
    text = (
        str(value)
        .replace("\u00a0", " ")
        .replace("\u202f", " ")
        .replace("\u2009", " ")
    )
    return " ".join(text.split())


def find_header_top(rows: Sequence[Sequence[Any]]) -> int | None:
    """Ищет первую строку шапки по набору характерных заголовков."""
    markers = [normalize_text(marker) for marker in HEADER_MARKERS]
    for index, row in enumerate(rows[:HEADER_SCAN_ROWS]):
        text = normalize_text(" ".join(cell_text(value) for value in row))
        hits = sum(1 for marker in markers if marker in text)
        if hits >= 3:
            return index
    return None


def find_column_number_row(
    rows: Sequence[Sequence[Any]],
    top: int,
) -> int | None:
    """Ищет строку нумерации колонок (1, 2, 3, ...)."""
    last = min(len(rows), top + HEADER_MAX_ROWS)
    for index in range(top + 1, last):
        values = [cell_text(value) for value in rows[index]]
        non_empty = [value for value in values if value]
        if len(non_empty) < 3:
            continue

        numbers: list[int] = []
        for value in non_empty:
            try:
                numbers.append(int(value))
            except ValueError:
                continue

        expected = list(range(1, len(numbers) + 1))
        if len(numbers) >= 3 and numbers == expected:
            if len(numbers) / len(non_empty) >= 0.8:
                return index
    return None


def combine_header_values(values: Sequence[Any]) -> str:
    """Склеивает многострочный заголовок колонки без повторов."""
    parts: list[str] = []
    for value in values:
        text = cell_text(value)
        if not text:
            continue
        if not parts or normalize_header(parts[-1]) != normalize_header(text):
            parts.append(text)
    return " / ".join(parts)


def build_headers(
    header_rows: Sequence[Sequence[Any]],
    width: int,
) -> list[str]:
    """Строит заголовки колонок из нескольких строк шапки."""
    return [
        combine_header_values(
            [
                row[column] if column < len(row) else None
                for row in header_rows
            ]
        )
        for column in range(width)
    ]


def _segments(value: Any) -> list[str]:
    text = normalize_text(value)
    return [
        normalize_header(part)
        for part in text.split("/")
        if len(normalize_header(part)) >= 3
    ]


def header_match_score(left: Any, right: Any) -> float:
    """Оценка похожести заголовков с учётом составных частей через «/»."""
    left_key = normalize_header(left)
    right_key = normalize_header(right)
    if not left_key or not right_key:
        return 0.0
    if left_key == right_key:
        return 1.0

    left_segments = _segments(left)
    right_segments = _segments(right)
    if left_segments and right_segments:
        left_set = set(left_segments)
        right_set = set(right_segments)
        if left_set <= right_set or right_set <= left_set:
            return 0.92

        common = left_set & right_set
        if common:
            longest = max(common, key=len)
            if len(longest) >= 3:
                left_len = sum(len(item) for item in left_set)
                right_len = sum(len(item) for item in right_set)
                coverage = sum(len(item) for item in common) / max(
                    left_len, right_len, 1
                )
                return min(0.9, 0.55 + 0.4 * coverage)

        return max(
            SequenceMatcher(None, left_item, right_item).ratio()
            for left_item in left_segments
            for right_item in right_segments
        )

    return SequenceMatcher(None, left_key, right_key).ratio()


def is_signature_row(row: Sequence[Any]) -> bool:
    """Похожа ли строка на строку подписей."""
    values = [cell_text(value) for value in row]
    non_empty = [value for value in values if value]
    if not non_empty or len(non_empty) > 4:
        return False
    first = normalize_text(non_empty[0])
    return any(first.startswith(marker) for marker in SIGNATURE_MARKERS)


def trim_signature_rows(
    rows: Sequence[Sequence[Any]],
    warnings: list[str] | None = None,
) -> tuple[list[list[Any]], int]:
    """Отбрасывает строки подписей и всё, что ниже них."""
    if warnings is None:
        warnings = []

    for index, row in enumerate(rows):
        if is_signature_row(row):
            trimmed = len(rows) - index
            warnings.append(f"Строки подписей отброшены: {trimmed}.")
            return [list(item) for item in rows[:index]], trimmed
    return [list(item) for item in rows], 0
