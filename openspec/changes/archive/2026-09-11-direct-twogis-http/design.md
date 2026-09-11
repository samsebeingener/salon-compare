# Design: direct-twogis-http

## Context

`TwoGisApi._get_json` вызывал `httpx.get(..., **httpx_client_kwargs())` → `trust_env=True`. Для `https://catalog.api.2gis.com` httpx берёт `HTTPS_PROXY`. Схема `https://` у прокси зависает на TLS. `ConnectTimeout` — подкласс `HTTPError`, ответ `None`, 0 карточек.

Живая проверка: прямой GET — 200 за ~0.3 с; `trust_env=True` — timeout.

HTML `2gis.ru` уже `trust_env=False`. Catalog API — нет.

## Decisions

- `direct_httpx_kwargs()` в `proxy.py`: `trust_env=False`.
- `maps_http._get_json` использует его, не `httpx_client_kwargs`.
- `html_client_kwargs`: хосты `2gis.com` так же, как `2gis.ru`.
- LLM: без изменений (`llm_transport_attempts`).
- Геокодер Яндекс остаётся на `httpx_client_kwargs` (не этот change).

## Risks / Trade-offs

- [2ГИС закрыт с домашнего IP] → тогда пусто и без прокси; сейчас наоборот: прямой канал живой, прокси мёртвый.
