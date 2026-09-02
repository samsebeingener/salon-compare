"""Живой поиск карточки. Если результатов не ровно один — не угадываем."""

from __future__ import annotations

import os

import httpx

from salon_compare.collect import EmptyMapApi, MapApi, MapCard
from salon_compare.intake import VenueCandidate
from salon_compare.maps_parse import card_from_twogis, card_from_yandex
from salon_compare.proxy import httpx_client_kwargs


def _get_json(url: str, params: dict[str, str]) -> object:
    response = httpx.get(
        url,
        params=params,
        timeout=15.0,
        **httpx_client_kwargs(),
    )
    response.raise_for_status()
    return response.json()


class TwoGisApi:
    def __init__(self, key: str) -> None:
        self._key = key

    def fetch_card(self, venue: VenueCandidate) -> MapCard | None:
        payload = _get_json(
            "https://catalog.api.2gis.com/3.0/items",
            {
                "q": venue.title,
                "key": self._key,
                "page_size": "5",
                "fields": "items.reviews,items.address_name",
            },
        )
        if not isinstance(payload, dict):
            return None
        result = payload.get("result")
        items = result.get("items") if isinstance(result, dict) else None
        if not isinstance(items, list) or len(items) != 1:
            return None
        item = items[0]
        if not isinstance(item, dict):
            return None
        return card_from_twogis(item)


class YandexPlacesApi:
    def __init__(self, key: str) -> None:
        self._key = key

    def fetch_card(self, venue: VenueCandidate) -> MapCard | None:
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
        if not isinstance(payload, dict):
            return None
        features = payload.get("features")
        if not isinstance(features, list) or len(features) != 1:
            return None
        feature = features[0]
        if not isinstance(feature, dict):
            return None
        return card_from_yandex(feature)


def map_api_from_env(kind: str) -> MapApi:
    if kind == "twogis":
        key = os.environ.get("TWOGIS_API_KEY", "").strip()
        return TwoGisApi(key) if key else EmptyMapApi()
    key = os.environ.get("YANDEX_MAPS_API_KEY", "").strip()
    return YandexPlacesApi(key) if key else EmptyMapApi()
