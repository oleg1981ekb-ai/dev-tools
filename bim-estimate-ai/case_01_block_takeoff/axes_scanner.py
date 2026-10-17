"""Фаза 0: разведка координат текста на чертеже.

Ставит три задачи:
1. Найти метки осей (буквы сверху/снизу, цифры слева/справа) и их координаты.
2. Показать распределение подписей размеров (где живут числа).
3. Найти блоки экспликации перегородок (Тип N + толщина).

Запуск: .venv/bin/python case_01_block_takeoff/axes_scanner.py [путь/к.pdf]
Вывод: отчёт в консоль (без записи файлов — это инструмент разведки).
"""
import sys
from pathlib import Path
from collections import defaultdict

import pymupdf as fitz

# Множества осевых меток (по чертежу: оси А..Л и 1..11)
AXIS_LETTERS = set("АБВГДЕЖИКЛМН")
AXIS_DIGITS = set("0123456789")

# Полосы листа, где традиционно стоят подписи осей (% от размера листа)
EDGE_PCT = 0.15


def find_pdf():
    if len(sys.argv) > 1:
        p = Path(sys.argv[1]).expanduser()
        if p.exists():
            return p
        print(f"❌ Файл не найден: {p}")
        sys.exit(1)
    data_dir = Path(__file__).resolve().parent / "data"
    pdfs = sorted(data_dir.glob("*.pdf")) if data_dir.exists() else []
    if not pdfs:
        print(f"❌ Нет PDF в {data_dir}")
        sys.exit(1)
    return pdfs[0]


def is_edge_zone(x, y, rect, edge_pct=EDGE_PCT):
    """True, если точка в краевой полосе листа (где живут метки осей)."""
    w, h = rect.width, rect.height
    return (x < w * edge_pct or x > w * (1 - edge_pct)
            or y < h * edge_pct or y > h * (1 - edge_pct))


def scan_page(page):
    """Собирает метки осей, числа-размеры и ключевые слова одной страницы."""
    rect = page.rect
    words = page.get_text("words")  # (x0, y0, x1, y1, word, block, line, no)
    total = len(words)

    axis_letters_top, axis_letters_bottom = [], []
    axis_digits_left, axis_digits_right = [], []
    numbers = []          # числа-кандидаты в размеры (не осевые метки)
    keywords = []         # перегородки/типы

    for x0, y0, x1, y1, word, *_ in words:
        cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
        in_edge = is_edge_zone(cx, cy, rect)

        # Метки осей: ОДИН символ в краевой зоне
        if in_edge and len(word) == 1:
            if word in AXIS_LETTERS:
                rec = (round(cx, 1), round(cy, 1), word)
                (axis_letters_top if cy < rect.height / 2 else axis_letters_bottom).append(rec)
                continue
            if word in AXIS_DIGITS:
                rec = (round(cx, 1), round(cy, 1), word)
                (axis_digits_left if cx < rect.width / 2 else axis_digits_right).append(rec)
                continue

        # Числа-размеры (длина >= 2 цифр), в т.ч. в краевой зоне
        if word.isdigit() and len(word) >= 2:
            numbers.append((round(cx, 1), round(cy, 1), int(word)))
            continue

        # Ключевые слова экспликации
        low = word.lower().strip(".,:;")
        if low in ("перегородка", "перегородки", "зашивка", "зашивки",
                   "наружная", "стена", "стены") or word in ("Тип", "типа"):
            keywords.append((round(cx, 1), round(cy, 1), word))

    return {
        "page_size": (round(rect.width, 1), round(rect.height, 1)),
        "total_words": total,
        "letters_top": axis_letters_top,
        "letters_bottom": axis_letters_bottom,
        "digits_left": axis_digits_left,
        "digits_right": axis_digits_right,
        "numbers": numbers,
        "keywords": keywords,
    }


def cluster(values, tol=8.0):
    """Схлопывает повторы (оси подписаны 2 раза): близкие координаты → один кластер.

    values: список (x, y, символ). Возвращает (x, y, символы, встреч).
    """
    if not values:
        return []
    values = sorted(values)
    out, group = [], [values[0]]
    for v in values[1:]:
        if abs(v[0] - group[-1][0]) <= tol and abs(v[1] - group[-1][1]) <= tol:
            group.append(v)
        else:
            out.append(group)
            group = [v]
    out.append(group)
    return [(round(sum(p[0] for p in g) / len(g), 1),
             round(sum(p[1] for p in g) / len(g), 1),
             "".join(sorted({p[2] for p in g})), len(g)) for g in out]


def main():
    pdf_path = find_pdf()
    print(f"🔎 ФАЗА 0: разведка координат — {pdf_path.name}\n")

    doc = fitz.open(pdf_path)
    for i, page in enumerate(doc, 1):
        r = scan_page(page)
        print(f"═══ Страница {i} | лист {r['page_size'][0]}×{r['page_size'][1]} pt "
              f"| слов: {r['total_words']} ═══")

        letters = cluster(r["letters_top"] + r["letters_bottom"])
        digits = cluster(r["digits_left"] + r["digits_right"])

        print(f"\n  🔤 Буквенные оси (кандидаты): {len(letters)} уникальных")
        for x, y, sym, n in letters:
            print(f"     '{sym}'  x={x:7.1f}  y={y:7.1f}  встреч={n}")

        print(f"\n  🔢 Цифровые оси (кандидаты): {len(digits)} уникальных")
        for x, y, sym, n in digits:
            print(f"     '{sym}'  x={x:7.1f}  y={y:7.1f}  встреч={n}")

        nums = r["numbers"]
        print(f"\n  📏 Числа-кандидаты в размеры: {len(nums)}")
        if nums:
            xs = [n[0] for n in nums]
            ys = [n[1] for n in nums]
            print(f"     X: {min(xs):.0f}..{max(xs):.0f}   Y: {min(ys):.0f}..{max(ys):.0f}")
            in_field = [n for n in nums if not is_edge_zone(n[0], n[1],
                        fitz.Rect(0, 0, *r["page_size"]))]
            print(f"     внутри листа (не кромка): {len(in_field)}, на кромке: {len(nums) - len(in_field)}")
            print(f"     примеры: {sorted({v for _, _, v in nums})[:20]}")

        print(f"\n  🏷 Ключевые слова: {len(r['keywords'])}")
        for x, y, w in r["keywords"][:15]:
            print(f"     '{w}'  x={x}  y={y}")
        print()


if __name__ == "__main__":
    main()
