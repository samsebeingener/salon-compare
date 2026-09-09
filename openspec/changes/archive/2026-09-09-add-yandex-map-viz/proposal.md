# Proposal: add-yandex-map-viz

## Why

После `drop-yandex-maps-source` сбор полей идёт только через 2ГИС, но в отчёте Streamlit полезно **визуально** сравнить три точки на карте. PR #40 добавил `yandex_viz.py` и блок «Карта» в expander — код уже в `main`, OpenSpec-пробел закрываем retroactive change.

Важно: это **только UI**. Яндекс JS API и HTTP-геокодер не участвуют в `collect`, `score` и не пишут поля в SQLite.

## What Changes

- Опциональный expander «Карта (Яндекс JS API, только просмотр)» в отчёте после сбора или открытия сохранённого разбора.
- Два **отдельных** ключа в кабинете Яндекса: `YANDEX_MAPS_JS_API_KEY` (карта в браузере) и `YANDEX_GEOCODER_API_KEY` (адрес → координаты на сервере, если 2ГИС не отдал `map_lat` / `map_lon`).
- Координаты: сначала `map_lat` / `map_lon` из записи 2ГИС; иначе один HTTP-запрос к Geocoder API по адресу или названию.
- Начальный viewport подгоняется под метки (`setBounds` / zoom по span).
- Без ключей — подсказка в UI, таблица и индекс работают как раньше.

## Capabilities

### New Capabilities

- `streamlit-ui`: опциональная карта Яндекс в expander; изоляция от сбора и scoring.

### Modified Capabilities

- `project-bootstrap`: необязательные viz-ключи в `.env.example` и `compose.yaml`; по-прежнему нет `YANDEX_MAPS_API_KEY` для сбора.

## Impact

- Код (уже merged, PR #40): `yandex_viz.py`, `app.py` (`_show_map`), `tests/test_yandex_viz.py`, README, `.env.example`, `compose.yaml`.
- Не входит: возврат Яндекс Places / полей `yandex_*`; изменение формулы или каскада 2ГИС; новые зависимости.

## Non-Goals

- Смешивать с `drop-yandex-maps-source` (данные карт только 2ГИС).
- Требовать ключи Яндекса для демо-прогона до таблицы.
- Геокодировать в `collect` или сохранять координаты Яндекса в payload.
