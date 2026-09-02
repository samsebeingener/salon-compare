from __future__ import annotations

from pathlib import Path
from urllib.parse import quote_plus

from salon_compare.collect import (
    CollectDeps,
    HtmlExtract,
    HtmlFetchResult,
    PlaceRecord,
    Trust,
    collect_place,
    collect_three,
)
from salon_compare.hooks import classify_hook
from salon_compare.intake import VenueCandidate
from salon_compare.legal import (
    LegalExtract,
    MarkerLegalParser,
    ddg_rusprofile_url,
    egrul_url,
    rusprofile_card_urls,
)

ROOT = Path(__file__).resolve().parents[1]
OGRN = "1147746349552"
CARD_WRONG = "https://www.rusprofile.ru/id/111"
CARD_OK = "https://www.rusprofile.ru/id/7301223"


class RecordingPacer:
    def __init__(self) -> None:
        self.calls = 0
        self._started = False

    def wait(self) -> None:
        if self._started:
            self.calls += 1
        self._started = True


class FakeMapApi:
    def fetch_card(self, venue: VenueCandidate) -> None:
        del venue
        return None


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
        return LegalExtract(
            registered_at="2014-04-01",
            status="действует",
            activity="парикмахерские",
        )

    def parse_fedresurs(self, html: str) -> str | None:
        del html
        return "банкротство"

    def parse_kad(self, html: str) -> str | None:
        del html
        return "есть дела"


def _venue(venue_id: str = "p1") -> VenueCandidate:
    return VenueCandidate(venue_id, "Точка", "https://example.com/place")


def _deps(html: FakeHtml, pacer: RecordingPacer | None = None) -> CollectDeps:
    return CollectDeps(
        yandex=FakeMapApi(),
        twogis=FakeMapApi(),
        html=html,
        parser=FakeMapsParser(),
        legal=FakeLegalParser(),
        pacer=pacer or RecordingPacer(),
    )


def _ddg_page(*cards: str) -> HtmlFetchResult:
    body = " ".join(f'<a href="{url}">hit</a>' for url in cards)
    url = ddg_rusprofile_url(OGRN)
    return HtmlFetchResult("ok", body, url)


def test_ddg_url_has_ogrn_and_site_filter() -> None:
    url = ddg_rusprofile_url(OGRN)
    assert url.startswith("https://html.duckduckgo.com/html/?q=")
    assert quote_plus(OGRN) in url or OGRN in url
    assert "rusprofile.ru" in url
    assert "site" in url


def test_rusprofile_card_urls_keep_id_order() -> None:
    html = f'<a href="{CARD_WRONG}"></a><a href="{CARD_OK}"></a>'
    assert rusprofile_card_urls(html) == [CARD_WRONG, CARD_OK]


def test_egrul_empty_fills_weak_from_rusprofile() -> None:
    ddg = ddg_rusprofile_url(OGRN)
    html = FakeHtml(
        {
            egrul_url(OGRN): HtmlFetchResult("blocked", "captcha", egrul_url(OGRN)),
            ddg: _ddg_page(CARD_OK),
            CARD_OK: HtmlFetchResult("ok", f"карточка {OGRN} действует", CARD_OK),
        }
    )
    pacer = RecordingPacer()
    place = collect_place(_venue(), classify_hook(OGRN), _deps(html, pacer))
    assert place.egrul_status.value == "действует"
    assert place.egrul_registered_at.value == "2014-04-01"
    assert place.egrul_activity.value == "парикмахерские"
    assert place.egrul_status.source_url == CARD_OK
    assert place.egrul_status.trust is Trust.WEAK
    assert place.fedresurs.trust is Trust.MISSING
    assert place.kad.trust is Trust.MISSING
    assert CARD_OK in html.calls
    assert pacer.calls >= 1


def test_skips_first_card_without_ogrn() -> None:
    ddg = ddg_rusprofile_url(OGRN)
    html = FakeHtml(
        {
            egrul_url(OGRN): HtmlFetchResult("empty", "", egrul_url(OGRN)),
            ddg: _ddg_page(CARD_WRONG, CARD_OK),
            CARD_WRONG: HtmlFetchResult("ok", "чужая фирма 1227700489917", CARD_WRONG),
            CARD_OK: HtmlFetchResult("ok", f"нужная {OGRN}", CARD_OK),
        }
    )
    place = collect_place(_venue(), classify_hook(OGRN), _deps(html, RecordingPacer()))
    assert place.egrul_status.source_url == CARD_OK
    assert place.egrul_status.trust is Trust.WEAK


def test_ddg_captcha_skips_rusprofile() -> None:
    ddg = ddg_rusprofile_url(OGRN)
    html = FakeHtml(
        {
            egrul_url(OGRN): HtmlFetchResult("blocked", "captcha", egrul_url(OGRN)),
            ddg: HtmlFetchResult("blocked", "captcha", ddg),
        }
    )
    place = collect_place(_venue(), classify_hook(OGRN), _deps(html, RecordingPacer()))
    assert place.egrul_status.trust is Trust.MISSING
    assert not any("rusprofile.ru/id/" in item for item in html.calls)


def test_official_egrul_skips_duckduckgo() -> None:
    ddg = ddg_rusprofile_url(OGRN)
    html = FakeHtml(
        {
            egrul_url(OGRN): HtmlFetchResult(
                "ok", f"<egrul>{OGRN} регистрация</egrul>", egrul_url(OGRN)
            ),
        }
    )
    place = collect_place(_venue(), classify_hook(OGRN), _deps(html, RecordingPacer()))
    assert place.egrul_status.trust is Trust.FOUND
    assert place.egrul_status.source_url == egrul_url(OGRN)
    assert ddg not in html.calls


def test_pause_between_ddg_and_card() -> None:
    ddg = ddg_rusprofile_url(OGRN)
    html = FakeHtml(
        {
            egrul_url(OGRN): HtmlFetchResult("empty", "", egrul_url(OGRN)),
            ddg: _ddg_page(CARD_OK),
            CARD_OK: HtmlFetchResult("ok", f"{OGRN}", CARD_OK),
        }
    )
    pacer = RecordingPacer()
    collect_place(_venue(), classify_hook(OGRN), _deps(html, pacer))
    assert pacer.calls == 1


def test_three_places_share_pacer() -> None:
    ogrns = ("1111111111111", "2222222222222", "3333333333333")
    pages: dict[str, HtmlFetchResult] = {}
    for ogrn in ogrns:
        ddg = ddg_rusprofile_url(ogrn)
        card = f"https://www.rusprofile.ru/id/{ogrn}"
        pages[egrul_url(ogrn)] = HtmlFetchResult("empty", "", egrul_url(ogrn))
        pages[ddg] = HtmlFetchResult("ok", f'<a href="{card}">x</a>', ddg)
        pages[card] = HtmlFetchResult("ok", ogrn, card)
    html = FakeHtml(pages)
    pacer = RecordingPacer()
    deps = _deps(html, pacer)
    venues = [_venue(f"p{i}") for i in range(3)]
    hooks = [classify_hook(ogrn) for ogrn in ogrns]
    collect_three(venues, hooks, deps)
    assert pacer.calls == 5


def test_rusprofile_html_does_not_copy_founder_names() -> None:
    ddg = ddg_rusprofile_url(OGRN)
    card_html = (
        f"ОГРН {OGRN}. Действующая организация. Дата регистрации 01.04.2014. "
        "Учредители: Сулейманова Гульнара Маратовна. "
        "Основной вид деятельности Предоставление услуг парикмахерскими"
    )
    html = FakeHtml(
        {
            egrul_url(OGRN): HtmlFetchResult("empty", "", egrul_url(OGRN)),
            ddg: _ddg_page(CARD_OK),
            CARD_OK: HtmlFetchResult("ok", card_html, CARD_OK),
        }
    )
    deps = CollectDeps(
        yandex=FakeMapApi(),
        twogis=FakeMapApi(),
        html=html,
        parser=FakeMapsParser(),
        legal=MarkerLegalParser(),
        pacer=RecordingPacer(),
    )
    place = collect_place(_venue(), classify_hook(OGRN), deps)
    assert place.egrul_status.value == "действует"
    blob = " ".join(
        str(item)
        for item in (
            place.egrul_status.value,
            place.egrul_registered_at.value,
            place.egrul_activity.value,
        )
    )
    assert "Сулейманова" not in blob
    assert "founder" not in PlaceRecord.model_fields


def test_app_shows_weak_label() -> None:
    text = (ROOT / "src" / "salon_compare" / "app.py").read_text(encoding="utf-8")
    assert "слабо" in text


def test_readme_mentions_ddg_rusprofile_pause() -> None:
    text = (ROOT / "README.md").read_text(encoding="utf-8")
    lowered = text.lower()
    assert "duckduckgo" in lowered
    assert "rusprofile" in lowered
    assert "пауз" in lowered or "задерж" in lowered
