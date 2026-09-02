## MODIFIED Requirements

### Requirement: Секреты не в git, образец окружения есть
Система MUST не включать `.env` в git. Репозиторий SHALL содержать отслеживаемый `.env.example` с плейсхолдером `TWOGIS_API_KEY`, переменными `LLM_*`, `HTTP_PROXY` и `HTTPS_PROXY`. Система MUST NOT требовать `YANDEX_MAPS_API_KEY`. Docker Compose SHALL передавать в контейнер `TWOGIS_API_KEY` и переменные `LLM_*` из окружения или файла `.env`.

#### Scenario: .env не коммитится
- GIVEN в рабочей копии есть файл `.env` с любыми значениями
- WHEN проверяют индекс git и правила игнорирования
- THEN `.env` не предназначен для коммита

#### Scenario: .env.example содержит ключи каркаса
- GIVEN клонированный репозиторий без локального `.env`
- WHEN открывают `.env.example`
- THEN файл есть в git
- THEN в нём есть `TWOGIS_API_KEY`, переменные с префиксом `LLM_`, `HTTP_PROXY` и `HTTPS_PROXY`
- THEN в нём нет `YANDEX_MAPS_API_KEY`

#### Scenario: Compose прокидывает ключ карт
- GIVEN заполненный `.env` с ключом 2ГИС
- WHEN поднимают приложение через Docker Compose
- THEN контейнер получает `TWOGIS_API_KEY`
- THEN `YANDEX_MAPS_API_KEY` в compose нет
