## ADDED Requirements

### Requirement: README про сайт на карточке 2ГИС
README SHALL записать: в браузере на карточке сайт виден; Places без `contact_groups` его не отдаёт; бот-GET 2gis.ru даёт 403 или `/museum`.

#### Scenario: README говорит про карточку 2ГИС
- GIVEN корневой README
- WHEN его читают
- THEN есть `contact_groups` и `museum`
