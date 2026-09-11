# Proposal: fix-audit-hygiene-v2

## Why

После первого `fix-audit-hygiene` остались дыры гигиены: CI не считает покрытие, Compose слушает все интерфейсы, HTML fetch может съесть огромный ответ, геокодер Яндекса игнорирует прокси, а тело чата шлёт `include_thoughts` / `reasoning_effort` на любой `LLM_BASE_URL` — чужие хосты это ломают.

## What Changes

- Команда качества и GitHub Actions: pytest с `pytest-cov` (отчёт покрытия), **без** `--cov-fail-under` и без порога в конфиге.
- Docker Compose: публикация Streamlit только на `127.0.0.1`.
- HTML GET/POST: жёсткий лимит размера тела; превышение — как пустой/неуспешный fetch, без загрузки всего ответа в память.
- Геокодер карты (`yandex_viz`) ходит в сеть через `proxy.httpx_client_kwargs()`, как карты и HTML, а не с `trust_env=False`.
- `include_thoughts` и `reasoning_effort` в payload чата — только если хост `LLM_BASE_URL` — `*.kie.ai` (включая `api.kie.ai`).

## Capabilities

### New Capabilities

- (нет)

### Modified Capabilities

- `project-bootstrap`: coverage в той же команде качества/CI без fail-under; bind Compose на loopback; Kie-only поля thinking в клиенте модели.
- `open-data-collect`: лимит размера HTML fetch на один GET/POST.
- `streamlit-ui`: серверный геокодер уважает `HTTP_PROXY` / `HTTPS_PROXY` через `httpx_client_kwargs`.

## Impact

- Код (другой агент, не этот change): `scripts/run_quality.py`, `.github/workflows/ci.yml`, `compose.yaml`, `pyproject.toml` (dev: pytest-cov), `html_fetch.py`, `yandex_viz.py`, `llm.py`; тесты bootstrap / html_fetch / llm transport / viz.
- Не входит: порог покрытия как gate, публикация порта наружу, смена провайдера LLM, scoring, сбор полей 2ГИС.

## Non-Goals

- Не трогать формулу индекса, OpenSpec live merge (это задача apply/archive).
- Не вводить отдельную capability `llm`.
- Не коммитить и не править `src/` / `tests/` в рамках этого planning-change.
