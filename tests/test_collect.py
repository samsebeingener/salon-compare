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
from salon_compare.html_parse import OpenHtmlParser
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
        twogis=FakeMapApi(_full_card("https://2gis.example/a")),
        html=html,
        parser=FakeParser(HtmlExtract()),
    )
    place = collect_place(_venue(), classify_hook("Вишня Таганская"), deps)
    assert place.twogis_rating.trust is Trust.FOUND
    assert place.twogis_rating.value == 4.7
    assert html.calls == []


def test_missing_api_rating_taken_from_html() -> None:
    twogis_html = "https://2gis.example/html"
    html = FakeHtml(
        {twogis_html: HtmlFetchResult("ok", "<html>рейтинг</html>", twogis_html)}
    )
    deps = CollectDeps(
        twogis=FakeMapApi(
            MapCard(
                rating=None,
                review_count=10,
                address="Москва",
                source_url="https://2gis.example/a",
                html_url=twogis_html,
                neighbor_count=None,
                neighbor_avg_rating=None,
            )
        ),
        html=html,
        parser=FakeParser(HtmlExtract(rating=4.1)),
    )
    place = collect_place(_venue(), classify_hook("Вишня Таганская"), deps)
    assert place.twogis_rating.value == 4.1
    assert place.twogis_rating.source_url == twogis_html
    assert place.twogis_rating.trust is Trust.FOUND
    assert html.calls == [twogis_html]


def test_captcha_html_is_missing_not_zero() -> None:
    blocked = "https://2gis.example/html"
    html = FakeHtml({blocked: HtmlFetchResult("blocked", "captcha", blocked)})
    empty = MapCard(
        rating=None,
        review_count=None,
        address=None,
        source_url="https://2gis.example/a",
        html_url=blocked,
        neighbor_count=None,
        neighbor_avg_rating=None,
    )
    deps = CollectDeps(
        twogis=FakeMapApi(empty),
        html=html,
        parser=FakeParser(HtmlExtract(rating=5.0, review_count=99)),
    )
    place = collect_place(_venue(), classify_hook("Вишня Таганская"), deps)
    assert place.twogis_rating.trust is Trust.MISSING
    assert place.twogis_rating.value is None
    assert place.twogis_review_count.value is None
    assert html.calls.count(blocked) == 1


def test_one_empty_twogis_does_not_cancel_others() -> None:
    full = _full_card("https://2gis.example/ok")
    empty = MapCard(
        rating=None,
        review_count=None,
        address=None,
        source_url="https://2gis.example/empty",
        html_url="https://2gis.example/empty/html",
        neighbor_count=None,
        neighbor_avg_rating=None,
    )
    html = FakeHtml(
        {
            "https://2gis.example/empty/html": HtmlFetchResult(
                "blocked", "403", "https://2gis.example/empty/html"
            )
        }
    )
    deps = CollectDeps(
        twogis=ScriptedMapApi({"1": empty, "2": full, "3": full}),
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
    assert rows[0].twogis_rating.trust is Trust.MISSING
    assert rows[1].twogis_rating.trust is Trust.FOUND
    assert rows[2].twogis_rating.trust is Trust.FOUND


def test_neighbors_from_api_skip_html() -> None:
    html = FakeHtml({})
    deps = CollectDeps(
        twogis=FakeMapApi(_full_card("https://2gis.example/a")),
        html=html,
        parser=FakeParser(HtmlExtract()),
    )
    place = collect_place(_venue(), classify_hook("Вишня Таганская"), deps)
    assert place.neighbor_count.value == 5
    assert place.neighbor_vs.value == "ниже"
    assert html.calls == []


def test_neighbors_blocked_html_missing_not_zero() -> None:
    url = "https://2gis.example/html"
    html = FakeHtml({url: HtmlFetchResult("blocked", "403", url)})
    deps = CollectDeps(
        twogis=FakeMapApi(
            MapCard(
                rating=4.5,
                review_count=1,
                address="Москва",
                source_url="https://2gis.example/a",
                html_url=url,
                neighbor_count=None,
                neighbor_avg_rating=None,
            )
        ),
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
        twogis=FakeMapApi(None),
        html=html,
        parser=FakeParser(HtmlExtract(about="Студия у метро")),
    )
    place = collect_place(_venue(), classify_hook(site), deps)
    assert place.site_about.value == "Студия у метро"
    assert place.site_about.source_url == site

    html_403 = FakeHtml({site: HtmlFetchResult("blocked", "403", site)})
    deps_403 = CollectDeps(
        twogis=FakeMapApi(None),
        html=html_403,
        parser=FakeParser(HtmlExtract(about="не должны взять")),
    )
    closed = collect_place(_venue(), classify_hook(site), deps_403)
    assert closed.site_about.value is None
    assert closed.site_about.trust is Trust.MISSING
    assert f"{site}.html" not in html_403.calls


def test_website_empty_retries_html_suffix() -> None:
    site = "https://pinklemon-nails.ru/baumanskaya"
    html_url = f"{site}.html"
    html = FakeHtml(
        {
            site: HtmlFetchResult("empty", "404", site),
            html_url: HtmlFetchResult("ok", "<html>о нас</html>", html_url),
        }
    )
    deps = CollectDeps(
        twogis=FakeMapApi(None),
        html=html,
        parser=FakeParser(HtmlExtract(about="Студия у метро")),
    )
    place = collect_place(_venue(), classify_hook(site), deps)
    assert place.site_about.value == "Студия у метро"
    assert place.site_about.source_url == html_url
    assert html_url in html.calls


def test_name_hook_loads_about_from_twogis_html_website() -> None:
    firm = "https://2gis.ru/firm/70000001083760610"
    site = "https://vishnyasalon.ru"
    html = FakeHtml(
        {
            firm: HtmlFetchResult(
                "ok",
                '{"type":"website","url":"https://vishnyasalon.ru"}',
                firm,
            ),
            site: HtmlFetchResult(
                "ok",
                "<html><h2>О нас</h2><p>Студия маникюра на Таганке.</p></html>",
                site,
            ),
        }
    )
    twogis = MapCard(
        rating=3.6,
        review_count=22,
        address="Таганская улица, 3",
        source_url=firm,
        html_url=firm,
        neighbor_count=None,
        neighbor_avg_rating=None,
        website=None,
    )
    deps = CollectDeps(
        twogis=FakeMapApi(twogis),
        html=html,
        parser=OpenHtmlParser(),
    )
    place = collect_place(_venue(), classify_hook("Вишня Таганская"), deps)
    assert place.site_about.source_url == site
    assert place.site_about.value is not None
    assert "Таганке" in str(place.site_about.value)


def test_blocked_twogis_html_does_not_invent_site() -> None:
    firm = "https://2gis.ru/firm/1"
    html = FakeHtml({firm: HtmlFetchResult("blocked", "403", firm)})
    twogis = MapCard(
        rating=3.6,
        review_count=22,
        address="Таганская улица, 3",
        source_url=firm,
        html_url=firm,
        neighbor_count=None,
        neighbor_avg_rating=None,
        website=None,
    )
    deps = CollectDeps(
        twogis=FakeMapApi(twogis),
        html=html,
        parser=OpenHtmlParser(),
    )
    place = collect_place(_venue(), classify_hook("Вишня Таганская"), deps)
    assert place.site_about.trust is Trust.MISSING
    assert place.site_about.value is None


def test_ogrn_hook_loads_site_from_twogis_website() -> None:
    site = "https://studio.example"
    html = FakeHtml({site: HtmlFetchResult("ok", "<html>о нас</html>", site)})
    twogis = MapCard(
        rating=4.6,
        review_count=80,
        address="Москва",
        source_url="https://2gis.ru/firm/1",
        html_url="https://2gis.ru/firm/1",
        neighbor_count=None,
        neighbor_avg_rating=None,
        website=site,
    )
    deps = CollectDeps(
        twogis=FakeMapApi(twogis),
        html=html,
        parser=FakeParser(HtmlExtract(about="Студия у метро")),
    )
    place = collect_place(_venue(), classify_hook("1147746349552"), deps)
    assert place.site_about.value == "Студия у метро"
    assert place.site_about.source_url == site
    assert site in html.calls


def test_twogis_hours_district_metro_fill_place() -> None:
    twogis = MapCard(
        rating=4.7,
        review_count=51,
        address="Новокузнецкая улица, 42 ст5",
        source_url="https://2gis.ru/firm/1",
        html_url="https://2gis.ru/firm/1",
        neighbor_count=None,
        neighbor_avg_rating=None,
        hours="пн-вс 10:00-22:00",
        district="Замоскворечье",
        metro="Павелецкая, 140 м",
    )
    deps = CollectDeps(
        twogis=FakeMapApi(twogis),
        html=FakeHtml({}),
        parser=FakeParser(HtmlExtract()),
    )
    place = collect_place(_venue(), classify_hook("Вишня Таганская"), deps)
    assert place.hours.value == "пн-вс 10:00-22:00"
    assert place.district.value == "Замоскворечье"
    assert place.metro.value == "Павелецкая, 140 м"
    assert place.hours.trust is Trust.FOUND
    assert place.district.trust is Trust.FOUND
    assert place.metro.trust is Trust.FOUND


def test_app_shows_fields_table_without_score_index() -> None:
    text = (ROOT / "src" / "salon_compare" / "app.py").read_text(encoding="utf-8")
    lowered = text.lower()
    assert "collect_three" in text or "collect_place" in text
    assert "не найдено" in lowered
    assert "покупай" not in lowered
    assert "Район" in text
    assert "Метро" in text
    assert "Яндекс рейтинг" not in text
    assert '"Рейтинг соседей"' not in text
