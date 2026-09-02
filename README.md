# salon-compare

Сравнение трёх маникюрных точек Москвы для инвестора: открытые данные, оценка привлекательности и честная достоверность.

Тестовое задание. Сейчас можно ввести три зацепки; сбор карт и отчёт ещё не включены.

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

Приложение: http://127.0.0.1:8501 — ключ модели для разбора зацепок не нужен.

На экране три поля. Приложение определяет тип зацепки (сайт, название, ОГРН, ИНН, ссылка на карты или запись, текст). Если точек несколько или две зацепки — один салон, покажет ссылки и попросит уточнить. Поиск на картах — следующий шаг.

## Прокси для LLM из РФ

Если модель с вашего компьютера в России не открывается, в `.env` задайте прокси (скопируйте из `.env.example`):

```text
HTTP_PROXY=http://USER:PASSWORD@HOST:PORT
HTTPS_PROXY=http://USER:PASSWORD@HOST:PORT
```

Это **ваш** HTTP-прокси (корпоративный или купленный), в формате `http://логин:пароль@хост:порт`. Публичные «бесплатные» списки не подходят и в репозиторий не пишем. Пустые значения — без прокси. Клиент LLM берёт `HTTP_PROXY` / `HTTPS_PROXY` из окружения. Docker Compose прокидывает их в контейнер; healthcheck на localhost через прокси не идёт.

Hello-каркас сам к LLM не ходит; переменные нужны заранее, чтобы не забыть на шаге с моделью.

Лицензия: [MIT](LICENSE). Автор: [Никита Куликов](https://samsebeingener.ru) ([samsebeingener](https://github.com/samsebeingener)).

## Как идут изменения

Каждый шаг — отдельная ветка и pull request в `main`. Не пушим рабочий код напрямую в `main`.

## Документы

- [ПОДГОТОВКА.md](ПОДГОТОВКА.md) — согласованные правила
- [Анализ маникюрных в Москве.html](Анализ%20маникюрных%20в%20Москве.html) — текст задания
- [AGENT_RULES.md](AGENT_RULES.md) — ограничения для агента

## Участие и безопасность

См. [CONTRIBUTING.md](CONTRIBUTING.md), [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md), [SECURITY.md](SECURITY.md).
