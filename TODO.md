# TODO & Context

> Автообновляемый срез состояния проекта `dev-tools` и плана действий.
> Обновлять при закрытии задач. Дата актуализации: 2026-10-17 (вечер:
> закрыты PR #2–#5, ветка feature/bim-estimate-axes удалена по правилу 9).

## 🧭 Контекст (как понято)

**Репозиторий** — личный monorepo-инкубатор `oleg1981ekb-ai/dev-tools` для утилит
одного разработчика. Стратегия — «инкубатор → продукт»: папка живёт здесь, пока
не созреет для отдельного репозитория (критерии — в [README](README.md)).

**Направления:**

| Направление | Папка | Стадия | Ветка работ |
|---|---|---|---|
| Графики (Ганта → Excel) | `gantt-generator/` | Продукт, CI собирает Windows EXE | `feature/interactive-tasks` |
| Расчёты по чертежам (PDF → смета) | `bim-estimate-ai/` | PoC | — |
| Общая утилита PDF → Excel | `pdf-table-extractor/` | Утилита | — |

**Принятые правила (закреплены):**
- Секреты (`.env`, `GROQ_API_KEY`) и клиентские PDF/чертежи — **никогда** в git
  (см. корневой `.gitignore` и `.gitignore` в `bim-estimate-ai`).
- Один коммит — одна тема.
- CI генератора запускается только при изменении `gantt-generator/**` (фильтр `paths`).
- Графики и расчёты — **два разных продукта**, в перспективе два отдельных репозитория.

**Исторический хвост (знать):**
- В `feature/interactive-tasks` закоммичены тестовые данные
  `gantt-generator/tasks.json` («а», «ук») — реальный график «Захватка №1.
  Фундаментная плита» восстанавливается из истории: `git show e359bdf^:gantt-generator/tasks.json`
  (коммит до `6679389`).
- Коммит `3a7fd47` объединил docs+ci (отступление от правила «одна тема») —
  оставлено осознанно, rewrite запушенного `main` не оправдан.

## ✅ Закрыто (2026-10-17)

- [x] `bim-estimate-ai` залит в GitHub: секреты и PDF исключены, README + requirements созданы.
- [x] Удалён дубликат `pdf-to-excel-parser/`, остался `pdf-table-extractor/`.
- [x] Корневой `.gitignore`; `.DS_Store` и lock-файлы сняты с трекинга.
- [x] CI: добавлен `paths: ['gantt-generator/**']` в push/pull_request.
- [x] README монорепо расширен: структура, конвенции, стратегия развития.
- [x] `main` влита в `feature/interactive-tasks` (конфликтов нет), обе ветки запушены.
- [x] PR #5 (Фаза 0 v2: сканер кружков осей) доведён до мержа; ось «1» не в кружках —
      это нормально для чертежа (первая ось без окружности), source='row', conf='medium';
      ветка feature/bim-estimate-axes удалена по правилу 9.

## 📌 TODO — сейчас (ветка feature/interactive-tasks)

- [ ] Доработать интерактивный редактор задач gantt-generator (текущая работа).
- [ ] Заменить тестовые `tasks.json` реальным графиком перед мержем в `main`
      (см. «Исторический хвост» выше).
- [ ] Открыть PR `feature/interactive-tasks` → `main` после завершения работ.

## 📌 TODO — ближайшее (bim-estimate-ai, ветка feature/bim-estimate-axes, PR #5 OPEN)

- [ ] Каталог типов + интерактивный выбор («что считаем»): `parse_spec_catalog()`,
      парсинг экспликации по разделам (Типы 1/2 наружных стен ≠ Типы 1..5 перегородок),
      флаги `--types 3,5 --height 2.8`, CSV только по выбранным.
- [ ] Фаза 1+3: `build_axis_grid()` + `snap_to_axes()` с тестами; калибровка px→мм (A1: 2.833 pt/мм).
- [ ] Неподписанные перегородки: длина через расстояние осей / `get_drawings` / флаг `review`
      + колонки `Источник`/`Confidence` в таблице.
- [ ] Штриховка: `detect_hatch_fields()` + `classify_shape()` (87 полей найдено в probe).
- [ ] Единый CLI: `--mode {ai,regex}`, общий формат CSV.

## 📌 TODO — ближайшее (dev-tools, общее)

- [x] Тесты на `extract_walls` (pytest) — PR #2 (29 тестов, зелёные).
- [x] Убрать абсолютные пути из `bim-estimate-ai/*.py` — PR #3 (`Path(__file__)`).
- [x] Полный отчёт расчёта (`build_report`/`print_report`, CSV 11 столбцов) — PR #4.
- [x] Решения ADR-0001..0003 зафиксированы в `docs/adr/`.
- [ ] `requirements.txt` для `gantt-generator` (openpyxl) и общий CI-lint (ruff) на push.
- [ ] README для `gantt-generator` (скриншот, установка, формат `tasks.json`).
- [ ] Ревью: два PDF-скрипта (`bim-estimate-ai/extract_walls.py`,
      `pdf-table-extractor`) — не дублируют ли логику, нужна ли общая утилита.
- [ ] Свой CI для `bim-estimate-ai` (`paths: bim-estimate-ai/**`: pytest + ruff).

## 📌 TODO — будущее (когда проекты созреют)

- [ ] `gantt-generator` → отдельный репозиторий (`gh repo create`), в `dev-tools` — ссылка в README.
      Порядок описан в README, раздел «Стратегия развития».
- [ ] `bim-estimate-ai` → отдельный репозиторий при появлении веб-интерфейса /
      внешнего пользователя (тесты уже есть — 29 pytest, PR #2).
- [ ] Для `bim-estimate-ai`: свой CI → версии (semver) → переезд.
      Решения фиксировать в `docs/adr/` (формат: Контекст → Решение → Последствия;
      принятые ADR не правятся задним числом — отмена только новым ADR).
- [ ] Проверить историю `dev-tools` на предмет случайно закоммиченных секретов:
      `git log --all --diff-filter=A --name-only | grep -E '\.env|\.pdf'`
      (при обнаружении — отозвать ключ в console.groq.com).
