## Context

См. proposal.md — Why. Код частично уже совпадает с целевым поведением; этот change фиксирует контракт в OpenSpec, чтобы live specs не отставали и apply мог сверить тесты.

Сейчас в каркасе: `run_quality.py` гоняет pytest с `--cov` / `--cov-report=term-missing` без fail-under; Compose — `127.0.0.1:8501:8501`; `html_fetch` режет ответы > 2_000_000 байт; `geocode_yandex_http` передаёт `**httpx_client_kwargs()`; `chat_payload` добавляет thinking-поля только через `_is_kie_host`.

## Goals / Non-Goals

**Goals:**

- Один контракт: coverage в той же quality-команде, что и CI, без порога.
- Порт UI только на loopback.
- HTML fetch не держит гигантские тела.
- Геокодер ходит через тот же proxy-helper, что карты/HTML по умолчанию.
- Thinking-поля только на `*.kie.ai`.

**Non-Goals:**

- Codecov / артефакт coverage.xml в CI.
- Streaming download с обрывом сокета до чтения всего тела (достаточно отсечь после ответа httpx).
- Менять исключения 2ГИС/DDG/РБК `trust_env=False` в `html_client_kwargs`.
- Новая capability `llm`.

## Decisions

- **Coverage без fail-under.** Pytest в `scripts/run_quality.py`: `--cov=src/salon_compare --cov-report=term-missing`. Не класть `[tool.coverage.report] fail_under` и не `--cov-fail-under`. Альтернатива (отдельный job) ломает «CI = локальная команда».
- **Compose bind.** `"127.0.0.1:8501:8501"` вместо `"8501:8501"`. Healthcheck внутри контейнера остаётся на `127.0.0.1:8501`. Альтернатива (`0.0.0.0` + firewall) хуже для демо на ноутбуке.
- **Лимит HTML 2_000_000 байт.** Сначала `Content-Length`, иначе `len(response.content)`. Превышение → `HtmlFetchResult(status="empty", body="")`. Не парсить капчу/поля. Альтернатива (обрывать stream) сложнее и не нужна при типичных страницах салонов.
- **Геокодер = `httpx_client_kwargs()`.** Не копировать `trust_env=True` вручную и не `trust_env=False` (сейчас ломает РФ-прокси). Не `llm_httpx_client_kwargs` (там явный proxy + direct retry — избыточно для одного GET геокода).
- **Kie-only thinking.** Тот же хост-тест, что URL chat completions: `api.kie.ai` или `*.kie.ai`. Пустой `base_url` → поля не слать. OpenRouter иначе отвечает ошибкой неизвестных ключей.

## Risks / Trade-offs

- [Content-Length врёт, тело маленькое] → всё равно empty; ложный промах лучше OOM.
- [Тело огромное без Content-Length] → httpx уже прочитал content; лимит не спасает RAM полностью. Приемлемо для v2; stream-cut — отдельный change.
- [Покрытие 0% из-за сбоя pytest-cov] → job падает как любой другой шаг quality, не из-за процента.
- [Поддомен не kie, но совместимый API] → thinking не уйдёт; это желаемо.

## Migration Plan

- Planning-only: дельты в `openspec/changes/fix-audit-hygiene-v2/`.
- Apply (другой запрос): сверить код/тесты со specs; при расхождении — дописать тесты, не ослаблять spec.
- Archive после merge: дельты → `openspec/specs/`.
- Rollback: вернуть голый bind, убрать cov-флаги, снять лимит, `trust_env=False` у геокода, вернуть thinking на все хосты — только если явно откатывают change.

## Open Questions

- Нет: порог 2_000_000 и отсутствие fail-under зафиксированы в specs.
