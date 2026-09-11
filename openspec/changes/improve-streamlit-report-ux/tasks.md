## 1. OpenSpec

- [x] 1.1 Change `improve-streamlit-report-ux`: proposal, design, tasks, дельта `streamlit-ui` на месте в `openspec/changes/improve-streamlit-report-ux/` — `openspec validate improve-streamlit-report-ux --type change --strict` проходит

## 2. Раскладка отчёта

- [x] 2.1 Обернуть отчёт контейнером `max-width: 1100px` по центру — в CSS обёртки есть это значение, `layout="wide"` не растягивает таблицу на весь экран
- [x] 2.2 `_show_report`: карта → баннеры сбора → сравнение → карточки → вывод модели → расход — по исходному `app.py` вызовы идут в этом порядке, заголовок сравнения без подстроки `сравнительн`

## 3. Таблица и карточки

- [x] 3.1 CSS zebra + `tabular-nums` на ячейках сравнения — в стилях есть чередование строк и `font-variant-numeric: tabular-nums` (или Tailwind-эквивалент не используется: чистый CSS)
- [x] 3.2 Строки/пометки лидеров по `PlaceScore.blocks` (`reputation` / `stability` / `location`) и индексу, ничья = все max, `None` не лидер — тест на чистую функцию лидеров (вынести из UI или проверить по разметке фикстурой трёх `PlaceRecord`)
- [x] 3.3 Expander на каждую точку: `card_payload(row, score_place(row))`, поля / `source_url` / `missing` — в `app.py` есть `card_payload`, нет второй схемы карточки; три expander при трёх рядах
- [x] 3.4 Диалог правки ячейки без регрессии: `_replace_working` + `_persist_working` вызываются как сейчас — существующие тесты `patch_field` / store зелёные; после «Сохранить» значение в таблице и в карточке одно

## 4. Прогресс сбора

- [x] 4.1 Сбор точек через `st.status` «точка i из n · этап»; убрать spinner «Собираем поля по трём точкам»; кэш `rows_from_cache` без повторного сбора — в `app.py` нет этой spinner-строки, есть `st.status` и шаблон точки/этапа; каскад `collect_place` не скопирован в UI
- [x] 4.2 В `test_hook_intake.py` снять assert на «Собираем поля по трём точкам»; утверждать `st.status` и «точка»/«из» — тест зелёный, `сравнительн` по-прежнему нет

## 5. Quality

- [x] 5.1 `uv run python scripts/run_quality.py` проходит
