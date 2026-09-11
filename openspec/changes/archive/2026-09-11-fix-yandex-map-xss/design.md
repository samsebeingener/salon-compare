# Design: fix-yandex-map-xss

## Context

`yandex_viz.py` собирает HTML карты: `json.dumps` точек вставляется как `const POINTS = {payload};` внутри `<script>`. Если `title` или `address` из 2ГИС содержат `</script>`, парсер HTML закрывает тег (S1). Те же строки идут в `balloonContentHeader` / `balloonContentBody` как HTML Яндекс API — `<img src=x onerror=...>` исполняется в балуне (S2). Оба вектора закрываются в одном change.

## Goals / Non-Goals

**Goals:**

- S1: JSON точек не ломает `<script>` (отдельный `application/json` + escape `</`, `<`, `>`, `&`).
- S2: содержимое балуна HTML-экранировано через `html.escape` на сервере до свойств метки.
- Регрессионные тесты на оба payload.

**Non-Goals:**

- Менять геокод, viewport, ключи, expander.
- DOMPurify / клиентская санитизация вместо серверного escape.
- Экранировать ключ JS API (он в `src` скрипта Яндекса, не в данных 2ГИС).

## Decisions

- **S1 — JSON вне executable script:** сериализовать точки `json.dumps(..., ensure_ascii=False)`, затем replace `"</"` (и при необходимости `"<!--"`), плюс unicode-escape `<` `>` `&` → `\u003c` `\u003e` `\u0026`. Кладём результат в `<script type="application/json" id="...">`. Клиент: `JSON.parse(document.getElementById(...).textContent)`. MUST NOT оставлять `const POINTS = {payload}` внутри JS-скрипта.
- **S2 — balloon до свойств метки:** `html.escape(title, quote=True)` и то же для `address` (пустой адрес — как сейчас «адрес не найден», уже безопасная константа). Escape **до** попадания в payload JSON / свойства Placemark.
- **Порядок:** сначала escape полей балуна, затем dumps + script-safe encode. Так балун безопасен даже если клиент читает JSON как HTML-строки API.
- **Тесты:** HTML не содержит сырую последовательность `</script>` из title/address внутри JS; после рендера в разметке нет незаэскейпленного `<img src=x onerror=`. Quality gate без браузера: проверка строки HTML.

## Risks / Trade-offs

- [Двойной escape в балуне] → приемлемо: лучше `&lt;img` в тексте метки, чем XSS.
- [ensure_ascii=False + unicode escape только спецсимволов] → кириллица остаётся читаемой, ломающие символы — нет.
- [Яндекс API сам экранирует balloon] → не полагаемся; серверный `html.escape` обязателен.
