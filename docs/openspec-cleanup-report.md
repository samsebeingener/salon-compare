# OpenSpec — финальный отчёт о гигиене (Stage 5)

> **Статус:** CLOSED / complete  
> **Дата:** 2026-09-09  
> **Ветка Stage 5:** `chore/openspec-stage-5-final-validation`

## Краткое резюме

OpenSpec-гигиена репозитория **завершена**. Активных change нет, все 9 live-спеков валидны, quality gate зелёный. В `openspec/changes/` осталась только папка `archive/` с 28 завершёнными change.

---

## Что было не так (до cleanup)

| Проблема | Масштаб |
|----------|---------|
| **23 «висящих» активных change** в `openspec/changes/` | Смерженный код в `main`, но дельты не перенесены в live specs и change не заархивированы |
| **Live specs устарели** | Поведение продукта (2ГИС-only, формула v2 50/25/25, Checko, карта Яндекс UI) не отражено в `openspec/specs/` |
| **Нет процессных правил** | Цикл change → PR → archive → specs не зафиксирован для агентов и ревьюеров |
| **Пробел PR #40** | `yandex_viz.py` в коде без OpenSpec capability |

Итог: «правда о продукте» жила в коде и разрозненных change, а не в `openspec/specs/`.

---

## Что сделали (Stages 0–4, PR #41–#50)

| Stage | PR | Содержание |
|-------|-----|------------|
| **0** | [#41](https://github.com/samsebeingener/salon-compare/pull/41) | Процессные правила в `AGENT_RULES.md` и `CONTRIBUTING.md` (цикл OpenSpec) |
| **1** | [#42](https://github.com/samsebeingener/salon-compare/pull/42) | Инвентаризация 23 активных change, группы архивации, gaps |
| **2** | [#43](https://github.com/samsebeingener/salon-compare/pull/43) | Целевая карта capability, правило «Яндекс = только UI», чеклист ревьюера |
| **3a** | [#44](https://github.com/samsebeingener/salon-compare/pull/44) | Архив группы 1 — юридический контур (5 change) |
| **3b** | [#45](https://github.com/samsebeingener/salon-compare/pull/45) | Архив группы 2 — инфраструктура и UX (5 change); live `saved-runs`, `delivery-readme` |
| **3c** | [#46](https://github.com/samsebeingener/salon-compare/pull/46) | Архив группы 3 — формула v1 и отчёт (3 change); live `scoring-formula`, `report-corrections`, `html-freshness` |
| **3d** | [#47](https://github.com/samsebeingener/salon-compare/pull/47) | Архив группы 4 — обогащение карт и disambiguation (4 change) |
| **3e** | [#48](https://github.com/samsebeingener/salon-compare/pull/48) | Архив группы 5 — пост-Яндекс и каскад сайт↔юрлицо (5 change) |
| **3f** | [#49](https://github.com/samsebeingener/salon-compare/pull/49) | Архив группы 6 — формула v2 50/25/25 (`revise-index-available-data`) |
| **4** | [#50](https://github.com/samsebeingener/salon-compare/pull/50) | Retroactive `add-yandex-map-viz` (код PR #40) → live `streamlit-ui` |

**Stage 5** (этот PR): финальная валидация, отчёт для ревьюера, обновление документации, статус CLOSED.

---

## Текущее состояние

| Метрика | Значение |
|---------|----------|
| Активных change | **0** |
| Заархивированных change | **28** |
| Live specs в `openspec/specs/` | **9** |
| Папок в `openspec/changes/` кроме `archive/` | **0** |

### Результаты валидации (2026-09-09)

```text
openspec list
→ No active changes found.

openspec validate --specs
→ 9 passed, 0 failed
  delivery-readme, hook-intake, html-freshness, open-data-collect,
  project-bootstrap, report-corrections, saved-runs, scoring-formula, streamlit-ui

openspec doctor
→ OpenSpec root: ok
→ References: (none declared)
→ Предупреждений нет

uv run python scripts/run_quality.py
→ All checks passed (ruff, mypy, pytest — 260 passed)
```

### Структура `openspec/changes/`

```text
openspec/changes/
└── archive/          ← 28 папок 2026-09-02-* и 2026-09-09-*
```

---

## Карта capability → код

| Live spec | Что описывает | Основные модули `src/salon_compare/` | Тесты |
|-----------|---------------|----------------------------------------|-------|
| `project-bootstrap` | uv, CI, Docker, `.env`, quality gate, ключи API | `load_env.py`, `env_file.py`, `proxy.py`, `runtime.py` | `tests/test_env_file.py`, `tests/test_load_env.py` |
| `hook-intake` | Три зацепки, типы, disambiguation, fallback без карт, slug Яндекс→2ГИС | `hooks.py`, `intake.py`, `resolver.py` | `tests/test_hooks.py`, `tests/test_intake.py`, `tests/test_resolver.py` |
| `open-data-collect` | Сбор 2ГИС-only, HTML-каскад, юрблок, Checko/РБК/DDG, соседи 500 м | `collect.py`, `maps_http.py`, `maps_parse.py`, `html_fetch.py`, `html_parse.py`, `legal.py`, `checko.py`, `site_enrichment.py` | `tests/test_collect.py`, `tests/test_legal.py`, `tests/test_checko.py`, … |
| `scoring-formula` | Индекс v2 **50/25/25**, частичный score, «недостоверный» | `score.py` | `tests/test_score.py` |
| `report-corrections` | Карточки салона, правки ячеек, LLM-вердикт | `report.py`, `llm.py`, `llm_log.py` | `tests/test_report.py`, `tests/test_llm.py` |
| `html-freshness` | Свежесть HTML, часы, usage/cost LLM | `report.py`, `llm.py` | `tests/test_report.py` |
| `saved-runs` | SQLite `data/`, сохранение и открытие разборов | `store.py`, `app.py` | `tests/test_store.py` |
| `delivery-readme` | Состав README сдачи, рамки, SQLite, ключи | `README.md`, `ПОДГОТОВКА.md` | — (manual QA) |
| `streamlit-ui` | Таблица, expander карты Яндекс, два viz-ключа | `app.py`, `yandex_viz.py` | `tests/test_yandex_viz.py`, `tests/test_app_smoke.py` |

### Жёсткое правило (сохранено)

| Область | Источник | Spec |
|---------|----------|------|
| Сбор полей салона | **Только 2ГИС** | `open-data-collect`, `hook-intake` |
| Карта в Streamlit | Яндекс JS API + Geocoder | **Только** `streamlit-ui` |

---

## Как поддерживать дальше

Любое изменение поведения продукта начинайте с change в `openspec/changes/<имя>/`, реализуйте с тестами, мержите PR, затем архивируйте change и перенесите дельты в `openspec/specs/`. Держите **0–1** активный change; после merge не оставляйте завершённую работу в корне `changes/`. Перед PR прогоняйте `openspec validate --specs` и `uv run python scripts/run_quality.py`. Подробный цикл и исключения — в [CONTRIBUTING.md — OpenSpec](../CONTRIBUTING.md#openspec).

---

## Связанные документы

- [openspec-inventory.md](openspec-inventory.md) — полная инвентаризация и история архивации
- [openspec/README.md](../openspec/README.md) — карта capability и чеклист ревьюера
- [CONTRIBUTING.md](../CONTRIBUTING.md#openspec) — обязательный цикл для контрибьюторов
