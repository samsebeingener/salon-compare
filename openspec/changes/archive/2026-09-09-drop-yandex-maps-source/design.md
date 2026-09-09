# Design: drop-yandex-maps-source

## Context

См. proposal.md — Why. `YandexPlacesApi` бьёт в платный Geosearch. Поля `yandex_*` в `PlaceRecord`, таблице и формуле. Отдельного модуля `yandex.py` нет.

## Goals / Non-Goals

**Goals:** вырезать API, поля, ключ, колонки; репутация по 2ГИС; старые разборы грузятся.

**Non-Goals:** удалять классификатор `yandex.ru/maps`; чистить `openspec/changes/archive/`; новые пакеты.

## Decisions

- `CollectDeps` и `MapsSearchResolver` — один каталог 2ГИС.
- `map_api_from_env()` без kind и без Яндекса.
- `candidate_from_maps_url` для `yandex.ru/maps/org/…` оставляет `yandex:{id}` без HTTP.
- Pydantic extra ignore: `yandex_*` в старом JSON не ломает `load_run`.
- Юрлицо: ОГРН только с карточки 2ГИС (и из зацепки). Два разных ОГРН «Яндекс vs 2ГИС» больше не сценарий карт.

## Risks / Trade-offs

- [Старый payload без полей 2ГИС] → дырки «не найдено», не падение.
- [Зацепка-ссылка Яндекса] → карточка Places 2ГИС пустая, пока пользователь не даст название/2ГИС.
