"""Классификация зацепки по строке, без модели и без сети."""

from __future__ import annotations

import re
from dataclasses import dataclass
from enum import StrEnum
from urllib.parse import urlparse

_SPACES = re.compile(r"\s+")


class HookKind(StrEnum):
    WEBSITE = "website"
    NAME = "name"
    OGRN = "ogrn"
    INN = "inn"
    MAPS_LINK = "maps_link"
    BOOKING_LINK = "booking_link"
    FREE_TEXT = "free_text"


@dataclass(frozen=True)
class ClassifiedHook:
    raw: str
    kind: HookKind
    normalized: str


def classify_hook(raw: str) -> ClassifiedHook:
    stripped = raw.strip()
    if re.fullmatch(r"[\d\s]+", stripped):
        digits = re.sub(r"\s+", "", stripped)
        if len(digits) in {13, 15}:
            return ClassifiedHook(raw, HookKind.OGRN, digits)
        if len(digits) in {10, 12}:
            return ClassifiedHook(raw, HookKind.INN, digits)

    parsed = urlparse(stripped)
    if parsed.scheme in {"http", "https"} and parsed.netloc:
        host = parsed.netloc.lower()
        path = parsed.path.lower()
        kind = _kind_from_url(host, path)
        normalized = f"{parsed.scheme}://{host}{parsed.path}".rstrip("/")
        return ClassifiedHook(raw, kind, normalized)

    collapsed = _SPACES.sub(" ", stripped).casefold()
    words = collapsed.split()
    if len(words) <= 6 and len(collapsed) <= 80:
        return ClassifiedHook(raw, HookKind.NAME, collapsed)
    return ClassifiedHook(raw, HookKind.FREE_TEXT, collapsed)


def _kind_from_url(host: str, path: str) -> HookKind:
    if "yclients." in host or "dikidi." in host:
        return HookKind.BOOKING_LINK
    if "2gis." in host:
        return HookKind.MAPS_LINK
    if "yandex." in host and "/maps" in path:
        return HookKind.MAPS_LINK
    return HookKind.WEBSITE
