# Proposal: fix-llm-usage-accumulation

## Why

`save_run_usage` подменяет блок `usage` в payload последним ответом модели. Повторный вердикт после правки ячейки стирает уже учтённые токены и деньги. Экран «Расход» и SQLite должны показывать сумму всех успешных вызовов в рамках разбора.

## What Changes

- `llm.merge_usage(a, b)`: сумма `prompt_tokens` / `completion_tokens` / `total_tokens` / `cost`; None-safe (`None+5=5`, `None+None=None`).
- `save_run_usage` читает старый usage и сохраняет merge, а не замену.
- UI: при успехе merge в `st.session_state["llm_usage"]`; пустой usage нового вызова MUST NOT затирать накопленное и MUST NOT писать пустышку в БД.
- Тест store: два `save_run_usage` подряд `1200+1050=2250`.

## Capabilities

### New Capabilities

- (нет)

### Modified Capabilities

- `html-freshness`: расход SHALL накапливаться по всем успешным вызовам модели в разборе, не перезаписываться последним.
- `project-bootstrap`: экран «Расход» показывает накопленные токены/стоимость разбора.

## Impact

- Код (другой агент): `src/salon_compare/llm.py` (`merge_usage`), `store.py` (`save_run_usage`), `app.py` (session + persist). Тесты: `tests/test_store.py` (два save подряд).
- Не входит: смена провайдера LLM, тарифы `.env`, схема SQLite, scoring, карта.

## Non-Goals

- Менять `usage_from_response` и оценку USD по тарифам, кроме сложения уже посчитанных `cost`.
- Сбрасывать накопление при новом разборе (другой `run_id` / новый сбор) — это отдельный запуск.
- Писать usage в БД, если у нового вызова нет токенов и нет cost.
