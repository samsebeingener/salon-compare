#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")" && pwd)"
cd "$ROOT"

if command -v python3 >/dev/null 2>&1; then
  exec python3 scripts/start_local.py "$@"
fi
if command -v python >/dev/null 2>&1; then
  exec python scripts/start_local.py "$@"
fi

echo "Нужен Python 3 в PATH (команда python3 или python)." >&2
exit 1
