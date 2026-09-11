## 1. OpenSpec

- [x] 1.1 Change `fix-audit-hygiene-v2`: proposal, design, tasks, дельты `project-bootstrap`, `open-data-collect`, `streamlit-ui` — проверить `openspec validate --change fix-audit-hygiene-v2`

## 2. Quality / CI / Compose

- [x] 2.1 `pytest-cov` в dev-группе; `scripts/run_quality.py` вызывает pytest с `--cov=src/salon_compare --cov-report=term-missing`; в скрипте и `pyproject.toml` нет `--cov-fail-under` / `fail_under` — проверить чтением файлов и что CI по-прежнему зовёт `scripts/run_quality.py`
- [x] 2.2 `compose.yaml` публикует `"127.0.0.1:8501:8501"` — проверить, что нет голого `"8501:8501"`

## 3. HTML fetch и геокодер

- [x] 3.1 HTML GET/POST: лимит 2_000_000 байт по `Content-Length` или длине тела → `empty` и пустое body — проверить тестами html_fetch (Content-Length и тело без заголовка)
- [x] 3.2 `geocode_yandex_http` передаёт `**httpx_client_kwargs()` из `proxy.py`, не `trust_env=False` — проверить исходник и/или тест kwargs геокода

## 4. LLM Kie-only thinking

- [x] 4.1 `chat_payload`: `include_thoughts=false` и `reasoning_effort=low` только для хостов `api.kie.ai` / `*.kie.ai`; иначе ключей нет — проверить `test_chat_payload_disables_stream` и `test_chat_payload_omits_kie_fields_for_openrouter`

## 5. Проверка

- [x] 5.1 `uv run python scripts/run_quality.py` — код 0; в выводе pytest есть coverage report и нет падения из‑за процента покрытия
