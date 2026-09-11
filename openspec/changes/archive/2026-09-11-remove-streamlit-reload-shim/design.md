## Context

См. proposal.md — Why. Сейчас `app.py` после импортов делает `_needs_collect_reload` + серию `importlib.reload`; `as_sourced_field` в docstring явно про «класс уже другой». `load_run` / `load_run_usage` / `load_run_verdict` каждый открывает SQLite и парсит тот же `payload`. `_load_rows` валидирует `PlaceRecord` напрямую; `coerce_place_record` в основном в UI/кэше/`yandex_viz`. Тест `test_report.py` требует строки `importlib.reload` в `app.py`.

## Goals / Non-Goals

**Goals:**

- Убрать reload-shim из точки входа Streamlit.
- Один SELECT + один `json.loads` на открытие разбора.
- Coerce оставить как миграцию схемы старых payload.

**Non-Goals:**

- Новый формат SQLite / миграция таблицы `runs`.
- Альтернативный hot-reload Streamlit.
- Менять каскад collect, scoring, карту Яндекс.

## Decisions

- **Импорты в `app.py`:** обычные `from salon_compare.X import ...` / `import salon_compare.X as X`. Удалить `_needs_collect_reload`, все `importlib.reload`, ветки `if not hasattr(..., "as_sourced_field"|"coerce_place_record")`. `importlib` убрать, если больше не используется. Альтернатива (оставить reload «на всякий случай») отвергнута: это и есть костыль.
- **`load_run_bundle(run_id, path=None)`:** сигнатура рядом с `load_run`. Возвращает `(rows | None, usage | None, verdict | None)` или небольшой named tuple / dataclass — на усмотрение реализации, главное: один `_connect` + один `_payload_parts` / `_load_rows`. Если файла или id нет — `rows is None` (как сейчас `load_run`). Битый JSON — как сейчас (`None` / пустые части, без исключения наружу).
- **Обёртки:** `load_run` = rows из бандла; `load_run_usage` / `load_run_verdict` = соответствующие поля. Существующие тесты на отдельные функции сохраняют контракт. Альтернатива (удалить три функции) — лишний churn; не делать в этом change.
- **Coerce на пути SQLite:** `_load_rows` (или бандл) пропускает каждую точку через `coerce_place_record` / дефолты `setdefault` для `map_lat`/`map_lon`, `efrsb`, `collect_ok`/`collect_error` до `model_validate`. Цель — старые JSON, не `isinstance` после reload. `as_sourced_field` MAY принимать dict и простой namespace (тесты `test_as_sourced_field_accepts_plain_namespace`), но docstring MUST описывать миграцию/чужой dump, не reload.
- **UI:** кнопка «Открыть сохранённый» вызывает `load_run_bundle` один раз и кладёт части в `session_state` (те же ключи, что сейчас).
- **Тесты:** убрать из `test_report.py` assertions `importlib.reload` / `reload(proxy)` / `reload(llm)`. Добавить тест store: бандл совпадает с тройкой обёрток; при желании — что `_payload_parts` на вызов бандла один раз (мок `json.loads` или счётчик). Тесты coerce старых JSON оставить.

## Risks / Trade-offs

- [После снятия reload Streamlit снова покажет stale class при правке `.py` без рестарта процесса] → Mitigation: рестарт `streamlit run`; не возвращать shim.
- [Старые payload без coerce в `_load_rows` сейчас могут падать на validation] → Mitigation: coerce на load из SQLite; это сужение дыры, не смена формата.
- [Три обёртки снова читают БД по отдельности, если UI забудут перевести] → Mitigation: UI только бандл; обёртки для тестов/прочих вызовов допустимы.

## Migration Plan

- Код и тесты в одном PR. Базу не мигрировать.
- Rollback: вернуть reload в `app.py` и тройной load — нежелателен; при регрессии UI достаточно рестарта процесса.
