## MODIFIED Requirements

### Requirement: Секреты не в git, образец окружения есть
Система MUST не включать `.env` в git. Репозиторий SHALL содержать отслеживаемый `.env.example` с плейсхолдером `TWOGIS_API_KEY`, переменными `LLM_*`, `HTTP_PROXY` и `HTTPS_PROXY`. Система MUST NOT требовать `YANDEX_MAPS_API_KEY`. Docker Compose SHALL передавать в контейнер `TWOGIS_API_KEY` и переменные `LLM_*`.

#### Scenario: .env.example содержит ключи каркаса
- GIVEN клонированный репозиторий без локального `.env`
- WHEN открывают `.env.example`
- THEN в нём есть `TWOGIS_API_KEY`, переменные с префиксом `LLM_`, `HTTP_PROXY` и `HTTPS_PROXY`
- THEN в нём нет `YANDEX_MAPS_API_KEY`
