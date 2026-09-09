# OpenSpec — целевая карта capabilities

> **Статус cleanup:** ✅ **COMPLETE** (Stages 0–5, 2026-09-09)  
> Активных change: **0**. Live specs: **9**. Архив: **28** change.  
> Финальный отчёт: [docs/openspec-cleanup-report.md](../docs/openspec-cleanup-report.md)

## История этапов

| Stage | PR | Статус |
|-------|-----|--------|
| **0** — процессные правила | [#41](https://github.com/samsebeingener/salon-compare/pull/41) | ✅ COMPLETE |
| **1** — инвентаризация 23 change | [#42](https://github.com/samsebeingener/salon-compare/pull/42) | ✅ COMPLETE |
| **2** — целевая карта capability | [#43](https://github.com/samsebeingener/salon-compare/pull/43) | ✅ COMPLETE |
| **3a** — архив группы 1 (юрконтур) | [#44](https://github.com/samsebeingener/salon-compare/pull/44) | ✅ COMPLETE |
| **3b** — архив группы 2 (инфра/UX) | [#45](https://github.com/samsebeingener/salon-compare/pull/45) | ✅ COMPLETE |
| **3c** — архив группы 3 (формула v1, отчёт) | [#46](https://github.com/samsebeingener/salon-compare/pull/46) | ✅ COMPLETE |
| **3d** — архив группы 4 (обогащение карт) | [#47](https://github.com/samsebeingener/salon-compare/pull/47) | ✅ COMPLETE |
| **3e** — архив группы 5 (пост-Яндекс, каскад) | [#48](https://github.com/samsebeingener/salon-compare/pull/48) | ✅ COMPLETE |
| **3f** — архив группы 6 (формула v2) | [#49](https://github.com/samsebeingener/salon-compare/pull/49) | ✅ COMPLETE |
| **4** — retroactive `streamlit-ui` (карта Яндекс) | [#50](https://github.com/samsebeingener/salon-compare/pull/50) | ✅ COMPLETE |
| **5** — финальная валидация и отчёт | *(текущий PR)* | ✅ COMPLETE |

---

## Что такое `openspec/specs/`

`openspec/specs/` — **live truth** (живая правда о продукте): что приложение **делает сейчас**, а не что планируется или уже смержено в код, но ещё не перенесено из change.

| Слой | Роль |
|------|------|
| `openspec/specs/<capability>/spec.md` | Актуальное поведение capability после архивации дельт |
| `openspec/changes/<имя>/` | Активная работа: proposal, design, tasks, дельты к specs |
| `openspec/changes/archive/` | Завершённые change (история решений) |

Правило: код в `main` не должен расходиться со `openspec/specs/` дольше одного PR.

Цикл работы с OpenSpec описан в [CONTRIBUTING.md — раздел OpenSpec](../CONTRIBUTING.md#openspec).

---

## Live capability (9)

| Capability | Покрывает |
|------------|-----------|
| `project-bootstrap` | Запуск проекта, `.env`, Docker, quality gate (uv, CI, линтеры) |
| `hook-intake` | Три типа зацепки, подтверждение карточек, disambiguation, fallback без карт |
| `open-data-collect` | Сбор полей салона: **только 2ГИС**, юридический блок, сайт, каскады DDG/РБК/Checko |
| `scoring-formula` | Индекс конкурента **50/25/25**, частичный score, репутация без Fedresurs/KAD |
| `report-corrections` | Карточки салона, правки полей, LLM-вердикт, «недостоверный» |
| `html-freshness` | HTML-свежесть, часы, блок usage/cost LLM |
| `saved-runs` | SQLite `data/`, список и открытие сохранённых разборов |
| `delivery-readme` | Состав README сдачи, рамки, ключи |
| `streamlit-ui` | Таблица разборов, опциональная **карта Яндекс (только UI)** |

Карта spec → модули кода: [docs/openspec-cleanup-report.md](../docs/openspec-cleanup-report.md#карта-capability--код).

---

## Жёсткое правило: Яндекс.Карты

| Область | Источник данных | Где в OpenSpec |
|---------|-----------------|----------------|
| Сбор полей салона (адрес, часы, рейтинг, отзывы, координаты для scoring) | **Только 2ГИС** | `open-data-collect`, `hook-intake` |
| Визуализация карты в Streamlit (опциональный виджет) | Яндекс JS API + Geocoder (`yandex_viz.py`) | **Только** `streamlit-ui` |

Ключи: `TWOGIS_API_KEY` — сбор; `YANDEX_MAPS_JS_API_KEY` / `YANDEX_GEOCODER_API_KEY` — только отображение в UI.

---

## Поддержка (maintenance)

1. **Новая фича или багфикс с изменением поведения** — создайте `openspec/changes/<имя>/` (proposal, design, tasks, дельты к затронутым specs).
2. **Реализация** — падающие тесты → код → `uv run python scripts/run_quality.py` и `openspec validate --specs`.
3. **После merge** — `openspec archive <имя>` (или sync по `.cursor/skills/openspec-sync-specs/SKILL.md`): change в `archive/`, дельты → `openspec/specs/`.
4. **Контроль** — в `openspec/changes/` держите **0–1** активный change; `openspec list` должен показывать пусто между задачами.

Мелкие правки docs/опечаток без смены поведения — без change. Полный цикл и исключения: [CONTRIBUTING.md#openspec](../CONTRIBUTING.md#openspec).

---

## Связанные документы

- [docs/openspec-cleanup-report.md](../docs/openspec-cleanup-report.md) — финальный отчёт Stage 5
- [docs/openspec-inventory.md](../docs/openspec-inventory.md) — инвентаризация и история архивации
- [CONTRIBUTING.md — OpenSpec](../CONTRIBUTING.md#openspec) — обязательный цикл change → PR → archive → specs
- `openspec/config.yaml` — конфигурация OpenSpec в репозитории

---

## Чеклист ревьюера: «spec соответствует коду»

Использовать при review PR и после архивации change в `openspec/specs/`.

### Общее

- [ ] Изменение поведения сопровождается change в `openspec/changes/` или обновлением live spec в том же PR
- [ ] Нет противоречий между capability (сбор из 2ГИС vs запрет Яндекс-источников в `drop-yandex-maps-source`)
- [ ] `openspec/changes/` не копит завершённую работу: после merge — архив и merge delta → `openspec/specs/`

### По capability

- [ ] **project-bootstrap** — `.env.example`, Docker/CI, quality gate и ключи API соответствуют коду
- [ ] **hook-intake** — три зацепки, radio/подтверждение, disambiguation, fallback без ключей карт
- [ ] **open-data-collect** — каскад 2ГИС → HTML/сайт → юрблок; нет Яндекс Places; честные статусы реестров
- [ ] **scoring-formula** — веса **50/25/25**; частичный индекс; репутация по рейтингу+отзывам 2ГИС
- [ ] **report-corrections** — JSON-вердикт, карточки салона, правки полей, «недостоверный»
- [ ] **html-freshness** — блок usage/cost, HTML-свежесть
- [ ] **saved-runs** — SQLite `data/`, список/открытие runs
- [ ] **streamlit-ui** — таблица, expander карты; карта Яндекс — опциональный UI, не влияет на собранные поля

### Код без spec (красные флаги)

- [ ] Новый модуль/поведение в `src/` без дельты в change или live spec
- [ ] `yandex_viz.py` описан только в `streamlit-ui`, не в `open-data-collect`
- [ ] Формула или веса в коде ≠ `scoring-formula`

### После архивации

- [ ] Дельты из `openspec/changes/archive/.../specs/` перенесены в `openspec/specs/<capability>/spec.md`
- [ ] `openspec list` — 0 active; `openspec validate --specs` — all pass
- [ ] Тесты и quality gate зелёные
