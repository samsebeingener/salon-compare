# Design: add-disambiguation-address

## Context

См. proposal.md — Why. Хиты поиска уже содержат `address_name` (2ГИС) и `CompanyMetaData.address` (Яндекс). `VenueCandidate` сейчас только `title` и `source_url`; Streamlit рисует `{title} — {url}`.

## Goals / Non-Goals

**Goals:** адрес из JSON поиска в подписи списка уточнения.

**Non-Goals:** второй запрос карточки ради адреса; автовыбор филиала; менять сбор `PlaceRecord.address`.

## Decisions

- Поле `VenueCandidate.address: str | None = None`. По умолчанию пусто — fallback без карт не ломается.
- 2ГИС: `full_address_name`, иначе `address_name`. Яндекс: адрес уже разобран в `card_from_yandex`.
- Одна функция подписи: `{title} — {address} — {url}` если адрес есть, иначе `{title} — {url}`. Streamlit только вызывает её.
- Адрес показываем всегда, когда он есть, не только при совпадении названий.

## Risks / Trade-offs

- [Поиск без адреса] → ссылка остаётся идентификатором.
- [Длинная подпись в radio] → адрес важнее короткой строки.
