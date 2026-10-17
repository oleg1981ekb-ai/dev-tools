"""Фаза 0 (v2): разведка координат текста на чертеже.

Ключевое отличие от v1: цифровые оси ищутся не «по краям листа»,
а структурно — как РЯД из не менее MIN_AXIS_COUNT чисел, выстроенных
по одной линии (общая x или общая y в пределах tol) и возрастающих
монотонно по координате. Это отсекает таблицы, размеры и случайные
числа: им такой закономерности не свойственна.

Запуск: .venv/bin/python case_01_block_takeoff/axes_scanner.py [путь/к.pdf]
"""
import sys
from pathlib import Path

import pymupdf as fitz

AXIS_LETTERS = set("АБВГДЕЖИКЛМН")   # буквенные метки осей (по чертежу А..Л)
MIN_AXIS_COUNT = 5                    # минимум чисел в ряду, чтобы считать рядом осей
LINE_TOL = 12.0                       # допуск «в одной линии», pt


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


def collect_words(page):
    """Все слова с центрами: [(cx, cy, word), ...]."""
    out = []
    for x0, y0, x1, y1, word, *_ in page.get_text("words"):
        out.append(((x0 + x1) / 2, (y0 + y1) / 2, word))
    return out


def find_axis_letters(words):
    """Буквенные оси: одиночная буква из AXIS_LETTERS → (x, y, символ).

    Метки дублируются по краям листа — схлопываем близкие (8 pt).
    """
    raw = [(cx, cy, w) for cx, cy, w in words
           if len(w) == 1 and w in AXIS_LETTERS]
    raw.sort()
    clusters = []
    for cx, cy, w in raw:
        for c in clusters:
            if abs(c[-1][0] - cx) < 8 and abs(c[-1][1] - cy) < 8:
                c.append((cx, cy, w))
                break
        else:
            clusters.append([(cx, cy, w)])
    return [(round(sum(p[0] for p in c) / len(c), 1),
             round(sum(p[1] for p in c) / len(c), 1),
             "".join(sorted({p[2] for p in c}))) for c in clusters]


def _group_lines(items, key_main, key_cross, tol):
    """Группирует элементы по главной координате с допуском tol."""
    items = sorted(items, key=lambda t: (t[0], t[1]))
    groups, current = [], [items[0]] if items else []
    for it in items[1:]:
        if current and abs(it[0] - current[-1][0]) <= tol:
            current.append(it)
        else:
            groups.append(current)
            current = [it]
    groups.append(current)
    return groups


def _axis_groups(nums, axis, min_count=MIN_AXIS_COUNT, tol=LINE_TOL):
    """Отбирает ряды чисел-осей.

    axis='x' → горизонтальные ряды (общая y, значения растут по x);
    axis='y' → вертикальные ряды (общая x, значения растут по y).
    Критерии: >= min_count членов И строгая монотонность значений
    (таблицы/размеры такого ряда не дают).
    """
    if axis == "x":
        items = [(cy, cx, v) for cx, cy, v in nums]   # главная — y
    else:
        items = [(cx, cy, v) for cx, cy, v in nums]   # главная — x

    result = []
    for g in _group_lines(items, None, None, tol):
        if len(g) < min_count:
            continue
        g = sorted(g, key=lambda t: t[1])             # по поперечной координате
        values = [t[2] for t in g]
        # Оси — это нумерация 1..N: значения маленькие и почти всегда растут.
        # «Почти»: допускаем до 20% нарушений монотонности (посторонние числа
        # вроде размера, попавшие в ту же линию).
        if max(values) > 40:
            continue
        grow = sum(1 for i in range(len(values) - 1) if values[i] < values[i + 1])
        pairs_cnt = len(values) - 1
        if pairs_cnt and grow / pairs_cnt >= 0.8:
            main_coord = round(sum(t[0] for t in g) / len(g), 1)
            pairs = [(t[1], t[2]) for t in g]         # (координата, значение)
            result.append((main_coord, pairs))
    return result


def find_number_rows(words, **kw):
    """Горизонтальные ряды осей: [(y, [(x, value), ...]), ...]."""
    nums = [(cx, cy, int(w)) for cx, cy, w in words if w.isdigit()]
    return _axis_groups(nums, axis="x", **kw)


def find_number_columns(words, **kw):
    """Вертикальные ряды осей: [(x, [(y, value), ...]), ...]."""
    nums = [(cx, cy, int(w)) for cx, cy, w in words if w.isdigit()]
    return _axis_groups(nums, axis="y", **kw)


def find_circled_axes(page, words):
    """Цифровые оси: цифра, находящаяся ВНУТРИ векторного кружка.

    Самый надёжный критерий — на чертеже ось всегда рисуется кружком
    с числом внутри. Маркеры/размеры кружков не имеют.
    """
    circles = []
    for d in page.get_drawings():
        r = d["rect"]
        w, h = r.width, r.height
        # кружок осей: ~28 pt, почти правильная окружность
        if 15 < w < 70 and 15 < h < 70 and abs(w - h) < w * 0.3:
            circles.append(r)
    if not circles:
        return []

    axes = []
    for cx, cy, w in words:
        if not w.isdigit():
            continue
        for r in circles:
            if r.x0 <= cx <= r.x1 and r.y0 <= cy <= r.y1:
                # центр кружка — точка привязки оси
                axes.append((round((r.x0 + r.x1) / 2, 1),
                             round((r.y0 + r.y1) / 2, 1), int(w),
                             round(r.width, 1)))
                break

    # Группировка кружков в ряды: один диаметр, одна линия, монотонная
    # нумерация и значения как у осей (1..N) — выноски размеров отсекаются.
    axes.sort(key=lambda a: (a[3], a[1], a[0]))       # по диаметру, затем y, x
    groups, cur = [], [axes[0]] if axes else []
    for a in axes[1:]:
        same_d = abs(a[3] - cur[-1][3]) < 3
        same_line_y = abs(a[1] - cur[-1][1]) < 12
        same_line_x = abs(a[0] - cur[-1][0]) < 12
        if same_d and (same_line_y or same_line_x):
            cur.append(a)
        else:
            groups.append(cur)
            cur = [a]
    groups.append(cur)

    result = []
    for g in groups:
        if len(g) < 5:
            continue
        if max(a[2] for a in g) > 40:
            continue
        # монотонность вдоль линии (y для горизонтального ряда)
        g = sorted(g, key=lambda a: a[0])
        vals = [a[2] for a in g]
        grow = sum(1 for i in range(len(vals) - 1) if vals[i] < vals[i + 1])
        if len(vals) > 1 and grow / (len(vals) - 1) >= 0.8:
            result.extend(g)
    return sorted(result)


def main():
    pdf_path = find_pdf()
    print(f"🔎 ФАЗА 0 v2: структурный поиск осей — {pdf_path.name}\n")

    doc = fitz.open(pdf_path)
    for i, page in enumerate(doc, 1):
        rect = page.rect
        words = collect_words(page)
        print(f"═══ Страница {i} | лист {rect.width:.0f}×{rect.height:.0f} pt "
              f"| слов: {len(words)} ═══")

        letters = sorted(find_axis_letters(words), key=lambda t: t[1])
        print(f"\n  🔤 Буквенные оси: {len(letters)} (по Y, сверху вниз)")
        for x, y, sym in letters:
            print(f"     '{sym}'  x={x:7.1f}  y={y:7.1f}")

        rows = find_number_rows(words)
        print(f"\n  ➖ Горизонтальные ряды чисел-осей: {len(rows)}")
        for y, pairs in rows:
            vals = ", ".join(str(v) for _, v in pairs)
            xs = ", ".join(f"{x:.0f}" for x, _ in pairs)
            print(f"     y={y:7.1f}  осей: {len(pairs)}  значения: {vals}")
            print(f"        x: {xs}")

        cols = find_number_columns(words)
        print(f"\n  ➕ Вертикальные ряды чисел-осей: {len(cols)}")
        for x, pairs in cols:
            vals = ", ".join(str(v) for _, v in pairs)
            ys = ", ".join(f"{y:.0f}" for y, _ in pairs)
            print(f"     x={x:7.1f}  осей: {len(pairs)}  значения: {vals}")
            print(f"        y: {ys}")

        circled = find_circled_axes(page, words)
        print(f"\n  ⭕ Оси в кружках (эталон): {len(circled)}")
        for x, y, v, d in circled:
            print(f"     ось {v:>2}  x={x:7.1f}  y={y:7.1f}  кружок d={d}")

        big = [(cx, cy, int(w)) for cx, cy, w in words if w.isdigit() and len(w) >= 3]
        print(f"\n  📏 Трёхзначные+ числа (кандидаты в размеры): {len(big)}")
        if big:
            xs = [b[0] for b in big]
            ys = [b[1] for b in big]
            print(f"     X: {min(xs):.0f}..{max(xs):.0f}  Y: {min(ys):.0f}..{max(ys):.0f}")

        kws = [(cx, cy, w) for cx, cy, w in words
               if w.lower().strip(".,:;") in ("перегородка", "перегородки", "зашивка", "зашивки")]
        print(f"\n  🏷 Слова 'перегородка/зашивка': {len(kws)}")
        for x, y, w in kws[:10]:
            print(f"     '{w}'  x={x:.1f}  y={y:.1f}")
        print()


if __name__ == "__main__":
    main()
