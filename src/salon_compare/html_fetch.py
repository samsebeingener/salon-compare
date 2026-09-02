"""Один GET открытой страницы. Капчу не обходим. «Войти» в меню — не капча."""

from __future__ import annotations

import httpx

from salon_compare.collect import HtmlFetchResult
from salon_compare.proxy import httpx_client_kwargs

_BLOCKED_CODES = {401, 403, 429}
_BLOCKED_MARKERS = (
    "smartcaptcha",
    "recaptcha",
    "g-recaptcha",
    "cf-challenge",
    "cloudflare",
    "captcha",
)
_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
)


def classify_fetch(status_code: int, text: str) -> str:
    if status_code in _BLOCKED_CODES:
        return "blocked"
    if status_code >= 400 or not text.strip():
        return "empty"
    lowered = text.lower()
    if any(marker in lowered for marker in _BLOCKED_MARKERS):
        return "blocked"
    return "ok"


class HttpxHtmlFetcher:
    def get(self, url: str) -> HtmlFetchResult:
        try:
            response = httpx.get(
                url,
                follow_redirects=True,
                timeout=15.0,
                headers={"User-Agent": _USER_AGENT},
                **httpx_client_kwargs(),
            )
        except httpx.HTTPError:
            return HtmlFetchResult(status="empty", body="", url=url)
        status = classify_fetch(response.status_code, response.text)
        body = response.text if status == "ok" else response.text[:2000]
        return HtmlFetchResult(status=status, body=body, url=str(response.url))
