# OpenSpec — инвентаризация (Stage 1 + Stage 3a)

> Снимок на 2026-09-09. Ветка Stage 3a: `chore/openspec-stage-3a-archive-group-1`.

## Сводка

| Метрика | Значение |
|--------|----------|
| Активных change в `openspec/changes/` | **18** |
| Уже в `openspec/changes/archive/` | **9** |
| Live-спеки в `openspec/specs/` | **3** (`hook-intake`, `open-data-collect`, `project-bootstrap`) |

### Рекомендуемый порядок архивации (Stage 3)

Хронологические группы — архивировать пакетами, после merge delta → live specs:

1. **Юридический контур и честный сбор** — `add-legal-registries`, `fix-live-collect-honesty`, `add-rusprofile-ddg-fallback`, `fix-rusprofile-live-collect`, `add-rbc-companies-ogrn` (PR #6–9, #18).
2. **Инфраструктура и UX** — `add-sqlite-saved-runs`, `add-hook-fallback-without-maps`, `add-twogis-moscow-region`, `add-streamlit-dotenv`, `add-streamlit-delivery` (PR #10–13, #16).
3. **Отчёт и формула v1 (40/25/20/15)** — `add-scoring-formula`, `add-report-corrections`, `add-html-freshness-and-usage` (PR #14–17). Архивировать **после** группы 6 — часть требований перекрыта `revise-index-available-data`.
4. **Обогащение карт и disambiguation** — `add-cross-source-enrichment`, `add-disambiguation-address`, `add-disambiguation-floor-mall`, `add-places-hours-district-metro` (PR #19–22).
5. **Пост-Яндекс и каскад сайт↔юрлицо** — `drop-yandex-maps-source`, `fix-audit-hygiene`, `fix-empty-site-html`, `fix-twogis-card-website`, `add-site-legal-enrichment-cascade` (PR #23–27).
6. **Формула v2 (50/25/25)** — `revise-index-available-data` (PR #32). Последней: обновляет live `scoring-formula` и сбор.

### Пробелы (gaps)

| Пробел | Статус | Действие |
|--------|--------|----------|
| `revise-index-available-data` — нет `tasks.md` | change без чеклиста | Добавить retroactive `tasks.md` или зафиксировать в archive README, что tasks не велись |
| Yandex map UI (`yandex_viz.py`, PR #40) — нет change | код есть, OpenSpec нет | Retroactive change (например `add-yandex-map-viz`) перед архивацией UI-фичи |
| PR #28–31, #33–39 | вне списка 23 change | Follow-up PR поверх уже merged change; не блокируют Stage 3, но Checko (#37) частично смещает `add-legal-registries` |

### Уже архивированные change (9)

| change | PR (если известен) |
|--------|-------------------|
| `2026-09-02-add-project-bootstrap` | #2 |
| `2026-09-02-add-hook-intake` | #3 |
| `2026-09-02-add-open-data-collect` | #4 |
| `2026-09-02-fix-maps-search-confirm` | #5 |
| `2026-09-09-add-legal-registries` | #6 |
| `2026-09-09-fix-live-collect-honesty` | #7 |
| `2026-09-09-add-rusprofile-ddg-fallback` | #8 |
| `2026-09-09-fix-rusprofile-live-collect` | #9 |
| `2026-09-09-add-rbc-companies-ogrn` | #18 |

---

## Stage 3 — прогресс архивации

| Группа | Change | Статус | Дата |
|--------|--------|--------|------|
| **1. Юридический контур и честный сбор** | `add-legal-registries` | ✅ archived | 2026-09-09 |
| | `fix-live-collect-honesty` | ✅ archived | 2026-09-09 |
| | `add-rusprofile-ddg-fallback` | ✅ archived | 2026-09-09 |
| | `fix-rusprofile-live-collect` | ✅ archived | 2026-09-09 |
| | `add-rbc-companies-ogrn` | ✅ archived | 2026-09-09 |
| 2. Инфраструктура и UX | 5 change | pending | — |
| 3. Отчёт и формула v1 | 3 change | pending | — |
| 4. Обогащение карт | 4 change | pending | — |
| 5. Пост-Яндекс и каскад | 5 change | pending | — |
| 6. Формула v2 | `revise-index-available-data` | pending | — |

Примечания Stage 3a:
- `add-legal-registries` — `--skip-specs` (live specs уже были синхронизированы вперёд через `fix-audit-hygiene`).
- Остальные 4 change группы 1 — merge delta → live specs; после merge каскада восстановлен контур «только 2ГИС» (без `и/или Яндекс`).

---

## Аудит активных change

| change | кратко что | в коде? | связанный PR | tasks все [x]? | рекомендация |
|--------|------------|---------|--------------|----------------|--------------|
| `add-cross-source-enrichment` | Сквозной сбор: сайт с карт, ОГРН→бренд РБК→поиск карт, поля `org`/`contact_groups` в 2ГИС | да | #19 | да | Archive группа 4; merge delta в `open-data-collect` / `hook-intake` |
| `add-disambiguation-address` | Адрес в подписи radio при нескольких карточках с одним названием | да | #20 | да | Archive группа 4 |
| `add-disambiguation-floor-mall` | Этаж, комментарий и ТЦ в адресе кандидата из JSON 2ГИС | да | #21 | да | Archive группа 4 |
| `add-hook-fallback-without-maps` | Без ключей карт — fallback одной точки по типу зацепки, демо до таблицы | да | #11 | да | Archive группа 2 |
| `add-html-freshness-and-usage` | HTML: часы, свежесть отзывов, плюс/минус; блок расхода LLM (токены/cost) | частично | #17 | да | Archive группа 3 **после** `revise-index`: поля свежести в коде есть, но scoring v2 не требует 90d; usage — да |
| ~~`add-legal-registries`~~ | ЕГРЮЛ, Федресурс, КАД; неоднозначность юрлица; один GET на реестр | частично | #6 (+ #37 Checko) | да | **Archived** 2026-09-09 (`--skip-specs`) |
| `add-places-hours-district-metro` | Часы, район, метро из Places JSON 2ГИС | да | #22 | да | Archive группа 4 |
| ~~`add-rbc-companies-ogrn`~~ | Fallback ЕГРЮЛ через поиск РБК по ОГРН | да | #18 | да | **Archived** 2026-09-09 |
| `add-report-corrections` | Карточки салона, JSON-вердикт LLM, правки полей, «недостоверный» | да | #15 (+ #38 LLM) | да | Archive группа 3 |
| ~~`add-rusprofile-ddg-fallback`~~ | DDG→rusprofile для полей ЕГРЮЛ, полка «слабо», pacer | да | #8 | да | **Archived** 2026-09-09 |
| `add-scoring-formula` | Индекс 40/25/20/15, частичный score, без нуля за дыры | частично | #14 | да | Archive группа 3 **после** `revise-index`: заменён на 50/25/25 |
| `add-site-legal-enrichment-cascade` | DDG сайта, РБК→сайт, обход контактов/политики для ОГРН/ИНН | да | #27 (+ #28–31) | да | Archive группа 5 |
| `add-sqlite-saved-runs` | SQLite `data/`, список/открытие разборов, кэш сессии | да | #10 | да | Archive группа 2 |
| `add-streamlit-delivery` | README: укладка, SQLite, рамки, абзац про агента/модели | да | #16 | да | Archive группа 2 |
| `add-streamlit-dotenv` | Загрузка `.env` из корня без python-dotenv | да | #13 | да | Archive группа 2 |
| `add-twogis-moscow-region` | `region_id=32` в поиске 2ГИС (Москва) | да | #12 | да | Archive группа 2 |
| `drop-yandex-maps-source` | Убрать Яндекс Places/поля/ключ; только 2ГИС для данных | да | #23 | да | Archive группа 5; не путать с PR #40 (viz-only) |
| `fix-audit-hygiene` | HTML «о нас», slug Яндекс→2ГИС, sync live specs, удаление мёртвого кода | да | #24 | да | Archive группа 5; live specs уже без `YANDEX_MAPS_API_KEY` |
| `fix-empty-site-html` | Retry `{url}.html` после 404; ОГРН только с маркера на сайте | да | #25 (+ #30) | да | Archive группа 5 |
| ~~`fix-live-collect-honesty`~~ | Не первая radio; честные реестры; ИНН≠ОГРН; соседи 500 м | да | #7 | да | **Archived** 2026-09-09 |
| ~~`fix-rusprofile-live-collect`~~ | POST DDG; ложная JSON-капча; статус/ОКВЭД rusprofile | да | #9 | да | **Archived** 2026-09-09 |
| `fix-twogis-card-website` | Сайт из HTML карточки 2ГИС при пустом JSON | да | #26 | да | Archive группа 5 |
| `revise-index-available-data` | Индекс 50/25/25; без Fedresurs/KAD в сборе и UI; репутация по рейтингу+отзывам | да | #32 (+ #33–34) | **нет файла** | Archive группа 6; **сначала** добавить `tasks.md` или явную отметку в archive |

---

## Код без change (отдельно)

| что в коде | PR | OpenSpec change | рекомендация |
|------------|-----|-----------------|--------------|
| `src/salon_compare/yandex_viz.py` — опциональная карта Яндекс (JS API + geocoder), ключи `YANDEX_MAPS_JS_API_KEY` / `YANDEX_GEOCODER_API_KEY` | #40 | **отсутствует** | Retroactive change `add-yandex-map-viz` (или аналог) → затем archive; не смешивать с `drop-yandex-maps-source` (данные карт только 2ГИС) |

---

## Live specs (текущее состояние)

| файл | покрывает (кратко) | заметки |
|------|-------------------|---------|
| `openspec/specs/hook-intake/spec.md` | три зацепки, disambiguation, fallback | delta из групп 2–4 частично ещё только в changes |
| `openspec/specs/open-data-collect/spec.md` | каскад 2ГИС→HTML, юрблок, без Яндекс Places | обновлён под одну карту; scoring 50/25/25 — в change `revise-index`, не в live |
| `openspec/specs/project-bootstrap/spec.md` | uv, CI, `.env.example`, Streamlit hello | без ключа Яндекс Карт; viz-ключи PR #40 в live spec не отражены |

---

## Следующие шаги

1. Retroactive change для Yandex map UI.
2. `tasks.md` для `revise-index-available-data` (или waiver в archive).
3. **Stage 3b:** архивация группы 2 (инфраструктура и UX).
4. После merge — вынести `scoring-formula` в live specs (сейчас только в changes).

---

## Stage 2 — целевая структура specs

Целевая карта из **шести** capability (`project-bootstrap`, `hook-intake`, `open-data-collect`, `scoring-formula`, `streamlit-ui`, `llm-report`), правило «Яндекс.Карты = только UI в `streamlit-ui`», чеклист ревьюера «spec ↔ код» и порядок merge при архивации — в **[openspec/README.md](../openspec/README.md)**.

Stage 2 — только планирование; архивация change и полные тела `spec.md` — Stage 3+.
