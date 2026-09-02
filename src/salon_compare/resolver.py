"""Поиск точек на картах: все карточки наружу, без выбора «первой»."""

from __future__ import annotations

from typing import Protocol

from salon_compare.hooks import ClassifiedHook, HookKind, search_query
from salon_compare.intake import VenueCandidate
from salon_compare.legal import egrul_url
from salon_compare.maps_parse import candidate_from_maps_url


class PlaceCatalog(Protocol):
    def search(self, query: str) -> list[VenueCandidate]: ...


class MapsSearchResolver:
    def __init__(self, twogis: PlaceCatalog, yandex: PlaceCatalog) -> None:
        self._twogis = twogis
        self._yandex = yandex

    def resolve(self, hook: ClassifiedHook) -> list[VenueCandidate]:
        if hook.kind is HookKind.MAPS_LINK:
            found = candidate_from_maps_url(hook)
            return [found] if found is not None else []
        query = search_query(hook)
        merged = _unique([*self._twogis.search(query), *self._yandex.search(query)])
        if merged:
            return merged
        fallback = _fallback_without_maps(hook)
        return [fallback] if fallback is not None else []


def _fallback_without_maps(hook: ClassifiedHook) -> VenueCandidate | None:
    title = hook.raw.strip()
    if hook.kind is HookKind.WEBSITE:
        return VenueCandidate(
            f"website:{hook.normalized}",
            title,
            hook.normalized,
            "website",
        )
    if hook.kind is HookKind.BOOKING_LINK:
        return VenueCandidate(
            f"booking:{hook.normalized}",
            title,
            hook.normalized,
            "booking",
        )
    if hook.kind is HookKind.OGRN:
        return VenueCandidate(
            f"ogrn:{hook.normalized}",
            title,
            egrul_url(hook.normalized),
            "ogrn",
        )
    if hook.kind is HookKind.INN:
        return VenueCandidate(
            f"inn:{hook.normalized}",
            title,
            egrul_url(hook.normalized),
            "inn",
        )
    if hook.kind is HookKind.NAME:
        return VenueCandidate(f"name:{hook.normalized}", title, "", "name")
    if hook.kind is HookKind.FREE_TEXT:
        return VenueCandidate(f"text:{hook.normalized}", title, "", "free_text")
    return None


def _unique(candidates: list[VenueCandidate]) -> list[VenueCandidate]:
    seen: set[str] = set()
    result: list[VenueCandidate] = []
    for item in candidates:
        if item.venue_id in seen:
            continue
        seen.add(item.venue_id)
        result.append(item)
    return result
