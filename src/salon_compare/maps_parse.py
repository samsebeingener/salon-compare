"""Разбор JSON карточек 2ГИС без сети."""

from __future__ import annotations

import re
from urllib.parse import urlparse

from salon_compare.collect import MapCard
from salon_compare.hooks import ClassifiedHook
from salon_compare.intake import VenueCandidate

_FIRM = re.compile(r"/firm/([^/?#]+)", re.IGNORECASE)
_ORG_SLUG = re.compile(r"/org/([^/?#]+)/([^/?#]+)", re.IGNORECASE)
_ORG = re.compile(r"/org/([^/?#]+)", re.IGNORECASE)


def item_by_id(items: list[dict[str, object]], ident: str) -> dict[str, object] | None:
    for item in items:
        if str(item.get("id")) == ident:
            return item
    return None


def candidates_from_twogis_items(
    items: list[dict[str, object]],
) -> list[VenueCandidate]:
    found: list[VenueCandidate] = []
    for item in items:
        ident_raw = item.get("id")
        if ident_raw is None:
            continue
        ident = str(ident_raw)
        raw_name = item.get("name") or item.get("address_name") or ident
        name = raw_name if isinstance(raw_name, str) else ident
        found.append(
            VenueCandidate(
                f"twogis:{ident}",
                name,
                f"https://2gis.ru/firm/{ident}",
                "twogis",
                _search_address(item),
            )
        )
    return found


def candidate_from_maps_url(hook: ClassifiedHook) -> VenueCandidate | None:
    url = hook.normalized
    host = urlparse(url).netloc.lower()
    firm = _FIRM.search(url)
    if "2gis." in host and firm:
        ident = firm.group(1)
        return VenueCandidate(f"twogis:{ident}", ident, url, "twogis")
    org_slug = _ORG_SLUG.search(url)
    if "yandex." in host and org_slug:
        slug, ident = org_slug.group(1), org_slug.group(2)
        if not slug.isdigit():
            return VenueCandidate(f"yandex:{ident}", slug, url, "yandex")
    org = _ORG.search(url)
    if "yandex." in host and org:
        ident = org.group(1)
        return VenueCandidate(f"yandex:{ident}", ident, url, "yandex")
    return VenueCandidate(f"maps:{url}", url, url, "maps")


def _nonempty(raw: object) -> str | None:
    if isinstance(raw, str) and raw.strip():
        return raw.strip()
    return None


def _append_unique(parts: list[str], extra: str | None, *, split: bool) -> None:
    if not extra:
        return
    chunks = [bit.strip() for bit in extra.split(",")] if split else [extra]
    joined = ", ".join(parts).casefold()
    for chunk in chunks:
        if not chunk or chunk.casefold() in joined:
            continue
        parts.append(chunk)
        joined = ", ".join(parts).casefold()


def _search_address(item: dict[str, object]) -> str | None:
    street: str | None = None
    for key in ("full_address_name", "address_name"):
        street = _nonempty(item.get(key))
        if street:
            break
    building = None
    nested = item.get("address")
    if isinstance(nested, dict):
        building = _nonempty(nested.get("building_name"))
    comment = _nonempty(item.get("address_comment"))
    parts: list[str] = []
    _append_unique(parts, street, split=False)
    _append_unique(parts, building, split=True)
    _append_unique(parts, comment, split=True)
    if not parts:
        return None
    return ", ".join(parts)


def _registry_id(raw: object, lengths: tuple[int, ...]) -> str | None:
    text = str(raw) if isinstance(raw, int) else raw
    if isinstance(text, str) and text.isdigit() and len(text) in lengths:
        return text
    return None


def _org_ids(payload: dict[str, object]) -> tuple[str | None, str | None]:
    ogrn = _registry_id(payload.get("ogrn"), (13, 15))
    inn = _registry_id(payload.get("inn"), (10, 12))
    nested = payload.get("org")
    if isinstance(nested, dict):
        ogrn = ogrn or _registry_id(nested.get("ogrn"), (13, 15))
        inn = inn or _registry_id(nested.get("inn"), (10, 12))
    return ogrn, inn


def neighbors_from_twogis_items(
    items: list[dict[str, object]],
    self_id: str,
) -> tuple[int | None, float | None]:
    ratings: list[float] = []
    for item in items:
        if str(item.get("id")) == self_id:
            continue
        reviews = item.get("reviews")
        if not isinstance(reviews, dict):
            continue
        raw = reviews.get("general_rating")
        if isinstance(raw, int | float):
            ratings.append(float(raw))
    if not ratings:
        return None, None
    return len(ratings), sum(ratings) / len(ratings)


def _geo_point(payload: dict[str, object]) -> tuple[float | None, float | None]:
    raw = payload.get("point")
    if isinstance(raw, dict):
        lon_raw = raw.get("lon") or raw.get("lng")
        lat_raw = raw.get("lat")
        if isinstance(lon_raw, int | float) and isinstance(lat_raw, int | float):
            return float(lon_raw), float(lat_raw)
    return None, None


def _contact_website(item: dict[str, object]) -> str | None:
    groups = item.get("contact_groups")
    if not isinstance(groups, list):
        return None
    for group in groups:
        if not isinstance(group, dict):
            continue
        contacts = group.get("contacts")
        if not isinstance(contacts, list):
            continue
        for contact in contacts:
            if not isinstance(contact, dict):
                continue
            if str(contact.get("type", "")).lower() != "website":
                continue
            found = _http_url(contact.get("url")) or _http_url(contact.get("value"))
            if found is not None:
                return found
    return None


def _http_url(raw: object) -> str | None:
    if not isinstance(raw, str):
        return None
    text = raw.strip().rstrip("/")
    if text.startswith("http://") or text.startswith("https://"):
        return text
    return None


_DAY_ORDER = (
    ("Mon", "пн"),
    ("Tue", "вт"),
    ("Wed", "ср"),
    ("Thu", "чт"),
    ("Fri", "пт"),
    ("Sat", "сб"),
    ("Sun", "вс"),
)


def _day_slot(day: object) -> str | None:
    if not isinstance(day, dict):
        return None
    hours = day.get("working_hours")
    if not isinstance(hours, list) or not hours:
        return None
    first = hours[0]
    if not isinstance(first, dict):
        return None
    start, end = first.get("from"), first.get("to")
    if isinstance(start, str) and isinstance(end, str) and start and end:
        return f"{start}-{end}"
    return None


def hours_from_schedule(schedule: object) -> str | None:
    if not isinstance(schedule, dict):
        return None
    rows: list[tuple[str, str]] = []
    for key, short in _DAY_ORDER:
        slot = _day_slot(schedule.get(key))
        if slot:
            rows.append((short, slot))
    if not rows:
        return None
    groups: list[tuple[str, str, str]] = []
    for short, slot in rows:
        if groups and groups[-1][2] == slot:
            start, _, same = groups[-1]
            groups[-1] = (start, short, same)
        else:
            groups.append((short, short, slot))
    parts: list[str] = []
    for start, end, slot in groups:
        label = start if start == end else f"{start}-{end}"
        parts.append(f"{label} {slot}")
    return ", ".join(parts)


def district_from_adm(adm: object) -> str | None:
    if not isinstance(adm, list):
        return None
    for item in adm:
        if not isinstance(item, dict):
            continue
        if item.get("type") != "district":
            continue
        name = item.get("name")
        if isinstance(name, str) and name.strip():
            return name.strip()
    return None


def metro_from_links(links: object) -> str | None:
    if not isinstance(links, dict):
        return None
    stations = links.get("nearest_stations")
    if not isinstance(stations, list):
        return None
    metros: list[tuple[int, str]] = []
    for item in stations:
        if not isinstance(item, dict):
            continue
        types = item.get("route_types")
        if isinstance(types, list):
            is_metro = "metro" in types
        elif isinstance(types, str):
            is_metro = types == "metro"
        else:
            is_metro = False
        if not is_metro:
            continue
        name = item.get("name")
        if not isinstance(name, str) or not name.strip():
            continue
        dist = item.get("distance")
        meters = int(dist) if isinstance(dist, int | float) else 10**9
        metros.append((meters, name.strip()))
    if not metros:
        return None
    metros.sort()
    meters, name = metros[0]
    if meters >= 10**9:
        return name
    return f"{name}, {meters} м"


def card_from_twogis(item: dict[str, object]) -> MapCard:
    ogrn, inn = _org_ids(item)
    reviews = item.get("reviews")
    rating: float | None = None
    count: int | None = None
    if isinstance(reviews, dict):
        raw_rating = reviews.get("general_rating")
        raw_count = reviews.get("general_review_count")
        if isinstance(raw_rating, int | float):
            rating = float(raw_rating)
        if isinstance(raw_count, int):
            count = raw_count
    raw_address = item.get("address_name")
    address = raw_address if isinstance(raw_address, str) else None
    ident = item.get("id")
    html_url = f"https://2gis.ru/firm/{ident}" if isinstance(ident, str) else ""
    lon, lat = _geo_point(item)
    return MapCard(
        rating,
        count,
        address,
        html_url,
        html_url,
        None,
        None,
        ogrn,
        inn,
        lon,
        lat,
        hours=hours_from_schedule(item.get("schedule")),
        website=_contact_website(item),
        district=district_from_adm(item.get("adm_div")),
        metro=metro_from_links(item.get("links")),
    )
