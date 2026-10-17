import fitz
import re
import sys
import pandas as pd
import os

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


def professional_split_takeoff(pdf_path, output_csv):
    print("\n=======================================================")
    print("🚀 Запуск универсального инженерного калькулятора стен")
    print("=======================================================")

    # Интерактивный ввод высоты стен от пользователя
    height = ask_height()

    print(f"\n📐 Расчет будет произведен для высоты стен: {height:.2f} м\n")
    print("⏳ Сканирование и анализ страниц чертежа...")

    doc = fitz.open(pdf_path)

    all_sizes = []
    for page in doc:
        all_sizes.extend(collect_sizes(page.get_text()))

    type1_lengths, type2_lengths = split_by_type(all_sizes)

    t1_len = sum(type1_lengths)
    t1_pure_vol, t1_waste_vol = calc_volumes(t1_len, height=height)

    t2_len = sum(type2_lengths)
    t2_pure_vol, t2_waste_vol = calc_volumes(t2_len, height=height)

    data = {
        "Konstrukciya": ["Narus_Stena_Tip_1", "Narus_Stena_Tip_2"],
        "Material": ["Gazosilikat_200mm", "Gazosilikat_200mm"],
        "Vysota_m": [f"{height:.2f}", f"{height:.2f}"],
        "Dlina_m": [f"{t1_len:.2f}", f"{t2_len:.2f}"],
        "Volume_m3": [f"{t1_pure_vol:.2f}", f"{t2_pure_vol:.2f}"],
        "Volume_with_waste_m3": [f"{t1_waste_vol:.2f}", f"{t2_waste_vol:.2f}"]
    }

    df = pd.DataFrame(data)
    df.to_csv(output_csv, index=False, encoding='utf-8')

    print("=======================================================")
    print("✅ ИНЖЕНЕРНЫЙ РАСЧЕТ ГЕОМЕТРИИ ЗАВЕРШЕН!")
    print(f"🧱 ТИП 1 (Заполнение): Длина {t1_len:.2f} м | Объем с запасом: {t1_waste_vol:.2f} м³")
    print(f"🏗 ТИП 2 (У несущих осей): Длина {t2_len:.2f} м | Объем с запасом: {t2_waste_vol:.2f} м³")
    print(f"📊 Итоговая точная ведомость сохранена в CSV!")
    print("=======================================================")

if __name__ == "__main__":
    # Пути строятся от расположения файла — без абсолютных захардкоженных путей
    from pathlib import Path

    data_dir = Path(__file__).resolve().parent / "data"
    output_csv = data_dir / "estimated_materials.csv"

    # PDF: аргумент CLI (python extract_walls.py путь/к/файлу.pdf) или первый *.pdf в data/
    if len(sys.argv) > 1:
        pdf_path = Path(sys.argv[1]).expanduser()
    else:
        pdfs = sorted(data_dir.glob("*.pdf")) if data_dir.exists() else []
        if not pdfs:
            print(f"❌ В папке {data_dir} нет PDF-чертежей.")
            print("   Положите PDF в эту папку или укажите путь аргументом: python extract_walls.py /path/to/drawing.pdf")
            sys.exit(1)
        pdf_path = pdfs[0]

    professional_split_takeoff(str(pdf_path), str(output_csv))