"""Загрузка `.env` без сторонних пакетов. Уже заданные переменные не трогаем."""

from __future__ import annotations

import os
from collections.abc import MutableMapping
from pathlib import Path


def project_root() -> Path:
    return Path(__file__).resolve().parents[2]


def load_dotenv_file(
    path: Path,
    environ: MutableMapping[str, str] | None = None,
) -> None:
    env: MutableMapping[str, str] = os.environ if environ is None else environ
    if not path.is_file():
        return
    for raw in path.read_text(encoding="utf-8-sig").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        key = key.strip()
        if key.lower().startswith("export "):
            key = key[7:].strip()
        value = value.strip().strip("'").strip('"')
        if not key or not value:
            continue
        if env.get(key, "").strip():
            continue
        env[key] = value


def load_project_env() -> None:
    load_dotenv_file(project_root() / ".env")
