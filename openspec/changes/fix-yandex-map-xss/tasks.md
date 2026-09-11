## 1. OpenSpec

- [x] 1.1 Change `fix-yandex-map-xss`: proposal, design, tasks, delta `streamlit-ui`
- [x] 1.2 `openspec validate` для change (без archive до кода)

## 2. Код и тесты (другой агент)

- [x] 2.1 `yandex_viz.py`: JSON точек в `<script type="application/json">` + `JSON.parse`; dumps + replace `"</"` и unicode escape `<` `>` `&`
- [x] 2.2 `html.escape` для `title` / `address` балуна на сервере до свойств метки
- [x] 2.3 Убрать сырой `const POINTS = {payload}` из executable `<script>`
- [x] 2.4 Тесты: payload `</script>` в названии; `<img src=x onerror=...>` в адресе; HTML без сырого `</script>` из полей и с экранированным balloon

## 3. Проверка

- [x] 3.1 `uv run python scripts/run_quality.py`
