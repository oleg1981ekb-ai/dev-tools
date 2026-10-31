"""Модели данных для чтения и сравнения таблиц."""

from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal
from enum import Enum
from typing import Any


class DifferenceType(str, Enum):
    """Тип расхождения."""

    NUMBER = "number"
    TEXT = "text"
    EMPTY_VS_VALUE = "empty_vs_value"
    MISSING_COLUMN = "missing_column"
    MISSING_ROW = "missing_row"


@dataclass(frozen=True)
class TableData:
    """Таблица, прочитанная из источника."""

    source: str
    headers: list[str]
    rows: list[list[Any]]
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def width(self) -> int:
        return len(self.headers)

    @property
    def height(self) -> int:
        return len(self.rows)


@dataclass(frozen=True)
class ColumnPair:
    """Сопоставленная пара колонок Excel и PDF."""

    excel_index: int
    pdf_index: int
    excel_name: str
    pdf_name: str
    method: str
    score: float = 1.0


@dataclass(frozen=True)
class Difference:
    """Одно расхождение между таблицами."""

    type: DifferenceType
    row_excel: int | None = None
    row_pdf: int | None = None
    column_excel: int | None = None
    column_pdf: int | None = None
    column_name_excel: str | None = None
    column_name_pdf: str | None = None
    value_excel: Any = None
    value_pdf: Any = None
    comment: str = ""


@dataclass
class ComparisonResult:
    """Результат сравнения двух таблиц."""

    excel: TableData
    pdf: TableData
    differences: list[Difference]
    column_pairs: list[ColumnPair]
    unmatched_excel_columns: list[int]
    unmatched_pdf_columns: list[int]
    warnings: list[str]
    abs_tolerance: Decimal
    rel_tolerance: Decimal

    @property
    def has_differences(self) -> bool:
        return bool(self.differences)

    def count_by_type(self) -> dict[DifferenceType, int]:
        counts = {difference_type: 0 for difference_type in DifferenceType}
        for difference in self.differences:
            counts[difference.type] += 1
        return counts
