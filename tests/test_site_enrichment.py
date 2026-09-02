from __future__ import annotations

from salon_compare.legal import labeled_inn, labeled_ogrn
from salon_compare.site_enrichment import (
    brand_slug,
    ddg_site_search_url,
    ddg_site_urls,
    domain_probe_urls,
    internal_legal_links,
    page_matches_address,
    rbc_company_card_url,
    rbc_website,
)

OGRN = "1147746349552"


def test_ddg_site_search_url_includes_title_and_address() -> None:
    url = ddg_site_search_url("Вишня Таганская", "Таганская улица, 3")
    assert "q=" in url
    assert "duckduckgo.com" in url


def test_ddg_site_urls_skips_aggregators() -> None:
    html = """
    <a class="result__a" href="https://yandex.ru/maps/org/vishnya/1">maps</a>
    <a class="result__a" href="https://vishnyasalon.ru/">studio</a>
    """
    assert ddg_site_urls(html) == ["https://vishnyasalon.ru"]


def test_internal_legal_links_same_host_only() -> None:
    html = """
    <a href="/politica">pol</a>
    <a href="https://other.ru/privacy">x</a>
    <a href="/contacts">c</a>
    """
    links = internal_legal_links(html, "https://vishnyasalon.ru/")
    assert "https://vishnyasalon.ru/politica" in links
    assert "https://vishnyasalon.ru/contacts" in links
    assert all("other.ru" not in item for item in links)


def test_rbc_company_card_url_from_search() -> None:
    html = (
        f'<a href="https://companies.rbc.ru/id/{OGRN}-i-like-nails/">I LIKE NAILS</a>'
    )
    assert rbc_company_card_url(html, OGRN) == (
        f"https://companies.rbc.ru/id/{OGRN}-i-like-nails/"
    )


def test_rbc_website_from_id_page() -> None:
    html = """
    <div>Сайт</div><div class="company-detail-block__item-inner-container">
    <a href="http://ilike-nails.ru" target="_blank">http://ilike-nails.ru</a>
    </div>
    """
    assert rbc_website(html) == "http://ilike-nails.ru"


def test_labeled_inn_requires_label() -> None:
    assert labeled_inn("<p>ИНН: 7720809493</p>") == "7720809493"
    assert labeled_inn("<p>7720809493</p>") is None


def test_brand_slug_vishnya() -> None:
    assert brand_slug("Вишня, маникюрный салон") == "vishnya"
    assert brand_slug("Вишня Таганская") == "vishnya"


def test_domain_probe_urls_vishnya() -> None:
    assert "https://vishnyasalon.ru" in domain_probe_urls("Вишня, маникюрный салон")


def test_page_matches_address_taganskaya() -> None:
    html = "<p>ул. Таганская, 3</p>"
    assert page_matches_address(html, "Таганская улица, 3")
    assert not page_matches_address("<p>Казань</p>", "Таганская улица, 3")


def test_labeled_ogrn_still_requires_label() -> None:
    assert labeled_ogrn("<p>ОГРН: 1147746349552</p>") == OGRN
    assert labeled_ogrn("<p>1147746349552</p>") is None
    assert labeled_ogrn("<p>ОГРНИП 319774600285920</p>") == "319774600285920"
    assert labeled_ogrn("<p>ОГРНИП 320 774 600 402 589</p>") == "320774600402589"


def test_labeled_inn_prefers_twelve_digits() -> None:
    assert labeled_inn("<p>ИНН: 750101059837</p>") == "750101059837"


def test_internal_legal_links_includes_payment() -> None:
    html = '<a href="/payment">оплата</a><a href="/politica">pol</a>'
    links = internal_legal_links(html, "https://vishnyasalon.ru")
    assert "https://vishnyasalon.ru/payment" in links


def test_domain_probe_compound_kultura() -> None:
    urls = domain_probe_urls("Культура маникюра Ани Хилькевич")
    assert "https://kulturamanicura.ru" in urls


def test_internal_legal_links_includes_dogovor() -> None:
    html = '<a href="/dogovor-oferty">оферта</a>'
    links = internal_legal_links(html, "https://kulturamanicura.ru")
    assert "https://kulturamanicura.ru/dogovor-oferty" in links
