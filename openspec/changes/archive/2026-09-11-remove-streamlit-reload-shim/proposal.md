# Proposal: remove-streamlit-reload-shim

## Why

`app.py` на каждом rerun Streamlit делает `importlib.reload` модулей (`collect`, `store`, `score`, `report`, `proxy`, `llm`), потому что hot-reload иначе оставляет в памяти старые классы. Это костыль: `as_sourced_field` и `coerce_place_record` заточены под смену identity класса, UI трижды читает один JSON SQLite (`load_run` / `load_run_usage` / `load_run_verdict`), тесты фиксируют сам reload. После стабилизации схемы `PlaceRecord` reload не нужен.

## What Changes

- Убрать `importlib.reload` и `_needs_collect_reload` из `app.py`; обычные импорты.
- `as_sourced_field` / `coerce_place_record` оставить только как миграцию старых JSON из SQLite (нет `map_lat`/`efrsb`/`collect_ok` и т.п.), не как защиту от reload.
- `store.load_run_bundle(run_id)`: одно чтение payload → `rows`, `usage`, `verdict`. `load_run` / `load_run_usage` / `load_run_verdict` MAY стать обёртками.
- UI «Открыть сохранённый» SHALL брать бандл одним вызовом, без трёх SELECT одного `payload`.

## Capabilities

### New Capabilities

- (нет)

### Modified Capabilities

- `streamlit-ui`: нет reload-shim; открытие разбора через `load_run_bundle`.
- `saved-runs`: одно чтение JSON на бандл; coerce только для схемы старых payload.

## Impact

- Код (другой агент): `app.py`, `store.py`; при необходимости упростить docstring/`as_sourced_field` в `collect.py` (без смены каскада сбора). Тесты: `test_report.py` (сейчас требует `importlib.reload`), `test_store.py`.
- Не входит: scoring, карта Яндекс, каскад collect, схема SQLite-таблицы `runs`.

## Non-Goals

- Менять формат payload `{rows, usage, verdict}`.
- Удалять coerce для старых JSON без новых полей.
- Чинить hot-reload Streamlit другим механизмом (watchdog, `--server.runOnSave` и т.д.).
