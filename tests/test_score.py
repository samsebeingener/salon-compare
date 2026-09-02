from __future__ import annotations

from datetime import date
from pathlib import Path

from salon_compare.collect import PlaceRecord, SourcedField, Trust
from salon_compare.score import score_place

ROOT = Path(__file__).resolve().parents[1]
AS_OF = date(2026, 9, 2)


def _gap() -> SourcedField:
    return SourcedField()


def _found(value: float | int | str, url: str = "https://example.test") -> SourcedField:
    return SourcedField(value=value, source_url=url, trust=Trust.FOUND)


def _place(**fields: SourcedField) -> PlaceRecord:
    payload = {
        "venue_id": "v1",
        "title": "Студия",
        "yandex_rating": _gap(),
        "yandex_review_count": _gap(),
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


def _block(score: object, name: str) -> object:
    for item in getattr(score, "blocks"):
        if getattr(item, "name") == name:
            return item
    raise AssertionError(name)


def test_two_ratings_without_freshness_skip_reputation() -> None:
    score = score_place(
        _place(yandex_rating=_found(4.9), twogis_rating=_found(4.1)),
        as_of=AS_OF,
    )
    rep = _block(score, "reputation")
    assert getattr(rep, "points") is None
    assert "не ясно какой свежее" in getattr(rep, "reason")
    assert score.index is None or score.index != 4.5


def test_single_high_rating_is_plus_two_not_three() -> None:
    score = score_place(
        _place(twogis_rating=_found(4.6), twogis_review_count=_found(80)),
        as_of=AS_OF,
    )
    rep = _block(score, "reputation")
    assert getattr(rep, "points") == 2
    assert score.index == round(100 * 0.4 * (2 / 3), 1)


def test_egrul_without_registries_skips_stability() -> None:
    score = score_place(
        _place(egrul_registered_at=_found("01.04.2014")),
        as_of=AS_OF,
    )
    stab = _block(score, "stability")
    assert getattr(stab, "points") is None
    assert "долгов нет" not in getattr(stab, "reason")


def test_open_registries_age_and_clean() -> None:
    score = score_place(
        _place(
            egrul_registered_at=_found("01.04.2014"),
            fedresurs=_found("не обнаружено"),
            kad=_found("не обнаружено"),
        ),
        as_of=AS_OF,
    )
    stab = _block(score, "stability")
    assert getattr(stab, "points") == 4


def test_empty_place_index_is_not_zero() -> None:
    score = score_place(_place(), as_of=AS_OF)
    assert score.index is None
    assert "не найден" in score.note.lower() or "не найдено" in score.note.lower()


def test_app_shows_index_not_buy_advice() -> None:
    text = (ROOT / "src" / "salon_compare" / "app.py").read_text(encoding="utf-8")
    lowered = text.lower()
    assert "индекс" in lowered
    assert "покупай" not in lowered
    assert "не совет" in lowered or "не инвестицион" in lowered
