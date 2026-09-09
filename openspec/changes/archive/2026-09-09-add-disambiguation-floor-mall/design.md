# Design: add-disambiguation-floor-mall

## Context

См. proposal.md — Why. `_search_address` сейчас берёт `full_address_name` / `address_name`. `address_comment` в базовом JSON 2ГИС («1 этаж»). Имя ТЦ — `address.building_name`, поле `items.address` сейчас не просим.

## Goals / Non-Goals

**Goals:** этаж и здание в той же строке адреса кандидата.

**Non-Goals:** менять `MapCard.address` для таблицы; второй запрос; Яндекс.

## Decisions

- Дописать к улице `building_name`, затем `address_comment`, через запятую.
- Пропуск куска, если он уже содержится в собранной строке (без учёта регистра).
- `TWOGIS_FIELDS` += `items.address`.
- Подпись UI не трогаем: `candidate_label` уже печатает `address`.

## Risks / Trade-offs

- [ТЦ уже в `full_address_name`] → не дублируем.
- [Нет `items.address` у ключа] → остаётся comment + улица.
