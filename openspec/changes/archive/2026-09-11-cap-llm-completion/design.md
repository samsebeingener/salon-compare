# Design: cap-llm-completion

## Context

Вердикт: request 12:32:57 → response 12:38:06, `completion_tokens=11412`, JSON ~2k символов, канал `proxy-http`. httpx timeout 120 с не рвёт: прокси капает токены, read timeout сбрасывается.

## Decisions

- `max_tokens` по умолчанию 1500: хватит на JSON вердикта, не хватит на 11k thinking.
- Не-Kie: объект `reasoning: {"effort": "none", "exclude": true}` — контракт OpenRouter.
- Kie: без ключа `reasoning` (у них свои поля).
- `LLM_MAX_TOKENS` — целое > 0, иначе дефолт. Невалидное игнорируем.
- Не режем timeout: при живом стриме он не спасает.

## Risks

- [Провайдер режет JSON по лимиту] → `complete_verdict` уже умеет пустой/битый JSON; на экране ошибка разбора, не вечный спиннер.
- [OpenRouter 400 на reasoning] → убрать exclude, оставить effort/none или только max_tokens (hotfix).
