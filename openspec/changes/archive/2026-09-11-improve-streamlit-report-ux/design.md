## Context

См. proposal.md — Why. Сейчас `_show_report` рисует карту, баннеры `collect_ok`, таблицу колонок, вывод модели и расход без карточек. `card_payload` / `CardView` есть в `report.py` и покрыты тестами, в `app.py` не вызываются. Сбор трёх точек — один `st.spinner("Собираем поля по трём точкам…")` вокруг `collect_three`. `st.set_page_config(..., layout="wide")` без max-width. Правки: `_edit_dialog` → `patch_field` / `mark_unreliable` → `_replace_working` → `_persist_working`. `PlaceScore.blocks` — кортеж `BlockScore` с `name` `reputation` | `stability` | `location` и `points: int | None`; индекс — `PlaceScore.index`. Тест `test_app_accepts_three_hooks_without_report` фиксирует строку spinner сбора и запрещает подстроку `сравнительн` в `app.py`.

## Goals / Non-Goals

**Goals:**

- Раскладка отчёта и CSS в `app.py` под приёмку.
- Показ карточек только через `card_payload`.
- Прогресс сбора, видимый по точке и этапу.
- Сохранить текущий путь правок ячеек.

**Non-Goals:**

- Менять формулу, `CardView`, каскад `collect_place`.
- Новый Streamlit-multipage / отдельный CSS-фреймворк.
- Трогать XSS/ключи карты.

## Decisions

- **Контейнер ~1100px:** обернуть отчёт (и при желании всю страницу ниже title) в `st.container` + CSS `max-width: 1100px; margin-inline: auto` на обёртке. Альтернатива `layout="centered"` отвергнута: ломает текущий wide без точного контроля 1100px.
- **Порядок блоков в `_show_report`:** (1) `_show_map` как справочный expander — без смены контракта карты; (2) баннеры падения сбора — сразу после карты, до сравнения, чтобы не терялись; (3) `_show_table` под заголовком «Сравнение» (слово «сравнительная» не использовать: тест запрещает `сравнительн`); (4) `_show_cards`; (5) `_show_verdict`; (6) `_show_usage`.
- **Карточки:** для каждой точки `st.expander` с `row.title` (+ пометка недостоверный при флаге). Внутри вызвать `card_payload(row, score_place(row))` и вывести `fields` (`label`, `text`, `source_url`), затем `missing`. Не собирать поля вручную из `FIELD_LABELS` в UI. Expander по умолчанию свёрнут, чтобы таблица оставалась первым рабочим видом.
- **Таблица:** оставить колонковый layout (не `st.dataframe` / `data_editor`): иначе сломаются покнопочные правки и сноски. Zebra: чередовать фон строк поля через CSS-класс на ряду (`even`/`odd`). `tabular-nums` на `.sc-cell-value` и ячейках лидеров/индекса. Строка «Индекс 50/25/25» остаётся; добавить компактную строку или подписи лидеров по трём блокам (баллы `points` или «не найдено») — данные только из `score_place`, без пересчёта весов в UI.
- **Лидеры:** для каждого ключа `reputation` / `stability` / `location` взять `points` по точкам; max среди не-`None`; пометить колонку (иконка/подпись «лидер» + `aria` не обязателен). Индекс: max среди `index is not None`. Ничья — все max. Недостоверный (`index is None`) не лидер индекса.
- **Прогресс сбора:** не оставлять один spinner на `collect_three`. Предпочтение: в UI цикл как в `collect_three` (try/except → `collect_ok` / `collect_error`) внутри `with st.status(...) as status:` и `status.update(label=f"точка {i} из {n} · {этап}")`. Этап минимум «поля»; если дешёво — прокинуть optional callback в `collect_place` / `collect_three` (`on_progress(i, n, stage: str)`), без смены каскада источников. Дублировать каскад в `app.py` нельзя. Кэш `rows_from_cache` MUST по-прежнему пропускать повторный сбор. Тест хука: убрать assert на «Собираем поля по трём точкам», проверить наличие `st.status` и шаблона «точка» / «из».
- **Правки:** не менять `_edit_dialog` / `_replace_working` / `_persist_working`, кроме ключей виджетов, если появятся новые кнопки. Карточки читают те же `working_rows`.

## Risks / Trade-offs

- [Цикл сбора в UI разъедется с `collect_three`] → Mitigation: тонкий callback или одна функция `collect_three(..., on_progress=...)`; UI не копирует `collect_place` каскад.
- [CSS zebra ломается из-за `st.columns` на каждую строку] → Mitigation: класс на контейнере строки, не на глобальном `stMarkdown`.
- [Широкая таблица трёх точек при 1100px] → Mitigation: 1100px как в ревью; горизонтальный скролл допустим, не расширять контейнер.
- [Тест `сравнительн`] → Mitigation: заголовок «Сравнение», не «сравнительная таблица».

## Migration Plan

- Один PR: OpenSpec + код + правка теста spinner. Откат: вернуть `_show_report` и spinner; данные SQLite не мигрировать.

## Open Questions

- Нет: этапы сбора достаточно грубые («поля» / имя источника из уже существующих логов), точный словарь этапов не меняет spec.
