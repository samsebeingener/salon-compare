from __future__ import annotations

from salon_compare.collect import PlaceRecord, SourcedField, Trust
from salon_compare.llm import LlmUsage
from salon_compare.llm_extract import extract_missing, gaps_for


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


class FakeLlm:
    def __init__(self, raw: str) -> None:
        self.raw = raw
        self.calls = 0
        self._usage = LlmUsage(prompt_tokens=10, completion_tokens=5, total_tokens=15)

    def complete(self, prompt: str, *, system: str | None = None) -> str:
        del prompt, system
        self.calls += 1
        return self.raw

    def last_usage(self) -> LlmUsage:
        return self._usage

    def last_error(self) -> str | None:
        return None


def test_missing_site_about_becomes_weak() -> None:
    row = _place()
    assert "site_about" in gaps_for(row)
    llm = FakeLlm('{"site_about": "Студия с 2014"}')
    filled, usage = extract_missing(row, llm, "на сайте: студия с 2014")
    assert llm.calls == 1
    assert usage.total_tokens == 15
    assert filled.site_about.value == "Студия с 2014"
    assert filled.site_about.trust is Trust.WEAK
    assert filled.site_about.source_url == "модель"
    assert filled.egrul_activity.trust is Trust.MISSING


def test_bad_json_leaves_missing() -> None:
    row = _place()
    llm = FakeLlm("{")
    filled, usage = extract_missing(row, llm, "любой контекст")
    assert llm.calls == 1
    assert usage.total_tokens == 15
    assert filled.site_about.trust is Trust.MISSING
    assert filled.site_about.value is None
    assert filled.egrul_activity.trust is Trust.MISSING


def test_no_gaps_does_not_call_llm() -> None:
    row = _place(
        site_about=_found("Уже есть"),
        egrul_activity=_found("парикмахерские"),
    )
    assert gaps_for(row) == []
    llm = FakeLlm('{"site_about": "нельзя"}')
    filled, usage = extract_missing(row, llm, "шум")
    assert llm.calls == 0
    assert usage == LlmUsage()
    assert filled.site_about.value == "Уже есть"
    assert filled.site_about.trust is Trust.FOUND
    assert filled.egrul_activity.trust is Trust.FOUND
