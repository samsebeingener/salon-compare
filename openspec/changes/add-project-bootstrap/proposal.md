# Proposal: add-project-bootstrap

## Why

Репозиторий пока только с документами: заказчик не может клонировать, поднять приложение одной командой и убедиться, что качество проверяется так же, как в CI. Каркас нужен сейчас, чтобы все следующие OpenSpec-изменения и TDD шли уже в готовый Python-проект, а не в пустую папку.

## What Changes

- Завести каркас Python 3.12: `uv`, Streamlit hello, SQLite как будущий файл рядом с проектом (сам файл в git не кладём).
- Одна команда качества: `ruff` + `mypy` + `pytest`. Та же команда — в GitHub Actions.
- Docker Compose поднимает hello-приложение. Ключ модели для старта не обязателен.
- В git есть `.env.example` с `TWOGIS_API_KEY`, `YANDEX_MAPS_API_KEY`, переменными `LLM_*`, `HTTP_PROXY` и `HTTPS_PROXY` (прокси, если LLM не открывается из РФ). Файл `.env` в git не попадает.
- Тесты не ходят в сеть: ответы внешних систем только из фикстур.
- **Не входит в это изменение:** сбор салонов, зацепки, отчёт, карты, модель, оценка привлекательности.

## Capabilities

### New Capabilities

- `project-bootstrap`: каркас репозитория, качество, Compose, секреты, hello Streamlit без сбора салонов.

### Modified Capabilities

- нет (спеков ещё нет).

## Impact

- Затрагивает пустой (по коду) репозиторий: `pyproject.toml` / `uv`, hello-приложение Streamlit, Dockerfile, Compose, workflow GitHub Actions, `.env.example`, `.gitignore`, тесты каркаса.
- Новые зависимости только из согласованного стека: Python 3.12, Streamlit, SQLite, uv, ruff, mypy, pytest, Docker Compose.
- Сбора салонов нет: интерфейс — hello, без форм зацепок и без обращения к 2ГИС / Яндекс Картам / LLM.
- Файл SQLite не коммитится; ключи не попадают в git, логи и образ Docker.
