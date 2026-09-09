# Design: add-twogis-moscow-region

## Context

`TwoGisApi.search` звал `/3.0/items` только с `q`. Без геоограничения Catalog отвечает meta.code 404 `itemNotFound`. С `region_id=32` запрос «Вишня» в Москве находит салоны.

## Decisions

- Константа `MOSCOW_REGION_ID = "32"` из документации 2ГИС (Regions API, пример Москва). Не дергать `/2.0/region/search` на каждый поиск: лишний запрос и квота.
- Одна функция параметров для `search` и fallback `q=title` в `fetch_card`.
- `byid` и соседи (`point`+`radius`) без `region_id`.

## Risks

- Если 2ГИС сменит id Москвы — поиск снова пустой, правится константа.
- Несколько «Вишня» в Москве — по-прежнему список на подтверждение, первую не берём.
