from __future__ import annotations

from pathlib import Path

from salon_compare.checko import (
    checko_activity,
    checko_card_url,
    checko_efrsb,
    checko_fedresurs,
    checko_kad,
    checko_legal_address,
    checko_registered_at,
    checko_status,
)
from salon_compare.collect import (
    CollectDeps,
    HtmlExtract,
    HtmlFetchResult,
    Trust,
    collect_place,
)
from salon_compare.hooks import classify_hook
from salon_compare.intake import VenueCandidate
from salon_compare.legal import (
    LegalExtract,
    egrul_url,
    rbc_search_url,
)

ROOT = Path(__file__).resolve().parents[1]
OGRN = "1147746349552"
OGRNIP = "319774600285920"
INN_IP = "750101059837"

COMPANY_HTML = """
<h1>ООО "НОГТЕВОЙ СЕРВИС"</h1>
<p>Действующая компания ОГРН 1147746349552 ИНН 7720809493</p>
<p>Дата регистрации 1 апреля 2014 года</p>
<p>Вид деятельности Предоставление услуг парикмахерскими
и салонами красоты 96.02</p>
<p>Юридический адрес Предыдущий юридический адрес
111394, г. Москва, пр-кт Зелёный, д. 34
Нажмите для перехода к истории изменений
127055, г. Москва, ул. Новослободская, д. 20</p>
<p>Арбитражные дела 2</p>
<p>Федресурс не опубликовала ни одного сообщения</p>
<p>ЕФРСБ (реестр банкротств) Нет сообщений о банкротстве</p>
"""

PERSON_HTML = """
<h1>Гловский Игорь Дмитриевич</h1>
<p>Действующий ИП ОГРНИП 319774600285920 ИНН 750101059837</p>
<p>Дата регистрации 8 мая 2019 года</p>
<p>Основной вид деятельности Предоставление услуг
парикмахерскими и салонами красоты 96.02</p>
<p>Не входит в реестр банкротств</p>
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


class EmptyLegal:
    def parse_egrul(self, html: str) -> LegalExtract:
        del html
        return LegalExtract()

    def parse_fedresurs(self, html: str) -> str | None:
        del html
        return None

    def parse_kad(self, html: str) -> str | None:
        del html
        return None


def _deps(html: FakeHtml) -> CollectDeps:
    return CollectDeps(
        twogis=FakeMapApi(),
        html=html,
        parser=FakeMapsParser(),
        legal=EmptyLegal(),
        pacer=RecordingPacer(),
    )


def test_checko_urls_company_person_entrepreneur() -> None:
    assert checko_card_url(OGRN) == f"https://checko.ru/company/{OGRN}"
    assert checko_card_url(OGRNIP, INN_IP) == f"https://checko.ru/person/{INN_IP}"
    assert checko_card_url(OGRNIP) == f"https://checko.ru/entrepreneur/{OGRNIP}"


def test_checko_company_fields() -> None:
    assert checko_registered_at(COMPANY_HTML) == "01.04.2014"
    assert checko_status(COMPANY_HTML) == "действует"
    assert checko_activity(COMPANY_HTML) is not None
    assert "96.02" in str(checko_activity(COMPANY_HTML))
    addr = checko_legal_address(COMPANY_HTML)
    assert addr is not None
    assert addr.startswith("127055")
    assert "111394" not in addr
    assert checko_kad(COMPANY_HTML) == "есть дела (2)"
    assert checko_fedresurs(COMPANY_HTML) == "не обнаружено"
    assert checko_efrsb(COMPANY_HTML) == "не обнаружено"


def test_checko_person_ip_has_date_no_address_no_kad() -> None:
    assert checko_registered_at(PERSON_HTML) == "08.05.2019"
    assert checko_legal_address(PERSON_HTML) is None
    assert checko_kad(PERSON_HTML) is None
    assert checko_efrsb(PERSON_HTML) == "не обнаружено"


def test_collect_fills_checko_when_egrul_empty() -> None:
    url = checko_card_url(OGRN)
    html = FakeHtml(
        {
            egrul_url(OGRN): HtmlFetchResult("blocked", "captcha", egrul_url(OGRN)),
            rbc_search_url(OGRN): HtmlFetchResult("empty", "", rbc_search_url(OGRN)),
            url: HtmlFetchResult("ok", COMPANY_HTML, url),
        }
    )
    venue = VenueCandidate("ogrn:" + OGRN, OGRN, egrul_url(OGRN), "ogrn")
    place = collect_place(venue, classify_hook(OGRN), _deps(html))
    assert place.egrul_registered_at.value == "01.04.2014"
    assert place.egrul_registered_at.trust is Trust.WEAK
    assert place.egrul_registered_at.source_url == url
    assert place.kad.value == "есть дела (2)"
    assert place.kad.trust is Trust.WEAK
    assert place.fedresurs.value == "не обнаружено"
    assert place.efrsb.value == "не обнаружено"
    assert place.address.value is not None
    assert str(place.address.value).startswith("127055")
    assert "Юсупова" not in str(place.egrul_activity.value)


def test_readme_mentions_checko() -> None:
    text = (ROOT / "README.md").read_text(encoding="utf-8").lower()
    assert "checko.ru" in text
    assert "огрнип" in text or "person" in text
