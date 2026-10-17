"""Юнит-тесты чистых функций extract_walls.

Запуск: cd bim-estimate-ai && python -m pytest tests/ -v
"""
import pytest

from extract_walls import (
    DEFAULT_HEIGHT,
    THICKNESS,
    WASTE_FACTOR,
    parse_height,
    collect_sizes,
    split_by_type,
    calc_volumes,
    build_report,
)


# ========================= parse_height =========================

@pytest.mark.parametrize("user_input,expected", [
    ("", DEFAULT_HEIGHT),        # пустой ввод → дефолт
    ("2.8", 2.8),                # точка
    ("2,8", 2.8),                # запятая (локаль)
    ("  3.3  ", 3.3),            # пробелы по краям
    ("3,3", 3.3),
    ("0", 0.0),                  # ноль — допустимое число
    ("2.80", 2.8),
    ("abc", DEFAULT_HEIGHT),     # мусор → дефолт
    ("2,8м", DEFAULT_HEIGHT),    # число с мусором → дефолт
    ("--2.8", DEFAULT_HEIGHT),
])
def test_parse_height(user_input, expected):
    assert parse_height(user_input) == expected


def test_parse_height_custom_default():
    assert parse_height("не число", default=3.0) == 3.0


# ========================= collect_sizes =========================

def test_collect_sizes_extracts_known_values():
    text = "5400 600 6400 3200 1160 ДШ-1 ±0.000"
    assert collect_sizes(text) == [5400.0, 600.0, 6400.0, 3200.0, 1160.0]


def test_collect_sizes_ignores_unknown_numbers():
    # 1100 и 125 отсутствуют в белом списке → не извлекаются
    assert collect_sizes("1100 125") == []


def test_collect_sizes_empty_text():
    assert collect_sizes("") == []


def test_collect_sizes_word_boundaries():
    # \b защита: 6000 не должно дать 600; 4600 — не 600
    assert collect_sizes("6000 4600") == []


# ========================= split_by_type =========================

def test_split_by_type_basic_rules():
    sizes = [600, 2999, 3000, 4999, 5000, 7200]
    t1, t2 = split_by_type(sizes)
    assert t1 == [0.6, 2.999, 3.0, 4.999]   # 600..4999 → Тип 1
    assert t2 == [5.0, 7.2]                 # >=5000 → Тип 2


def test_split_by_type_skips_building_dimensions():
    # 38600 и 39500 — габариты здания, не суммируются
    t1, t2 = split_by_type([38600, 39500])
    assert t1 == [] and t2 == []


def test_split_by_type_deduplicates():
    # Повторяющиеся размеры считаются один раз (поведение set)
    t1, t2 = split_by_type([600, 600, 600, 6400, 6400])
    assert t1 == [0.6]
    assert t2 == [6.4]


def test_split_by_type_ignores_below_min():
    t1, t2 = split_by_type([125, 75, 599])
    assert t1 == [] and t2 == []


def test_split_by_type_returns_meters():
    t1, t2 = split_by_type([600, 5100])
    assert t1 == [0.6]   # мм → м
    assert t2 == [5.1]


# ========================= calc_volumes =========================

def test_calc_volumes_reference_from_csv():
    # Эталон из estimated_materials.csv при высоте 3.4:
    # Тип 1: длина 38.06 → 25.88 / 27.17; Тип 2: длина 49.90 → 33.93 / 35.63
    assert [round(x, 2) for x in calc_volumes(38.06, height=3.4)] == [25.88, 27.17]
    assert [round(x, 2) for x in calc_volumes(49.90, height=3.4)] == [33.93, 35.63]


def test_calc_volumes_formula():
    pure, with_waste = calc_volumes(10.0, height=2.8)
    assert pure == pytest.approx(10.0 * THICKNESS * 2.8)          # 5.6
    assert with_waste == pytest.approx(5.6 * WASTE_FACTOR)        # 5.88


def test_calc_volumes_zero_length():
    pure, with_waste = calc_volumes(0.0)
    assert pure == 0.0 and with_waste == 0.0


def test_calc_volumes_custom_thickness():
    pure, _ = calc_volumes(10.0, thickness=0.3, height=3.0)
    assert pure == pytest.approx(9.0)


# ========================= build_report =========================

def test_build_report_all_values():
    rows = build_report([0.6, 37.4], [49.9], height=3.4)
    t1, t2 = rows

    assert t1["Konstrukciya"] == "Narus_Stena_Tip_1"
    assert t1["Kolichestvo_razmerov"] == 2
    assert t1["Dlina_m"] == 38.0
    assert t1["Ploshad_m2"] == round(38.0 * 3.4, 2)              # 129.2
    assert t1["Tolshina_m"] == THICKNESS
    assert t1["Volume_m3"] == round(38.0 * THICKNESS * 3.4, 2)
    assert t1["Waste_factor"] == WASTE_FACTOR
    # строгая связка: чистый + запас = с запасом
    assert round(t1["Volume_m3"] + t1["Zapas_m3"], 2) == t1["Volume_with_waste_m3"]

    assert t2["Konstrukciya"] == "Narus_Stena_Tip_2"
    assert t2["Dlina_m"] == 49.9


def test_build_report_reference_from_csv():
    """Эталон: значения CSV (38.06 / 49.90 м при высоте 3.4) сохраняются."""
    rows = build_report([38.06], [49.90], height=3.4)
    t1, t2 = rows
    assert t1["Dlina_m"] == 38.06 and t2["Dlina_m"] == 49.90
    assert t1["Volume_with_waste_m3"] == round(38.06 * 0.2 * 3.4 * 1.05, 2)   # 27.17
    assert t2["Volume_with_waste_m3"] == round(49.90 * 0.2 * 3.4 * 1.05, 2)   # 35.63


def test_build_report_empty_types():
    rows = build_report([], [], height=2.8)
    for row in rows:
        assert row["Dlina_m"] == 0.0
        assert row["Ploshad_m2"] == 0.0
        assert row["Volume_m3"] == 0.0
        assert row["Volume_with_waste_m3"] == 0.0
        assert row["Kolichestvo_razmerov"] == 0


def test_build_report_custom_params():
    rows = build_report([10.0], [], height=3.0, thickness=0.3, waste_factor=1.10)
    t1 = rows[0]
    assert t1["Volume_m3"] == 9.0            # 10 × 0.3 × 3.0
    assert t1["Volume_with_waste_m3"] == 9.9  # +10%
    assert t1["Zapas_m3"] == 0.9


# ========================= Регрессия на реальном чертеже =========================

def test_full_pipeline_on_real_extracted_text():
    """Смоук-тест: реальный текстовый слой чертежа → эталонные значения из CSV."""
    import os
    txt_path = os.path.join(os.path.dirname(__file__), "..",
                            "case_01_block_takeoff", "raw_extracted_text.txt")
    if not os.path.exists(txt_path):
        pytest.skip("raw_extracted_text.txt отсутствует (не в git — см. .gitignore)")

    text = open(txt_path, encoding="utf-8").read()
    t1, t2 = split_by_type(collect_sizes(text))

    assert round(sum(t1), 2) == 38.06
    assert round(sum(t2), 2) == 49.90
    assert [round(x, 2) for x in calc_volumes(sum(t1), height=3.4)] == [25.88, 27.17]
    assert [round(x, 2) for x in calc_volumes(sum(t2), height=3.4)] == [33.93, 35.63]
