# Proposal: os-start-launchers

## Why

`START.bat` работает только на Windows. На Linux и macOS двойной щелчок / одна команда из README не описаны. iPhone/iPad приложение не запускает (нет Docker/Streamlit как на десктопе) — это надо явно сказать, а не обещать «iOS».

## What Changes

- Windows: `START.bat` как сейчас.
- Linux и macOS: `start.sh` → тот же `scripts/start_local.py`.
- macOS Finder: `START.command` вызывает `start.sh`.
- README: таблица ОС; iOS не поддерживается.

## Capabilities

### Modified Capabilities

- `project-bootstrap`: лаунчеры по ОС.


## Impact

- Корневые `start.sh`, `START.command`, README, тесты текста лаунчеров.
