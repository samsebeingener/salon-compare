"""Логи вызовов LLM в data/llm-interactions.log (ключи не пишем)."""

from __future__ import annotations

import json
import os
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from salon_compare.load_env import project_root

_LOG_PATH = project_root() / "data" / "llm-interactions.log"
_PREVIEW_CHARS = 4000


def llm_logging_enabled() -> bool:
    raw = os.environ.get("LLM_LOG", "1").strip().lower()
    return raw not in {"0", "false", "no", "off"}


def _mask_key(key: str) -> str:
    text = key.strip()
    if len(text) <= 8:
        return "***"
    return f"{text[:4]}…{text[-4:]}"


def _preview(text: str, limit: int = _PREVIEW_CHARS) -> str:
    if len(text) <= limit:
        return text
    return text[: limit - 3] + "..."


def log_llm_event(event: str, **fields: Any) -> None:
    if not llm_logging_enabled():
        return
    payload: dict[str, Any] = {
        "ts": datetime.now(UTC).isoformat(),
        "event": event,
    }
    for key, value in fields.items():
        if key == "api_key" and isinstance(value, str):
            payload["api_key_masked"] = _mask_key(value)
            continue
        if key in {"system", "user_prompt", "response_text"} and isinstance(value, str):
            payload[key] = _preview(value)
            payload[f"{key}_len"] = len(value)
            continue
        payload[key] = value
    _LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    line = json.dumps(payload, ensure_ascii=False)
    with _LOG_PATH.open("a", encoding="utf-8") as handle:
        handle.write(line + "\n")


def log_path() -> Path:
    return _LOG_PATH
