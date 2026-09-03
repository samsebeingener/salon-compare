from __future__ import annotations

from datetime import date
from pathlib import Path

import pytest

from salon_compare.collect import PlaceRecord, SourcedField, Trust
from salon_compare.llm import make_llm
from salon_compare.report import (
    MODEL_DISCLAIMER,
    build_prompt,
    card_payload,
    mark_unreliable,
    parse_verdict,
    patch_field,
)
from salon_compare.score import score_place

ROOT = Path(__file__).resolve().parents[1]
AS_OF = date(2026, 9, 2)


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


def test_empty_json_is_not_a_verdict() -> None:
    assert parse_verdict("") is None
    assert parse_verdict("{}") is None
    assert parse_verdict("{") is None


def test_extra_fields_are_ignored() -> None:
    raw = (
        '{"interesting":"А","why_better":"рейтинг",'
        '"breaks_if":"нет отзывов","junk":true}'
    )
    verdict = parse_verdict(raw)
    assert verdict is not None
    assert verdict.interesting == "А"
    assert verdict.why_better == "рейтинг"
    assert verdict.breaks_if == "нет отзывов"
    assert not hasattr(verdict, "junk") or getattr(verdict, "junk", None) is None


def test_index_string_becomes_float() -> None:
    verdict = parse_verdict(
        '{"interesting":"А","why_better":"x","breaks_if":"y","compared_index":"26.7"}'
    )
    assert verdict is not None
    assert verdict.compared_index == 26.7


def test_no_llm_key_returns_empty(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("LLM_API_KEY", raising=False)
    monkeypatch.delenv("LLM_BASE_URL", raising=False)
    monkeypatch.delenv("LLM_MODEL", raising=False)
    assert make_llm().complete("любой промпт") == ""


def test_prompt_uses_scores_not_buy_advice() -> None:
    row = _place(twogis_rating=_found(4.6), title="Вишня")
    prompt = build_prompt([row])
    lowered = prompt.lower()
    assert "вишня" in lowered
    assert "покупай" not in lowered
    scored = score_place(row, as_of=AS_OF)
    assert scored.index is not None
    assert str(scored.index) in prompt


def test_card_lists_missing_fields() -> None:
    row = _place(twogis_rating=_found(4.6), title="Вишня")
    card = card_payload(row, score_place(row, as_of=AS_OF))
    assert card["title"] == "Вишня"
    assert "Яндекс рейтинг" not in card["missing"]
    found = [item for item in card["fields"] if item["label"] == "2ГИС рейтинг"]
    assert found[0]["value"] == 4.6
    assert found[0]["source_url"] == "https://example.test"


def test_patch_field_is_weak_human_edit() -> None:
    row = _place(twogis_rating=_found(3.2))
    patched = patch_field(row, "twogis_rating", "4.8")
    assert patched.twogis_rating.value == 4.8
    assert patched.twogis_rating.trust is Trust.WEAK
    assert patched.twogis_rating.source_url == "правка человека"
    before = score_place(row, as_of=AS_OF).index
    after = score_place(patched, as_of=AS_OF).index
    assert after != before


def test_unreliable_object_drops_index() -> None:
    row = mark_unreliable(_place(twogis_rating=_found(4.6)))
    assert row.unreliable is True
    score = score_place(row, as_of=AS_OF)
    assert score.index is None
    assert "недостоверн" in score.note.lower()


def test_app_shows_model_disclaimer_without_duplicate_cards() -> None:
    text = (ROOT / "src" / "salon_compare" / "app.py").read_text(encoding="utf-8")
    lowered = text.lower()
    assert "текст модели, не инвестиционный совет" in lowered
    assert MODEL_DISCLAIMER.lower() in lowered
    assert "покупай" not in lowered
    assert "недостоверн" in lowered
    assert "_show_cards" not in text
    assert "Индекс пояснение" not in text
