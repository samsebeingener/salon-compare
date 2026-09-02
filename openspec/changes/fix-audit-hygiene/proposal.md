# Proposal: fix-audit-hygiene

## Why

Аудит после вырезания Яндекса: живой HTML-парсер не заполняет «о нас» и рейтинг, хотя collect и таблица их ждут. Ссылка Яндекс Карт даёт `yandex:{id}` и пустые поля 2ГИС. Live OpenSpec и куски ПОДГОТОВКА ещё описывают две карты. В src лежат неиспользуемые `EmptyParser` и `PassthroughResolver`.

## What Changes

- `OpenHtmlParser` читает только явные маркеры: JSON-LD / meta / заголовок «О нас» — без выдумки.
- Зацепка `yandex.ru/maps/org/{slug}/…` ищет 2ГИС по человекочитаемому slug. Голый числовой id — без выдуманного поиска, карточка как сейчас.
- Live `openspec/specs/` и пометки в ПОДГОТОВКА §5–9: одна карта 2ГИС.
- Удалить мёртвые `EmptyParser`, `PassthroughResolver`.
- Подпись соседей: не «рейтинг», а выше/ниже. Упростить prefix в score.

## Capabilities

### New Capabilities

- (нет)

### Modified Capabilities

- `open-data-collect`: HTML-каскад about/rating/address из явных маркеров.
- `hook-intake`: Яндекс-ссылка со slug → поиск 2ГИС.
- `project-bootstrap` / live specs: без `YANDEX_MAPS_API_KEY`.
- `scoring-formula`: репутация только 2ГИС (sync live, если появится файл).

## Impact

- Код: `html_parse.py`, `resolver.py`, `maps_parse.py`, `collect.py`, `intake.py`, `score.py`, `app.py`, `report.py`.
- Документы: `openspec/specs/*`, ПОДГОТОВКА (пометки, не перепись задания).
- Не входит: Playwright, платный ППО, блок локации/масштаба без данных, обход капчи.
