# Proposal: cap-llm-completion

## Why

Спиннер «Ждём ответ модели» крутится минуты: Qwen на OpenRouter жрёт тысячи thinking-токенов на короткий JSON (живой прогон: ~11k completion / 5 мин). Прокси при этом отвечает. Нужен жёсткий потолок ответа и выключение reasoning вне Kie.

## What Changes

- В тело chat completions всегда `max_tokens` (по умолчанию 1500, `LLM_MAX_TOKENS`).
- Для не-Kie хостов: `reasoning.effort = none` (без скрытого thinking).
- Kie: как сейчас `include_thoughts` / `reasoning_effort`, плюс тот же `max_tokens`.

## Capabilities

### Modified Capabilities

- `project-bootstrap`: лимит completion и reasoning на OpenRouter.

## Impact

- `llm.py` `chat_payload`, `.env.example`, тесты payload.
