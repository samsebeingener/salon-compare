"""Разбор JSON карточек 2ГИС и Яндекс без сети."""

from __future__ import annotations

import re
from urllib.parse import urlparse

from salon_compare.collect import MapCard
from salon_compare.hooks import ClassifiedHook
from salon_compare.intake import VenueCandidate

_FIRM = re.compile(r"/firm/([^/?#]+)", re.IGNORECASE)
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
            )
        )
    return found


def candidates_from_yandex_features(
    features: list[dict[str, object]],
) -> list[VenueCandidate]:
    found: list[VenueCandidate] = []
    for feature in features:
        card = card_from_yandex(feature)
        ident = _yandex_id(feature)
        if not ident:
            continue
        title = ident
        props = feature.get("properties")
        if isinstance(props, dict):
            meta = props.get("CompanyMetaData")
            if isinstance(meta, dict):
                raw_name = meta.get("name")
                if isinstance(raw_name, str) and raw_name:
                    title = raw_name
        url = card.source_url or card.html_url or f"https://yandex.ru/maps/org/{ident}"
        found.append(VenueCandidate(f"yandex:{ident}", title, url, "yandex"))
    return found


def _yandex_id(feature: dict[str, object]) -> str:
    props = feature.get("properties")
    if not isinstance(props, dict):
        return ""
    meta = props.get("CompanyMetaData")
    if isinstance(meta, dict):
        ident = meta.get("id")
        if isinstance(ident, str) and ident:
            return ident
    ident = props.get("id") or props.get("companyId")
    return ident if isinstance(ident, str) else ""


def candidate_from_maps_url(hook: ClassifiedHook) -> VenueCandidate | None:
    url = hook.normalized
    host = urlparse(url).netloc.lower()
    firm = _FIRM.search(url)
    if "2gis." in host and firm:
        ident = firm.group(1)
        return VenueCandidate(f"twogis:{ident}", ident, url, "twogis")
    org = _ORG.search(url)
    if "yandex." in host and org:
        ident = org.group(1)
        return VenueCandidate(f"yandex:{ident}", ident, url, "yandex")
    return VenueCandidate(f"maps:{url}", url, url, "maps")


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
        website=_contact_website(item),
    )


def card_from_yandex(feature: dict[str, object]) -> MapCard:
    props = feature.get("properties")
    meta: dict[str, object] = {}
    if isinstance(props, dict):
        raw_meta = props.get("CompanyMetaData")
        if isinstance(raw_meta, dict):
            meta = raw_meta
    raw_address = meta.get("address")
    address = raw_address if isinstance(raw_address, str) else None
    ratings = meta.get("Ratings")
    rating: float | None = None
    if isinstance(ratings, dict):
        raw_rating = ratings.get("value") or ratings.get("Rating")
        if isinstance(raw_rating, int | float):
            rating = float(raw_rating)
    reviews = meta.get("Reviews")
    count: int | None = None
    if isinstance(reviews, dict):
        raw_count = reviews.get("Count") or reviews.get("count")
        if isinstance(raw_count, int):
            count = raw_count
    ident = meta.get("id")
    url = meta.get("url")
    html_url = ""
    if isinstance(ident, str):
        html_url = f"https://yandex.ru/maps/org/{ident}"
    website = _http_url(url)
    source = html_url or (website or "")
    hours_block = meta.get("Hours")
    hours: str | None = None
    if isinstance(hours_block, dict):
        raw_hours = hours_block.get("text")
        if isinstance(raw_hours, str) and raw_hours.strip():
            hours = raw_hours.strip()
    ogrn, inn = _org_ids(meta)
    return MapCard(
        rating,
        count,
        address,
        source,
        html_url or source,
        None,
        None,
        ogrn,
        inn,
        hours=hours,
        website=website,
    )
