## 1. OpenSpec

- [x] 1.1 Change `fix-llm-usage-accumulation`: proposal, design, tasks, дельты `html-freshness` и `project-bootstrap`
- [x] 1.2 `openspec validate` для change (без archive до кода)

## 2. Код и тесты (другой агент)

- [x] 2.1 `llm.merge_usage(a, b)`: сумма prompt/completion/total/cost; `None+5=5`, `None+None=None`
- [x] 2.2 `save_run_usage`: читать старый usage из payload, сохранять merge, не замену
- [x] 2.3 UI: при успехе merge в session; пустой usage нового вызова не затирает накопленное и не пишет пустышку в БД
- [x] 2.4 Тест store: два `save_run_usage` подряд `total_tokens` 1200 затем 1050 → 2250

## 3. Проверка

- [x] 3.1 `uv run python scripts/run_quality.py`
