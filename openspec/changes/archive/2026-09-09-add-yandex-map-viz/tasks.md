## 1. OpenSpec (retroactive, PR #40)

- [x] 1.1 Change `add-yandex-map-viz`: proposal, design, tasks, deltas `streamlit-ui` + `project-bootstrap`
- [x] 1.2 `openspec archive add-yandex-map-viz -y` → live `openspec/specs/streamlit-ui/spec.md`
- [x] 1.3 `openspec validate --specs`

## 2. Код и тесты (уже в main)

- [x] 2.1 `yandex_viz.py`: маркеры, геокод, viewport, HTML
- [x] 2.2 `app._show_map`: expander, два ключа, caption «не влияет на индекс»
- [x] 2.3 `tests/test_yandex_viz.py`
- [x] 2.4 `.env.example`, `compose.yaml`, README

## 3. Документация Stage 4

- [x] 3.1 `docs/openspec-inventory.md` — пробел PR #40 закрыт
- [x] 3.2 `openspec/README.md` — Stage 4, live `streamlit-ui`
- [x] 3.3 `uv run python scripts/run_quality.py`
