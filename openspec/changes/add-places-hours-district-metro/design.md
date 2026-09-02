# Design: add-places-hours-district-metro

## Context

См. proposal.md — Why. `card_from_twogis` не читает `schedule`. Поля `adm_div` и `links` не просим. `MapCard.hours` есть, район и метро — нет.

## Goals / Non-Goals

**Goals:** три поля из того же `byid`, без новых API.

**Non-Goals:** Geocoder, услуги, дата отзыва, смена формулы локации.

## Decisions

- `TWOGIS_FIELDS` += `items.adm_div,items.links`.
- Часы: схлопнуть одинаковые дни, формат `пн-вс 10:00-22:00`.
- Район: первый `adm_div` с `type=district`.
- Метро: станции с `metro` в `route_types`, ближайшая по `distance`: `Павелецкая, 140 м`.
- `PlaceRecord.district` и `PlaceRecord.metro`. HTML-fallback для них нет.

## Risks / Trade-offs

- [Нет district в adm_div] → «не найдено».
- [Метро только как id в nearest_metro] → берём `nearest_stations` с именем.
