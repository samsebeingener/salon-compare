# salon-compare

Сравнение трёх маникюрных точек Москвы для инвестора: открытые данные, оценка привлекательности и честная достоверность.

Тестовое задание. Сейчас в репозитории каркас Streamlit (hello), без сбора салонов.

## Клонирование

```text
git clone https://github.com/samsebeingener/salon-compare.git
cd salon-compare
cp .env.example .env
```

Локально:

```text
uv sync --group dev
uv run python scripts/run_quality.py
uv run streamlit run src/salon_compare/app.py
```

Сдача заказчику:

```text
docker compose up --build
```

Приложение: http://127.0.0.1:8501 — ключ модели для hello не нужен.

Лицензия: [MIT](LICENSE). Автор: [Никита Куликов](https://samsebeingener.ru) ([samsebeingener](https://github.com/samsebeingener)).

## Как идут изменения

Каждый шаг — отдельная ветка и pull request в `main`. Не пушим рабочий код напрямую в `main`.

## Документы

- [ПОДГОТОВКА.md](ПОДГОТОВКА.md) — согласованные правила
- [Анализ маникюрных в Москве.html](Анализ%20маникюрных%20в%20Москве.html) — текст задания
- [AGENT_RULES.md](AGENT_RULES.md) — ограничения для агента

## Участие и безопасность

См. [CONTRIBUTING.md](CONTRIBUTING.md), [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md), [SECURITY.md](SECURITY.md).
