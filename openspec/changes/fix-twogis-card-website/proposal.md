# Proposal: fix-twogis-card-website

## Why

Карточка [Вишня на Таганке](https://2gis.ru/moscow/firm/70000001083760610) в браузере показывает сайт `vishnyasalon.ru`. Places JSON при нашем ключе `contact_groups` не отдаёт (поле платное). Бэкенд GET `2gis.ru/firm/…` через прокси LLM — 403; без прокси — редирект `/museum`, не страница с сайтом. «О нас» пустое, хотя ссылка на карточку в отчёте есть.

## What Changes

- Если в JSON нет website — один GET HTML карточки 2ГИС (уже `html_url`). Сайт студии: JSON `"type":"website"`, иначе внешний `href`/`url`, не хост 2ГИС/соцсети.
- GET `2gis.ru` (не `catalog.api`) без `HTTP_PROXY`. Редирект `/museum` — страница закрыта, не «о нас».
- Капчу не обходим. `contact_groups` в ключе не покупаем в этом change.

## Capabilities

### Modified Capabilities

- `open-data-collect`: сайт с HTML карточки 2ГИС, если JSON молчит.
- `project-bootstrap`: README — браузер видит сайт, Places без contact_groups нет, бот ловит 403/museum.

## Impact

- `html_parse.py`, `collect.py`, `html_fetch.py`, README.
- Новых пакетов нет.
