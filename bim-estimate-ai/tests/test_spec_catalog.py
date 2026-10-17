"""Тесты каталога экспликации (spec_catalog): парсинг по разделам, выбор, маркеры."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "case_01_block_takeoff"))

from spec_catalog import (
    parse_spec_catalog,
    parse_selection,
    count_markers,
    markers_by_catalog_id,
)
from extract_walls import parse_cli_args, build_report

SPEC_SAMPLE = """
Наружная стена Тип 1:
- Газосиликатные блоки толщиной 200мм ГОСТ 31359-2007
Наружная стена Тип 2:
- монолитный железобетон 200 мм
- газосиликатные блоки толщиной 200мм
Перегородки:
- Тип 1. перегородка ГКЛ толщиной 125 мм
- Тип 2. перегородка комбинированная ГКЛ/ГКЛВ толщиной 125 мм
- Тип 4. стандартная зашивка ГКЛ толщиной 75 мм;
"""


def test_sections_do_not_mix():
    items = parse_spec_catalog(SPEC_SAMPLE)
    ids = {it["id"] for it in items}
    # Тип 1 — один слой (газоблок), остаётся одной позицией
    assert "Наружная стена|Тип 1" in ids
    # Тип 2 — два слоя (монолит + газоблок), разбивается на позиции-слои
    assert "Наружная стена|Тип 2|слой 1" in ids  # монолит
    assert "Наружная стена|Тип 2|слой 2" in ids  # газоблок
    assert "Перегородка|Тип 1" in ids
    assert "Перегородка|Тип 2" in ids
    assert "Перегородка|Тип 4" in ids
    # 1 (Тип1) + 2 (Тип2 слои) + 3 (перегородки) = 6 позиций
    assert len(items) == 6


def test_multiline_description_joins_thickness():
    # описание Типа 2 наружных стен идёт на 2 строках — толщина 200 должна найтись
    items = {it["id"]: it for it in parse_spec_catalog(SPEC_SAMPLE)}
    # Тип 2 разбился на слои: слой 1 — монолит (без толщины), слой 2 — газоблок 200 мм
    t2_gas = items["Наружная стена|Тип 2|слой 2"]
    assert t2_gas["thickness_mm"] == 200
    assert t2_gas["countable"] is True
    assert items["Перегородка|Тип 1"]["thickness_mm"] == 125
    assert items["Перегородка|Тип 4"]["thickness_mm"] == 75


def test_material_extraction():
    items = {it["id"]: it for it in parse_spec_catalog(SPEC_SAMPLE)}
    assert "ГКЛ" in items["Перегородка|Тип 1"]["material"]
    assert "зашивка" in items["Перегородка|Тип 4"]["material"].lower()


def test_multilayer_wall_material_from_structural_layer():
    # в многослойной стене материал берётся из слоя с несущей толщиной,
    # а не из первого пункта (фасад/утеплитель)
    sample = (
        "Наружная стена Тип 1:\n"
        "- Стальные композитные панели на навесной фасадной системе\n"
        "- Утеплитель минераловатные плиты - 80мм\n"
        "- Газосиликатные блоки толщиной 200мм ГОСТ 31359-2007\n"
    )
    items = {it["id"]: it for it in parse_spec_catalog(sample)}
    # 3 слоя → 3 отдельные позиции
    assert "Наружная стена|Тип 1|слой 1" in items  # фасад
    assert "Наружная стена|Тип 1|слой 2" in items  # утеплитель
    assert "Наружная стена|Тип 1|слой 3" in items  # газоблок

    facade = items["Наружная стена|Тип 1|слой 1"]
    assert "композитные" in facade["material"]
    assert facade["thickness_mm"] is None
    assert facade["countable"] is False

    insulation = items["Наружная стена|Тип 1|слой 2"]
    assert "Утеплитель" in insulation["material"]
    assert insulation["thickness_mm"] == 80
    assert insulation["countable"] is False

    gas = items["Наружная стена|Тип 1|слой 3"]
    assert "Газосиликатные блоки" in gas["material"]
    assert gas["thickness_mm"] == 200
    assert gas["countable"] is True


def test_same_thickness_layers_joined():
    # монолит 200 + газоблок 200 → в материал идёт только газоблок:
    # толщину монолита не учитываем никогда (см. КР), объём — только по АР-слоям
    sample = (
        "Наружная стена Тип 2:\n"
        "- монолитный железобетон 200 мм\n"
        "- газосиликатные блоки толщиной 200мм\n"
    )
    items = {it["id"]: it for it in parse_spec_catalog(sample)}
    # 2 слоя → 2 отдельные позиции
    assert "Наружная стена|Тип 2|слой 1" in items  # монолит
    assert "Наружная стена|Тип 2|слой 2" in items  # газоблок

    mono = items["Наружная стена|Тип 2|слой 1"]
    assert "монолит" in mono["material"].lower()
    assert mono["thickness_mm"] is None
    assert mono["countable"] is False

    gas = items["Наружная стена|Тип 2|слой 2"]
    assert "газосиликатные блоки" in gas["material"]
    assert gas["thickness_mm"] == 200
    assert gas["countable"] is True


def test_duplicates_collapse():
    items = parse_spec_catalog(SPEC_SAMPLE + "\n- Тип 1. перегородка ГКЛ толщиной 125 мм\n")
    assert len([i for i in items if i["id"] == "Перегородка|Тип 1"]) == 1


def test_outside_sections_ignored():
    items = parse_spec_catalog("Мусор Тип 9. что-то 100 мм\n" + SPEC_SAMPLE)
    assert not any(it["type_no"] == 9 for it in items)


def test_selection_all_variants():
    assert parse_selection("все", 5) == [0, 1, 2, 3, 4]
    assert parse_selection("", 5) == [0, 1, 2, 3, 4]
    assert parse_selection("all", 5) == [0, 1, 2, 3, 4]


def test_selection_numbers():
    assert parse_selection("3,5", 7) == [2, 4]
    assert parse_selection("1", 7) == [0]
    assert parse_selection("2;4", 7) == [1, 3]


def test_selection_garbage_ignored():
    assert parse_selection("0,99,abc,2", 5) == [1]
    assert parse_selection("3,3,3", 5) == [2]


def test_count_markers_pairs_tip_with_number():
    words = [(100, 100, "Тип"), (130, 102, "3"),
             (200, 200, "Тип"), (220, 205, "3"),
             (300, 300, "Тип"),  # без числа рядом — не считается
             (500, 500, "6400")]  # размер — не маркер
    assert count_markers(words) == {3: 2}


def test_markers_ambiguous_type_splits_with_mark():
    items = [{"id": "Наружная стена|Тип 2", "type_no": 2, "countable": True},
             {"id": "Перегородка|Тип 2", "type_no": 2, "countable": True},
             {"id": "Перегородка|Тип 3", "type_no": 3, "countable": True}]
    out = markers_by_catalog_id(items, {2: 6, 3: 8})
    assert out["Перегородка|Тип 3"] == 8
    assert out["Наружная стена|Тип 2"].endswith("?")
    assert out["Перегородка|Тип 2"].endswith("?")


def test_cli_args_types_and_height():
    types_raw, height_raw, all_flag = parse_cli_args(["--types", "3,5", "--height", "3,4"])
    assert types_raw == "3,5"
    assert height_raw == "3,4"
    assert all_flag is False


def test_cli_args_equals_form_and_all():
    types_raw, height_raw, all_flag = parse_cli_args(["--types=1,2", "--all"])
    assert types_raw == "1,2"
    assert height_raw is None
    assert all_flag is True


def test_cli_args_empty_is_interactive():
    assert parse_cli_args([]) == (None, None, False)


def test_build_report_stores_chosen_labels():
    rows = build_report([10.0], [20.0], 2.8, chosen_labels=["Перегородка Тип 4"])
    assert rows[0]["Vybrano_dlya_rascheta"] == "Перегородка Тип 4"
    assert rows[1]["Vybrano_dlya_rascheta"] == "Перегородка Тип 4"


def test_build_report_no_labels_keeps_backcompat():
    rows = build_report([10.0], [], 2.8)
    assert rows[0]["Vybrano_dlya_rascheta"] == ""
    assert rows[0]["Dlina_m"] == 10.0


# ========================= Внутренние стены =========================

def test_inner_walls_from_stray_type2_layers():
    """Кирпич и газоблок, прилипшие к Типу 2, отщепляются во внутренние стены."""
    sample = (
        "Наружная стена Тип 2:\n"
        "- монолитный железобетон 200 мм\n"
        "- перегородки из керамического полнотелого кирпича - 120ммм, 250 мм\n"
        "- газосиликатные блоки толщиной 200мм ГОСТ 31359-2007\n"
        "Внутренние стены:\n"
        "- монолитный железобетон (см. КР)\n"
    )
    items = {it["id"]: it for it in parse_spec_catalog(sample)}
    assert "Внутренняя стена|1" in items
    assert items["Внутренняя стена|1"]["thickness_mm"] is None
    assert "монолитный" in items["Внутренняя стена|1"]["material"].lower()
    assert "Внутренняя стена|2" in items
    lay2 = [L for L in items["Внутренняя стена|2"]["layers"] if "кирпич" in L["material"].lower()][0]
    assert lay2["thickness_mm"] == [120, 250]
    assert "Внутренняя стена|3" in items
    assert items["Внутренняя стена|3"]["thickness_mm"] == 200
    assert items["Внутренняя стена|3"]["countable"] is True
    t2 = items["Наружная стена|Тип 2"]
    assert "кирпич" not in t2["desc"].lower()
    assert "газосиликат" not in t2["desc"].lower()


def test_fixup_outer_type2_not_triggered_without_inner_section():
    """Без раздела «Внутренние стены» слои Типа 2 не отщепляются во внутренние стены,
    но сам тип всё равно разбивается на отдельные позицию-слои."""
    sample = (
        "Наружная стена Тип 2:\n"
        "- монолитный железобетон 200 мм\n"
        "- газосиликатные блоки толщиной 200мм\n"
    )
    items = {it["id"]: it for it in parse_spec_catalog(sample)}
    assert "Внутренняя стена|1" not in items
    # Тип 2 разбился на слои, газоблок — отдельная позиция-слой
    assert "Наружная стена|Тип 2|слой 2" in items
    gas = items["Наружная стена|Тип 2|слой 2"]
    assert "газосиликатные блоки" in gas["material"]
    assert gas["thickness_mm"] == 200


def test_inner_wall_countable_gas_concrete():
    """Газоблок 200 во внутренней стене — счётный."""
    sample = (
        "Внутренние стены:\n"
        "- газосиликатные блоки толщиной 200мм ГОСТ 31359-2007\n"
    )
    items = {it["id"]: it for it in parse_spec_catalog(sample)}
    inner = items["Внутренняя стена|1"]
    assert inner["thickness_mm"] == 200
    assert inner["countable"] is True


def test_inner_wall_monolithic_no_thickness():
    """Монолит внутри — толщина None, не счётный."""
    sample = (
        "Внутренние стены:\n"
        "- монолитный железобетон (см. КР)\n"
    )
    items = {it["id"]: it for it in parse_spec_catalog(sample)}
    inner = items["Внутренняя стена|1"]
    assert inner["thickness_mm"] is None
    assert inner["countable"] is False


def test_inner_wall_brick_double_thickness():
    """Кирпич внутри — двойная толщина [120, 250], не счётный."""
    sample = (
        "Внутренние стены:\n"
        "- перегородки из керамического полнотелого кирпича - 120ммм, 250 мм\n"
    )
    items = {it["id"]: it for it in parse_spec_catalog(sample)}
    inner = items["Внутренняя стена|1"]
    lay = [L for L in inner["layers"] if "кирпич" in L["material"].lower()][0]
    assert lay["thickness_mm"] == [120, 250]
    assert inner["countable"] is False
