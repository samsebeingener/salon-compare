# Design: add-report-corrections

## Context

Формула уже считает `PlaceScore` по полям. Модель не должна заново искать факты: только объяснить уже посчитанное.

## Decisions

- Схема ответа: `interesting`, `why_better`, `breaks_if`; опционально `compared_index` (число, в том числе из строки). `extra="ignore"`.
- Пустой JSON, не-JSON, нет обязательных полей → `None`, UI пишет «вывод модели не разобран» или «не найден (нет ключа)».
- Клиент: OpenAI-compatible `POST {LLM_BASE_URL}/chat/completions`, `httpx`, `trust_env=True`. Нет ключа/URL/модели → `NullLlm`, `complete` = пустая строка.
- Правка: `SourcedField(trust=WEAK, source_url="правка человека")`. Рабочая копия строк в `session_state`, без нового collect.
- `PlaceRecord.unreliable: bool = False`. Старый SQLite без поля читается. `score_place` при флаге: `index=None`, пометка «недостоверный».
- Вызов модели кэшируется по отпечатку рабочих строк, чтобы виджеты Streamlit не били API на каждый rerun.

## Non-Goals

Токены и стоимость запуска. Парсер HTML отзывов. Смена провайдера кодом (только `LLM_*`).
