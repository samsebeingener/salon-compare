## MODIFIED Requirements

### Requirement: README про каскад юрполей
README SHALL указать, что после пустого ЕГРЮЛ поля ищут на `companies.rbc.ru/search/?query={ОГРН}`, и только если карточки нет — DuckDuckGo→rusprofile.

#### Scenario: README знает РБК
- GIVEN README сдачи
- WHEN его читают
- THEN есть `companies.rbc.ru` и `query`
