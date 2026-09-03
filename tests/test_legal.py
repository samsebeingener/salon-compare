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
    labeled_inn,
    labeled_ogrn,
    resolve_legal_orgs,
    site_requisites_extract,
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
        hours="пн-вс 10:00-21:00",
        last_review="2026-08-01",
        plus_minus="10 плюс / 1 минус",
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
    twogis: MapCard | None = None,
    legal: FakeLegalParser | None = None,
) -> CollectDeps:
    parser = legal or FakeLegalParser(
        _legal_extract(), "не обнаружено", "не обнаружено"
    )
    return CollectDeps(
        twogis=FakeMapApi(twogis),
        html=html,
        parser=FakeMapsParser(),
        legal=parser,
    )


def test_ogrn_hook_is_single_org_without_search() -> None:
    hook = classify_hook(OGRN)
    found = resolve_legal_orgs(hook, _card(), [])
    assert len(found) == 1
    assert found[0].ogrn == OGRN
    assert found[0].source_url == egrul_url(OGRN)


def test_ogrn_fills_egrul_skips_courts() -> None:
    html = FakeHtml(
        {
            egrul_url(OGRN): HtmlFetchResult(
                "ok", f"<egrul>{OGRN}</egrul>", egrul_url(OGRN)
            ),
        }
    )
    place = collect_place(_venue(), classify_hook(OGRN), _deps(html))
    assert place.egrul_registered_at.value == "2014-04-01"
    assert place.egrul_status.value == "действует"
    assert place.egrul_activity.value == "парикмахерские"
    assert place.egrul_status.source_url == egrul_url(OGRN)
    assert place.fedresurs.trust is Trust.MISSING
    assert place.kad.trust is Trust.MISSING
    assert all("fedresurs" not in item for item in html.calls)
    assert all("kad.arbitr" not in item for item in html.calls)
    assert place.legal_candidates == ()
    assert "founder" not in PlaceRecord.model_fields


def test_labeled_ogrn_reads_marker_not_bare_digits() -> None:
    assert labeled_ogrn(f"ОГРН {OGRN} в подвале") == OGRN
    assert labeled_ogrn("ОГРН/ОГРНИП 1147746349552") == OGRN
    assert labeled_ogrn("ОГРНИП 319774600285920") == "319774600285920"
    assert labeled_ogrn("ОГРНИП 320 774 600 402 589") == "320774600402589"
    assert labeled_ogrn("id 1495810359387 в скрипте") is None


def test_site_requisites_extract_reads_ip_block() -> None:
    body = "<p>ИП Гловский И.Д. ИНН 750101059837 ОГРНИП 319774600285920</p>"
    extract = site_requisites_extract(body, "319774600285920")
    assert extract is not None
    assert "Гловский" in str(extract.activity)
    assert "750101059837" in str(extract.activity)


def test_site_requisites_extract_kultura_oferta() -> None:
    body = (
        "<p>индивидуальный предприниматель Максимова Анжелика Джоновна "
        "ОГРНИП 320 774 600 402 589 ИНН 770 500 285 069</p>"
    )
    extract = site_requisites_extract(body, "320774600402589")
    assert extract is not None
    assert "Максимова" in str(extract.activity)
    assert "770500285069" in str(extract.activity)
    assert "ОГРНИП 320774600402589" in str(extract.activity)


def test_labeled_inn_skips_ogrnip_digits() -> None:
    body = "ОГРНИП 320 774 600 402 589 ИНН 770 500 285 069"
    assert labeled_inn(body) == "770500285069"


def test_site_labeled_ogrn_hits_egrul_when_maps_empty() -> None:
    site = "https://studio.example/place"
    html = FakeHtml({site: HtmlFetchResult("ok", f"<p>ОГРН {OGRN}</p>", site)})
    collect_place(_venue(), classify_hook(site), _deps(html))
    assert egrul_url(OGRN) in html.calls


def test_bare_digits_on_site_do_not_hit_egrul() -> None:
    site = "https://studio.example/place"
    html = FakeHtml(
        {site: HtmlFetchResult("ok", "<script>1495810359387</script>", site)}
    )
    collect_place(_venue(), classify_hook(site), _deps(html))
    assert egrul_url("1495810359387") not in html.calls


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


def test_twogis_ogrn_collects_that_org() -> None:
    html = FakeHtml({})
    twogis = _card(ogrn="2222222222222", url="https://2gis.example/firm/b")
    place = collect_place(
        _venue(),
        classify_hook("Вишня Таганская"),
        _deps(html, twogis=twogis),
    )
    assert place.legal_candidates == ()
    assert egrul_url("2222222222222") in html.calls
    assert place.egrul_status.trust is Trust.MISSING


def test_confirm_ogrn_collects_that_org() -> None:
    html = FakeHtml(
        {
            egrul_url("2222222222222"): HtmlFetchResult(
                "ok", "<egrul>2222222222222</egrul>", egrul_url("2222222222222")
            ),
        }
    )
    twogis = _card(ogrn="2222222222222", url="https://2gis.example/firm/b")
    extract = LegalExtract(
        registered_at="2018-01-01",
        status="действует",
        activity="маникюр",
        orgs=[],
    )
    deps = _deps(
        html,
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
    assert place.kad.trust is Trust.MISSING
    assert egrul_url("1111111111111") not in html.calls
    assert all("kad.arbitr" not in item for item in html.calls)


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
    assert all("fedresurs" not in item for item in html.calls)


def test_courts_are_not_requested() -> None:
    html = FakeHtml(
        {
            egrul_url(OGRN): HtmlFetchResult(
                "ok", f"<egrul>{OGRN}</egrul>", egrul_url(OGRN)
            ),
        }
    )
    place = collect_place(_venue(), classify_hook(OGRN), _deps(html))
    assert place.egrul_status.value == "действует"
    assert place.fedresurs.trust is Trust.MISSING
    assert place.kad.trust is Trust.MISSING
    assert all("fedresurs" not in item for item in html.calls)
    assert all("kad.arbitr" not in item for item in html.calls)


def test_app_asks_legal_confirm_and_shows_registry_rows() -> None:
    text = (ROOT / "src" / "salon_compare" / "app.py").read_text(encoding="utf-8")
    labels = (ROOT / "src" / "salon_compare" / "report.py").read_text(encoding="utf-8")
    assert "legal_candidates" in text
    assert "Подтвердить юрлицо" in text
    assert "ЕГРЮЛ" in labels
    assert "Федресурс" not in text
    assert "КАД" not in text
    assert "покупай" not in text.lower()


def test_readme_mentions_registries() -> None:
    text = (ROOT / "README.md").read_text(encoding="utf-8")
    assert "ЕГРЮЛ" in text or "егрюл" in text.lower()
    assert "Федресурс" in text or "федресурс" in text.lower()
