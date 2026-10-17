# TODO & Context

> Автообновляемый срез состояния проекта `dev-tools` и плана действий.
> Обновлять при закрытии задач. Дата актуализации: 2026-10-17.

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

## 📌 TODO — сейчас (ветка feature/interactive-tasks)

- [ ] Доработать интерактивный редактор задач gantt-generator (текущая работа).
- [ ] Заменить тестовые `tasks.json` реальным графиком перед мержем в `main`
      (см. «Исторический хвост» выше).
- [ ] Открыть PR `feature/interactive-tasks` → `main` после завершения работ.

## 📌 TODO — ближайшее (dev-tools)

- [ ] Тест на `extract_walls.parse_height()` / расчёт объёма (pytest).
- [ ] Убрать абсолютные пути из `bim-estimate-ai/*.py` (через `Path(__file__)` или аргументы CLI).
- [ ] `requirements.txt` для `gantt-generator` (openpyxl) и общий CI-lint (ruff) на push.
- [ ] README для `gantt-generator` (скриншот, установка, формат `tasks.json`).
- [ ] Ревью: два PDF-скрипта (`bim-estimate-ai/extract_walls.py`,
      `pdf-table-extractor`) — не дублируют ли логику, нужна ли общая утилита.

## 📌 TODO — будущее (когда проекты созреют)

- [ ] `gantt-generator` → отдельный репозиторий (`gh repo create`), в `dev-tools` — ссылка в README.
      Порядок описан в README, раздел «Стратегия развития».
- [ ] `bim-estimate-ai` → отдельный репозиторий при появлении тестов / веб-интерфейса /
      внешнего пользователя.
- [ ] Для `bim-estimate-ai`: тесты → свой CI → версии (semver) → переезд.
- [ ] Проверить историю `dev-tools` на предмет случайно закоммиченных секретов:
      `git log --all --diff-filter=A --name-only | grep -E '\.env|\.pdf'`
      (при обнаружении — отозвать ключ в console.groq.com).
