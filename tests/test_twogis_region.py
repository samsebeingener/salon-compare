from __future__ import annotations

from typing import Any

import httpx
import pytest

from salon_compare.maps_http import (
    MOSCOW_REGION_ID,
    TwoGisApi,
    twogis_items_search_params,
)


def test_twogis_search_params_include_moscow_region() -> None:
    params = twogis_items_search_params("Вишня Таганская", "test")
    assert params["q"] == "Вишня Таганская"
    assert params["region_id"] == "32"
    assert params["region_id"] == MOSCOW_REGION_ID


class _FakeResponse:
    def __init__(self, item: dict[str, object] | None = None) -> None:
        self._item = item

    def raise_for_status(self) -> None:
        return None

    def json(self) -> dict[str, object]:
        if self._item is None:
            return {"result": {"items": []}}
        return {"result": {"items": [self._item]}}


def test_twogis_search_sends_region_id(monkeypatch: pytest.MonkeyPatch) -> None:
    captured: dict[str, Any] = {}

    def fake_get(
        url: str,
        params: dict[str, str] | None = None,
        **kwargs: object,
    ) -> _FakeResponse:
        captured["url"] = url
        captured["params"] = params or {}
        captured["kwargs"] = kwargs
        return _FakeResponse()

    monkeypatch.setattr(httpx, "get", fake_get)
    TwoGisApi("test").search("Вишня Таганская")
    assert "/3.0/items" in str(captured["url"])
    sent = captured["params"]
    assert sent["region_id"] == "32"
    assert sent["q"] == "Вишня Таганская"
    assert captured["kwargs"].get("trust_env") is False
    fields = sent["fields"].split(",")
    assert "contact_groups" in sent["fields"]
    assert "org" in sent["fields"]
    assert "items.address" in fields
    assert "items.adm_div" in fields
    assert "items.links" in fields


def test_twogis_byid_and_neighbors_skip_env_proxy(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from salon_compare.intake import VenueCandidate

    calls: list[dict[str, Any]] = []
    ident = "70000001000000000"
    item: dict[str, object] = {
        "id": ident,
        "name": "Вишня",
        "point": {"lon": 37.6, "lat": 55.7},
    }

    def fake_get(
        url: str,
        params: dict[str, str] | None = None,
        **kwargs: object,
    ) -> _FakeResponse:
        del params
        calls.append({"url": str(url), "kwargs": kwargs})
        return _FakeResponse(item)

    monkeypatch.setattr(httpx, "get", fake_get)
    venue = VenueCandidate(
        f"twogis:{ident}",
        "Вишня",
        f"https://2gis.ru/firm/{ident}",
        "twogis",
    )
    TwoGisApi("test").fetch_card(venue)
    urls = [call["url"] for call in calls]
    assert any("/3.0/items/byid" in url for url in urls)
    assert any("/3.0/items" in url and "/byid" not in url for url in urls)
    assert calls
    assert all(call["kwargs"].get("trust_env") is False for call in calls)
