"""Разбор JSON карточек 2ГИС и Яндекс без сети."""

from __future__ import annotations

from salon_compare.collect import MapCard


def card_from_twogis(item: dict[str, object]) -> MapCard:
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
    return MapCard(rating, count, address, html_url, html_url, None, None)


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
    html_url = ""
    if isinstance(ident, str):
        html_url = f"https://yandex.ru/maps/org/{ident}"
    url = meta.get("url")
    source = url if isinstance(url, str) and url else html_url
    return MapCard(rating, count, address, source, html_url or source, None, None)
