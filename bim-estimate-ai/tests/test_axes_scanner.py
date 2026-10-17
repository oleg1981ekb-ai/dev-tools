"""Тесты Фазы 0 v2: сканер осей (ряды чисел + кружки)."""
from dataclasses import dataclass

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "case_01_block_takeoff"))

from axes_scanner import (
    Axis,
    _axis_groups,
    _match_circled,
    detect_axes,
    find_circled_axes,
    find_number_columns,
    find_number_rows,
)


# ---------------------------------------------------------------------------
# _axis_groups — группировка чисел в ряды осей
# ---------------------------------------------------------------------------

def test_axis_groups_basic_row():
    """5 чисел в одной линии, монотонно растут → это ряд осей."""
    nums = [(100, 100, 1), (200, 100, 2), (300, 100, 3), (400, 100, 4), (500, 100, 5)]
    rows = _axis_groups(nums, axis="x", min_count=5, tol=12.0)
    assert len(rows) == 1
    y, pairs = rows[0]
    assert y == 100.0
    assert [v for _, v in pairs] == [1, 2, 3, 4, 5]


def test_axis_groups_rejects_non_monotonic():
    """Значения не растут монотонно → не ряд осей."""
    nums = [(100, 100, 5), (200, 100, 3), (300, 100, 4), (400, 100, 2), (500, 100, 1)]
    rows = _axis_groups(nums, axis="x", min_count=5, tol=12.0)
    assert rows == []


def test_axis_groups_rejects_too_few():
    """Менее 5 чисел → не ряд осей."""
    nums = [(100, 100, 1), (200, 100, 2), (300, 100, 3)]
    rows = _axis_groups(nums, axis="x", min_count=5, tol=12.0)
    assert rows == []


def test_axis_groups_rejects_big_values():
    """Значения > 40 (размеры, а не номера осей) → не ряд осей."""
    nums = [(100, 100, 100), (200, 100, 200), (300, 100, 300), (400, 100, 400), (500, 100, 500)]
    rows = _axis_groups(nums, axis="x", min_count=5, tol=12.0)
    assert rows == []


def test_axis_groups_tolerates_some_non_monotonic():
    """Допускаем до 20% нарушений монотонности (посторонние числа в линии)."""
    # 6 чисел, 5 пар, 1 немонотонная (2 > 0) → 4/5 = 0.8 >= 0.8 → проходит
    nums = [(100, 100, 1), (200, 100, 2), (300, 100, 0), (400, 100, 4),
            (500, 100, 5), (600, 100, 6)]
    rows = _axis_groups(nums, axis="x", min_count=5, tol=12.0)
    assert len(rows) == 1


def test_axis_groups_rejects_too_many_non_monotonic():
    """Более 20% нарушений монотонности → не ряд осей."""
    # 5 чисел, 4 пары, 2 немонотонные → 2/4 = 0.5 < 0.8 → не проходит
    nums = [(100, 100, 1), (200, 100, 99), (300, 100, 2), (400, 100, 98), (500, 100, 3)]
    rows = _axis_groups(nums, axis="x", min_count=5, tol=12.0)
    assert rows == []


# ---------------------------------------------------------------------------
# find_number_rows / find_number_columns — с моковыми словами
# ---------------------------------------------------------------------------

def test_find_number_rows():
    nums_as_words = [
        (100, 100, "1"), (200, 100, "2"), (300, 100, "3"),
        (400, 100, "4"), (500, 100, "5"),
    ]
    rows = find_number_rows(nums_as_words)
    assert len(rows) == 1
    y, pairs = rows[0]
    assert y == 100.0
    assert [v for _, v in pairs] == [1, 2, 3, 4, 5]


def test_find_number_columns():
    nums_as_words = [
        (100, 100, "1"), (100, 200, "2"), (100, 300, "3"),
        (100, 400, "4"), (100, 500, "5"),
    ]
    cols = find_number_columns(nums_as_words)
    assert len(cols) == 1
    x, pairs = cols[0]
    assert x == 100.0
    assert [v for _, v in pairs] == [1, 2, 3, 4, 5]


# ---------------------------------------------------------------------------
# detect_axes — объединение рядов и кружков
# ---------------------------------------------------------------------------

@dataclass
class _FakeRect:
    x0: float
    y0: float
    x1: float
    y1: float

    @property
    def width(self):
        return self.x1 - self.x0

    @property
    def height(self):
        return self.y1 - self.y0


@dataclass
class _FakeDrawing:
    rect: _FakeRect
    type: str = "s"
    items: list = None

    def __post_init__(self):
        if self.items is None:
            self.items = []

    def __getitem__(self, key):
        return {"rect": self.rect, "type": self.type, "items": self.items}[key]


class _FakePage:
    """Имитация страницы PyMuPDF с векторными кружками осей."""

    def __init__(self, circles):
        self._circles = circles  # [(x0, y0, x1, y1), ...]

    def get_drawings(self):
        return [
            _FakeDrawing(_FakeRect(*c)) for c in self._circles
        ]


def test_detect_axes_row_only():
    """Ось только в ряде чисел, без кружка → source='row', confidence='medium'."""
    words = [
        (100, 100, "1"), (200, 100, "2"), (300, 100, "3"),
        (400, 100, "4"), (500, 100, "5"),
    ]
    page = _FakePage([])  # нет кружков
    axes = detect_axes(page, words)
    axis1 = [a for a in axes if a.value == 1]
    assert len(axis1) == 1
    assert axis1[0].source == "row"
    assert axis1[0].confidence == "medium"
    assert axis1[0].axis == "x"


def test_detect_axes_both():
    """Оси и в ряде, и в кружках → source='both', confidence='high'.
    find_circled_axes требует минимум 5 кружков в ряду, поэтому создаём 5."""
    words = [
        (100, 100, "1"), (200, 100, "2"), (300, 100, "3"),
        (400, 100, "4"), (500, 100, "5"),
    ]
    # Кружки вокруг всех 5 цифр (центры 100..500, диаметр 28)
    circles = [
        (86, 86, 114, 114),   # ось 1
        (186, 86, 214, 114),  # ось 2
        (286, 86, 314, 114),  # ось 3
        (386, 86, 414, 114),  # ось 4
        (486, 86, 514, 114),  # ось 5
    ]
    page = _FakePage(circles)
    axes = detect_axes(page, words)
    assert len(axes) == 5
    for a in axes:
        assert a.source == "both"
        assert a.confidence == "high"


def test_detect_axes_circle_only_empty():
    """Без данных — пустой результат."""
    page = _FakePage([])
    axes = detect_axes(page, [])
    assert axes == []


def test_detect_axes_mixed():
    """Смешанный сценарий: ось 1 — только ряд, оси 2-6 — ряд + круг.
    Нужно 6 осей в ряду и 5 кружков (find_circled_axes требует >= 5 кружков)."""
    words = [
        (100, 100, "1"), (200, 100, "2"), (300, 100, "3"),
        (400, 100, "4"), (500, 100, "5"), (600, 100, "6"),
    ]
    # Кружки вокруг 2,3,4,5,6 (ось 1 без кружка — как на реальном чертеже)
    circles = [
        (186, 86, 214, 114),  # ось 2
        (286, 86, 314, 114),  # ось 3
        (386, 86, 414, 114),  # ось 4
        (486, 86, 514, 114),  # ось 5
        (586, 86, 614, 114),  # ось 6
    ]
    page = _FakePage(circles)
    axes = detect_axes(page, words)

    by_value = {a.value: a for a in axes}
    assert by_value[1].source == "row"
    assert by_value[1].confidence == "medium"
    for v in (2, 3, 4, 5, 6):
        assert by_value[v].source == "both"
        assert by_value[v].confidence == "high"
    assert len(axes) == 6


# ---------------------------------------------------------------------------
# _match_circled — поиск кружка по значению и координатам
# ---------------------------------------------------------------------------

def test_match_circled_found():
    cx, cy, v = 300.0, 100.0, 3
    # find_circled_axes возвращает (cx, cy, value, d)
    circled_axes = [(300, 100, 3, 28), (500, 100, 5, 28)]
    idx = _match_circled(cx, cy, v, circled_axes, tol=3.0)
    assert idx == 0


def test_match_circled_tolerance():
    """Кружок чуть смещён относительно цифры, но внутри tol → найден."""
    circled_axes = [(302, 102, 3, 28)]
    idx = _match_circled(300, 100, 3, circled_axes, tol=5.0)
    assert idx == 0


def test_match_circled_outside_tolerance():
    """Кружок вне tol → не найден."""
    circled_axes = [(310, 110, 3, 28)]
    idx = _match_circled(300, 100, 3, circled_axes, tol=3.0)
    assert idx is None


def test_match_circled_wrong_value():
    """Точные координаты, но другое значение оси → не найден."""
    circled_axes = [(300, 100, 5, 28)]
    idx = _match_circled(300, 100, 3, circled_axes, tol=3.0)
    assert idx is None


def test_match_circled_empty():
    idx = _match_circled(300, 100, 3, [], tol=3.0)
    assert idx is None