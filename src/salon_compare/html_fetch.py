"""Один GET открытой страницы. Капчу и логин не обходим."""

from __future__ import annotations

import httpx

from salon_compare.collect import HtmlFetchResult
from salon_compare.proxy import httpx_client_kwargs

_BLOCKED_MARKERS = ("captcha", "войдите", "войти", "cloudflare")


class HttpxHtmlFetcher:
    def get(self, url: str) -> HtmlFetchResult:
        try:
            response = httpx.get(
                url,
                follow_redirects=True,
                timeout=15.0,
                **httpx_client_kwargs(),
            )
        except httpx.HTTPError:
            return HtmlFetchResult(status="empty", body="", url=url)
        text = response.text
        lowered = text.lower()
        blocked_code = response.status_code in {401, 403, 429}
        blocked_body = any(marker in lowered for marker in _BLOCKED_MARKERS)
        if blocked_code or blocked_body:
            return HtmlFetchResult(status="blocked", body=text[:2000], url=url)
        if response.status_code >= 400 or not text.strip():
            return HtmlFetchResult(status="empty", body="", url=url)
        return HtmlFetchResult(status="ok", body=text, url=str(response.url))
