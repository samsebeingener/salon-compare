"""Разбор открытого HTML карточки: часы, отзывы, плюс/минус."""

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


def _dates_from_ld(blob: str) -> list[str]:
    try:
        data = json.loads(blob)
    except json.JSONDecodeError:
        return []
    found: list[str] = []
    _walk_dates(data, found)
    return found


def parse_open_html(html: str) -> HtmlExtract:
    text = unescape(html)
    dates: list[str] = []
    for match in _JSON_LD.finditer(text):
        dates.extend(_dates_from_ld(match.group(1)))
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
    return HtmlExtract(last_review=last, hours=hours, plus_minus=plus_minus)


class OpenHtmlParser:
    def parse(self, html: str) -> HtmlExtract:
        return parse_open_html(html)
