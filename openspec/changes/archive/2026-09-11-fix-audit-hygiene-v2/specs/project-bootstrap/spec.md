## MODIFIED Requirements

### Requirement: Одна команда качества ruff, mypy и pytest
Система SHALL предоставлять одну локальную команду, которая последовательно запускает ruff, mypy и pytest. GitHub Actions MUST вызывать ту же команду, без отдельного набора проверок. Прогон pytest MUST включать отчёт покрытия (`pytest-cov`) по пакету приложения. Команда и конфиг MUST NOT задавать `--cov-fail-under` и MUST NOT падать только из‑за процента покрытия.

#### Scenario: Локальный прогон качества
- GIVEN зависимости проекта установлены
- WHEN запускают единственную команду качества
- THEN выполняются ruff, mypy и pytest
- THEN pytest печатает отчёт покрытия
- THEN при успешных проверках команда завершается с кодом 0 даже если покрытие не 100%

#### Scenario: CI совпадает с локальной командой
- GIVEN открыт pull request или push в ветку с workflow
- WHEN GitHub Actions выполняет job качества
- THEN вызывается та же команда качества, что и локально
- THEN тесты в этом прогоне не обращаются к сети
- THEN в аргументах pytest нет `--cov-fail-under`

## ADDED Requirements

### Requirement: Compose публикует Streamlit только на loopback
Docker Compose SHALL публиковать порт Streamlit как `127.0.0.1:8501:8501`. Система MUST NOT публиковать `8501:8501` на все интерфейсы хоста. Локальный HTTP-клиент к `http://127.0.0.1:8501` MUST по-прежнему достучаться до health и UI.

#### Scenario: Bind только localhost
- GIVEN файл Compose в корне репозитория
- WHEN читают публикацию портов сервиса приложения
- THEN есть `127.0.0.1:8501:8501`
- THEN нет голого `8501:8501` без адреса хоста

#### Scenario: Health с loopback
- GIVEN `docker compose up` завершил старт приложения
- WHEN клиент на той же машине запрашивает `http://127.0.0.1:8501/_stcore/health`
- THEN соединение устанавливается

### Requirement: Поля thinking модели только для хостов Kie
Клиент чата SHALL включать `include_thoughts` и `reasoning_effort` в JSON-тело запроса только если хост `LLM_BASE_URL` — `api.kie.ai` или заканчивается на `.kie.ai`. Для прочих хостов (в том числе OpenRouter и OpenAI-совместимых) эти ключи MUST отсутствовать. Значения на Kie: `include_thoughts` ложь, `reasoning_effort` `low`. `stream` MUST быть ложь на любом хосте.

#### Scenario: Kie получает thinking-поля
- GIVEN `LLM_BASE_URL` с хостом `api.kie.ai`
- WHEN собирают тело chat completions
- THEN в теле есть `include_thoughts` = ложь
- THEN в теле есть `reasoning_effort` = `low`
- THEN `stream` ложь

#### Scenario: OpenRouter без thinking-полей
- GIVEN `LLM_BASE_URL` с хостом не из `*.kie.ai`
- WHEN собирают тело chat completions
- THEN ключей `include_thoughts` и `reasoning_effort` нет
- THEN `stream` ложь
