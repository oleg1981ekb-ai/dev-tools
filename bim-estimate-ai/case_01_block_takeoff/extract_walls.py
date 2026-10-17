import fitz
import re
import sys
import pandas as pd
import os
from pathlib import Path

from spec_catalog import (
    parse_spec_catalog,
    print_catalog,
    parse_selection,
    ask_selection,
    count_markers,
    markers_by_catalog_id,
)

# ========================= Константы (единый источник правды) =========================
DEFAULT_HEIGHT = 2.80          # высота стен по умолчанию, м
THICKNESS = 0.20               # толщина газосиликатного блока, м
WASTE_FACTOR = 1.05            # запас на подрезку и бой, +5%
MIN_SIZE = 600                 # нижняя граница «стенового» размера, мм
BIG_WALL_THRESHOLD = 5000      # размеры >= этого значения → Тип 2, мм
BUILDING_DIM_THRESHOLD = 30000 # габариты здания — не стены, мм

SIZE_PATTERN = re.compile(
    r'\b(600|675|700|725|800|900|1130|1145|1160|1190|1250|1350|1450|1500|1600|1800|2025|2050|2105|2225|2700|2780|3000|3200|38600|39500|5100|5400|5800|6200|6400|6800|7000|7200)\b'
)

# ========================= Чистые функции (без ввода/файлов — тестируются) =========================

def parse_height(user_input, default=DEFAULT_HEIGHT):
    """Разбирает высоту стен из строки пользователя ('2.8', '2,8', '').

    Возвращает float. Любая некорректность → default.
    """
    text = str(user_input).strip()
    if text == "":
        return default
    try:
        return float(text.replace(',', '.'))
    except ValueError:
        return default


def collect_sizes(text):
    """Возвращает все размеры (мм) из текстового слоя страницы PDF."""
    return [float(match) for match in SIZE_PATTERN.findall(text)]


def split_by_type(sizes):
    """Делит размеры на типы стен: (типы_1_в_метрах, типы_2_в_метрах).

    Правила: >=30000 — габариты здания, пропуск;
    >=5000 → Тип 2 (у несущих осей); >=600 → Тип 1 (заполнение).
    Дубликаты размеров не суммируются (set).
    """
    type1, type2 = [], []
    for size in set(sizes):
        if size >= BUILDING_DIM_THRESHOLD:
            continue
        meters = size / 1000.0
        if size >= BIG_WALL_THRESHOLD:
            type2.append(meters)
        elif size >= MIN_SIZE:
            type1.append(meters)
    return sorted(type1), sorted(type2)


def calc_volumes(length_m, thickness=THICKNESS, height=DEFAULT_HEIGHT, waste_factor=WASTE_FACTOR):
    """Возвращает (объем_чистый_м3, объем_с_запасом_м3)."""
    pure = length_m * thickness * height
    return pure, pure * waste_factor


def build_report(type1_lengths, type2_lengths, height,
                 thickness=THICKNESS, waste_factor=WASTE_FACTOR,
                 chosen_labels=None):
    """Собирает ВСЕ расчётные значения по каждому типу стены.

    Возвращает список dict-строк (по одной на тип) с полным набором величин:
    длина, площадь кладки, чистый объём, запас, объём с запасом.

    chosen_labels — метки каталога («Перегородка Тип 4»), выбранные
    пользователем. Пока расчёт геометрии покрывает только наружные стены
    (split_by_type), поэтому метки фиксируются в строке Vybrano_dlya_rascheta;
    полный расчёт по перегородкам — следующий шаг (Фаза 1: snap_to_axes).
    """
    rows = []
    for name, lengths in (
        ("Narus_Stena_Tip_1", type1_lengths),
        ("Narus_Stena_Tip_2", type2_lengths),
    ):
        length_m = sum(lengths)
        area_m2 = length_m * height                       # площадь кладки, м²
        pure_vol = length_m * thickness * height          # чистый объём, м³
        waste_vol = pure_vol * waste_factor               # объём с запасом, м³
        rows.append({
            "Konstrukciya": name,
            "Material": "Gazosilikat_200mm",
            "Tolshina_m": round(thickness, 2),
            "Vysota_m": round(height, 2),
            "Kolichestvo_razmerov": len(lengths),
            "Dlina_m": round(length_m, 2),
            "Ploshad_m2": round(area_m2, 2),
            "Volume_m3": round(pure_vol, 2),
            "Waste_factor": waste_factor,
            "Zapas_m3": round(waste_vol - pure_vol, 2),
            "Volume_with_waste_m3": round(waste_vol, 2),
            "Vybrano_dlya_rascheta": "; ".join(chosen_labels) if chosen_labels else "",
        })
    return rows


# ========================= Основной сценарий (ввод/вывод/файлы) =========================

def ask_height():
    """Интерактивно запрашивает высоту стен у пользователя."""
    user_input = input("👉 Введите высоту стен в метрах (например, 2.8 или 3.3) [по умолчанию 2.8]: ").strip()

    if user_input == "":
        return DEFAULT_HEIGHT

    try:
        return float(user_input.replace(',', '.'))
    except ValueError:
        print(f"❌ Ошибка: Введено некорректное число. Используется высота по умолчанию: {DEFAULT_HEIGHT} м")
        return DEFAULT_HEIGHT


def print_report(rows, type1_lengths, type2_lengths, height):
    """Выводит ВСЕ расчётные значения подробным отчётом в консоль."""
    print("=======================================================")
    print(f"📋 ПОЛНЫЙ ОТЧЕТ РАСЧЕТА (высота {height:.2f} м, блок {THICKNESS * 1000:.0f} мм)")
    print("=======================================================")

    for row, lengths in ((rows[0], type1_lengths), (rows[1], type2_lengths)):
        label = "ТИП 1 (Заполнение)" if row["Konstrukciya"].endswith("1") else "ТИП 2 (У несущих осей)"
        print(f"\n🧱 {label}")
        print(f"   Найдено размеров:        {row['Kolichestvo_razmerov']}")
        print(f"   Размеры (мм):            {', '.join(f'{l * 1000:.0f}' for l in sorted(lengths)) or '—'}")
        print(f"   Суммарная длина:         {row['Dlina_m']:.2f} м")
        print(f"   Площадь кладки:          {row['Ploshad_m2']:.2f} м²")
        print(f"   Толщина блока:           {row['Tolshina_m'] * 1000:.0f} мм")
        print(f"   Чистый объём:            {row['Volume_m3']:.2f} м³")
        print(f"   Запас ({WASTE_FACTOR - 1:.0%}):               {row['Zapas_m3']:.2f} м³")
        print(f"   Объём с запасом:         {row['Volume_with_waste_m3']:.2f} м³")

    t1, t2 = rows[0], rows[1]
    print("\n───────────────────────────────────────────────────────")
    print(f"   ИТОГО длина:             {t1['Dlina_m'] + t2['Dlina_m']:.2f} м")
    print(f"   ИТОГО площадь:           {t1['Ploshad_m2'] + t2['Ploshad_m2']:.2f} м²")
    print(f"   ИТОГО чистый объём:      {t1['Volume_m3'] + t2['Volume_m3']:.2f} м³")
    print(f"   ИТОГО с запасом:         {t1['Volume_with_waste_m3'] + t2['Volume_with_waste_m3']:.2f} м³")
    print("=======================================================")


def parse_cli_args(argv):
    """CLI-флаги: --types 3,5 --height 2.8 --all. Без флагов → интерактив."""
    types_raw, height_raw, all_flag = None, None, False
    args = list(argv)
    i = 0
    while i < len(args):
        a = args[i]
        if a == "--types" and i + 1 < len(args):
            types_raw = args[i + 1]
            i += 2
        elif a.startswith("--types="):
            types_raw = a.split("=", 1)[1]
            i += 1
        elif a == "--height" and i + 1 < len(args):
            height_raw = args[i + 1]
            i += 2
        elif a.startswith("--height="):
            height_raw = a.split("=", 1)[1]
            i += 1
        elif a in ("--all", "-a"):
            all_flag = True
            i += 1
        else:
            i += 1
    return types_raw, height_raw, all_flag


def professional_split_takeoff(pdf_path, output_csv, types_raw=None,
                               height_raw=None, select_all=False):
    print("\n=======================================================")
    print("🚀 Запуск универсального инженерного калькулятора стен")
    print("=======================================================")

    doc = fitz.open(pdf_path)

    # --- Каталог конструкций из экспликации ---
    full_text = "\n".join(page.get_text() for page in doc)
    catalog = parse_spec_catalog(full_text)
    if not catalog:
        print("❌ В текстовом слое не найдена экспликация (разделы 'Наружная стена/Перегородки').")
        print("   Расчёт невозможен — проверьте PDF.")
        return
    words = []
    for page in doc:
        words += [((x0 + x1) / 2, (y0 + y1) / 2, w)
                  for x0, y0, x1, y1, w, *_ in page.get_text("words")]
    markers = markers_by_catalog_id(catalog, count_markers(words))
    print_catalog(catalog, markers)

    # --- Выбор «что считаем» ---
    if types_raw is not None:
        picked = parse_selection(types_raw, len(catalog))
    elif select_all:
        picked = list(range(len(catalog)))
    else:
        picked = ask_selection(len(catalog))
    if not picked:
        print("   ⚠️ Ничего не выбрано — считаю все типы.")
        picked = list(range(len(catalog)))
    chosen = [catalog[i] for i in picked]
    print(f"\n✅ Выбрано: {', '.join(c['label'] for c in chosen)}\n")

    # --- Высота ---
    if height_raw is not None:
        height = parse_height(height_raw)
    else:
        height = ask_height()

    print(f"\n📐 Расчет будет произведен для высоты стен: {height:.2f} м\n")
    print("⏳ Сканирование и анализ страниц чертежа...")

    all_sizes = []
    for page in doc:
        all_sizes.extend(collect_sizes(page.get_text()))

    type1_lengths, type2_lengths = split_by_type(all_sizes)

    # Все расчётные значения в одной структуре
    rows = build_report(type1_lengths, type2_lengths, height,
                        chosen_labels=[c["label"] for c in chosen])

    # Подробный консольный отчёт
    print_report(rows, type1_lengths, type2_lengths, height)

    # CSV со всеми столбцами
    df = pd.DataFrame(rows)
    df.to_csv(output_csv, index=False, encoding='utf-8')

    print(f"📊 Итоговая ведомость со всеми расчётными значениями сохранена: {output_csv}")
    print("=======================================================")

if __name__ == "__main__":
    # Пути строятся от расположения файла — без абсолютных захардкоженных путей
    data_dir = Path(__file__).resolve().parent / "data"
    output_csv = data_dir / "estimated_materials.csv"

    # CLI-флаги --types/--height/--all; первый непознанный аргумент = путь к PDF
    types_raw, height_raw, select_all = parse_cli_args(sys.argv[1:])

    # PDF: явный путь-позиционный аргумент или первый *.pdf в data/
    positional = [a for a in sys.argv[1:]
                  if not a.startswith("--") and a != types_raw and a != height_raw]
    if positional:
        pdf_path = Path(positional[0]).expanduser()
    else:
        pdfs = sorted(data_dir.glob("*.pdf")) if data_dir.exists() else []
        if not pdfs:
            print(f"❌ В папке {data_dir} нет PDF-чертежей.")
            print("   Положите PDF в эту папку или укажите путь аргументом: python extract_walls.py /path/to/drawing.pdf")
            sys.exit(1)
        pdf_path = pdfs[0]
    if len(sorted(data_dir.glob("*.pdf"))) > 1 and not positional:
        print(f"⚠️ В {data_dir} несколько PDF — беру первый: {pdf_path.name}")

    professional_split_takeoff(str(pdf_path), str(output_csv),
                               types_raw=types_raw, height_raw=height_raw,
                               select_all=select_all)