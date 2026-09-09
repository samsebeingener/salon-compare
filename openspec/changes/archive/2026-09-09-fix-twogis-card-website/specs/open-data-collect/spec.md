## ADDED Requirements

### Requirement: Сайт студии с HTML карточки 2ГИС
Если JSON 2ГИС не содержит website, система SHALL сделать один GET `html_url` карточки. Website MUST браться из явного маркера: JSON `"type":"website"` и url/value, иначе внешняя http(s)-ссылка не на хост 2ГИС и не соцсеть. Этот URL MAY дальше открываться для поля «о нас». Нет маркера или HTML закрыт — «о нас» MUST NOT выдумываться с домена 2gis.ru.

#### Scenario: В HTML карточки есть type website
- GIVEN JSON без contact_groups и HTML карточки с `"type":"website"` и `vishnyasalon.ru`
- WHEN собирают точку с зацепкой-названием
- THEN «о нас» грузится с `https://vishnyasalon.ru`, не с `2gis.ru`

#### Scenario: HTML карточки закрыт
- GIVEN GET карточки 2ГИС статус `blocked`
- WHEN собирают точку без URL в зацепке
- THEN отдельный сайт не угадывается
- THEN «о нас» — «не найдено»

### Requirement: 2gis.ru HTML без прокси LLM, museum закрыт
GET страницы `2gis.ru` (не Catalog API) MUST идти без `HTTP_PROXY`/`HTTPS_PROXY`. Если финальный путь `/museum`, статус MUST быть `blocked`.

#### Scenario: Редирект на museum
- GIVEN ответ 200 с URL path `/museum`
- WHEN классифицируют fetch
- THEN статус `blocked`
