# Design: fix-live-collect-honesty

## Context

Прогон без ключей карт: сайт 404, реестры — оболочка. Тесты по-прежнему фикстуры.

## Goals / Non-Goals

**Goals:** не угадывать карточку; не врать по реестрам; ИНН≠ОГРН; соседи из API при наличии точки; честный 404.

**Non-Goals:** LLM-парсер, обход капчи, смена демо-зацепки в ПОДГОТОВКА, формула баллов.

## Decisions

- `classify_fetch(status, body)`: 401/403/429 или маркеры капчи (`captcha`, `recaptcha`, `smartcaptcha`, `cloudflare`) → blocked. Слово «войти» само по себе — нет.
- Значение реестра только если идентификатор есть в теле HTML.
- Федресурс/КАД только если `len(digits) in {13,15}`.
- 2ГИС `fields` включает `items.point`. Nearby: `point` + `radius=500` + `type=branch`, исключить свой id.
- HTML GET с обычным browser User-Agent.
- Radio: пустой выбор не заменяется на `options[0]`.

## Risks / Trade-offs

- Без ключа 2ГИС соседи в живом UI пустые — честно.
- Подстрока `captcha` на КАД по-прежнему blocked — совпадает с прогоном (данных нет).
