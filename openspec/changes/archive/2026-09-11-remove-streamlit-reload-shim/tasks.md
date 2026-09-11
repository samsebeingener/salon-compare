## 1. OpenSpec

- [x] 1.1 Change `remove-streamlit-reload-shim`: proposal, design, tasks, дельты `streamlit-ui` и `saved-runs` — файлы на месте в `openspec/changes/remove-streamlit-reload-shim/`
- [x] 1.2 `openspec validate remove-streamlit-reload-shim --type change --strict` проходит (без archive до кода)

## 2. Store: бандл и coerce JSON

- [x] 2.1 Добавить `load_run_bundle(run_id)`: один SELECT payload, один разбор JSON → rows, usage, verdict; нет файла/id → rows пусты как у текущего `load_run` — проверить тестом в `test_store.py`
- [x] 2.2 Сделать `load_run` / `load_run_usage` / `load_run_verdict` обёртками над бандлом; отсутствие usage/verdict не падает — существующие тесты store + сценарий «обёртки совпадают с частями бандла»
- [x] 2.3 На пути чтения SQLite прогонять точки через coerce с дефолтами `map_lat`/`map_lon`, `efrsb`, `collect_ok`/`collect_error`; старый JSON без этих ключей открывается — тесты coerce + load из SQLite
- [x] 2.4 Docstring `as_sourced_field` / `coerce_place_record`: миграция схемы/dump, не reload класса — grep по исходникам не обещает «после reload»

## 3. Streamlit UI

- [x] 3.1 Убрать `_needs_collect_reload`, `importlib.reload` и hasattr-ветки из `app.py`; обычные импорты — в файле нет `importlib.reload`
- [x] 3.2 Кнопка «Открыть сохранённый» вызывает `load_run_bundle` один раз и заполняет те же ключи session_state — в `app.py` нет тройки `load_run`+`load_run_usage`+`load_run_verdict` на этот клик

## 4. Тесты и quality

- [x] 4.1 В `test_report.py` снять assertions `importlib.reload` / `reload(proxy)` / `reload(llm)`; при необходимости утверждать отсутствие reload — тест зелёный
- [x] 4.2 `uv run python scripts/run_quality.py` проходит
