from __future__ import annotations

from pathlib import Path

from salon_compare.collect import (
    CollectDeps,
    HtmlExtract,
    HtmlFetchResult,
    MapCard,
    Trust,
    collect_place,
)
from salon_compare.hooks import classify_hook
from salon_compare.html_fetch import classify_fetch
from salon_compare.intake import VenueCandidate
from salon_compare.legal import LegalExtract, kad_url
from salon_compare.maps_parse import neighbors_from_twogis_items

ROOT = Path(__file__).resolve().parents[1]
OGRN = "1147746349552"
INN = "7707083893"


class FakeMapApi:
    def __init__(self, card: MapCard | None) -> None:
        self.card = card

    def fetch_card(self, venue: VenueCandidate) -> MapCard | None:
        del venue
        return self.card


class FakeHtml:
    def __init__(self, pages: dict[str, HtmlFetchResult]) -> None:
        self.pages = pages
        self.calls: list[str] = []

    def get(self, url: str) -> HtmlFetchResult:
        self.calls.append(url)
        return self.pages.get(url, HtmlFetchResult(status="empty", body="", url=url))


class FakeMapsParser:
    def parse(self, html: str) -> HtmlExtract:
        del html
        return HtmlExtract()


class FakeLegalParser:
    def parse_egrul(self, html: str) -> LegalExtract:
        del html
        return LegalExtract(status="действует")

    def parse_fedresurs(self, html: str) -> str | None:
        del html
        return "банкротство"

    def parse_kad(self, html: str) -> str | None:
        del html
        return "есть дела"


def _venue() -> VenueCandidate:
    return VenueCandidate("p1", "Точка", "https://example.com/place")


def test_login_word_is_not_blocked_captcha_is() -> None:
    assert classify_fetch(200, "<html>Войти в кабинет</html>") == "ok"
    assert classify_fetch(200, "<html>smartcaptcha</html>") == "blocked"
    assert classify_fetch(403, "<html>ok</html>") == "blocked"
    assert classify_fetch(404, "<html>not found</html>") == "empty"


def test_kad_shell_without_ogrn_is_missing_not_has_cases() -> None:
    url = kad_url(OGRN)
    html = FakeHtml(
        {
            url: HtmlFetchResult(
                "ok",
                "<html>Картотека арбитражных дел. Войти</html>",
                url,
            )
        }
    )
    deps = CollectDeps(
        twogis=FakeMapApi(None),
        html=html,
        parser=FakeMapsParser(),
        legal=FakeLegalParser(),
    )
    place = collect_place(_venue(), classify_hook(OGRN), deps)
    assert place.kad.trust is Trust.MISSING
    assert place.kad.value is None


def test_inn_on_card_does_not_hit_fedresurs() -> None:
    html = FakeHtml({})
    card = MapCard(
        rating=4.2,
        review_count=3,
        address="Москва",
        source_url="https://2gis.example/firm/1",
        html_url="https://2gis.example/firm/1",
        neighbor_count=1,
        neighbor_avg_rating=4.0,
        ogrn=None,
        inn=INN,
    )
    deps = CollectDeps(
        twogis=FakeMapApi(card),
        html=html,
        parser=FakeMapsParser(),
        legal=FakeLegalParser(),
    )
    collect_place(_venue(), classify_hook("Вишня Таганская"), deps)
    assert not any("fedresurs" in item for item in html.calls)
    assert not any("kad.arbitr" in item for item in html.calls)


def test_neighbors_from_radius_items_exclude_self() -> None:
    items: list[dict[str, object]] = [
        {"id": "self", "reviews": {"general_rating": 4.9}},
        {"id": "a", "reviews": {"general_rating": 4.2}},
        {"id": "b", "reviews": {"general_rating": 4.0}},
    ]
    count, avg = neighbors_from_twogis_items(items, "self")
    assert count == 2
    assert avg == 4.1


def test_app_does_not_default_first_radio_card() -> None:
    text = (ROOT / "src" / "salon_compare" / "app.py").read_text(encoding="utf-8")
    assert "options[0]" not in text


def test_twogis_requests_point_field() -> None:
    text = (ROOT / "src" / "salon_compare" / "maps_http.py").read_text(encoding="utf-8")
    assert "items.point" in text


def test_html_fetcher_sends_user_agent() -> None:
    path = ROOT / "src" / "salon_compare" / "html_fetch.py"
    text = path.read_text(encoding="utf-8")
    assert "User-Agent" in text


def test_readme_records_live_probe() -> None:
    text = (ROOT / "README.md").read_text(encoding="utf-8")
    assert "404" in text
    assert "baumanskaya.html" in text
    assert "оболоч" in text.lower() or "капч" in text.lower()
