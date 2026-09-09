## ADDED Requirements

### Requirement: Слабая полка и описание fallback без ключа
Таблица MUST отличать полку «слабо» от «не найдено» и от подтверждённого первоисточника. README SHALL описать контур DuckDuckGo HTML → карточка rusprofile без API-ключа и паузу между запросами.

#### Scenario: Ячейка слабо
- GIVEN юрполе с полкой слабо и URL rusprofile
- WHEN рисуют таблицу
- THEN в ячейке есть значение, слово «слабо» и ссылка

#### Scenario: README без ключа rusprofile
- GIVEN README репозитория
- WHEN его читают
- THEN там есть DuckDuckGo, rusprofile и пауза
- THEN нет требования платного ключа rusprofile
