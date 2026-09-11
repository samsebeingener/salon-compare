# Proposal: fix-collect-error-visibility

## Why

`collect_three` ловит любой `Exception` вокруг `collect_place` (~926) и подставляет `_empty_place`: инвестор видит «все поля не найдены» и не отличает молчание API от бага парсера. `_safe_card` (~470) так же глотает `Exception` (включая `AttributeError`/`TypeError`) и отдаёт пустую `MapCard`. Сбой должен быть виден в записи и в UI, без остановки двух других точек.

## What Changes

- На `PlaceRecord`: `collect_ok: bool = True`, `collect_error: str | None = None`.
- При исключении в `collect_three`: `logging.exception`, затем `_empty_place` с `collect_ok=False` и кратким сообщением (тип исключения; stack только в лог, не в UI).
- `_safe_card`: не глотать баг кода. Ловить только сетевые сбои (`httpx`/`OSError`); `TypeError`/`AttributeError` пробрасывать в `collect_place` → тот же путь `collect_ok=False`. Пустая карточка API без исключения остаётся «не найдено».
- UI: баннер «Сбор точки X упал», если `collect_ok` ложь.
- Старый JSON без полей: `coerce_place_record` ставит `True` / `None`.

## Capabilities

### New Capabilities

- (нет)

### Modified Capabilities

- `open-data-collect`: сбой сбора точки помечается в записи, не маскируется под «не найдено».
- `streamlit-ui`: баннер падения сбора по точке.

## Impact

- Код (другой агент): `collect.py` (`PlaceRecord`, `_empty_place`, `_safe_card`, `collect_three`, `coerce_place_record`), `app.py` (баннер). Тесты: `test_collect.py` / coerce.
- Не входит: каскад API→HTML, scoring, карта Яндекс, SQLite-схема кроме JSON payload точки.

## Non-Goals

- Менять архитектуру каскада полей.
- Останавливать весь прогон из‑за одной точки.
- Показывать stack trace в Streamlit.
- Менять семантику «не найдено» при честом отсутствии данных API/HTML.
