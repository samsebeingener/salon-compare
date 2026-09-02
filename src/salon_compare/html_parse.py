"""Разбор открытого HTML карточки: часы, отзывы, плюс/минус, JSON-LD."""

from __future__ import annotations

import json
import re
from html import unescape

from salon_compare.collect import HtmlExtract

_JSON_LD = re.compile(
    r'<script[^>]*type=["\']application/ld\+json["\'][^>]*>(.*?)</script>',
    re.IGNORECASE | re.DOTALL,
)
_TIME = re.compile(r"<time[^>]*datetime=[\"']([^\"']+)[\"']", re.IGNORECASE)
_ISO = re.compile(r"(\d{4})-(\d{2})-(\d{2})")
_HOURS = re.compile(
    r"(?:график(?:\s+работы)?|часы(?:\s+работы)?)\s*:\s*([^<]{1,80})",
    re.IGNORECASE,
)
_PLUS = re.compile(r"положительн[а-яё]*[^\d]{0,20}(\d+)", re.IGNORECASE)
_MINUS = re.compile(r"отрицательн[а-яё]*[^\d]{0,20}(\d+)", re.IGNORECASE)
_ABOUT_HEADING = re.compile(
    r"<h[1-3]\b[^>]*>\s*(?:О\s+нас|О\s+студии)\s*</h[1-3]\s*>\s*"
    r"<p\b[^>]*>(.*?)</p>",
    re.IGNORECASE | re.DOTALL,
)
_META_NAME_THEN_CONTENT = re.compile(
    r"<meta\b[^>]*\bname=['\"]description['\"][^>]*\bcontent=['\"]([^'\"]*)['\"]",
    re.IGNORECASE,
)
_META_CONTENT_THEN_NAME = re.compile(
    r"<meta\b[^>]*\bcontent=['\"]([^'\"]*)['\"][^>]*\bname=['\"]description['\"]",
    re.IGNORECASE,
)
_TAGS = re.compile(r"<[^>]+>")


class _LdFields:
    def __init__(self) -> None:
        self.description: str | None = None
        self.rating: float | None = None
        self.review_count: int | None = None
        self.address: str | None = None


def _walk_dates(node: object, out: list[str]) -> None:
    if isinstance(node, list):
        for item in node:
            _walk_dates(item, out)
        return
    if not isinstance(node, dict):
        return
    for key in ("datePublished", "dateCreated"):
        raw = node.get(key)
        if isinstance(raw, str):
            found = _ISO.search(raw)
            if found:
                out.append(f"{found.group(1)}-{found.group(2)}-{found.group(3)}")
    for value in node.values():
        if isinstance(value, dict | list):
            _walk_dates(value, out)


def _as_float(raw: object) -> float | None:
    if isinstance(raw, bool):
        return None
    if isinstance(raw, int | float):
        return float(raw)
    if isinstance(raw, str):
        stripped = raw.strip().replace(",", ".")
        try:
            return float(stripped)
        except ValueError:
            return None
    return None


def _as_int(raw: object) -> int | None:
    if isinstance(raw, bool):
        return None
    if isinstance(raw, int):
        return raw
    if isinstance(raw, float) and raw.is_integer():
        return int(raw)
    if isinstance(raw, str):
        stripped = raw.strip()
        if stripped.isdigit():
            return int(stripped)
    return None


def _address_text(raw: object) -> str | None:
    if isinstance(raw, str) and raw.strip():
        return raw.strip()
    if not isinstance(raw, dict):
        return None
    street = raw.get("streetAddress")
    locality = raw.get("addressLocality")
    street_s = street.strip() if isinstance(street, str) else ""
    loc_s = locality.strip() if isinstance(locality, str) else ""
    if loc_s and street_s:
        return f"{loc_s}, {street_s}"
    if street_s:
        return street_s
    if loc_s:
        return loc_s
    return None


def _walk_ld(node: object, out: _LdFields) -> None:
    if isinstance(node, list):
        for item in node:
            _walk_ld(item, out)
        return
    if not isinstance(node, dict):
        return
    desc = node.get("description")
    if out.description is None and isinstance(desc, str) and desc.strip():
        out.description = desc.strip()
    agg = node.get("aggregateRating")
    if isinstance(agg, dict):
        if out.rating is None:
            out.rating = _as_float(agg.get("ratingValue"))
        if out.review_count is None:
            count = _as_int(agg.get("reviewCount"))
            if count is None:
                count = _as_int(agg.get("ratingCount"))
            out.review_count = count
    if out.address is None:
        parsed = _address_text(node.get("address"))
        if parsed:
            out.address = parsed
    for value in node.values():
        if isinstance(value, dict | list):
            _walk_ld(value, out)


def _dates_from_ld(blob: str) -> list[str]:
    try:
        data = json.loads(blob)
    except json.JSONDecodeError:
        return []
    found: list[str] = []
    _walk_dates(data, found)
    return found


def _fields_from_ld(blob: str) -> _LdFields:
    out = _LdFields()
    try:
        data = json.loads(blob)
    except json.JSONDecodeError:
        return out
    _walk_ld(data, out)
    return out


def _clip(text: str, limit: int = 280) -> str:
    stripped = " ".join(text.split())
    if len(stripped) <= limit:
        return stripped
    return stripped[:limit]


def _meta_description(html: str) -> str | None:
    match = _META_NAME_THEN_CONTENT.search(html) or _META_CONTENT_THEN_NAME.search(html)
    if match is None:
        return None
    text = match.group(1).strip()
    return _clip(text) if text else None


def _about_from_heading(html: str) -> str | None:
    match = _ABOUT_HEADING.search(html)
    if match is None:
        return None
    text = _TAGS.sub("", match.group(1)).strip()
    if not text:
        return None
    return _clip(text)


def parse_open_html(html: str) -> HtmlExtract:
    text = unescape(html)
    dates: list[str] = []
    ld = _LdFields()
    for match in _JSON_LD.finditer(text):
        blob = match.group(1)
        dates.extend(_dates_from_ld(blob))
        extra = _fields_from_ld(blob)
        if ld.description is None:
            ld.description = extra.description
        if ld.rating is None:
            ld.rating = extra.rating
        if ld.review_count is None:
            ld.review_count = extra.review_count
        if ld.address is None:
            ld.address = extra.address
    for match in _TIME.finditer(text):
        found = _ISO.search(match.group(1))
        if found:
            dates.append(f"{found.group(1)}-{found.group(2)}-{found.group(3)}")
    last = max(dates) if dates else None
    hours_match = _HOURS.search(text)
    hours = hours_match.group(1).strip() if hours_match else None
    if hours == "":
        hours = None
    plus = _PLUS.search(text)
    minus = _MINUS.search(text)
    plus_minus: str | None = None
    if plus and minus:
        plus_minus = f"{plus.group(1)} плюс / {minus.group(1)} минус"
    elif plus:
        plus_minus = f"{plus.group(1)} плюс"
    elif minus:
        plus_minus = f"{minus.group(1)} минус"
    about = ld.description
    if about is None:
        about = _meta_description(text)
    if about is None:
        about = _about_from_heading(text)
    return HtmlExtract(
        rating=ld.rating,
        review_count=ld.review_count,
        address=ld.address,
        about=about,
        last_review=last,
        hours=hours,
        plus_minus=plus_minus,
    )


class OpenHtmlParser:
    def parse(self, html: str) -> HtmlExtract:
        return parse_open_html(html)
