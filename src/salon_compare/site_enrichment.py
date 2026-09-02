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
    "payment",
    "pay",
    "oplata",
    "оплат",
    "oferta",
    "oferty",
    "dogovor",
    "offer",
    "agreement",
    "soglashen",
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
_SALON_WORDS = frozenset(
    {
        "салон",
        "студия",
        "маникюр",
        "маникюрный",
        "ногтевая",
        "ногтевой",
        "красоты",
        "beauty",
        "nails",
        "nail",
    }
)
_COMPOUND_BRAND_WORDS = frozenset(
    {
        "маникюра",
        "маникюр",
        "nails",
        "nail",
        "beauty",
        "красоты",
    }
)
_WORD_SLUG_OVERRIDES = {
    "маникюра": "manicura",
    "маникюр": "manicur",
    "педикюра": "pedicura",
    "педикюр": "pedicur",
}
_TRANSLIT = {
    "а": "a",
    "б": "b",
    "в": "v",
    "г": "g",
    "д": "d",
    "е": "e",
    "ё": "e",
    "ж": "zh",
    "з": "z",
    "и": "i",
    "й": "y",
    "к": "k",
    "л": "l",
    "м": "m",
    "н": "n",
    "о": "o",
    "п": "p",
    "р": "r",
    "с": "s",
    "т": "t",
    "у": "u",
    "ф": "f",
    "х": "h",
    "ц": "ts",
    "ч": "ch",
    "ш": "sh",
    "щ": "sch",
    "ъ": "",
    "ы": "y",
    "ь": "",
    "э": "e",
    "ю": "yu",
    "я": "ya",
}


def ddg_site_search_queries(title: str, address: str | None = None) -> list[str]:
    base = title.strip()
    queries = [base]
    if "маникюр" not in base.casefold():
        queries.append(f"{base} маникюр")
    if address:
        street = address.split(",")[0].strip()
        if street and street.casefold() not in base.casefold():
            queries.append(f"{base} {street}")
    seen: set[str] = set()
    out: list[str] = []
    for query in queries:
        key = query.casefold()
        if key in seen:
            continue
        seen.add(key)
        out.append(query)
    return out


def ddg_site_search_url(title: str, address: str | None = None) -> str:
    query = ddg_site_search_queries(title, address)[0]
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


def _translit_word(word: str) -> str:
    lowered = word.casefold().strip(".")
    override = _WORD_SLUG_OVERRIDES.get(lowered)
    if override is not None:
        return override
    out: list[str] = []
    for char in lowered:
        if char in _TRANSLIT:
            out.append(_TRANSLIT[char])
        elif char.isalnum():
            out.append(char)
    return "".join(out)


_LOCATION_SUFFIXES = ("ская", "ский", "ная", "ный", "ской", "ское")


def _looks_like_location(word: str) -> bool:
    lowered = word.casefold()
    return any(lowered.endswith(suffix) for suffix in _LOCATION_SUFFIXES)


def _brand_token_words(title: str) -> list[str]:
    head = title.split(",", 1)[0].strip()
    words = [item for item in re.split(r"[\s\-–—]+", head) if item]
    picked: list[str] = []
    for index, word in enumerate(words):
        lowered = word.casefold().strip(".")
        if len(lowered) < 4:
            continue
        if lowered in _SALON_WORDS:
            if (
                len(picked) == 1
                and index > 0
                and words[index - 1].casefold().strip(".") == picked[0]
                and lowered in _COMPOUND_BRAND_WORDS
            ):
                picked.append(lowered)
            continue
        if picked and _looks_like_location(lowered):
            break
        picked.append(lowered)
        if len(picked) >= 2:
            break
    return picked


def brand_slug(title: str) -> str | None:
    picked = _brand_token_words(title)
    if not picked:
        return None
    slug = "".join(_translit_word(word) for word in picked[:1])
    return slug if len(slug) >= 3 else None


def domain_probe_urls(title: str) -> list[str]:
    words = _brand_token_words(title)
    tokens = [_translit_word(word) for word in words]
    hosts: list[str] = []
    if len(tokens) >= 2:
        hosts.append(f"{tokens[0]}{tokens[1]}.ru")
        hosts.append(f"{''.join(tokens[:2])}.ru")
    slug = brand_slug(title)
    if slug is not None:
        hosts.extend(
            [
                f"{slug}salon.ru",
                f"{slug}-salon.ru",
                f"salon-{slug}.ru",
                f"{slug}.ru",
            ]
        )
    seen: set[str] = set()
    urls: list[str] = []
    for host in hosts:
        if host in seen:
            continue
        seen.add(host)
        urls.append(f"https://{host}")
    return urls


def page_matches_address(html: str, address: str | None) -> bool:
    if not address or not address.strip():
        return True
    street = address.split(",")[0].strip()
    token = street.split()[0] if street else street
    if len(token) < 4:
        return True
    return token.casefold() in html.casefold()
