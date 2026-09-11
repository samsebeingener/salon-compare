## MODIFIED Requirements

### Requirement: Поля thinking модели только для хостов Kie
Клиент чата SHALL включать `include_thoughts` и `reasoning_effort` в JSON-тело запроса только если хост `LLM_BASE_URL` — `api.kie.ai` или заканчивается на `.kie.ai`. Для прочих хостов (в том числе OpenRouter и OpenAI-совместимых) эти ключи MUST отсутствовать. Значения на Kie: `include_thoughts` ложь, `reasoning_effort` `low`. `stream` MUST быть ложь на любом хосте. Тело MUST содержать `max_tokens`: целое из `LLM_MAX_TOKENS`, если оно больше нуля, иначе 1500. Для хостов не Kie тело SHALL содержать объект `reasoning` с `effort` равным `none` и `exclude` истина, чтобы не генерировать скрытые thinking-токены. Для хостов Kie ключа `reasoning` MUST NOT быть.

#### Scenario: Kie получает thinking-поля
- GIVEN `LLM_BASE_URL` с хостом `api.kie.ai`
- WHEN собирают тело chat completions
- THEN в теле есть `include_thoughts` = ложь
- THEN в теле есть `reasoning_effort` = `low`
- THEN `stream` ложь
- THEN есть `max_tokens` 1500 (или значение из `LLM_MAX_TOKENS`)
- THEN ключа `reasoning` нет

#### Scenario: OpenRouter без thinking-полей
- GIVEN `LLM_BASE_URL` с хостом не из `*.kie.ai`
- WHEN собирают тело chat completions
- THEN ключей `include_thoughts` и `reasoning_effort` нет
- THEN `stream` ложь
- THEN есть `max_tokens`
- THEN есть `reasoning.effort` = `none`
