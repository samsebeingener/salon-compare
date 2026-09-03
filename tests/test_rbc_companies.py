from __future__ import annotations

from pathlib import Path

from salon_compare.collect import (
    CollectDeps,
    HtmlExtract,
    HtmlFetchResult,
    PlaceRecord,
    Trust,
    collect_place,
)
from salon_compare.hooks import classify_hook
from salon_compare.intake import VenueCandidate
from salon_compare.legal import (
    LegalExtract,
    MarkerLegalParser,
    ddg_rusprofile_url,
    egrul_url,
    rbc_brand_names,
    rbc_company_snippet,
    rbc_search_url,
)
from salon_compare.site_enrichment import rbc_company_card_url

ROOT = Path(__file__).resolve().parents[1]
OGRN = "1147746349552"
RBC = "https://companies.rbc.ru/search/?query=1147746349552"

RBC_CARD = """
<div class="company-card info-card">
<span class="company-status-badge company-status-badge--green">Действует</span>
<a class="company-name-highlight"
 href="https://companies.rbc.ru/id/1147746349552-i-like-nails/">I LIKE NAILS</a>
<p>ОБЩЕСТВО С ОГРАНИЧЕННОЙ ОТВЕТСТВЕННОСТЬЮ «НОГТЕВОЙ СЕРВИС»</p>
<div class="category-breadcrumb">
<span class="category-breadcrumb__item">Бытовые услуги</span>
<span class="category-breadcrumb__item">Парикмахерские и салоны красоты</span>
</div>
<p class="company-card__info"><span>Генеральный Директор:</span>
Сулейманова Гульнара Маратовна</p>
<p class="company-card__info"><span>Дата регистрации:</span>01.04.2014</p>
<p class="company-card__info"><span>ОГРН:</span><em>1147746349552</em></p>
</div>
</main>
"""

RBC_HEADING_ONLY = """
<h3>Результаты по запросу &laquo;1147746349552&raquo; <small>0</small></h3>
<div id="common-react-root"></div>
"""

OGRNIP = "319774600285920"
RBC_IP_HREF = (
    "https://companies.rbc.ru/persons/ogrnip/319774600285920-glovskij-igor-dmitrievich/"
)
RBC_IP_CARD = f"""
<div class="company-card info-card">
<span class="company-status-badge company-status-badge--green">Действует</span>
<a class="company-name-highlight" href="{RBC_IP_HREF}">ИП Гловский Игорь Дмитриевич</a>
<p class="company-card__info"><span>Дата регистрации:</span>08.05.2019</p>
<p class="company-card__info"><span>ОГРНИП:</span><em>{OGRNIP}</em></p>
<div class="category-breadcrumb">
<span class="category-breadcrumb__item">Парикмахерские и салоны красоты</span>
</div>
</div>
"""


class RecordingPacer:
    def wait(self) -> None:
        return None


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
            registered_at="01.04.2014",
            status="действует",
            activity="парикмахерские",
        )

    def parse_fedresurs(self, html: str) -> str | None:
        del html
        return None

    def parse_kad(self, html: str) -> str | None:
        del html
        return None


def _venue() -> VenueCandidate:
    return VenueCandidate("p1", "Точка", "https://example.com/place")


def _deps(
    html: FakeHtml,
    legal: FakeLegalParser | MarkerLegalParser | None = None,
) -> CollectDeps:
    return CollectDeps(
        twogis=FakeMapApi(),
        html=html,
        parser=FakeMapsParser(),
        legal=legal or FakeLegalParser(),
        pacer=RecordingPacer(),
    )


def test_rbc_search_url_puts_ogrn_in_query() -> None:
    assert rbc_search_url(OGRN) == RBC
    assert "query=" in rbc_search_url(OGRN)


def test_rbc_snippet_needs_card_not_heading() -> None:
    assert rbc_company_snippet(RBC_CARD, OGRN) is not None
    assert OGRN in (rbc_company_snippet(RBC_CARD, OGRN) or "")
    assert rbc_company_snippet(RBC_HEADING_ONLY, OGRN) is None


def test_rbc_brand_name_from_highlight_not_generic_legal_phrase() -> None:
    names = rbc_brand_names(RBC_CARD, OGRN)
    assert names == ["I LIKE NAILS"]
    assert rbc_brand_names(RBC_HEADING_ONLY, OGRN) == []


def test_egrul_empty_fills_weak_from_rbc() -> None:
    html = FakeHtml(
        {
            egrul_url(OGRN): HtmlFetchResult("blocked", "captcha", egrul_url(OGRN)),
            RBC: HtmlFetchResult("ok", RBC_CARD, RBC),
        }
    )
    place = collect_place(_venue(), classify_hook(OGRN), _deps(html))
    assert place.egrul_status.value == "действует"
    assert place.egrul_registered_at.value == "01.04.2014"
    assert place.egrul_status.source_url == RBC
    assert place.egrul_status.trust is Trust.WEAK
    assert place.fedresurs.trust is Trust.MISSING
    assert ddg_rusprofile_url(OGRN) not in html.calls
    assert not any("rusprofile.ru/id/" in item for item in html.calls)


def test_rbc_heading_falls_through_without_filling() -> None:
    ddg = ddg_rusprofile_url(OGRN)
    html = FakeHtml(
        {
            egrul_url(OGRN): HtmlFetchResult("empty", "", egrul_url(OGRN)),
            RBC: HtmlFetchResult("ok", RBC_HEADING_ONLY, RBC),
            ddg: HtmlFetchResult("blocked", "captcha", ddg),
        }
    )
    place = collect_place(_venue(), classify_hook(OGRN), _deps(html))
    assert place.egrul_status.trust is Trust.MISSING
    assert RBC in html.calls
    assert ddg in html.calls


def test_official_egrul_skips_rbc_for_fields() -> None:
    html = FakeHtml(
        {
            egrul_url(OGRN): HtmlFetchResult(
                "ok", f"<egrul>{OGRN} регистрация</egrul>", egrul_url(OGRN)
            ),
        }
    )
    place = collect_place(_venue(), classify_hook(OGRN), _deps(html))
    assert place.egrul_status.trust is Trust.FOUND
    assert place.egrul_status.source_url == egrul_url(OGRN)


def test_rbc_html_does_not_copy_director_name() -> None:
    html = FakeHtml(
        {
            egrul_url(OGRN): HtmlFetchResult("empty", "", egrul_url(OGRN)),
            RBC: HtmlFetchResult("ok", RBC_CARD, RBC),
        }
    )
    deps = _deps(html, legal=MarkerLegalParser())
    place = collect_place(_venue(), classify_hook(OGRN), deps)
    assert place.egrul_status.value == "действует"
    assert place.egrul_registered_at.value == "01.04.2014"
    assert place.egrul_activity.value is not None
    assert "Парикмахерские" in str(place.egrul_activity.value)
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


def test_readme_mentions_rbc_search() -> None:
    text = (ROOT / "README.md").read_text(encoding="utf-8").lower()
    assert "companies.rbc.ru" in text
    assert "query" in text
    assert "ogrnip" in text or "огрнип" in text


def test_rbc_ip_snippet_and_brand_from_persons_href() -> None:
    assert rbc_company_snippet(RBC_IP_CARD, OGRNIP) is not None
    assert rbc_company_card_url(RBC_IP_CARD, OGRNIP) == RBC_IP_HREF
    names = rbc_brand_names(RBC_IP_CARD, OGRNIP)
    assert "ИП Гловский Игорь Дмитриевич" in names
    assert "Гловский Игорь Дмитриевич" in names


def test_egrul_empty_fills_weak_from_rbc_ogrnip() -> None:
    search = rbc_search_url(OGRNIP)
    html = FakeHtml(
        {
            egrul_url(OGRNIP): HtmlFetchResult("blocked", "captcha", egrul_url(OGRNIP)),
            search: HtmlFetchResult("ok", RBC_IP_CARD, search),
        }
    )
    venue = VenueCandidate("ogrn:" + OGRNIP, OGRNIP, egrul_url(OGRNIP), "ogrn")
    deps = _deps(html, legal=MarkerLegalParser())
    place = collect_place(venue, classify_hook(OGRNIP), deps)
    assert place.egrul_status.value == "действует"
    assert place.egrul_registered_at.value == "08.05.2019"
    assert place.egrul_status.source_url == search
    assert place.egrul_status.trust is Trust.WEAK
    assert "Парикмахерские" in str(place.egrul_activity.value)
    assert ddg_rusprofile_url(OGRNIP) not in html.calls


def test_egrul_fills_from_rbc_ogrnip_card_when_search_has_only_href() -> None:
    search = rbc_search_url(OGRNIP)
    listing = f'<a href="{RBC_IP_HREF}">ИП</a>'
    html = FakeHtml(
        {
            egrul_url(OGRNIP): HtmlFetchResult("blocked", "captcha", egrul_url(OGRNIP)),
            search: HtmlFetchResult("ok", listing, search),
            RBC_IP_HREF: HtmlFetchResult("ok", RBC_IP_CARD, RBC_IP_HREF),
        }
    )
    venue = VenueCandidate("ogrn:" + OGRNIP, OGRNIP, egrul_url(OGRNIP), "ogrn")
    deps = _deps(html, legal=MarkerLegalParser())
    place = collect_place(venue, classify_hook(OGRNIP), deps)
    assert place.egrul_status.source_url == RBC_IP_HREF
    assert place.egrul_status.trust is Trust.WEAK
    assert RBC_IP_HREF in html.calls
