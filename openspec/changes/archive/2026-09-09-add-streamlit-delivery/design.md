# Design: add-streamlit-delivery

## Context

UI (зацепки, таблица, карточки, сохранённые прогоны) уже в `main`. Дырка сдачи — README.

## Decisions

- Не плодить второй экран. Проверяем, что в `app.py` по-прежнему три поля, отчёт и список разборов; в README — секции укладки, БД, рамки, агент.
- Агент в абзаце — Cursor Agent. Модель этой сдачи — Cursor Grok 4.6. Не приписывать Claude/GPT.
- Человек: ПОДГОТОВКА, merge, `.env`, запрет новых пакетов. Агент: OpenSpec, красный тест, код, PR.
- SQLite: одна таблица `runs` (`id`, `created_at`, `payload` JSON). Ключи в payload не пишем.
- Старые проверки README (прокси, rusprofile, живой прогон, sqlite) сохранить.

## Non-Goals

Парсер часов/отзывов 90 дней. Расход токенов. Archive OpenSpec. Новые зависимости.
