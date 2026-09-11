from __future__ import annotations

from types import SimpleNamespace

import pytest

from salon_compare.html_fetch import (
    _MAX_HTML_BYTES,
    HttpxHtmlFetcher,
    html_client_kwargs,
)


def test_html_fetch_rejects_content_length_over_limit(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fake_get(url: str, **_kwargs: object) -> object:
        return SimpleNamespace(
            status_code=200,
            text="should-not-be-used",
            url=url,
            headers={"Content-Length": str(_MAX_HTML_BYTES + 1)},
            content=b"ok",
        )

    monkeypatch.setattr("salon_compare.html_fetch.httpx.get", fake_get)
    page = HttpxHtmlFetcher().get("https://example.com/page")
    assert page.status == "empty"
    assert page.body == ""
    assert page.url == "https://example.com/page"


def test_html_fetch_rejects_large_body_without_content_length(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fake_get(url: str, **_kwargs: object) -> object:
        return SimpleNamespace(
            status_code=200,
            text="ignored",
            url=url,
            headers={},
            content=b"x" * (_MAX_HTML_BYTES + 1),
        )

    monkeypatch.setattr("salon_compare.html_fetch.httpx.get", fake_get)
    page = HttpxHtmlFetcher().get("https://example.com/huge")
    assert page.status == "empty"
    assert page.body == ""
    assert page.url == "https://example.com/huge"


def test_html_client_skips_proxy_for_twogis_api_host() -> None:
    catalog = html_client_kwargs("https://catalog.api.2gis.com/3.0/items")
    firm = html_client_kwargs("https://2gis.ru/firm/1")
    ddg = html_client_kwargs("https://html.duckduckgo.com/html/")
    assert catalog["trust_env"] is False
    assert firm["trust_env"] is False
    assert ddg["trust_env"] is False
