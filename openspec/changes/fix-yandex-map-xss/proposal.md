# Proposal: fix-yandex-map-xss

## Why

Ревью приёмки: название и адрес из 2ГИС вставляются в HTML карты через `json.dumps` внутри `<script>` — XSS script-breakout (S1). Те же поля попадают в `balloonContentHeader` / `balloonContentBody` без экранирования — XSS через балун (S2). Нужны **оба** фикса: данные не должны ломать тег скрипта и не должны исполняться как HTML в балуне.

## What Changes

- Точки карты отдавать в `<script type="application/json">` и читать через `JSON.parse` на клиенте, а не сырой `const POINTS = {payload}` внутри JS.
- После сериализации экранировать `<`, `>`, `&` в JSON как `\u003c` `\u003e` `\u0026` **или** вынести JSON в отдельный тег (предпочтительно оба: `json.dumps` + replace `"</"` и unicode escape).
- `title` / `address` для балуна — `html.escape` на сервере **до** свойств метки.
- Тесты с payload `</script>` и `<img src=x onerror=...>`.

## Capabilities

### New Capabilities

- (нет)

### Modified Capabilities

- `streamlit-ui`: безопасная вставка данных 2ГИС в HTML карты (S1 + S2).

## Impact

- Код (другой агент): `src/salon_compare/yandex_viz.py`, `tests/test_yandex_viz.py`.
- Не входит: ключи Яндекса, геокод, viewport, сбор/scoring, SQLite.

## Non-Goals

- Менять состав меток, ключи env или API Яндекса.
- Санитизация всего HTML виджета кроме данных title/address и JSON точек.
- Трогать `collect` / `score`.
