## 1. OpenSpec

- [x] 1.1 Change `add-partial-scale-fields`: proposal, design, tasks, дельты `open-data-collect` и `streamlit-ui` лежат в `openspec/changes/add-partial-scale-fields/`
- [x] 1.2 `openspec validate add-partial-scale-fields --type change --strict` проходит (без archive до кода)

## 2. Код и тесты (другой агент)

- [x] 2.1 `maps_parse`: рубрики (топ 3 `name`), `place_type` (ТЦ / этаж / улица), `price_level` только явное JSON-поле; фикстуры в `tests/test_maps_parse.py` без сети
- [x] 2.2 `MapCard` + `PlaceRecord` + `collect_place`: `twogis_rubrics`, `place_type`, `twogis_price_level`; нет GET сайта ради цены; свежесть отзывов без выдумки (часто MISSING)
- [x] 2.3 `FIELD_LABELS` (и секции таблицы): `twogis_last_review`, `twogis_reviews_90d`, `twogis_plus_minus`, `place_type`, `twogis_rubrics`, `twogis_price_level`; пустое → «не найдено»; `score.py` без блока масштаб
- [x] 2.4 Старый JSON без новых ключей открывается; тест таблицы/карточки видит новые строки; лидера «масштаб» нет

## 3. Проверка

- [x] 3.1 `uv run python scripts/run_quality.py`
- [x] 3.2 Archive change только после merge кода, не в этом шаге
