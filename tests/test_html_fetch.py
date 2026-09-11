from __future__ import annotations

from types import SimpleNamespace

import pytest

from salon_compare.html_fetch import _MAX_HTML_BYTES, HttpxHtmlFetcher


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
