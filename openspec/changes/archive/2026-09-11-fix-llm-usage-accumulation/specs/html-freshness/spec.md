## MODIFIED Requirements

### Requirement: Расход токенов запуска
После вызова модели система SHALL показать число токенов из ответа API (`usage.total_tokens` или сумма prompt/completion). Стоимость MUST браться из `usage.cost` (как у OpenRouter), без выдуманного тарифа. Если `cost` нет, MAY посчитать по `LLM_USD_PER_1M_*`. Иначе стоимость MUST быть «не найдена». Отсутствие ключа модели MUST оставить расход пустым, без падения. Старый SQLite без блока usage MUST открываться. Расход SHALL накапливаться по всем успешным вызовам модели в рамках одного разбора (`merge` prompt/completion/total/cost), MUST NOT перезаписываться последним вызовом. Пустой usage нового вызова MUST NOT затирать накопленное и MUST NOT записываться в SQLite вместо суммы.

#### Scenario: Ответ с usage, тарифа нет
- GIVEN `usage.prompt_tokens=100` и `completion_tokens=50`, поля `cost` нет, тарифы пустые
- WHEN считают расход
- THEN токены 150
- THEN стоимость не найдена

#### Scenario: OpenRouter прислал cost
- GIVEN `usage.total_tokens=196` и `usage.cost=0.95`
- WHEN считают расход
- THEN токены 196
- THEN стоимость 0.95 из ответа, не из `.env`

#### Scenario: Два успешных вызова в одном разборе
- GIVEN у разбора уже сохранён usage с `total_tokens=1200`
- AND повторный вызов модели вернул `total_tokens=1050`
- WHEN сохраняют расход запуска
- THEN в payload `total_tokens=2250`
- THEN prompt/completion/cost сложены None-safe (`None+5=5`, `None+None=None`)

#### Scenario: Пустой usage повторного вызова
- GIVEN в разборе уже есть накопленные токены
- AND новый вызов вернул пустой `LlmUsage` (нет `total_tokens` и нет `cost`)
- WHEN показывают расход и пишут SQLite
- THEN накопленные токены на экране остаются
- THEN в БД не пишут пустышку вместо суммы
