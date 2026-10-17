"""Каталог конструкций из экспликации чертежа + интерактивный выбор «что считаем».

Экспликация на листе разбита на РАЗДЕЛЫ, нумерация типов внутри разделов
независимая: «Наружная стена Тип 1» ≠ «Перегородка Тип 1». Поэтому каталог
строится парсингом по разделам, а не голым поиском «Тип N» (см. ADR-0004).

Запуск тестов: .venv/bin/python -m pytest tests/test_spec_catalog.py -v
"""
import re

# Заголовки разделов экспликации (нормализованные, нижний регистр)
SECTION_MARKERS = (
    ("наружная стена", "Наружная стена"),
    ("внутренние стены", "Внутренняя стена"),
    ("перегородки", "Перегородка"),
    ("зашивки", "Зашивка"),
)

# «Тип 1. перегородка ГКЛ толщиной 125 мм» / «Наружная стена Тип 2:» / «- Тип 4. ...»
TYPE_RE = re.compile(r"тип\s*(\d+)\s*[.:]?\s*(.*)", re.IGNORECASE)
# толщина: «толщиной 125 мм» / «толщина 200мм» / «200 мм»
THICKNESS_RE = re.compile(r"толщин[а-я]*\s*(\d+)\s*мм", re.IGNORECASE)
BARE_THICKNESS_RE = re.compile(r"(\d+)\s*мм", re.IGNORECASE)
# материал: первое осмысленное слово описания («перегородка ГКЛ ...», «монолитный ...»)
MATERIAL_STOP = {"толщиной", "толщина"}


def _is_section_header(low):
    """Строка — заголовок раздела, а не слой-описание.

    Ловушка: слой «- перегородки из кирпича ... 250 мм» начинается со слова
    «перегородки» и naive startswith переключал раздел раньше времени,
    обрезая Тип 2 (терялись кирпич и газосиликат). Поэтому заголовок —
    только короткая строка без «мм»: «Перегородки:», «Внутренние стены:»,
    «Наружная стена Тип 1:» (тут же и тип — его разберёт TYPE_RE ниже).
    """
    if "мм" in low:
        return None
    for marker, section_name in SECTION_MARKERS:
        if not low.startswith(marker):
            continue
        rest = low[len(marker):].strip().strip(":;-–—• ").strip()
        if rest == "" or rest.startswith("тип"):
            return section_name
        # «внутренние стены» без уточнения — тоже заголовок
        if marker == "внутренние стены" and len(rest) < 20:
            return section_name
    return None


def _clean(text):
    """Нормализация строки экспликации."""
    return re.sub(r"\s+", " ", text.strip().lstrip("-–—•").strip())


def _is_countable(layer_text, thickness):
    """Слой идёт в смету блоков? Только газосиликат 200 (ГОСТ 31359).

    Монолит ЖБ — раздел КР, не считаем (толщина тем более может быть
    не отражена в АР). Утеплитель/фасад/кирпич — не блоки.
    thickness может быть списком (кирпич 120/250) — счётным он не
    становится в любом случае.
    """
    if isinstance(thickness, list) or thickness != 200:
        return False
    low = layer_text.lower()
    return ("газосиликат" in low or "газосиликатн" in low
            or "ячеист" in low or "31359" in low)


def build_layers(desc):
    """Описание типа → список слоёв [{material, thickness_mm, countable}].

    Пункты-слои разделены « | » (см. parse_spec_catalog). Каждый пункт —
    отдельный слой пирога: фасад, утеплитель, монолит, кирпич, газоблок.
    thickness_mm=None = толщина не отражена (монолит без «мм» — штатно,
    объём по такому слою не считается никогда).
    """
    layers = []
    for layer_text in [p.strip().strip("| ") for p in desc.split("|")]:
        if not layer_text:
            continue
        thickness = _layer_thickness(layer_text)
        layers.append({
            "material": _layer_material(layer_text),
            "thickness_mm": thickness,
            "countable": _is_countable(layer_text, thickness),
        })
    return layers


def _material_and_thickness(desc):
    """Обратная совместимость: (материал, толщина) из слоёв.

    Материал — счётные слои через « + » (газоблок Типа 1; в Типе 2 только
    газоблок — монолит/кирпич не счётные). Толщина — толщина первого
    счётного слоя, иначе последнего слоя с «мм» (утеплитель 80 в середине
    не должен перекрывать несущий 200 в конце).
    """
    layers = build_layers(desc)
    counted = [layer for layer in layers if layer["countable"]]
    if counted:
        mats = [layer["material"] for layer in counted if layer["material"]]
        return " + ".join(dict.fromkeys(mats)), counted[0]["thickness_mm"]
    for layer in reversed(layers):
        if layer["thickness_mm"] is not None:
            return layer["material"], layer["thickness_mm"]
    if layers:
        return layers[0]["material"], None
    return "", None


def _layer_thickness(layer_text):
    """Толщина слоя в мм, список [a, b] при двойной («120, 250») или None.

    Монолит ЖБ: толщину НЕ учитываем никогда (в АР может быть не отражена,
    объём — по разделу КР) → всегда None.

    Важно: отсутствие толщины — штатная ситуация (монолит ЖБ в АР часто
    идёт без «мм» с пометкой «см. КР»). None означает «не отражена»,
    а не «нулевая» — объём по такому слою не считается никогда.

    Двойные толщины («120мм, 250 мм» у кирпича) возвращаются списком —
    слой один, вариантов толщины два (верста/перегородка).
    """
    low = layer_text.lower()
    if "монолит" in low or "железобетон" in low or "ж/б" in low or "жб" in low:
        return None
    nums = [int(n) for n in re.findall(r"(\d+)\s*мм", layer_text, re.IGNORECASE)]
    # опечатка чертежа «120ммм» — тройное «м» тоже ловим
    nums += [int(n) for n in re.findall(r"(\d+)ммм", layer_text, re.IGNORECASE)]
    nums = list(dict.fromkeys(nums))
    if not nums:
        m = THICKNESS_RE.search(layer_text)
        if m:
            return int(m.group(1))
        return None
    return nums[0] if len(nums) == 1 else nums


def _layer_material(layer):
    """Первые слова слоя до стоп-слова («толщиной»/цифры)."""
    words = [w for w in re.split(r"[\s,;()]+\s*", layer) if w]
    material_words = []
    for w in words:
        wl = w.lower().strip(".,:;")
        if wl in MATERIAL_STOP or wl.isdigit() or wl == "мм":
            break
        material_words.append(w)
    return " ".join(material_words).strip(" .,;:")


def _is_bullet(raw_line):
    """Строка — пункт-буллит экспликации («- ...», «– ...», «• ...»)."""
    s = raw_line.strip()
    return s[:1] in ("-", "–", "—", "•") and len(s) > 3


def _make_inner_item(desc, n):
    """Буллит раздела «Внутренние стены» → отдельная однослойная позиция."""
    layers = build_layers(desc)
    lay = layers[0] if layers else {"material": desc, "thickness_mm": None, "countable": False}
    short = lay["material"][:40] if lay["material"] else desc[:40]
    thick = lay["thickness_mm"]
    return {
        "id": f"Внутренняя стена|{n}",
        "section": "Внутренняя стена",
        "type_no": None,
        "label": f"Внутренняя стена {n}: {short}",
        "material": lay["material"],
        "thickness_mm": thick if not isinstance(thick, list) else None,
        "desc": desc,
        "layers": layers,
        "countable": lay["countable"],
    }


def _fixup_outer_type2(items):
    """Отделяет прилипшие слои Типа 2: кирпич и газосиликат — это внутренние стены.

    Причина: в текстовом слое PDF пункты кирпича/газоблока идут ДО заголовка
    «Внутренние стены:» (порядок чтения справа налево), поэтому pending-аккумулятор
    приписывает их Типу 2. По картинке Тип 2 = панели + утеплитель + монолит.
    Отщеплённые слои становятся позициями внутренних стен (монолит уже создан
    из буллита раздела — порядок приводим к картинке: монолит, кирпич, газоблок).
    """
    outer = next((it for it in items if it["id"] == "Наружная стена|Тип 2"), None)
    if outer is None:
        return items
    keep, stray = [], []
    for chunk in outer["desc"].split("|"):
        c = chunk.strip()
        if not c:
            continue
        low = c.lower()
        if "кирпич" in low or "газосиликат" in low or "ячеист" in low or "31359" in low:
            stray.append(c)
        else:
            keep.append(c)
    if not stray:
        return items
    outer["desc"] = "|".join(keep)
    outer["layers"] = build_layers(outer["desc"])
    # внутренние стены: существующие (монолит) + новые из stray
    inners = [it for it in items if it["section"] == "Внутренняя стена"]
    have_brick = any("кирпич" in (it["desc"] or "").lower() for it in inners)
    have_gas = any("газосиликат" in (it["desc"] or "").lower()
                   or "ячеист" in (it["desc"] or "").lower() for it in inners)
    n = len(inners)
    new_inners = []
    for chunk in stray:
        low = chunk.lower()
        if "кирпич" in low and not have_brick:
            n += 1
            new_inners.append(_make_inner_item(chunk, n))
            have_brick = True
        elif ("газосиликат" in low or "ячеист" in low or "31359" in low) and not have_gas:
            n += 1
            new_inners.append(_make_inner_item(chunk, n))
            have_gas = True
    if not new_inners:
        return items
    out = []
    for it in items:
        out.append(it)
        if it["section"] == "Внутренняя стена" and not any(
                x["id"] == it["id"] for x in out[:-1] if x["section"] == "Внутренняя стена"):
            pass
    # вставляем новые позиции сразу после последней внутренней стены
    inner_indices = [i for i, it in enumerate(out) if it["section"] == "Внутренняя стена"]
    if inner_indices:
        last_inner = max(inner_indices)
        out[last_inner + 1:last_inner + 1] = new_inners
    else:
        out.extend(new_inners)
    return out


def parse_spec_catalog(text):
    """Текстовый слой PDF → список записей каталога.

    Запись: {id, section, type_no, label, material, thickness_mm}.
    id уникален: «Наружная стена|Тип 1», «Перегородка|Тип 1» — разные id.
    Строки вне разделов игнорируются. Дубли схлопываются.
    """
    items, seen = [], set()
    section = None
    pending = None  # (section, type_no, desc) — тип, чьё описание продолжается
    for raw_line in text.splitlines():
        line = _clean(raw_line)
        if not line:
            continue
        low = line.lower()
        # смена раздела — только настоящий заголовок (см. _is_section_header):
        # «Перегородки:» — да; «- перегородки из кирпича ... 250 мм» — слой, нет
        new_section = _is_section_header(low)
        if new_section is not None and new_section != section:
            # граница разделов (в т.ч. «Внутренние стены:»): закрываем накопленное
            if pending:
                _flush(items, seen, pending)
                pending = None
            section = new_section
        if section is None:
            continue
        m = TYPE_RE.search(line)
        if m:
            if pending:
                _flush(items, seen, pending)
            # описание после «Тип N» на той же строке; чистый заголовок
            # («Наружная стена Тип 1:») даёт пустой desc — доберём ниже
            desc0 = m.group(2).strip().strip(":;-–—• ").strip()
            pending = (section, int(m.group(1)), desc0)
        elif pending:
            # строка-продолжение; одиночные числа (размеры «250», «200») — мусор
            if re.fullmatch(r"[\d\s.,;()λАВтм°∙/+-]+", line):
                continue
            # строка-заголовок без «Тип N» и без «мм» (повтор «Наружная стена...»):
            # стоп. Строка С «мм» (напр. «- перегородки из кирпича ... 250 мм»
            # внутри Типа 2) — это слой-описание, а не заголовок.
            if "мм" not in low and any(k in low for k in ("стена", "перегородк", "зашивк", "внутренние")):
                _flush(items, seen, pending)
                pending = None
                continue
            # пункт-слой «- ...»: отделяем разделителем « | » (сырьё для
            # _material_and_thickness). _clean срезает ведущий дефис, поэтому
            # маркер проверяем по сырой строке.
            if raw_line.lstrip()[:1] in ("-", "–", "—", "•"):
                pending = (pending[0], pending[1], (pending[2] + " | " + line).strip(" |"))
                continue
            pending = (pending[0], pending[1], (pending[2] + " " + line).strip())
        else:
            # В разделе, но нет накопленного типа — буллит-описание
            # без «Тип N» (например, под «Внутренние стены:»).
            if raw_line.lstrip()[:1] in ("-", "–", "—", "•"):
                n = len([it for it in items if it["section"] == section]) + 1
                items.append(_make_inner_item(line, n))
    if pending:
        _flush(items, seen, pending)
    # внутренние стены: отделяем кирпич/газоблок, которые прицепились к Типу 2.
    # Срабатывает только если раздел «Внутренние стены» уже есть в каталоге
    # (иначе легитимные слои Типа 2 будут ошибочно отщеплены).
    has_inner_section = any(it["section"] == "Внутренняя стена" for it in items)
    if has_inner_section:
        items = _fixup_outer_type2(items)
    return items


def _flush(items, seen, pending):
    """Сохраняет накопленный тип в каталог (схлопывая дубли).

    Запись: {id, section, type_no, label, material, thickness_mm, layers}.
    layers — полный пирог [{material, thickness_mm, countable}]; material /
    thickness_mm — сводка по счётным слоям (обратная совместимость).
    """
    section, type_no, desc = pending
    layers = build_layers(desc)
    material, thickness = _material_and_thickness(desc)
    item_id = f"{section}|Тип {type_no}"
    if item_id in seen:
        return
    seen.add(item_id)
    items.append({
        "id": item_id,
        "section": section,
        "type_no": type_no,
        "label": f"{section} Тип {type_no}",
        "material": material,
        "thickness_mm": thickness,
        "desc": desc,
        "layers": layers,
    })


# «Тип» + число рядом (маркер на плане): «Тип 2», «ТИП 3», «Тип\n4»
TYPE_MARKER_RE = re.compile(r"^тип$", re.IGNORECASE)


def count_markers(words):
    """Считает маркеры «Тип N» на плане по словам с координатами.

    words: [(cx, cy, word), ...]. Маркер = слово «Тип» + ближайшее число
    справа/снизу в радиусе 60 pt. Возвращает {(section_hint, type_no): count}.
    section_hint всегда None (раздел по координатам не определяем —
    привязка маркера к разделу каталога делается по номеру типа ниже).
    """
    nums = [(cx, cy, w) for cx, cy, w in words
            if w.strip().isdigit() and len(w.strip()) <= 2]
    counts = {}
    for cx, cy, w in words:
        if not TYPE_MARKER_RE.match(w.strip().strip(".,:;")):
            continue
        best, best_d = None, 60.0
        for nx, ny, nw in nums:
            dx, dy = nx - cx, ny - cy
            if dx < -5 or abs(dy) > 40 or dx > 60:
                continue
            d = (dx ** 2 + dy ** 2) ** 0.5
            if d < best_d:
                best, best_d = int(nw.strip()), d
        if best is not None:
            counts[best] = counts.get(best, 0) + 1
    return counts


def markers_by_catalog_id(items, counts):
    """Раскладывает счётчики маркеров по id каталога.

    Номер типа может встречаться в нескольких разделах («Тип 1» у наружных
    стен и у перегородок): счётчик делится поровну с пометкой — точное
    распределение требует привязки по координатам (Фаза 1, snap_to_axes).
    Возвращает {id: count | '~N (неоднозначно)'}.
    """
    from collections import defaultdict
    by_no = defaultdict(list)
    for it in items:
        by_no[it["type_no"]].append(it["id"])
    out = {}
    for type_no, n in counts.items():
        ids = by_no.get(type_no, [])
        if len(ids) == 1:
            out[ids[0]] = n
        elif ids:
            share, rest = divmod(n, len(ids))
            for i, _id in enumerate(ids):
                out[_id] = f"~{share + (1 if i < rest else 0)}?"
    return out


def print_catalog(items, markers=None):
    """Печатает каталог таблицей. markers: {id: кол-во} маркеров «Тип N» на плане."""
    markers = markers or {}
    label_w = max([len(it["label"]) for it in items] + [11])
    mat_w = max([len(it["material"] or "—") for it in items] + [8])
    mat_w = min(mat_w, 60)
    print("\n📋 НАЙДЕННЫЕ КОНСТРУКЦИИ (каталог экспликации):")
    print(f" №  {'Раздел/Тип':<{label_w}}  {'Материал':<{mat_w}}  Толщина   Маркеров")
    print("─" * (6 + label_w + mat_w + 22))
    for i, it in enumerate(items, 1):
        thick = f"{it['thickness_mm']} мм" if it["thickness_mm"] else "—"
        mat = (it["material"] or "—")[:mat_w]
        n = markers.get(it["id"], "—")
        print(f" {i:>2}  {it['label']:<{label_w}}  {mat:<{mat_w}}  {thick:<9} {n}")
    print("─" * (6 + label_w + mat_w + 22))


def parse_selection(user_input, count):
    """'3,5' / 'все' / '' → список индексов (0-based). Мусор игнорируется."""
    text = str(user_input).strip().lower()
    if text in ("", "все", "все", "all", "*"):
        return list(range(count))
    picked = []
    for part in text.replace(";", ",").split(","):
        part = part.strip()
        if part.isdigit():
            n = int(part)
            if 1 <= n <= count and (n - 1) not in picked:
                picked.append(n - 1)
    return picked


def ask_selection(count):
    """Интерактивный выбор номеров. Пустой ввод / 'все' = все типы."""
    try:
        raw = input("👉 Выберите номера через запятую (или 'все'): ")
    except (EOFError, KeyboardInterrupt):
        print()
        return list(range(count))
    picked = parse_selection(raw, count)
    if not picked:
        print("   ⚠️ Ничего не выбрано — считаю все типы.")
        return list(range(count))
    return picked
