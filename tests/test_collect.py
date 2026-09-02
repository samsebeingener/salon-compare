from __future__ import annotations

from pathlib import Path

from salon_compare.collect import (
    CollectDeps,
    HtmlExtract,
    HtmlFetchResult,
    MapCard,
    Trust,
    collect_place,
    collect_three,
)
from salon_compare.hooks import classify_hook
from salon_compare.intake import VenueCandidate

ROOT = Path(__file__).resolve().parents[1]


class FakeMapApi:
    def __init__(self, card: MapCard | None) -> None:
        self.card = card

    def fetch_card(self, venue: VenueCandidate) -> MapCard | None:
        del venue
        return self.card


class ScriptedMapApi:
    def __init__(self, by_id: dict[str, MapCard | None]) -> None:
        self.by_id = by_id

    def fetch_card(self, venue: VenueCandidate) -> MapCard | None:
        return self.by_id.get(venue.venue_id)


class FakeHtml:
    def __init__(self, pages: dict[str, HtmlFetchResult]) -> None:
        self.pages = pages
        self.calls: list[str] = []

    def get(self, url: str) -> HtmlFetchResult:
        self.calls.append(url)
        return self.pages.get(url, HtmlFetchResult(status="empty", body="", url=url))


class FakeParser:
    def __init__(self, extract: HtmlExtract) -> None:
        self.extract = extract

    def parse(self, html: str) -> HtmlExtract:
        del html
        return self.extract


def _venue(venue_id: str = "p1") -> VenueCandidate:
    return VenueCandidate(venue_id, "Точка", "https://example.com/place")


def _full_card(url: str) -> MapCard:
    return MapCard(
        rating=4.7,
        review_count=120,
        address="Москва",
        source_url=url,
        html_url=f"{url}/html",
        neighbor_count=5,
        neighbor_avg_rating=4.2,
        hours="пн-вс 10:00-21:00",
        last_review="2026-08-01",
        plus_minus="40 плюс / 3 минус",
    )


def test_full_api_skips_html() -> None:
    html = FakeHtml({})
    deps = CollectDeps(
        yandex=FakeMapApi(_full_card("https://yandex.example/a")),
        twogis=FakeMapApi(_full_card("https://2gis.example/a")),
        html=html,
        parser=FakeParser(HtmlExtract()),
    )
    place = collect_place(_venue(), classify_hook("Вишня Таганская"), deps)
    assert place.yandex_rating.trust is Trust.FOUND
    assert place.yandex_rating.value == 4.7
    assert place.twogis_rating.trust is Trust.FOUND
    assert html.calls == []


def test_missing_api_rating_taken_from_html() -> None:
    yandex_html = "https://yandex.example/html"
    html = FakeHtml(
        {yandex_html: HtmlFetchResult("ok", "<html>рейтинг</html>", yandex_html)}
    )
    deps = CollectDeps(
        yandex=FakeMapApi(
            MapCard(
                rating=None,
                review_count=10,
                address="Москва",
                source_url="https://yandex.example/a",
                html_url=yandex_html,
                neighbor_count=None,
                neighbor_avg_rating=None,
            )
        ),
        twogis=FakeMapApi(None),
        html=html,
        parser=FakeParser(HtmlExtract(rating=4.1)),
    )
    place = collect_place(_venue(), classify_hook("Вишня Таганская"), deps)
    assert place.yandex_rating.value == 4.1
    assert place.yandex_rating.source_url == yandex_html
    assert place.yandex_rating.trust is Trust.FOUND
    assert html.calls == [yandex_html]


def test_captcha_html_is_missing_not_zero() -> None:
    blocked = "https://yandex.example/html"
    html = FakeHtml({blocked: HtmlFetchResult("blocked", "captcha", blocked)})
    empty = MapCard(
        rating=None,
        review_count=None,
        address=None,
        source_url="https://yandex.example/a",
        html_url=blocked,
        neighbor_count=None,
        neighbor_avg_rating=None,
    )
    deps = CollectDeps(
        yandex=FakeMapApi(empty),
        twogis=FakeMapApi(empty),
        html=html,
        parser=FakeParser(HtmlExtract(rating=5.0, review_count=99)),
    )
    place = collect_place(_venue(), classify_hook("Вишня Таганская"), deps)
    assert place.yandex_rating.trust is Trust.MISSING
    assert place.yandex_rating.value is None
    assert place.yandex_review_count.value is None
    assert place.twogis_rating.value is None
    assert html.calls.count(blocked) == 1


def test_one_empty_yandex_does_not_cancel_others() -> None:
    full = _full_card("https://yandex.example/ok")
    empty = MapCard(
        rating=None,
        review_count=None,
        address=None,
        source_url="https://yandex.example/empty",
        html_url="https://yandex.example/empty/html",
        neighbor_count=None,
        neighbor_avg_rating=None,
    )
    html = FakeHtml(
        {
            "https://yandex.example/empty/html": HtmlFetchResult(
                "blocked", "403", "https://yandex.example/empty/html"
            )
        }
    )
    deps = CollectDeps(
        yandex=ScriptedMapApi({"1": empty, "2": full, "3": full}),
        twogis=ScriptedMapApi(
            {
                "1": _full_card("https://2gis.example/1"),
                "2": _full_card("https://2gis.example/2"),
                "3": _full_card("https://2gis.example/3"),
            }
        ),
        html=html,
        parser=FakeParser(HtmlExtract()),
    )
    venues = (
        VenueCandidate("1", "A", "https://a.example"),
        VenueCandidate("2", "B", "https://b.example"),
        VenueCandidate("3", "C", "https://c.example"),
    )
    hooks = (
        classify_hook("aaa"),
        classify_hook("bbb"),
        classify_hook("ccc"),
    )
    rows = collect_three(venues, hooks, deps)
    assert len(rows) == 3
    assert rows[0].yandex_rating.trust is Trust.MISSING
    assert rows[1].yandex_rating.trust is Trust.FOUND
    assert rows[2].yandex_rating.trust is Trust.FOUND
    assert rows[0].twogis_rating.trust is Trust.FOUND


def test_neighbors_from_api_skip_html() -> None:
    html = FakeHtml({})
    deps = CollectDeps(
        yandex=FakeMapApi(_full_card("https://yandex.example/a")),
        twogis=FakeMapApi(None),
        html=html,
        parser=FakeParser(HtmlExtract()),
    )
    place = collect_place(_venue(), classify_hook("Вишня Таганская"), deps)
    assert place.neighbor_count.value == 5
    assert place.neighbor_vs.value == "ниже"
    assert html.calls == []


def test_neighbors_blocked_html_missing_not_zero() -> None:
    url = "https://yandex.example/html"
    html = FakeHtml({url: HtmlFetchResult("blocked", "403", url)})
    deps = CollectDeps(
        yandex=FakeMapApi(
            MapCard(
                rating=4.5,
                review_count=1,
                address="Москва",
                source_url="https://yandex.example/a",
                html_url=url,
                neighbor_count=None,
                neighbor_avg_rating=None,
            )
        ),
        twogis=FakeMapApi(None),
        html=html,
        parser=FakeParser(HtmlExtract(neighbor_count=8)),
    )
    place = collect_place(_venue(), classify_hook("Вишня Таганская"), deps)
    assert place.neighbor_count.value is None
    assert place.neighbor_count.trust is Trust.MISSING


def test_website_ok_and_forbidden() -> None:
    site = "https://pinklemon-nails.ru/baumanskaya"
    html = FakeHtml({site: HtmlFetchResult("ok", "<html>о нас</html>", site)})
    deps = CollectDeps(
        yandex=FakeMapApi(None),
        twogis=FakeMapApi(None),
        html=html,
        parser=FakeParser(HtmlExtract(about="Студия у метро")),
    )
    place = collect_place(_venue(), classify_hook(site), deps)
    assert place.site_about.value == "Студия у метро"
    assert place.site_about.source_url == site

    html_403 = FakeHtml({site: HtmlFetchResult("blocked", "403", site)})
    deps_403 = CollectDeps(
        yandex=FakeMapApi(None),
        twogis=FakeMapApi(None),
        html=html_403,
        parser=FakeParser(HtmlExtract(about="не должны взять")),
    )
    closed = collect_place(_venue(), classify_hook(site), deps_403)
    assert closed.site_about.value is None
    assert closed.site_about.trust is Trust.MISSING


def test_app_shows_fields_table_without_score_index() -> None:
    text = (ROOT / "src" / "salon_compare" / "app.py").read_text(encoding="utf-8")
    lowered = text.lower()
    assert "collect_three" in text or "collect_place" in text
    assert "не найдено" in lowered
    assert "покупай" not in lowered
