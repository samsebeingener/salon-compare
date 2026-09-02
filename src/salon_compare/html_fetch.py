"""Один GET открытой страницы. Капчу не обходим. «Войти» в меню — не капча."""

from __future__ import annotations

import re
from urllib.parse import parse_qs, urlparse

import httpx

from salon_compare.collect import HtmlFetchResult
from salon_compare.proxy import HttpxClientKwargs, httpx_client_kwargs

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


def html_client_kwargs(url: str) -> HttpxClientKwargs:
    host = urlparse(url).netloc.lower()
    if host == "2gis.ru" or host.endswith(".2gis.ru"):
        return {"trust_env": False}
    if "duckduckgo.com" in host:
        return {"trust_env": False}
    if host == "companies.rbc.ru" or host.endswith(".companies.rbc.ru"):
        return {"trust_env": False}
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
        status = classify_fetch(response.status_code, response.text, str(response.url))
        body = response.text if status == "ok" else response.text[:2000]
        return HtmlFetchResult(status=status, body=body, url=str(response.url))
