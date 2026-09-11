# Proposal: add-llm-field-extract

## Why

Ревью требует извлечение признаков моделью. Полная замена парсеров ломает каскад 2ГИС → HTML → реестры. Нужен гибрид: парсеры остаются источником истины FOUND, модель добирает только дыры whitelist после сбора.

## What Changes

- После `collect_three` (новый сбор, `wrote=True`) для каждой точки с дырами — **один** LLM-вызов, не внутри `maps_http` и не внутри `collect_place`.
- Whitelist v1: `site_about`, `egrul_activity`. `hours` MAY в том же вызове, не отдельным запросом.
- Ответ — Pydantic `ExtractPatch`. Патч кладёт только MISSING: `trust=WEAK`, `source_url="модель"`. FOUND и уже заполненный WEAK не трогать.
- Невалидный JSON / пустой патч → поля остаются MISSING. Нет ключа (`NullLlm`) → пропуск, без падения.
- Расход добора идёт в тот же `merge_usage`, что и вердикт.
- Модуль `llm_extract.py`. Сеть сам не открывает: контекст — уже собранные строки точки.

## Capabilities

### New Capabilities

- (нет)

### Modified Capabilities

- `open-data-collect`: гибридный добор MISSING после парсеров.
- `html-freshness`: usage добора складывается через `merge_usage`.
- `project-bootstrap`: блок «Расход» включает токены добора, не только вердикта.

## Impact

- Код (другой агент): `src/salon_compare/llm_extract.py`, вызов из `app.py` после успешного `collect_three`. Тесты: `tests/test_llm_extract.py` без сети.
- Не входит: полный LLM-extract всего `PlaceRecord`, вызов из `maps_http`, отдельный вызов на каждое поле, архив change (после кода).

## Non-Goals

- Выкидывать детерминированные парсеры или подменять FOUND моделью.
- Ходить в HTTP из `llm_extract.py`.
- Менять формулу индекса, каскад 2ГИС, ключи карт.
- N вызовов модели на N дыр одной точки.
