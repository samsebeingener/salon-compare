# Design: add-sqlite-saved-runs

## Context

`collect_three` вызывается в ветке READY на каждый rerun Streamlit. Юрблок с паузой 3 с это ломает. Сценарий подготовки «старый отчёт» требует файл SQLite. Docker уже имеет `/app/data`.

## Goals / Non-Goals

**Goals:** сохранить строки таблицы, открыть без сети, не дёргать сбор повторно в сессии.

**Non-Goals:** индекс, LLM, миграции Alembic, многопользовательский доступ.

## Decisions

- Файл: `data/salon-compare.sqlite` от корня репозитория (`Path(__file__).parents[2] / "data" / ...`). Тесты передают `tmp_path`.
- Таблица `runs(id INTEGER PK, created_at TEXT, payload TEXT)`. Payload — JSON списка `PlaceRecord`.
- `LegalOrg` остаётся структурой в записи; сериализация через Pydantic `model_dump` / `model_validate`.
- Кэш: `session_state` ключ из venue_id + legal_choices. Промах — `collect_three` + `save_run`. Попадание — взять кэш.
- Кнопка «Открыть сохранённый» кладёт строки в `session_state["saved_rows"]` и показывает таблицу с текстом, что нового поиска нет.
- «Разобрать зацепки» сбрасывает `saved_rows`.

## Risks / Trade-offs

- Схема payload вырастет вместе с полями — читаем текущим `PlaceRecord`; несовместимый JSON → пропуск записи, не падение приложения.
