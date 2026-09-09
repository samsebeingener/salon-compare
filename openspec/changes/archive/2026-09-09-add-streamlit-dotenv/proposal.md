# Proposal: add-streamlit-dotenv

## Why

Локальный Streamlit не читает `.env`. Ключи 2ГИС в файле есть, процесс пустой → поиск карт ноль карточек → fallback website/name/ogrn → таблица «не найдено». Docker Compose переменные прокидывает, `uv run streamlit` — нет. Новых пакетов не ставим.

## What Changes

- При старте приложения загрузить `.env` из корня проекта стандартной библиотекой.
- Не перезаписывать уже заданные переменные окружения (Docker/CI важнее файла).
- Пустые значения и комментарии пропускать. Файл `.env` по-прежнему в gitignore.
- README: локальный Streamlit берёт ключи из `.env`.

## Capabilities

### New Capabilities

- (нет)

### Modified Capabilities

- `project-bootstrap`: Streamlit читает `.env` без python-dotenv.

## Impact

- Код: `load_env.py`, вызов из `app.py`, тесты на tmp_path. Новых зависимостей нет.
- Не входит: формула, ключ Яндекса, коммит `.env`.
