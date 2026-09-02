"""Живой поиск карточек. Все хиты наружу; карточку грузим по id."""

from __future__ import annotations

import os

import httpx

from salon_compare.collect import EmptyMapApi, MapCard
from salon_compare.intake import VenueCandidate
from salon_compare.maps_parse import (
    candidates_from_twogis_items,
    candidates_from_yandex_features,
    card_from_twogis,
    card_from_yandex,
    item_by_id,
    neighbors_from_twogis_items,
)
from salon_compare.proxy import httpx_client_kwargs

TWOGIS_FIELDS = "items.reviews,items.address_name,items.point"


def _get_json(url: str, params: dict[str, str]) -> object | None:
    try:
        response = httpx.get(
            url,
            params=params,
            timeout=15.0,
            **httpx_client_kwargs(),
        )
        response.raise_for_status()
        data: object = response.json()
    except httpx.HTTPError:
        return None
    return data


def _with_twogis_neighbors(key: str, ident: str, card: MapCard) -> MapCard:
    if card.lon is None or card.lat is None:
        return card
    payload = _get_json(
        "https://catalog.api.2gis.com/3.0/items",
        {
            "q": "маникюр",
            "point": f"{card.lon},{card.lat}",
            "radius": "500",
            "type": "branch",
            "page_size": "10",
            "key": key,
            "fields": "items.reviews",
        },
    )
    count, avg = neighbors_from_twogis_items(_twogis_items(payload), ident)
    return MapCard(
        card.rating,
        card.review_count,
        card.address,
        card.source_url,
        card.html_url,
        count,
        avg,
        card.ogrn,
        card.inn,
        card.lon,
        card.lat,
    )


def _twogis_items(payload: object) -> list[dict[str, object]]:
    if not isinstance(payload, dict):
        return []
    result = payload.get("result")
    items = result.get("items") if isinstance(result, dict) else None
    if not isinstance(items, list):
        return []
    return [item for item in items if isinstance(item, dict)]


def _yandex_features(payload: object) -> list[dict[str, object]]:
    if not isinstance(payload, dict):
        return []
    features = payload.get("features")
    if not isinstance(features, list):
        return []
    return [item for item in features if isinstance(item, dict)]


class TwoGisApi:
    def __init__(self, key: str) -> None:
        self._key = key

    def search(self, query: str) -> list[VenueCandidate]:
        payload = _get_json(
            "https://catalog.api.2gis.com/3.0/items",
            {
                "q": query,
                "key": self._key,
                "page_size": "5",
                "fields": TWOGIS_FIELDS,
            },
        )
        return candidates_from_twogis_items(_twogis_items(payload))

    def fetch_card(self, venue: VenueCandidate) -> MapCard | None:
        if not venue.venue_id.startswith("twogis:"):
            return None
        ident = venue.venue_id.removeprefix("twogis:")
        payload = _get_json(
            "https://catalog.api.2gis.com/3.0/items/byid",
            {
                "id": ident,
                "key": self._key,
                "fields": TWOGIS_FIELDS,
            },
        )
        items = _twogis_items(payload)
        item = item_by_id(items, ident)
        if item is None and venue.title:
            payload = _get_json(
                "https://catalog.api.2gis.com/3.0/items",
                {
                    "q": venue.title,
                    "key": self._key,
                    "page_size": "5",
                    "fields": TWOGIS_FIELDS,
                },
            )
            item = item_by_id(_twogis_items(payload), ident)
        if item is None:
            return None
        card = card_from_twogis(item)
        return _with_twogis_neighbors(self._key, ident, card)


class YandexPlacesApi:
    def __init__(self, key: str) -> None:
        self._key = key

    def search(self, query: str) -> list[VenueCandidate]:
        payload = _get_json(
            "https://search-maps.yandex.ru/v1/",
            {
                "apikey": self._key,
                "text": query,
                "lang": "ru_RU",
                "type": "biz",
                "results": "5",
            },
        )
        return candidates_from_yandex_features(_yandex_features(payload))

    def fetch_card(self, venue: VenueCandidate) -> MapCard | None:
        if not venue.venue_id.startswith("yandex:"):
            return None
        ident = venue.venue_id.removeprefix("yandex:")
        payload = _get_json(
            "https://search-maps.yandex.ru/v1/",
            {
                "apikey": self._key,
                "text": venue.title,
                "lang": "ru_RU",
                "type": "biz",
                "results": "5",
            },
        )
        for feature in _yandex_features(payload):
            props = feature.get("properties")
            meta: object = None
            if isinstance(props, dict):
                meta = props.get("CompanyMetaData")
            feature_id = ""
            if isinstance(meta, dict):
                raw_id = meta.get("id")
                if isinstance(raw_id, str):
                    feature_id = raw_id
            if feature_id == ident:
                return card_from_yandex(feature)
        return None


def map_api_from_env(kind: str) -> EmptyMapApi | TwoGisApi | YandexPlacesApi:
    if kind == "twogis":
        key = os.environ.get("TWOGIS_API_KEY", "").strip()
        return TwoGisApi(key) if key else EmptyMapApi()
    key = os.environ.get("YANDEX_MAPS_API_KEY", "").strip()
    return YandexPlacesApi(key) if key else EmptyMapApi()
