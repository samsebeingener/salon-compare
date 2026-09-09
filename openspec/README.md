# OpenSpec — целевая карта capabilities (Stage 2 + Stage 3a–3f + Stage 4)

> Карта capabilities и правила merge.  
> **Stage 3a (2026-09-09):** группа 1 «юридический контур» заархивирована (5 change).  
> **Stage 3b (2026-09-09):** группа 2 «инфраструктура и UX» заархивирована (5 change).  
> **Stage 3c (2026-09-09):** группа 3 «отчёт и формула v1» ✅ заархивирована (3 change).  
> **Stage 3d (2026-09-09):** группа 4 «обогащение карт и disambiguation» ✅ заархивирована (4 change).  
> **Stage 3e (2026-09-09):** группа 5 «пост-Яндекс и каскад сайт↔юрлицо» ✅ заархивирована (5 change).  
> **Stage 3f (2026-09-09):** группа 6 «формула v2 (50/25/25)» ✅ заархивирована (`revise-index-available-data`).  
> **Stage 4 (2026-09-09):** retroactive `add-yandex-map-viz` (PR #40) → live **`streamlit-ui`**. **Активных change: 0.** См. [инвентаризацию](../docs/openspec-inventory.md#stage-3--прогресс-архивации).

## Что такое `openspec/specs/`

`openspec/specs/` — **live truth** (живая правда о продукте): что приложение **делает сейчас**, а не что планируется или уже смержено в код, но ещё не перенесено из change.

| Слой | Роль |
|------|------|
| `openspec/specs/<capability>/spec.md` | Актуальное поведение capability после архивации дельт |
| `openspec/changes/<имя>/` | Активная работа: proposal, design, tasks, дельты к specs |
| `openspec/changes/archive/` | Завершённые change (история решений) |

Правило: код в `main` не должен расходиться со `openspec/specs/` дольше одного PR. Все 23 исходных change заархивированы (Stage 3a–3f); live specs синхронизированы с кодом — см. [инвентаризацию](../docs/openspec-inventory.md).

Цикл работы с OpenSpec описан в [CONTRIBUTING.md — раздел OpenSpec](../CONTRIBUTING.md#openspec).

---

## Целевые capability после cleanup (Stage 3–5)

После архивации по группам 1→6 (см. [openspec-inventory](../docs/openspec-inventory.md)) в `openspec/specs/` остаётся **шесть** capability:

| Capability path | Покрывает (простыми словами) | Основные change для merge при архивации |
|-----------------|------------------------------|----------------------------------------|
| `project-bootstrap` | Запуск проекта, `.env`, Docker, quality gate (uv, CI, линтеры) | Архивированы группы 1–5; bootstrap без ключа Яндекс Карт для сбора |
| `hook-intake` | Три типа зацепки, подтверждение карточек, disambiguation, fallback без карт, slug Яндекс→2ГИС | Архивированы группы 2–5 |
| `open-data-collect` | Сбор полей салона: **только 2ГИС**, юридический блок, сайт, каскады DDG/РБК/политика | Архивированы группы **1, 4, 5** |
| `scoring-formula` | Индекс конкурента **50/25/25**, частичный score, репутация без Fedresurs/KAD | **Archived:** `revise-index-available-data` (группа 6, Stage 3f) |
| `streamlit-ui` | Таблица разборов, правки полей, SQLite runs, **карта Яндекс (только UI)** | **Live:** `add-yandex-map-viz` (PR #40); консолидация с `saved-runs` / `report-corrections` — Stage 5 |
| `llm-report` | Вывод модели, прокси, HTML-отчёт, usage/cost | Архивированы: `add-report-corrections`, `add-html-freshness-and-usage` |

Сейчас в live **девять** capability: `project-bootstrap`, `hook-intake`, `open-data-collect`, `saved-runs`, `delivery-readme`, `scoring-formula` (**v2**, 50/25/25), `report-corrections`, `html-freshness`, **`streamlit-ui`** (карта Яндекс, Stage 4). Группы 4–6 merged в `hook-intake`, `open-data-collect`, `scoring-formula`. Полная консолидация UI — Stage 5.

---

## Жёсткое правило: Яндекс.Карты

| Область | Источник данных | Где в OpenSpec |
|---------|-----------------|----------------|
| Сбор полей салона (адрес, часы, рейтинг, отзывы, координаты для scoring) | **Только 2ГИС** | `open-data-collect`, `hook-intake` |
| Визуализация карты в Streamlit (опциональный виджет) | Яндекс JS API + Geocoder (`yandex_viz.py`) | **Только** `streamlit-ui` |

Change `drop-yandex-maps-source` снимает Яндекс Places и поля карт из **сбора данных**. PR #40 (`yandex_viz.py`) — **отдельная** UI-фича; её нельзя смешивать с источниками в `open-data-collect`.

Ключи: `TWOGIS_API_KEY` — сбор; `YANDEX_MAPS_JS_API_KEY` / `YANDEX_GEOCODER_API_KEY` — только отображение в UI (`streamlit-ui` + необязательные плейсхолдеры в `project-bootstrap`). Старый `YANDEX_MAPS_API_KEY` для сбора не используется.

---

## Связанные документы

- [docs/openspec-inventory.md](../docs/openspec-inventory.md) — Stage 1: аудит 23 активных change, группы архивации, пробелы
- [CONTRIBUTING.md — OpenSpec](../CONTRIBUTING.md#openspec) — обязательный цикл change → PR → archive → specs
- `openspec/config.yaml` — конфигурация OpenSpec в репозитории

---

## Чеклист ревьюера: «spec соответствует коду»

Использовать при review PR и после архивации change в `openspec/specs/`.

### Общее

- [ ] Изменение поведения сопровождается change в `openspec/changes/` или обновлением live spec в том же PR
- [ ] Нет противоречий между двумя capability (например, сбор из 2ГИС в `open-data-collect` и запрет Яндекс-источников в `drop-yandex-maps-source`)
- [ ] `openspec/changes/` не копит завершённую работу: после merge — архив и merge delta → `openspec/specs/`

### По capability

- [ ] **project-bootstrap** — `.env.example`, Docker/CI, quality gate и ключи API соответствуют фактическим переменным в коде (без устаревших `YANDEX_MAPS_API_KEY` для сбора)
- [ ] **hook-intake** — три зацепки, radio/подтверждение, disambiguation (адрес, этаж/ТЦ), fallback без ключей карт
- [ ] **open-data-collect** — каскад 2ГИС → HTML/сайт → юрблок; нет полей/вызовов Яндекс Places; честные статусы реестров
- [ ] **scoring-formula** — веса **50/25/25**; частичный индекс; репутация по рейтингу+отзывам (не Fedresurs/KAD в формуле)
- [ ] **streamlit-ui** — таблица, правки, SQLite `data/`, список/открытие runs; карта Яндекс — опциональный UI, не влияет на собранные поля
- [ ] **llm-report** — JSON-вердикт, карточки салона, блок usage/cost, HTML-свежесть; прокси и модель из env

### Код без spec (красные флаги)

- [ ] Новый модуль/поведение в `src/` без дельты в change или live spec
- [ ] `yandex_viz.py` описан только в `streamlit-ui`, не в `open-data-collect`
- [ ] Формула или веса в коде ≠ `scoring-formula` (после выноса в live)

### После архивации

- [ ] Дельты из `openspec/changes/archive/.../specs/` перенесены в `openspec/specs/<capability>/spec.md`
- [ ] В [openspec-inventory](../docs/openspec-inventory.md) нет «висящих» change из архивированной группы
- [ ] Тесты и quality gate зелёные; требования из spec покрыты сценариями или явно помечены как manual QA

---

## Что дальше

1. **Stage 5:** консолидация `streamlit-ui` / `llm-report` и финальная карта capability
