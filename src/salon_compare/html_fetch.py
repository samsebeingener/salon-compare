"""Один GET открытой страницы. Капчу не обходим. «Войти» в меню — не капча."""

from __future__ import annotations

import re
from urllib.parse import parse_qs, urlparse

import httpx

from salon_compare.collect import HtmlFetchResult
from salon_compare.proxy import (
    HttpxClientKwargs,
    direct_httpx_kwargs,
    httpx_client_kwargs,
)

_BLOCKED_CODES = {401, 403, 429}
_BLOCKED_MARKERS = (
    "smartcaptcha",
    "recaptcha",
    "g-recaptcha",
    "cf-challenge",
    "cloudflare",
    "captcha",
)
_JSON_CAPTCHA_FLAG = re.compile(
    r'"(?:has_captcha|disable_captcha)"\s*:\s*(?:true|false)',
    re.IGNORECASE,
)
_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
)
_HEADERS = {
    "User-Agent": _USER_AGENT,
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "ru-RU,ru;q=0.9,en;q=0.8",
}
_MAX_HTML_BYTES = 2_000_000


def _response_too_large(response: httpx.Response) -> bool:
    headers = getattr(response, "headers", None)
    raw_length: str | None = None
    if headers is not None:
        raw_length = headers.get("Content-Length") or headers.get("content-length")
    if raw_length:
        try:
            if int(raw_length) > _MAX_HTML_BYTES:
                return True
        except ValueError:
            pass
    content = getattr(response, "content", None)
    if content is not None:
        return len(content) > _MAX_HTML_BYTES
    return False


def classify_fetch(status_code: int, text: str, final_url: str = "") -> str:
    path = urlparse(final_url).path.lower()
    if path == "/museum" or path.startswith("/museum/"):
        return "blocked"
    if status_code in _BLOCKED_CODES:
        return "blocked"
    if status_code == 202:
        return "empty"
    if status_code >= 400 or not text.strip():
        return "empty"
    lowered = _JSON_CAPTCHA_FLAG.sub("", text).lower()
    if any(marker in lowered for marker in _BLOCKED_MARKERS):
        return "blocked"
    return "ok"


def ddg_html_post(url: str) -> tuple[str, dict[str, str]] | None:
    parsed = urlparse(url)
    if "html.duckduckgo.com" not in parsed.netloc.lower():
        return None
    query = parse_qs(parsed.query).get("q", [""])[0]
    path = parsed.path or "/html/"
    return f"{parsed.scheme}://{parsed.netloc}{path}", {"q": query, "b": ""}


def _host_skips_env_proxy(host: str) -> bool:
    if "duckduckgo.com" in host:
        return True
    for base in ("2gis.ru", "2gis.com", "companies.rbc.ru", "checko.ru"):
        if host == base or host.endswith(f".{base}"):
            return True
    return False


def html_client_kwargs(url: str) -> HttpxClientKwargs:
    host = urlparse(url).netloc.lower()
    if _host_skips_env_proxy(host):
        return direct_httpx_kwargs()
    return httpx_client_kwargs()


class HttpxHtmlFetcher:
    def get(self, url: str) -> HtmlFetchResult:
        try:
            posted = ddg_html_post(url)
            kwargs = html_client_kwargs(url)
            if posted is not None:
                target, data = posted
                response = httpx.post(
                    target,
                    data=data,
                    follow_redirects=True,
                    timeout=15.0,
                    headers=_HEADERS,
                    **kwargs,
                )
            else:
                response = httpx.get(
                    url,
                    follow_redirects=True,
                    timeout=15.0,
                    headers=_HEADERS,
                    **kwargs,
                )
        except httpx.HTTPError:
            return HtmlFetchResult(status="empty", body="", url=url)
        final_url = str(response.url)
        if _response_too_large(response):
            return HtmlFetchResult(status="empty", body="", url=final_url)
        status = classify_fetch(response.status_code, response.text, final_url)
        body = response.text if status == "ok" else response.text[:2000]
        return HtmlFetchResult(status=status, body=body, url=final_url)
