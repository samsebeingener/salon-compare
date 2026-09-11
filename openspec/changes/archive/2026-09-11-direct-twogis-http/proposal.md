# Proposal: direct-twogis-http

## Why

Поиск и карточки Catalog API 2ГИС шли через `HTTP_PROXY`/`HTTPS_PROXY` (`trust_env=True`). `HTTPS_PROXY` со схемой `https://` даёт SSL handshake timeout. Ошибка глотается — зацепки, которые раньше находились, выглядят как «не найдено». Прокси нужен только модели.

## What Changes

- Запросы `catalog.api.2gis.com` (поиск, byid, соседи) — напрямую, `trust_env=False`.
- HTML `2gis.ru` / `2gis.com` — тоже напрямую (как уже `2gis.ru`).
- Клиент LLM не меняется: явный прокси, затем direct.

## Capabilities

### Modified Capabilities

- `open-data-collect`: Catalog API 2ГИС без прокси окружения.
- `project-bootstrap`: прокси из `.env` — для LLM, не для 2ГИС.

## Impact

- `maps_http.py`, `html_fetch.py`, `proxy.py`, README, тесты.
