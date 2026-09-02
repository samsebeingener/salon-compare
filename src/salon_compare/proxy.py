"""Клиент LLM должен уважать HTTP_PROXY / HTTPS_PROXY из окружения."""

from typing import TypedDict


class HttpxClientKwargs(TypedDict):
    trust_env: bool


def httpx_client_kwargs() -> HttpxClientKwargs:
    """httpx подхватит HTTP_PROXY и HTTPS_PROXY, если trust_env=True."""
    return {"trust_env": True}
