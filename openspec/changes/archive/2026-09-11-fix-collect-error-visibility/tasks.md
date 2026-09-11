## 1. OpenSpec

- [x] 1.1 Change `fix-collect-error-visibility`: proposal, design, tasks, дельты `open-data-collect` и `streamlit-ui`
- [x] 1.2 `openspec validate` для change (без archive до кода)

## 2. Код и тесты (другой агент)

- [x] 2.1 `PlaceRecord`: `collect_ok: bool = True`, `collect_error: str | None = None`
- [x] 2.2 `coerce_place_record`: defaults `True` / `None` для старых JSON
- [x] 2.3 `collect_three`: `logging.exception`; `_empty_place` + `collect_ok=False` + краткое сообщение; остальные точки продолжаются
- [x] 2.4 `_safe_card`: except только httpx/OSError (лог); `TypeError`/`AttributeError` пробрасывать
- [x] 2.5 UI: баннер «Сбор точки X упал» при `collect_ok` ложь; без stack
- [x] 2.6 Тесты: исключение в одной из трёх → флаг сбоя только у неё; coerce без полей; `_safe_card` не глотает TypeError; сеть → пустая карта без `collect_ok=False`

## 3. Проверка

- [x] 3.1 `uv run python scripts/run_quality.py`
