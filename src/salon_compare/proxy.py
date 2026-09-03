"""Клиент LLM должен уважать HTTP_PROXY / HTTPS_PROXY из окружения."""

from __future__ import annotations

import os
from typing import TypedDict
from urllib.parse import urlsplit, urlunsplit


class HttpxClientKwargs(TypedDict):
    trust_env: bool


class LlmHttpxKwargs(TypedDict, total=False):
    trust_env: bool
    proxy: str


def _truthy(name: str) -> bool:
    return os.environ.get(name, "").strip().lower() in {"1", "true", "yes", "on"}


def httpx_client_kwargs() -> HttpxClientKwargs:
    """httpx подхватит HTTP_PROXY и HTTPS_PROXY, если trust_env=True."""
    return {"trust_env": True}


def proxy_url_from_env() -> str | None:
    for name in ("HTTPS_PROXY", "HTTP_PROXY", "https_proxy", "http_proxy"):
        raw = os.environ.get(name, "").strip()
        if raw:
            return normalize_proxy_url(raw)
    return None


def normalize_proxy_url(raw: str) -> str:
    """HTTP-прокси в .env часто пишут как https:// — httpx тогда бьёт TLS на прокси."""
    text = raw.strip()
    parts = urlsplit(text)
    if parts.scheme.lower() == "https" and parts.hostname:
        return urlunsplit(
            ("http", parts.netloc, parts.path, parts.query, parts.fragment)
        )
    return text


def proxy_public_label(raw: str) -> str:
    parts = urlsplit(raw)
    host = parts.hostname or ""
    if parts.port:
        host = f"{host}:{parts.port}"
    scheme = parts.scheme or "http"
    return f"{scheme}://{host}" if host else scheme


def llm_transport_attempts() -> tuple[tuple[str, LlmHttpxKwargs], ...]:
    """Сначала явный proxy=, при сбое — напрямую. Не надеемся на trust_env."""
    direct: tuple[str, LlmHttpxKwargs] = ("direct", {"trust_env": False})
    proxy_url = proxy_url_from_env()
    if proxy_url:
        via_proxy: tuple[str, LlmHttpxKwargs] = (
            "proxy",
            {"trust_env": False, "proxy": proxy_url},
        )
        if _truthy("LLM_DIRECT"):
            return (direct, via_proxy)
        return (via_proxy, direct)
    return (direct,)


def llm_httpx_client_kwargs() -> LlmHttpxKwargs:
    """Первый канал из llm_transport_attempts (совместимость тестов)."""
    return llm_transport_attempts()[0][1]
