from __future__ import annotations

from pathlib import Path

from salon_compare.collect import (
    CollectDeps,
    HtmlExtract,
    HtmlFetchResult,
    MapCard,
    PlaceRecord,
    Trust,
    collect_place,
)
from salon_compare.hooks import classify_hook
from salon_compare.intake import VenueCandidate
from salon_compare.legal import (
    LegalExtract,
    LegalOrg,
    egrul_url,
    fedresurs_url,
    kad_url,
    resolve_legal_orgs,
)

ROOT = Path(__file__).resolve().parents[1]
OGRN = "1147746349552"


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
    def __init__(
        self,
        extract: LegalExtract,
        fedresurs: str | None,
        kad: str | None,
    ) -> None:
        self.extract = extract
        self.fedresurs = fedresurs
        self.kad = kad

    def parse_egrul(self, html: str) -> LegalExtract:
        del html
        return self.extract

    def parse_fedresurs(self, html: str) -> str | None:
        del html
        return self.fedresurs

    def parse_kad(self, html: str) -> str | None:
        del html
        return self.kad


def _venue() -> VenueCandidate:
    return VenueCandidate("p1", "Точка", "https://example.com/place")


def _card(
    *,
    ogrn: str | None = None,
    inn: str | None = None,
    url: str = "https://maps.example/a",
) -> MapCard:
    return MapCard(
        rating=4.7,
        review_count=10,
        address="Москва",
        source_url=url,
        html_url=url,
        neighbor_count=1,
        neighbor_avg_rating=4.0,
        ogrn=ogrn,
        inn=inn,
    )


def _legal_extract() -> LegalExtract:
    return LegalExtract(
        registered_at="2014-04-01",
        status="действует",
        activity="парикмахерские",
        orgs=[LegalOrg(OGRN, "ООО Ногтевой Сервис", egrul_url(OGRN))],
    )


def _deps(
    html: FakeHtml,
    yandex: MapCard | None = None,
    twogis: MapCard | None = None,
    legal: FakeLegalParser | None = None,
) -> CollectDeps:
    parser = legal or FakeLegalParser(
        _legal_extract(), "не обнаружено", "не обнаружено"
    )
    return CollectDeps(
        yandex=FakeMapApi(yandex),
        twogis=FakeMapApi(twogis),
        html=html,
        parser=FakeMapsParser(),
        legal=parser,
    )


def test_ogrn_hook_is_single_org_without_search() -> None:
    hook = classify_hook(OGRN)
    found = resolve_legal_orgs(hook, _card(), _card(), [])
    assert len(found) == 1
    assert found[0].ogrn == OGRN
    assert found[0].source_url == egrul_url(OGRN)


def test_ogrn_fills_three_registries() -> None:
    html = FakeHtml(
        {
            egrul_url(OGRN): HtmlFetchResult("ok", "<egrul>", egrul_url(OGRN)),
            fedresurs_url(OGRN): HtmlFetchResult("ok", "<fed>", fedresurs_url(OGRN)),
            kad_url(OGRN): HtmlFetchResult("ok", "<kad>", kad_url(OGRN)),
        }
    )
    place = collect_place(_venue(), classify_hook(OGRN), _deps(html))
    assert place.egrul_registered_at.value == "2014-04-01"
    assert place.egrul_status.value == "действует"
    assert place.egrul_activity.value == "парикмахерские"
    assert place.egrul_status.source_url == egrul_url(OGRN)
    assert place.fedresurs.value == "не обнаружено"
    assert place.fedresurs.source_url == fedresurs_url(OGRN)
    assert place.kad.value == "не обнаружено"
    assert place.kad.source_url == kad_url(OGRN)
    assert place.legal_candidates == ()
    assert "founder" not in PlaceRecord.model_fields


def test_no_ogrn_does_not_claim_no_debts() -> None:
    html = FakeHtml({})
    place = collect_place(
        _venue(),
        classify_hook("https://pinklemon-nails.ru/baumanskaya"),
        _deps(html),
    )
    assert place.egrul_status.trust is Trust.MISSING
    assert place.fedresurs.value is None
    assert place.kad.value is None
    for field in (place.egrul_status, place.fedresurs, place.kad):
        assert field.value not in {"долгов нет", "чисто", 0, "0"}


def test_two_map_ogrns_ask_confirmation_not_missing() -> None:
    html = FakeHtml({})
    yandex = _card(ogrn="1111111111111", url="https://yandex.example/org/a")
    twogis = _card(ogrn="2222222222222", url="https://2gis.example/firm/b")
    place = collect_place(
        _venue(),
        classify_hook("Вишня Таганская"),
        _deps(html, yandex=yandex, twogis=twogis),
    )
    links = {item.source_url for item in place.legal_candidates}
    ogrns = {item.ogrn for item in place.legal_candidates}
    assert ogrns == {"1111111111111", "2222222222222"}
    assert "https://yandex.example/org/a" in links
    assert "https://2gis.example/firm/b" in links
    assert place.egrul_status.trust is Trust.MISSING
    assert html.calls == []


def test_confirm_ogrn_collects_that_org() -> None:
    html = FakeHtml(
        {
            egrul_url("2222222222222"): HtmlFetchResult(
                "ok", "<egrul>", egrul_url("2222222222222")
            ),
            fedresurs_url("2222222222222"): HtmlFetchResult(
                "ok", "<fed>", fedresurs_url("2222222222222")
            ),
            kad_url("2222222222222"): HtmlFetchResult(
                "ok", "<kad>", kad_url("2222222222222")
            ),
        }
    )
    yandex = _card(ogrn="1111111111111", url="https://yandex.example/org/a")
    twogis = _card(ogrn="2222222222222", url="https://2gis.example/firm/b")
    extract = LegalExtract(
        registered_at="2018-01-01",
        status="действует",
        activity="маникюр",
        orgs=[],
    )
    deps = _deps(
        html,
        yandex=yandex,
        twogis=twogis,
        legal=FakeLegalParser(extract, "не обнаружено", "есть дела"),
    )
    place = collect_place(
        _venue(),
        classify_hook("Вишня Таганская"),
        deps,
        legal_choice="2222222222222",
    )
    assert place.legal_candidates == ()
    assert place.egrul_status.value == "действует"
    assert place.egrul_status.source_url == egrul_url("2222222222222")
    assert place.kad.value == "есть дела"
    assert egrul_url("1111111111111") not in html.calls


def test_inn_two_orgs_need_confirm() -> None:
    inn = "7707083893"
    html = FakeHtml({egrul_url(inn): HtmlFetchResult("ok", "<two>", egrul_url(inn))})
    extract = LegalExtract(
        orgs=[
            LegalOrg("1111111111111", "Первая", egrul_url("1111111111111")),
            LegalOrg("2222222222222", "Вторая", egrul_url("2222222222222")),
        ]
    )
    place = collect_place(
        _venue(),
        classify_hook(inn),
        _deps(html, legal=FakeLegalParser(extract, None, None)),
    )
    assert len(place.legal_candidates) == 2
    assert {item.source_url for item in place.legal_candidates} == {
        egrul_url("1111111111111"),
        egrul_url("2222222222222"),
    }
    assert place.egrul_status.trust is Trust.MISSING
    assert fedresurs_url("1111111111111") not in html.calls


def test_fedresurs_captcha_missing_egrul_ok() -> None:
    html = FakeHtml(
        {
            egrul_url(OGRN): HtmlFetchResult("ok", "<egrul>", egrul_url(OGRN)),
            fedresurs_url(OGRN): HtmlFetchResult(
                "blocked", "captcha", fedresurs_url(OGRN)
            ),
            kad_url(OGRN): HtmlFetchResult("ok", "<kad>", kad_url(OGRN)),
        }
    )
    place = collect_place(_venue(), classify_hook(OGRN), _deps(html))
    assert place.egrul_status.value == "действует"
    assert place.fedresurs.trust is Trust.MISSING
    assert place.fedresurs.value is None
    assert place.kad.value == "не обнаружено"
    assert html.calls.count(fedresurs_url(OGRN)) == 1


def test_app_asks_legal_confirm_and_shows_registry_rows() -> None:
    text = (ROOT / "src" / "salon_compare" / "app.py").read_text(encoding="utf-8")
    assert "legal_candidates" in text
    assert "Подтвердить юрлицо" in text
    assert "ЕГРЮЛ" in text
    assert "Федресурс" in text
    assert "КАД" in text
    assert "индекс" not in text.lower()


def test_readme_mentions_registries() -> None:
    text = (ROOT / "README.md").read_text(encoding="utf-8")
    assert "ЕГРЮЛ" in text or "егрюл" in text.lower()
    assert "Федресурс" in text or "федресурс" in text.lower()
