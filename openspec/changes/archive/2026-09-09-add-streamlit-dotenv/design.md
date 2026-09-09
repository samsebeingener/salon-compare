# Design: add-streamlit-dotenv

## Decisions

- Парсер `KEY=VALUE` без сторонних пакетов. Кавычки снимаем. Строки `#` и пустые — нет.
- `load_dotenv_file(path, environ=os.environ)`: ключ пишем только если в `environ` его ещё нет или он пустой.
- Путь по умолчанию: корень репозитория (`Path(__file__).resolve().parents[2] / ".env"`), как у SQLite.
- Вызов только из `app.py` на импорте, не из `maps_http`: pytest не должен подхватывать живые ключи.
- Нет файла — тихий no-op.

## Risks

- Старый процесс Streamlit всё равно нужно перезапустить один раз.
- В контейнере `.env` в образ не копируется — Compose по-прежнему задаёт env; загрузка файла no-op.
