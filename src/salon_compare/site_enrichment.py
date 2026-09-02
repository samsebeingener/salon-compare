"""Каскад: DDG-сайт, внутренние legal-страницы, сайт с РБК."""

from __future__ import annotations

import re
from html import unescape
from urllib.parse import quote_plus, urljoin, urlparse

_DDG_RESULT = re.compile(
    r"""<a[^>]*class=["']result__a["'][^>]*href=["'](https?://[^"'#]+)["']""",
    re.IGNORECASE,
)
_INTERNAL_HREF = re.compile(r"""href=["']([^"'#]+)["']""", re.IGNORECASE)
_PATH_KEYWORDS = (
    "contact",
    "kontakt",
    "контакт",
    "реквизит",
    "politic",
    "privacy",
    "confiden",
    "конфиден",
    "персональн",
    "personal",
    "about",
    "о-нас",
    "o-nas",
    "legal",
)
_SKIP_DDG_HOSTS = (
    "2gis.",
    "yandex.",
    "google.",
    "instagram.",
    "facebook.",
    "vk.com",
    "ok.ru",
    "t.me",
    "zoon.",
    "widget.",
    "duckduckgo.",
)
_RBC_WEBSITE = re.compile(
    r"Сайт</div>.*?href=[\"'](https?://[^\"']+)[\"']",
    re.IGNORECASE | re.DOTALL,
)

MAX_SITE_PAGES = 10
_MAX_INTERNAL_PER_PAGE = 6


def ddg_site_search_url(title: str, address: str | None = None) -> str:
    parts = [title.strip()]
    if address and address.strip():
        parts.append(address.strip())
    query = " ".join(parts)
    return f"https://html.duckduckgo.com/html/?q={quote_plus(query)}"


def _host_ok(url: str) -> bool:
    host = urlparse(url).netloc.lower().removeprefix("www.")
    if not host:
        return False
    return not any(bit in host for bit in _SKIP_DDG_HOSTS)


def ddg_site_urls(html: str, limit: int = 3) -> list[str]:
    seen: set[str] = set()
    urls: list[str] = []
    for match in _DDG_RESULT.finditer(html):
        raw = unescape(match.group(1)).strip().rstrip("/")
        if not _host_ok(raw):
            continue
        key = raw.rstrip("/").lower()
        if key in seen:
            continue
        seen.add(key)
        urls.append(raw if raw.startswith("http") else f"https://{raw}")
        if len(urls) >= limit:
            break
    return urls


def internal_legal_links(
    html: str,
    base_url: str,
    limit: int = _MAX_INTERNAL_PER_PAGE,
) -> list[str]:
    base = urlparse(base_url)
    base_host = base.netloc.lower().removeprefix("www.")
    seen: set[str] = set()
    out: list[str] = []
    for match in _INTERNAL_HREF.finditer(html):
        href = unescape(match.group(1)).strip()
        if not href or href.startswith(("mailto:", "tel:", "javascript:")):
            continue
        full = urljoin(base_url, href)
        parsed = urlparse(full)
        host = parsed.netloc.lower().removeprefix("www.")
        if host != base_host:
            continue
        path = parsed.path.lower()
        if not any(key in path for key in _PATH_KEYWORDS):
            continue
        key = full.split("#", 1)[0].rstrip("/")
        if key in seen:
            continue
        seen.add(key)
        out.append(full)
        if len(out) >= limit:
            break
    return out


def rbc_company_card_url(search_html: str, ogrn: str) -> str | None:
    pattern = re.compile(
        rf'href="(https://companies\.rbc\.ru/id/{re.escape(ogrn)}-[^"]+)"',
        re.IGNORECASE,
    )
    match = pattern.search(search_html)
    if match is None:
        return None
    return match.group(1)


def rbc_website(html: str) -> str | None:
    match = _RBC_WEBSITE.search(html)
    if match is None:
        return None
    url = match.group(1).strip().rstrip("/")
    return url if url.startswith("http") else None
