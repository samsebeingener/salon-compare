## 1. OpenSpec и формула (PR #32)

- [x] 1.1 Change `revise-index-available-data`: proposal + delta `scoring-formula` (50/25/25) + delta `open-data-collect` (без GET fedresurs/kad)
- [x] 1.2 `score.py`: веса 50/25/25 (репутация / устойчивость / локация); масштаб убран; Fedresurs/KAD не входят в устойчивость
- [x] 1.3 Репутация: только рейтинг 2ГИС; +3 при >4.5 без требования свежести отзывов
- [x] 1.4 Устойчивость: дата и статус ЕГРЮЛ/ЕГРИП; ликвидация → 0; без «долгов нет»
- [x] 1.5 Локация: метро (метры) + соседи выше/ниже; частичный индекс без нуля за дыры
- [x] 1.6 `collect.py`: убраны GET на `fedresurs.ru` и `kad.arbitr.ru`; поля `fedresurs`/`kad` остаются gap (SQLite legacy)
- [x] 1.7 UI/README: «Индекс 50/25/25», без «покупай»; `ПОДГОТОВКА.md` / README обновлены
- [x] 1.8 Тесты: `test_score.py`, `test_legal.py`, `test_live_honesty.py` — формула и отсутствие запросов реестров судов

## 2. Скрытие полей ленты отзывов (PR #33)

- [x] 2.1 Delta `scoring-formula`: отзывы/свежесть/плюс-минус MUST NOT входить в индекс и таблицу
- [x] 2.2 `collect.py` / `report.py` / `app.py`: убраны колонки «2ГИС отзывы», «последний отзыв», «отзывы за 90 дней», «плюс/минус» из таблицы и карточек
- [x] 2.3 `score.py`: репутация не читает поля отзывов
- [x] 2.4 Тесты: `test_score.py`, `test_drop_yandex.py`, `test_html_freshness.py`

## 3. UI-гигиена (PR #34)

- [x] 3.1 `app.py`: убраны дублирующие карточки салона и лишняя строка пояснения индекса
- [x] 3.2 README / `test_delivery.py` / `test_report.py` — согласованы с таблицей

## 4. Quality

- [x] 4.1 `uv run python scripts/run_quality.py` — зелёный на main после merge #32–34
