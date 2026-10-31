# Changelog

Формат — [Keep a Changelog](https://keepachangelog.com/ru/1.0.0/).
Жизнь продуктов — в их собственных ченджлогах:
[gantt-generator](gantt-generator/CHANGELOG.md),
[bim-estimate-ai](bim-estimate-ai/CHANGELOG.md).
Здесь — только изменения уровня репозитория.

## [Unreleased]

### Added
- `docs/adr/` — записи архитектурных решений (ADR-0001..0003).
- `docs/adr/README.md` — индекс ADR, формат и порядок ведения.
- `AGENTS.md` — инструкции и контекст для AI-агентов.
- `TODO.md` — живой срез состояния и план работ.
- `CHANGELOG.md` — в корне и у каждого продукта.

### Changed
- `README.md` — карта монорепо: структура, конвенции, стратегия «инкубатор → продукт».
- `AGENTS.md` — ADR повышены до обязательного правила 6; ченджлог — правило 7.
- `AGENTS.md` — усилены правила: DoD, тесты, безопасность, границы агента,
  окружение, bootstrap нового проекта; убраны устаревшие данные.
- Корневой `.gitignore` — закрывает `.env`, клиентские документы и артефакты
  сборки/тестов.
- CI `build.yml` — фильтр `paths: gantt-generator/**`, сборка EXE только при изменении генератора.

### Fixed
- Корневой `.gitignore`; `.DS_Store` и lock-файлы LibreOffice сняты с трекинга.
- Удалён дубликат `pdf-to-excel-parser/` (опечатка `parcer.py`), остался `pdf-table-extractor/`.
