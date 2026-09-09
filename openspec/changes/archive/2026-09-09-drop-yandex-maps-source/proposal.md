# Proposal: drop-yandex-maps-source

## Why

Яндекс Places / ППО (`search-maps.yandex.ru`) платный. JavaScript API карт рейтинг в Streamlit не отдаёт. Ключ из консоли JS даёт 403. Второй контур карт держать нельзя.

## What Changes

- Убрать HTTP, парсер, поля, колонки, формулу и ключ Яндекса.
- Поиск и карточки карт — только 2ГИС.
- Репутация — только 2ГИС. Сценарий «не ясно какой свежее» из‑за двух карт без дат — снят.
- Ссылка `yandex.ru/maps` остаётся зацепкой «ссылка на карты»; Geosearch по ней не вызываем.
- Старый SQLite с `yandex_*` открывается: лишние ключи игнорируем.

## Capabilities

### New Capabilities

- (нет)

### Modified Capabilities

- `open-data-collect`: каскад поля только 2ГИС, затем один HTML.
- `scoring-formula`: репутация только 2ГИС.
- `project-bootstrap`: нет `YANDEX_MAPS_API_KEY`.
- `hook-intake`: поиск каталога только 2ГИС; URL Яндекса — тип карты без fetch API.

## Impact

- Код: `maps_http.py`, `maps_parse.py`, `resolver.py`, `collect.py`, `score.py`, `app.py`, `report.py`, `legal.py`, `store.py`.
- Документы: README, `.env.example`, `compose.yaml`, пометка в ПОДГОТОВКА.
- Не входит: archive OpenSpec, обход капчи, Playwright, платный ППО.
