## ADDED Requirements

### Requirement: Поиск сайта через DDG при пустых картах
Если после зацепки, JSON 2ГИС и HTML карточки нет URL сайта, система SHALL один раз искать DuckDuckGo HTML по названию и адресу точки. Первые подходящие внешние http(s) URL MAY открываться для «о нас». Агрегаторы (Яндекс.Карты, Zoon, соцсети) MUST NOT подставляться как сайт студии.

#### Scenario: 2ГИС HTML blocked, DDG находит vishnyasalon.ru
- GIVEN карточка 2ГИС без website, GET карточки `blocked`
- AND DDG HTML содержит `result__a` на `https://vishnyasalon.ru/`
- WHEN собирают «Вишня Таганская» с адресом
- THEN «о нас» грузится с `vishnyasalon.ru`

### Requirement: Сайт с карточки РБК по ОГРН
При зацепке ОГРН система SHALL открыть карточку компании на РБК (из поиска по ОГРН) и взять URL из блока «Сайт» для поля «о нас».

#### Scenario: ОГРН → ilike-nails.ru с РБК
- GIVEN поиск РБК по ОГРН и id-страница с `Сайт` → `http://ilike-nails.ru`
- WHEN собирают точку с зацепкой ОГРН
- THEN URL студии открывается для «о нас»

### Requirement: ОГРН/ИНН на внутренних страницах сайта
Если на загруженной странице сайта нет labeled ОГРН/ИНН, система SHALL следовать по same-host ссылкам с path, содержащим контакты/политику/реквизиты (лимит GET), и искать labeled маркеры.

#### Scenario: ОГРН на /politica
- GIVEN главная без ОГРН, `/politica` с `ОГРН: 1234567890123`
- WHEN собирают сайт
- THEN `extra_ogrn` передаётся в юрблок
