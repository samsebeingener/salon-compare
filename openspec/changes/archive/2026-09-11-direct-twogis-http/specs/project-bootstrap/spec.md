## MODIFIED Requirements

### Requirement: Прокси для LLM из РФ
Система SHALL читать `HTTP_PROXY` и `HTTPS_PROXY` из окружения. Клиент к модели MUST ходить через эти переменные (явный `proxy` и/или `trust_env`), чтобы при недоступности LLM из РФ работал прокси. Пустые значения MUST означать работу без прокси. Запросы Catalog API 2ГИС MUST NOT идти через этот прокси. README SHALL описывать эти переменные и что 2ГИС идёт напрямую.

#### Scenario: Образец и клиент уважают прокси
- GIVEN в `.env.example` есть `HTTP_PROXY` и `HTTPS_PROXY`
- WHEN собирают HTTP-клиент для модели
- THEN клиент использует прокси из окружения (не голый выход к LLM, если прокси задан)
- THEN в README указано, зачем прокси нужен из РФ

#### Scenario: README говорит что 2ГИС без прокси LLM
- GIVEN README проекта
- WHEN его читают
- THEN указано, что Catalog API / страницы 2ГИС не гоняют через `HTTP_PROXY`/`HTTPS_PROXY`
