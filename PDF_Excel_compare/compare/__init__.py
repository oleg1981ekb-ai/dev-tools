"""Сравнение таблиц из Excel и PDF."""

from .models import (
    ColumnPair,
    ComparisonResult,
    Difference,
    DifferenceType,
    TableData,
)

__all__ = [
    "ColumnPair",
    "ComparisonResult",
    "Difference",
    "DifferenceType",
    "TableData",
]
