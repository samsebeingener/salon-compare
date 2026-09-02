from datetime import date
from pathlib import Path

import pytest

from salon_compare.collect import PlaceRecord, SourcedField, Trust
from salon_compare.html_parse import OpenHtmlParser
from salon_compare.llm import LlmUsage, estimate_usd, usage_from_response
from salon_compare.score import score_place
from salon_compare.store import load_run, load_run_usage, save_run, save_run_usage

ROOT = Path(__file__).resolve().parents[1]
AS_OF = date(2026, 9, 2)

HTML_OK = """
<html>
<script type="application/ld+json">
{"@type":"Review","datePublished":"2026-08-15"}
</script>
<div>График работы: пн-вс 10:00–21:00</div>
<div>положительных 40</div>
<div>отрицательных 3</div>
</html>
"""

HTML_RATING_ONLY = """
<html><div class="rating">4.6</div></html>
"""

HTML_JSON_LD = """
<html>
<script type="application/ld+json">
{
  "@type": "LocalBusiness",
  "description": "Студия у метро",
  "aggregateRating": {
    "@type": "AggregateRating",
    "ratingValue": 4.6,
    "reviewCount": 80
  },
  "address": {
    "@type": "PostalAddress",
    "streetAddress": "Таганская улица, 1"
  }
}
</script>
</html>
"""

HTML_ABOUT = """
<html>
<h2>О нас</h2>
<p>Студия маникюра на Таганке, работаем с 2018 года.</p>
</html>
"""


def _gap() -> SourcedField:
    return SourcedField()


def _found(value: float | int | str, url: str = "https://example.test") -> SourcedField:
    return SourcedField(value=value, source_url=url, trust=Trust.FOUND)


def _place(**fields: object) -> PlaceRecord:
    payload: dict[str, object] = {
        "venue_id": "v1",
        "title": "Студия",
        "twogis_rating": _gap(),
        "twogis_review_count": _gap(),
        "address": _gap(),
        "neighbor_count": _gap(),
        "neighbor_vs": _gap(),
        "site_about": _gap(),
        "egrul_registered_at": _gap(),
        "egrul_status": _gap(),
        "egrul_activity": _gap(),
        "fedresurs": _gap(),
        "kad": _gap(),
    }
    payload.update(fields)
    return PlaceRecord.model_validate(payload)


def test_open_html_parser_reads_hours_review_and_plus_minus() -> None:
    extract = OpenHtmlParser().parse(HTML_OK)
    assert extract.last_review == "2026-08-15"
    assert extract.hours is not None
    assert "10:00" in extract.hours
    assert extract.plus_minus is not None
    assert "40" in extract.plus_minus
    assert "3" in extract.plus_minus


def test_open_html_parser_skips_invented_plus_minus() -> None:
    extract = OpenHtmlParser().parse(HTML_RATING_ONLY)
    assert extract.plus_minus is None
    assert extract.last_review is None
    assert extract.rating is None
    assert extract.about is None


def test_open_html_parser_reads_json_ld_about_rating_address() -> None:
    extract = OpenHtmlParser().parse(HTML_JSON_LD)
    assert extract.about is not None
    assert "Студия у метро" in extract.about
    assert extract.rating == 4.6
    assert extract.review_count == 80
    assert extract.address is not None
    assert "Таганская" in extract.address


def test_open_html_parser_about_from_heading() -> None:
    extract = OpenHtmlParser().parse(HTML_ABOUT)
    assert extract.about is not None
    assert "Студия маникюра на Таганке" in extract.about
    assert len(extract.about) <= 280


def test_high_rating_with_reviews_in_90_days_is_plus_three() -> None:
    score = score_place(
        _place(
            twogis_rating=_found(4.8),
            twogis_review_count=_found(80),
            twogis_last_review=_found("2026-08-01"),
            twogis_reviews_90d=_found("да"),
        ),
        as_of=AS_OF,
    )
    rep = next(item for item in score.blocks if item.name == "reputation")
    assert rep.points == 3


def test_usage_tokens_without_rate_have_no_usd() -> None:
    usage = usage_from_response(
        {"usage": {"prompt_tokens": 100, "completion_tokens": 50}}
    )
    assert usage.total_tokens == 150
    assert estimate_usd(usage) is None


def test_openrouter_usage_includes_cost_and_total() -> None:
    usage = usage_from_response(
        {
            "usage": {
                "prompt_tokens": 194,
                "completion_tokens": 2,
                "total_tokens": 196,
                "cost": 0.95,
            }
        }
    )
    assert usage.total_tokens == 196
    assert usage.cost == 0.95
    assert estimate_usd(usage) == 0.95


def test_usage_cost_accepts_float_token_counts() -> None:
    usage = usage_from_response(
        {"usage": {"prompt_tokens": 10.0, "completion_tokens": 5.0, "cost": 0.0015}}
    )
    assert usage.prompt_tokens == 10
    assert usage.completion_tokens == 5
    assert estimate_usd(usage) == 0.0015


def test_usage_with_rates_is_linear() -> None:
    usage = LlmUsage(prompt_tokens=1_000_000, completion_tokens=1_000_000)
    usd = estimate_usd(usage, prompt_rate=1.0, completion_rate=2.0)
    assert usd == 3.0


def test_openrouter_cost_beats_env_rates(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LLM_USD_PER_1M_PROMPT", "999")
    monkeypatch.setenv("LLM_USD_PER_1M_COMPLETION", "999")
    usage = usage_from_response(
        {
            "usage": {
                "prompt_tokens": 194,
                "completion_tokens": 2,
                "total_tokens": 196,
                "cost": 0.95,
            }
        }
    )
    assert estimate_usd(usage) == 0.95


def test_sqlite_keeps_openrouter_cost(tmp_path: Path) -> None:
    path = tmp_path / "usage.sqlite"
    run_id = save_run([_place()], path)
    save_run_usage(
        run_id,
        LlmUsage(
            prompt_tokens=194,
            completion_tokens=2,
            total_tokens=196,
            cost=0.95,
        ),
        path,
    )
    loaded = load_run_usage(run_id, path)
    assert loaded is not None
    assert loaded.total_tokens == 196
    assert loaded.cost == 0.95
    assert estimate_usd(loaded) == 0.95


def test_old_sqlite_list_payload_still_loads(tmp_path: Path) -> None:
    path = tmp_path / "old.sqlite"
    run_id = save_run([_place()], path)
    loaded = load_run(run_id, path)
    assert loaded is not None
    assert loaded[0].title == "Студия"
    assert load_run_usage(run_id, path) is None


def test_app_shows_usage_and_new_fields() -> None:
    text = (ROOT / "src" / "salon_compare" / "app.py").read_text(encoding="utf-8")
    lowered = text.lower()
    assert "токен" in lowered
    assert "90" in text
    assert "OpenHtmlParser" in text
    assert "покупай" not in lowered


def test_readme_no_longer_lists_freshness_as_hole() -> None:
    text = (ROOT / "README.md").read_text(encoding="utf-8").lower()
    assert "дырки этой сдачи" not in text
    assert "90" in text
    assert "токен" in text
