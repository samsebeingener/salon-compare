# Proposal: add-partial-scale-fields

## Why

В JSON 2ГИС уже есть рубрики и тип места (здание/этаж), а в `PlaceRecord` лежат дата последнего отзыва, отзывы за 90 дней и плюс/минус — но таблица их не показывает. Человеку нужен частичный «масштаб» как справочные строки, без нового блока индекса 50/25/25.

## What Changes

- Сбор из JSON карточки 2ГИС: `twogis_rubrics` (топ рубрик/услуги, если есть `items.rubrics`).
- Сбор `place_type`: метка ТЦ / улица / этаж из `address.building_name` и `address_comment`.
- Сбор `twogis_price_level` только если в JSON есть явное поле уровня цен; иначе всегда «не найдено». Сайт салона MUST NOT скрейпить ради цен.
- Таблица сравнения (`FIELD_LABELS`): новые поля плюс уже существующие `twogis_last_review`, `twogis_reviews_90d`, `twogis_plus_minus`. Пустые значения — «не найдено», без нуля и без выдумки.
- Формула индекса **не** меняется: четвёртого блока «масштаб» нет.

## Capabilities

### New Capabilities

- (нет)

### Modified Capabilities

- `open-data-collect`: рубрики, тип места и уровень цен из JSON 2ГИС; честный MISSING без скрейпа сайта.
- `streamlit-ui`: строки таблицы сравнения для масштаба и свежести отзывов 2ГИС.

## Impact

- Код (другой агент): `maps_parse.py`, `maps_http.py` (`items.rubrics` в fields), `collect.py` / `PlaceRecord`, `report.py` `FIELD_LABELS` (+ карточка через тот же список), `coerce_place_record` для старых JSON. Тесты без сети.
- `scoring-formula` не в дельте: веса 50/25/25 и «масштаб не в индексе» остаются. Живая фраза «поля отзывов MUST NOT показываться в таблице» расходится с этим UI — источник правды для строк таблицы после change: `streamlit-ui`. Индекс по-прежнему без этих полей.

## Non-Goals

- Новый блок индекса «масштаб» и пересчёт 50/25/25.
- Скрейп прайса с сайта салона, агрегаторов, LLM-добор цен/рубрик.
- Заполнять `twogis_last_review` / `twogis_reviews_90d` / `twogis_plus_minus`, если каскад API/HTML их не дал: честный MISSING.
- Яндекс Places, Федресурс/КАД, archive change в этом шаге.
