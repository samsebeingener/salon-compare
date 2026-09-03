from __future__ import annotations

from datetime import date
from pathlib import Path

import pytest

from salon_compare.collect import PlaceRecord, SourcedField, Trust
from salon_compare.legal import LegalOrg
from salon_compare.llm import make_llm
from salon_compare.report import (
    MODEL_DISCLAIMER,
    SITE_ABOUT_PREVIEW,
    ModelVerdict,
    build_evidence_dossier,
    build_prompt,
    build_user_prompt,
    card_payload,
    footnote_map,
    mark_unreliable,
    parse_verdict,
    patch_field,
    table_cell,
    validate_verdict,
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
    prompt = build_prompt([row], as_of=AS_OF)
    lowered = prompt.lower()
    assert "вишня" in lowered
    assert "покупай" not in lowered
    assert "external_research" in lowered
    assert "trust" in lowered
    scored = score_place(row, as_of=AS_OF)
    assert scored.index is not None
    assert str(scored.index) in prompt


def test_evidence_dossier_includes_trust_and_sources() -> None:
    row = _place(
        twogis_rating=_found(4.6, "https://2gis.ru/firm/1"),
        title="Вишня",
    )
    dossier = build_evidence_dossier([row], as_of=AS_OF)
    meta = dossier["meta"]
    assert isinstance(meta, dict)
    assert meta.get("external_research") == []
    venues = dossier["venues"]
    assert isinstance(venues, list) and len(venues) == 1
    venue = venues[0]
    assert isinstance(venue, dict)
    evidence = venue["evidence"]
    assert isinstance(evidence, dict)
    rating = evidence["twogis_rating"]
    assert isinstance(rating, dict)
    assert rating["value"] == 4.6
    assert rating["trust"] == "found"
    assert rating["source_url"] == "https://2gis.ru/firm/1"
    assert "twogis_review_count" in evidence
    assert "twogis_review_count" in venue["missing_fields"]


def test_validate_verdict_rejects_unknown_index() -> None:
    row = _place(twogis_rating=_found(4.6), title="Вишня")
    scored = score_place(row, as_of=AS_OF)
    assert scored.index is not None
    verdict = ModelVerdict(
        interesting="А",
        why_better="x",
        breaks_if="y",
        compared_index=scored.index + 10,
    )
    assert validate_verdict(verdict, [row], as_of=AS_OF) is None


def test_validate_verdict_accepts_matching_index() -> None:
    row = _place(twogis_rating=_found(4.6), title="Вишня")
    scored = score_place(row, as_of=AS_OF)
    assert scored.index is not None
    verdict = ModelVerdict(
        interesting="А",
        why_better="x",
        breaks_if="y",
        compared_index=scored.index,
    )
    assert validate_verdict(verdict, [row], as_of=AS_OF) == verdict


def test_parse_verdict_strips_json_fence() -> None:
    raw = (
        '```json\n{"interesting":"А","why_better":"b",'
        '"breaks_if":"c","compared_index":1.0}\n```'
    )
    verdict = parse_verdict(raw)
    assert verdict is not None
    assert verdict.compared_index == 1.0


def test_user_prompt_mentions_dossie_structure() -> None:
    row = _place(twogis_rating=_found(4.6), title="Вишня")
    text = build_user_prompt(build_evidence_dossier([row], as_of=AS_OF))
    assert "Досье:" in text
    assert "compared_index" in text


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


def test_empty_patch_clears_field() -> None:
    row = _place(twogis_rating=_found(4.8))
    cleared = patch_field(row, "twogis_rating", "  ")
    assert cleared.twogis_rating.value is None
    assert cleared.twogis_rating.trust is Trust.MISSING


def test_unreliable_object_drops_index() -> None:
    row = mark_unreliable(_place(twogis_rating=_found(4.6)))
    assert row.unreliable is True
    score = score_place(row, as_of=AS_OF)
    assert score.index is None
    assert "недостоверн" in score.note.lower()


def test_table_cell_uses_shared_footnotes() -> None:
    shared = "https://2gis.ru/firm/1"
    left = _place(
        title="А",
        twogis_rating=_found(4.7, shared),
        hours=_found("пн-вс 10:00-22:00", shared),
        site_about=_found(
            "\n".join(["студия"] * 40), "https://pinklemon.example/about"
        ),
    )
    right = _place(
        venue_id="v2",
        title="Б",
        twogis_rating=_found(3.6, shared),
    )
    notes = footnote_map([left, right])
    assert notes[shared] == 1
    assert notes["https://pinklemon.example/about"] == 2
    assert table_cell(left, "twogis_rating", notes) == "4.7 [1]"
    assert table_cell(right, "twogis_rating", notes) == "3.6 [1]"
    assert table_cell(left, "hours", notes) == "пн-вс 10:00-22:00 [1]"
    about = table_cell(left, "site_about", notes)
    assert about.endswith("[2]")
    assert "http" not in about
    assert "\n" not in about
    assert len(about) <= SITE_ABOUT_PREVIEW + 4
    weak = patch_field(left, "twogis_rating", "4.9")
    weak_notes = footnote_map([weak])
    assert table_cell(weak, "twogis_rating", weak_notes) == "4.9 · слабо [1]"
    pending = _place(
        legal_candidates=(
            LegalOrg("1", "ООО А", "https://egrul.example/a"),
            LegalOrg("2", "ООО Б", "https://egrul.example/b"),
        )
    )
    legal_notes = footnote_map([pending])
    assert table_cell(pending, "egrul_status", legal_notes) == "уточните юрлицо [1][2]"


def test_app_shows_model_disclaimer_without_duplicate_cards() -> None:
    text = (ROOT / "src" / "salon_compare" / "app.py").read_text(encoding="utf-8")
    lowered = text.lower()
    assert "текст модели, не инвестиционный совет" in lowered
    assert MODEL_DISCLAIMER.lower() in lowered
    assert "покупай" not in lowered
    assert "недостоверн" in lowered
    assert "_show_cards" not in text
    assert "Индекс пояснение" not in text
    assert "_show_corrections" not in text
    assert "update_run" in text
    assert "@st.dialog" in text
    assert ":material/edit:" in text
    assert "footnote_map" in text
    assert "Источники" in text
    assert "importlib.reload" in text
    assert "cell_help" in text
