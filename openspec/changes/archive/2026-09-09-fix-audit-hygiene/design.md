# Design: fix-audit-hygiene

## Context

`collect._field` зовёт `parser.parse` для rating/about/address. `OpenHtmlParser` отдаёт только hours / last_review / plus_minus. Тесты collect закрыты FakeParser — ложная зелень.

`MapsSearchResolver` на MAPS_LINK возвращает `yandex:{id}` без поиска 2ГИС. `TwoGisApi.fetch_card` такой id не грузит.

## Goals / Non-Goals

**Goals:** честный HTML-каскад; Яндекс-URL со slug → 2ГИС; доки = код; выкинуть мёртвые классы.

**Non-Goals:** тип точки / мастера; GET HTML Яндекса; новые пакеты.

## Decisions

- About: JSON-LD `description`, иначе `meta name=description`, иначе текст после заголовка «О нас» / «О студии» (до 280 символов). Нет маркера — None.
- Rating / review_count / address: только JSON-LD `aggregateRating` / `address`. Не угадывать по `class="rating"`.
- Neighbors из HTML не парсим (нет надёжного маркера).
- Яндекс URL `/org/{slug}/{id}`: query = slug с `_` → пробел, `twogis.search`. Хиты — наружу (уточнение если >1). Ноль хитов — оставляем `yandex:` кандидата, поля карт «не найдено».
- `/org/{digits}`: поиск 2ГИС не выдумываем.
- Live specs правим в этом change, не только в delta drop-yandex.
- ПОДГОТОВКА: короткие пометки «снято, см. решение про Яндекс», исходный текст задания не стираем.

## Risks

- [Slug не имя салона] → 2ГИС вернёт чужие карточки → пользователь подтверждает, первую не берём.
- [Описание в meta — реклама] → полка found со ссылкой на сайт, не выдумка текста.
