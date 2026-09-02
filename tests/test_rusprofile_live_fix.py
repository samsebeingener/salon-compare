from __future__ import annotations

from pathlib import Path
from urllib.parse import parse_qs, urlparse

import pytest

from salon_compare.html_fetch import HttpxHtmlFetcher, classify_fetch
from salon_compare.legal import MarkerLegalParser, ddg_rusprofile_url

ROOT = Path(__file__).resolve().parents[1]
OGRN = "1147746349552"


class _FakeResponse:
    def __init__(self, status_code: int, text: str, url: str) -> None:
        self.status_code = status_code
        self.text = text
        self.url = url


def test_ddg_html_search_posts_query(monkeypatch: pytest.MonkeyPatch) -> None:
    posted: list[tuple[str, dict[str, str]]] = []

    def fake_post(url: str, **kwargs: object) -> _FakeResponse:
        data = kwargs.get("data")
        assert isinstance(data, dict)
        posted.append((url, data))
        return _FakeResponse(200, '<a href="https://www.rusprofile.ru/id/7301223">x</a>', url)

    def fake_get(url: str, **kwargs: object) -> _FakeResponse:
        del kwargs
        raise AssertionError(f"GET must not run for DuckDuckGo: {url}")

    monkeypatch.setattr("salon_compare.html_fetch.httpx.post", fake_post)
    monkeypatch.setattr("salon_compare.html_fetch.httpx.get", fake_get)
    page = HttpxHtmlFetcher().get(ddg_rusprofile_url(OGRN))
    assert page.status == "ok"
    assert posted, "expected POST"
    post_url, data = posted[0]
    assert "html.duckduckgo.com" in post_url
    assert "html" in urlparse(post_url).path
    expected_q = parse_qs(urlparse(ddg_rusprofile_url(OGRN)).query)["q"][0]
    assert data["q"] == expected_q


def test_has_captcha_json_is_not_blocked_page() -> None:
    html = (
        f'<html>Действующая организация ОГРН {OGRN} '
        '"has_captcha":true,"disable_captcha":false</html>'
    )
    assert classify_fetch(200, html) == "ok"


def test_smartcaptcha_still_blocked() -> None:
    assert classify_fetch(200, "<html>smartcaptcha</html>") == "blocked"
    assert classify_fetch(200, "<form>captcha input</form>") == "blocked"


def test_acting_org_not_killed_by_related_liquidated() -> None:
    html = """
    <span>Действующая организация</span>
    Дата регистрации 01.04.2014
    <a>оквэд меню flexpoint</a>
    <span>Основной вид деятельности</span> Предоставление услуг парикмахерскими
    Выявлены 4 действующие и 6 ликвидированных связанных организаций
    """
    extract = MarkerLegalParser().parse_egrul(html)
    assert extract.status == "действует"
    assert extract.registered_at == "01.04.2014"
    assert extract.activity is not None
    assert "парикмахерскими" in extract.activity.lower()
    assert "flexpoint" not in extract.activity.lower()


def test_readme_records_post_and_false_captcha() -> None:
    text = (ROOT / "README.md").read_text(encoding="utf-8").lower()
    assert "post" in text
    assert "has_captcha" in text or "ложн" in text
