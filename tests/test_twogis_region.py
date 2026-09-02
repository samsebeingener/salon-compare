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
    def raise_for_status(self) -> None:
        return None

    def json(self) -> dict[str, object]:
        return {"result": {"items": []}}


def test_twogis_search_sends_region_id(monkeypatch: pytest.MonkeyPatch) -> None:
    captured: dict[str, Any] = {}

    def fake_get(
        url: str,
        params: dict[str, str] | None = None,
        **kwargs: object,
    ) -> _FakeResponse:
        del kwargs
        captured["url"] = url
        captured["params"] = params or {}
        return _FakeResponse()

    monkeypatch.setattr(httpx, "get", fake_get)
    TwoGisApi("test").search("Вишня Таганская")
    assert "/3.0/items" in str(captured["url"])
    sent = captured["params"]
    assert sent["region_id"] == "32"
    assert sent["q"] == "Вишня Таганская"
    assert "contact_groups" in sent["fields"]
    assert "org" in sent["fields"]
