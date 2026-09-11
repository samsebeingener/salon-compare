## ADDED Requirements

### Requirement: Catalog API 2ГИС без прокси окружения
HTTP-клиент Catalog API 2ГИС (`catalog.api.2gis.com`: поиск `/3.0/items`, карточка `/3.0/items/byid`, соседи) MUST вызывать httpx с `trust_env` ложь. Система MUST NOT направлять эти запросы через `HTTP_PROXY` / `HTTPS_PROXY` из окружения. Клиент модели MAY по-прежнему использовать прокси. Сбой сети SHALL по-прежнему давать пустой поиск / пустую карточку, без падения приложения. Живой HTTP в тестах MUST NOT вызываться.

#### Scenario: Поиск не передаёт trust_env истину
- GIVEN `TwoGisApi` и подмена `httpx.get`
- WHEN вызывают search
- THEN в kwargs вызова `trust_env` ложь
- THEN сеть не открывается

#### Scenario: HTML API-хоста 2ГИС тоже напрямую
- GIVEN URL на хосте `catalog.api.2gis.com` или `2gis.ru`
- WHEN считают kwargs HTML-клиента
- THEN `trust_env` ложь
