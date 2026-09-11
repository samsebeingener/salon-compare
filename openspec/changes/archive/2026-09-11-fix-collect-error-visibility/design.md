# Design: fix-collect-error-visibility

## Context

`collect_three` обходит три точки независимо: `except Exception` не рвёт цикл, но вызывает `_empty_place` без следа. Инвестор в таблице видит те же «не найдено», что и при пустом 2ГИС. `_safe_card` делает то же на уровне карточки: любой сбой `fetch_card` → пустые поля, как будто API честно пуст.

Каскад API→HTML→missing не меняем. Меняем только видимость **исключения кода/сети**, которое сейчас неотличимо от missing.

## Goals / Non-Goals

**Goals:**

- Исключение при сборе точки → запись с `collect_ok=False` и кратким `collect_error`.
- Лог: полный traceback (`logging.exception`).
- UI: баннер «Сбор точки X упал» + короткое сообщение без stack.
- Две другие точки собираются как сейчас.
- Старые payload без полей открываются (`collect_ok=True`).

**Non-Goals:**

- Retry, смена каскада, отдельные типы ошибок по каждому источнику.
- DOM/HTML stack в карточке.
- Падать всем `collect_three` из‑за одной точки.

## Decisions

- **Поля записи:** `collect_ok: bool = True`, `collect_error: str | None = None`. Успешный `collect_place` не трогает дефолты. `_empty_place` по умолчанию тоже `True`/`None` (честный пустой каркас); флаги сбоя ставит только обработчик исключения в `collect_three` (и тесты могут собрать запись вручную).
- **Сообщение:** `f"{type(exc).__name__}: {exc}"` обрезать до разумной длины (~200 символов), без traceback. Не класть тело HTML/ответа API.
- **`collect_three`:** оставить цикл и независимость точек. В `except Exception`: `logging.exception("collect_place failed venue_id=%s", venue.venue_id)`; `row = _empty_place(venue)` с `collect_ok=False` и `collect_error=...`; append. MUST NOT глотать без лога и флагов.
- **`_safe_card` — узкий except (предпочтительно):** ловить только `httpx.HTTPError` (или базовый тип клиента, которым пользуется `maps_http`) и `OSError`. Тогда пустая `MapCard` = «карточки нет / сеть»; `AttributeError`/`TypeError`/`KeyError` всплывают из `collect_place` и помечают точку как сбой сбора. Пустой ответ API без исключения по-прежнему missing, `collect_ok=True`.
  - Если импорт `httpx` в `collect.py` нежелателен: ловить `OSError` + тип из `maps_http` (например алиас `MapsHttpError`), не голый `Exception`.
  - Логировать пойманную сеть: `logging.exception` или `logging.warning` с venue_id; карточка остаётся пустой, **без** `collect_ok=False` (это отсутствие данных источника, не падение разбора точки).
- **UI:** после таблицы или над колонкой точки, если `not row.collect_ok`: `st.error` / `st.warning` вида «Сбор точки {title} упал» и `collect_error`. Три баннера, если упали все три. Scoring/таблица полей остаются (пустые missing).
- **Coerce:** в `coerce_place_record` `setdefault("collect_ok", True)` и `setdefault("collect_error", None)` до `model_validate`, по аналогии с `map_lat`/`map_lon`.

## Risks / Trade-offs

- [Сеть как сбой точки vs missing карточки] → сеть в `_safe_card` = пустая карта + лог; баг кода = `collect_ok=False`. Инвестор отличает «2ГИС пуст» от «упал парсер».
- [Широкий except в `_safe_card` «на всякий случай»] → запрещён: снова маскирует TypeError.
- [Двойной escape / длинный str(exc)] → обрезка; UI не рендерит HTML из сообщения (`st.error` текста достаточно).
- [Старые JSON] → default True: прошлые прогоны не помечаются ложным сбоем.
