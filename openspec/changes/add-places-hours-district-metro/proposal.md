# Proposal: add-places-hours-district-metro

## Why

Places API уже отдаёт график, район и ближайшее метро. В таблице часы «не найдено», района и метро нет — мы их не разбираем.

## What Changes

- Часы из `schedule` (сжатая строка вроде `пн-вс 10:00-22:00`).
- Район из `adm_div` type=district.
- Метро: ближайшая станция с `route_types` metro и расстояние.
- В запрос Places: `items.adm_div`, `items.links`. `items.schedule` уже просим.
- Нет поля — «не найдено», без выдумки. Geocoder/Suggest не подключаем.

## Capabilities

### New Capabilities

- (нет)

### Modified Capabilities

- `open-data-collect`: часы, район и метро из JSON 2ГИС Places.

## Impact

- Код: `maps_parse.py`, `maps_http.py`, `collect.py`, таблица Streamlit, `FIELD_LABELS`.
- Не входит: даты отзывов, плюс/минус, услуги, формула локации, Geocoder.
