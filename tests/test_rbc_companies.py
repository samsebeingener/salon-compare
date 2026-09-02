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
    rbc_company_snippet,
    rbc_search_url,
)

ROOT = Path(__file__).resolve().parents[1]
OGRN = "1147746349552"
RBC = "https://companies.rbc.ru/search/?query=1147746349552"

RBC_CARD = """
<div class="company-card info-card">
<span class="company-status-badge company-status-badge--green">Действует</span>
<a class="company-name-highlight" href="https://companies.rbc.ru/id/1147746349552-i-like-nails/">I LIKE NAILS</a>
<p>ОБЩЕСТВО С ОГРАНИЧЕННОЙ ОТВЕТСТВЕННОСТЬЮ «НОГТЕВОЙ СЕРВИС»</p>
<div class="category-breadcrumb">
<span class="category-breadcrumb__item">Бытовые услуги</span>
<span class="category-breadcrumb__item">Парикмахерские и салоны красоты</span>
</div>
<p class="company-card__info"><span>Генеральный Директор:</span>Сулейманова Гульнара Маратовна</p>
<p class="company-card__info"><span>Дата регистрации:</span>01.04.2014</p>
<p class="company-card__info"><span>ОГРН:</span><em>1147746349552</em></p>
</div>
</main>
"""

RBC_HEADING_ONLY = """
<h3>Результаты по запросу &laquo;1147746349552&raquo; <small>0</small></h3>
<div id="common-react-root"></div>
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
        yandex=FakeMapApi(),
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


def test_official_egrul_skips_rbc() -> None:
    html = FakeHtml(
        {
            egrul_url(OGRN): HtmlFetchResult(
                "ok", f"<egrul>{OGRN} регистрация</egrul>", egrul_url(OGRN)
            ),
        }
    )
    collect_place(_venue(), classify_hook(OGRN), _deps(html))
    assert RBC not in html.calls


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
