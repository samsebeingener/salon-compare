# Design: fix-twogis-card-website

## Context

`MapCard.website` только из `contact_groups`. Ключ без доплаты поле обнуляет. `html_url` уже есть и уходит в таблицу как источник рейтинга. HTML карточки для сайта не читали. `HttpxHtmlFetcher` шлёт все GET через `trust_env` — прокси LLM банится на 2gis.ru.

## Decisions

- Сначала JSON website. Нет — GET `html_url`, `OpenHtmlParser.website`.
- Маркеры: `"type":"website"` + url/value; иначе первый http(s) `href`, хост не 2gis/yandex/google/соцсети. Голый домен → `https://`.
- `2gis.ru` HTML: `trust_env=False`. `catalog.api.2gis.com` как сейчас.
- Path `/museum` → `blocked` (антибот), тело не разбираем как карточку.
- Не парсим «о нас» с домена 2gis.ru.

## Risks

- [Домашний IP тоже museum] → сайт «не найдено»; нужен contact_groups на ключе или зацепка-URL.
- [Чужая ссылка в рекламе] → берём type=website в приоритете.
