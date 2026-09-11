# Design: fix-llm-usage-accumulation

## Context

Вердикт модели вызывается снова, если fingerprint строк разбора сменился (правка ячейки). Сейчас `save_run_usage` кладёт в payload только `usage.model_dump()` нового ответа; `_show_verdict` при ненулевых токенах/cost **затирает** `st.session_state["llm_usage"]`. Второй вызов дешевле первого — на экране «Расход» и в SQLite остаются только последние цифры.

## Goals / Non-Goals

**Goals:**

- Сложить prompt/completion/total/cost по всем успешным вызовам одного разбора.
- Не терять накопленное, если повторный вызов вернул пустой `LlmUsage()`.
- Не писать пустышку в БД в этом случае.
- Регрессия store: `1200 + 1050 = 2250` `total_tokens`.

**Non-Goals:**

- Менять формулу `estimated_usd_parts` / тарифы `.env` (складывается уже известный `cost`).
- Накапливать usage между разными `run_id`.
- Менять UI-вёрстку блока «Расход» кроме источника цифр.

## Decisions

- **`merge_usage(a, b) -> LlmUsage` в `llm.py`:** для каждого поля (`prompt_tokens`, `completion_tokens`, `total_tokens`, `cost`) `None`-safe сумма: оба `None` → `None`; иначе `(a or 0) + (b or 0)`. `total_tokens` не пересчитывать из prompt+completion, если оба total уже заданы — складывать total как есть. Если у одной стороны total `None`, а у другой число — результат это число (как `None+5=5`).
- **`save_run_usage`:** после `_payload_parts` прочитать `_old`; если словарь — `LlmUsage.model_validate`; merge с новым; записать merge. Нет run / битый JSON — как сейчас (no-op).
- **UI `_show_verdict`:** если у нового `usage` есть `total_tokens` или `cost` — `session["llm_usage"] = merge_usage(старый session или пустой, usage)` и `save_run_usage`. Если оба поля пустые — не трогать session (если там уже накопление) и не вызывать `save_run_usage`. Первый вызов без usage по-прежнему может положить пустой объект в session, чтобы экран показал «токены не найдены».
- **Тест:** два последовательных `save_run_usage` на один `run_id`: `total_tokens=1200` затем `1050` → load `2250`; prompt/completion/cost тоже суммы.

## Risks / Trade-offs

- [Двойной complete без смены fingerprint] → не копится: UI вызывает модель только при смене `llm_fp`.
- [Открытие сохранённого разбора] → load кладёт usage из payload; повторный live-вызов поверх SavedRun сольётся с загруженным — это желаемое «все вызовы этого run».
- [cost None + cost 0.1] → 0.1; два cost складываются в float без округления в store.
