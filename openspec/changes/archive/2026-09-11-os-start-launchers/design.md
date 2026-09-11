# Design: os-start-launchers

## Context

Логика старта уже в `scripts/start_local.py` (кроссплатформенный Python). Не хватает оболочек Unix. `.bat` на Linux/macOS не исполняется.

## Decisions

- Не делать «универсальный .bat»: на Unix он бесполезен.
- `start.sh`: `python3` затем `python`, `cd` в корень репо, `exec` в `start_local.py`.
- `START.command`: обёртка для Finder на macOS.
- iOS: только отказ в README, без фейкового лаунчера.
- Сообщения `start_local.py` про docker без `docker.exe`, чтобы Linux не пугал.

## Risks

- [Нет +x у start.sh после clone на Windows-копии] → README: `chmod +x start.sh` / `bash start.sh`.
