"""Клиент LLM должен уважать HTTP_PROXY / HTTPS_PROXY из окружения."""

from __future__ import annotations

import os
from typing import TypedDict
from urllib.parse import urlsplit


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


def proxy_urls_from_env() -> tuple[str, ...]:
    """Уникальные URL как в .env: схему https:// у прокси не переписываем."""
    found: list[str] = []
    for name in ("HTTP_PROXY", "HTTPS_PROXY", "http_proxy", "https_proxy"):
        raw = os.environ.get(name, "").strip()
        if raw and raw not in found:
            found.append(raw)
    return tuple(found)


def proxy_url_from_env() -> str | None:
    urls = proxy_urls_from_env()
    return urls[0] if urls else None


def proxy_channel_name(url: str) -> str:
    scheme = urlsplit(url).scheme.lower()
    if scheme == "https":
        return "proxy-https"
    if scheme == "http":
        return "proxy-http"
    return "proxy"


def proxy_public_label(raw: str) -> str:
    parts = urlsplit(raw)
    host = parts.hostname or ""
    if parts.port:
        host = f"{host}:{parts.port}"
    scheme = parts.scheme or "http"
    return f"{scheme}://{host}" if host else scheme


def proxy_public_labels() -> str:
    return ",".join(proxy_public_label(url) for url in proxy_urls_from_env())


def llm_transport_attempts() -> tuple[tuple[str, LlmHttpxKwargs], ...]:
    """Каждый уникальный прокси, затем напрямую. Схему URL не меняем."""
    direct: tuple[str, LlmHttpxKwargs] = ("direct", {"trust_env": False})
    via_proxy: list[tuple[str, LlmHttpxKwargs]] = []
    for url in proxy_urls_from_env():
        kwargs: LlmHttpxKwargs = {"trust_env": False, "proxy": url}
        via_proxy.append((proxy_channel_name(url), kwargs))
    if not via_proxy:
        return (direct,)
    if _truthy("LLM_DIRECT"):
        return (direct, *via_proxy)
    return (*via_proxy, direct)


def llm_httpx_client_kwargs() -> LlmHttpxKwargs:
    """Первый канал из llm_transport_attempts (совместимость тестов)."""
    return llm_transport_attempts()[0][1]
