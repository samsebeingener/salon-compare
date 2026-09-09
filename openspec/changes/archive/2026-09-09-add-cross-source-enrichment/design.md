# Design: add-cross-source-enrichment

## Context

`search_query(OGRN)` = цифры → 2ГИС 0 хитов. `TWOGIS_FIELDS` сейчас только reviews/address/point. `site_about` заполняется только при `HookKind.WEBSITE`. Поиск [РБК по «ногтевой сервис»](https://companies.rbc.ru/search/?query=%D0%BD%D0%BE%D0%B3%D1%82%D0%B5%D0%B2%D0%BE%D0%B9+%D1%81%D0%B5%D1%80%D0%B2%D0%B8%D1%81) — 182523 юрлица.

## Goals / Non-Goals

**Goals:** не терять сайт/ОГРН с карт; ОГРН→бренд РБК→карты с подтверждением; сайт с карт для любой зацепки.

**Non-Goals:** подставлять первую карточку РБК по общему названию; Playwright; масштаб.

## Decisions

- 2ГИС `fields`: `items.reviews,items.address_name,items.point,items.contact_groups,items.schedule,items.org`.
- `MapCard.website` из `contact_groups` type=website (url/value) и из Яндекс `CompanyMetaData.url`. Источник рейтинга — URL карты, не сайт студии.
- `collect`: URL сайта = зацепка-сайт (если она) и/или `website` с карт. Первый открывшийся HTML даёт «о нас».
- ОГРН: если поиск по цифрам пуст, `rbc_brand_names` с карточки ОГРН (highlight I LIKE NAILS), затем search карт по этому имени. 2+ хита — disambiguation.
- Не ищем РБК `query=ногтевой сервис` без подтверждения.

## Risks

- Бренд на РБК может не совпасть с вывеской 2ГИС — тогда список на подтверждение.
- `contact_groups` в API может быть платным полем; нет поля — сайт «не найдено».
