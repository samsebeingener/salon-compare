# Design: add-partial-scale-fields

## Context

См. proposal.md — Why. Сбор уже кладёт рейтинг, часы, район, метро из JSON 2ГИС. `PlaceRecord` уже имеет `twogis_last_review`, `twogis_reviews_90d`, `twogis_plus_minus`, но `collect_place` часто оставляет их MISSING, а таблица их не показывала. Формула — 50/25/25, масштаб в индекс не входит (`scoring-formula`).

## Goals / Non-Goals

**Goals:**

- Разобрать рубрики, тип места и явный уровень цен из того же JSON карточки, что рейтинг.
- Показать эти поля и три поля свежести в `FIELD_LABELS` (таблица + карточка).
- Старый SQLite JSON без новых ключей открывать через дефолты `SourcedField`.

**Non-Goals:**

- Четвёртый блок `PlaceScore` / смена весов.
- HTML сайта салона или LLM ради цен и рубрик.
- Обязательно заполнить свежесть отзывов, если API/HTML молчат.

## Decisions

- **Один JSON, без второго каскада:** `rubrics` / `place_type` / `price_level` только из item 2ГИС (`card_from_twogis`). HTML карточки 2ГИС и GET сайта — не для этих трёх полей. `items.rubrics` уже в `TWOGIS_FIELDS`.
- **Топ рубрик:** первые до трёх `name` из массива `rubrics`, через запятую. Пустой массив → MISSING.
- **place_type:** непустое `building_name` с маркером ТЦ/торговый → «ТЦ»; иначе комментарий с «этаж» → текст комментария (это метка этажа); иначе улица без здания → «улица»; иначе MISSING. Альтернатива «всегда ТЦ при любом building_name» отклонена: офис без ТЦ не маскируем под ТЦ.
- **price_level:** явные ключи item `price_level` / `price`; MAY атрибут JSON с tag/name про цену. Нет ключа → MISSING. Не парсить `site_about`.
- **Свежесть в UI, не в формуле:** добавить три существующих поля в `FIELD_LABELS` (и секции таблицы Streamlit при группировке). `score.py` не трогать. Если collect по-прежнему пишет gap — ячейка «не найдено».
- **Имена полей:** `twogis_rubrics`, `place_type`, `twogis_price_level` как `SourcedField` на `PlaceRecord` / `MapCard`.
- **Дельта specs:** только `open-data-collect` и `streamlit-ui`. Предложение «MUST NOT показывать отзывы в таблице» в live `scoring-formula` после archive UI перекрывается `streamlit-ui`; индекс без этих полей.

## Risks / Trade-offs

- [Catalog без price_level] → почти всегда «не найдено» по цене. Это честно; не скрейпить сайт.
- [building_name без «ТЦ»] → MISSING или улица, не ложный ТЦ.
- [Расхождение scoring-formula vs таблица] → не добавлять блок масштаба; при archive UI — поправить одну фразу в `scoring-formula` отдельным change при необходимости.

## Migration Plan

- Новые ключи в payload; `extra="ignore"` + default `SourcedField` для старых runs.
- Откат: убрать поля из `FIELD_LABELS` и парсера; формула не менялась.

## Open Questions

- Нет: ключи цены и лимит трёх рубрик зафиксированы; свежесть можно добирать отдельным change, если появится поле в JSON.
