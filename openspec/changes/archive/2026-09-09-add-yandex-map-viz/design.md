# Design: add-yandex-map-viz

## Context

`drop-yandex-maps-source` убрал платный Geosearch и поля `yandex_*` из сбора. Пользователю всё ещё нужна наглядная карта трёх салонов в отчёте. Streamlit не отдаёт рейтинг через JS API, но **показать метки по координатам 2ГИС или геокоду адреса** — отдельная задача только для UI.

Модуль: `src/salon_compare/yandex_viz.py`. Вызов из `app._show_map` перед таблицей.

## Goals / Non-Goals

**Goals:**

- Expander с `st.components.v1.html` и Яндекс JS API 2.1.
- Два env-ключа: JS API и Geocoder (разные продукты в кабинете Яндекса).
- Координаты из `PlaceRecord.map_lat` / `map_lon` (2ГИС); fallback — `geocode-maps.yandex.ru/1.x/` на сервере.
- Viewport: центр по меткам, `setBounds` с margin для нескольких точек, фиксированный zoom для одной.
- Явная подпись: не влияет на сбор и индекс.

**Non-Goals:**

- Писать координаты или поля Яндекса в SQLite.
- Вызывать Яндекс в `collect.py`, `score.py`, `maps_http.py`.
- Обязательные ключи для старта приложения.
- Новые pip-зависимости (httpx уже есть).

## Decisions

- **Изоляция:** весь Яндекс-код в `yandex_viz.py` + `_show_map` в `app.py`; `open-data-collect` не трогаем.
- **Ключи:** `YANDEX_MAPS_JS_API_KEY` — только подгрузка `<script src="api-maps.yandex.ru">`; `YANDEX_GEOCODER_API_KEY` — только `geocode_yandex_http` при отсутствии lat/lon.
- **Порядок геокода:** адрес с префиксом «Москва,» если нет в строке; затем «Москва, {title}».
- **Viewport:** `compute_map_viewport` на Python для начального center/zoom; в HTML — `setBounds` + `MIN_ZOOM` 13, single point zoom 15.
- **Ошибки:** нет JS-ключа → `st.info`; нет геокодера при нужде → `st.warning`, карта с теми метками, у кого есть coords; ноль меток → предупреждение, без падения.
- **Bootstrap:** `.env.example` и `compose.yaml` документируют оба viz-ключа; `YANDEX_MAPS_API_KEY` (старый ключ сбора) по-прежнему запрещён.

## Risks / Trade-offs

- [Геокодер платный / лимиты] → опциональный ключ; при отсутствии — только точки с coords 2ГИС.
- [Путаница с drop-yandex] → жёсткое правило в `streamlit-ui` spec и README: viz ≠ collect.
- [Тесты с сетью] → `geocode_yandex_http` мокается в pytest; quality gate без интернета.
