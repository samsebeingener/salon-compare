## 1. OpenSpec

- [x] 1.1 Change `add-llm-field-extract`: proposal, design, tasks, дельты `open-data-collect`, `html-freshness`, `project-bootstrap`
- [x] 1.2 `openspec validate add-llm-field-extract --type change --strict` проходит (без archive до кода)

## 2. Код и тесты (другой агент)

- [x] 2.1 Модуль `src/salon_compare/llm_extract.py`: `EXTRACT_FIELDS`, `ExtractPatch`, `gaps_for`, `parse_extract`, `apply_extract`, `extract_missing`; без HTTP
- [x] 2.2 `app.py`: после `collect_three` при `wrote=True` и не-`NullLlm` — один extract на точку с дырами; `collect_ok` ложь пропускать; `merge_usage` + `save_run_usage`
- [x] 2.3 Не вызывать добор из `maps_http` и не встраивать LLM в `collect_place`
- [x] 2.4 Тесты `tests/test_llm_extract.py` без сети: валидный JSON → WEAK `source_url="модель"`; плохой JSON → MISSING; нет gaps → `complete` не вызывается

## 3. Проверка

- [x] 3.1 `uv run python scripts/run_quality.py`
- [x] 3.2 Archive change только после merge кода, не в этом шаге
