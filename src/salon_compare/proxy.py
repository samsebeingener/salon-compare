"""Клиент LLM должен уважать HTTP_PROXY / HTTPS_PROXY из окружения."""

import os
from typing import TypedDict


class HttpxClientKwargs(TypedDict):
    trust_env: bool


def _truthy(name: str) -> bool:
    return os.environ.get(name, "").strip().lower() in {"1", "true", "yes", "on"}


def httpx_client_kwargs() -> HttpxClientKwargs:
    """httpx подхватит HTTP_PROXY и HTTPS_PROXY, если trust_env=True."""
    return {"trust_env": True}


def llm_httpx_client_kwargs() -> HttpxClientKwargs:
    """LLM_DIRECT=1 — без прокси (отладка или прямой доступ к API)."""
    if _truthy("LLM_DIRECT"):
        return {"trust_env": False}
    return httpx_client_kwargs()
