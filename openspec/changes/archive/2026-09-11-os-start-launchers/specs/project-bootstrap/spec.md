## ADDED Requirements

### Requirement: Лаунчер старта по операционной системе
Репозиторий SHALL содержать `START.bat` для Windows и `start.sh` для Linux и macOS. Оба MUST вызывать `scripts/start_local.py` и MUST NOT дублировать логику `.env`/Docker. Для macOS MAY быть `START.command`, который запускает `start.sh`. Документация MUST назвать Windows, Linux и macOS. Документация MUST NOT обещать запуск на iOS (iPhone/iPad).

#### Scenario: Windows-лаунчер зовёт Python-скрипт
- GIVEN файл `START.bat` в корне
- WHEN его читают
- THEN в нём есть путь `scripts\start_local.py` или `scripts/start_local.py`

#### Scenario: Unix-лаунчер зовёт тот же скрипт
- GIVEN файл `start.sh` в корне
- WHEN его читают
- THEN есть `scripts/start_local.py`
- THEN есть вызов `python3` или `python`
