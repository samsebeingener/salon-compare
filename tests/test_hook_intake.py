from __future__ import annotations

from pathlib import Path

from salon_compare.hooks import HookKind, classify_hook
from salon_compare.intake import (
    IntakeStatus,
    VenueCandidate,
    candidate_label,
    resolve_intake,
)

ROOT = Path(__file__).resolve().parents[1]


class ScriptedResolver:
    def __init__(self, mapping: dict[str, list[VenueCandidate]]) -> None:
        self._mapping = mapping

    def resolve(self, hook: object) -> list[VenueCandidate]:
        key = getattr(hook, "normalized", str(hook))
        return list(self._mapping.get(key, []))


def test_classify_demo_triple() -> None:
    site = classify_hook("https://pinklemon-nails.ru/baumanskaya")
    assert site.kind is HookKind.WEBSITE
    assert classify_hook("Вишня Таганская").kind is HookKind.NAME
    assert classify_hook("1147746349552").kind is HookKind.OGRN


def test_classify_inn_maps_booking_and_free_text() -> None:
    assert classify_hook("7707083893").kind is HookKind.INN
    maps_yandex = classify_hook("https://yandex.ru/maps/org/123")
    assert maps_yandex.kind is HookKind.MAPS_LINK
    maps_2gis = classify_hook("https://2gis.ru/moscow/firm/123")
    assert maps_2gis.kind is HookKind.MAPS_LINK
    booking = classify_hook("https://n12345.yclients.com/company/1")
    assert booking.kind is HookKind.BOOKING_LINK
    blob = (
        "студия у метро рядом с пекарней на первой линии дома 15 корпус 2 после ремонта"
    )
    assert classify_hook(blob).kind is HookKind.FREE_TEXT


def test_need_three_hooks() -> None:
    outcome = resolve_intake(["сайт", "", "огрн"], ScriptedResolver({}))
    assert outcome.status is IntakeStatus.NEED_THREE


def test_ambiguous_candidates_keep_links_and_do_not_pick() -> None:
    hook = classify_hook("Вишня Таганская")
    resolver = ScriptedResolver(
        {
            hook.normalized: [
                VenueCandidate("a", "Вишня на Таганке", "https://yandex.ru/maps/org/a"),
                VenueCandidate("b", "Вишня другая", "https://2gis.ru/moscow/firm/b"),
            ]
        }
    )
    outcome = resolve_intake(
        [
            "https://pinklemon-nails.ru/baumanskaya",
            "Вишня Таганская",
            "1147746349552",
        ],
        resolver,
    )
    assert outcome.status is IntakeStatus.NEED_DISAMBIGUATION
    links = [c.source_url for slot in outcome.candidates_by_slot for c in slot]
    assert "https://yandex.ru/maps/org/a" in links
    assert "https://2gis.ru/moscow/firm/b" in links
    assert outcome.chosen_venues is None


def test_zero_candidates_need_disambiguation() -> None:
    outcome = resolve_intake(
        ["aaa", "bbb", "ccc"],
        ScriptedResolver({}),
    )
    assert outcome.status is IntakeStatus.NEED_DISAMBIGUATION
    assert outcome.chosen_venues is None


def test_duplicate_venues_ask_to_replace() -> None:
    same = VenueCandidate("one", "Одна точка", "https://example.com/one")
    other = VenueCandidate("two", "Другая", "https://example.com/two")
    pink = classify_hook("https://pinklemon-nails.ru/baumanskaya")
    ogrn = classify_hook("1147746349552")
    name = classify_hook("Вишня Таганская")
    resolver = ScriptedResolver(
        {
            pink.normalized: [same],
            ogrn.normalized: [same],
            name.normalized: [other],
        }
    )
    outcome = resolve_intake(
        [
            "https://pinklemon-nails.ru/baumanskaya",
            "Вишня Таганская",
            "1147746349552",
        ],
        resolver,
    )
    assert outcome.status is IntakeStatus.DUPLICATE_VENUES
    assert "https://example.com/one" in outcome.message
    assert outcome.chosen_venues is None


def test_ready_when_three_distinct_venues() -> None:
    pink = classify_hook("https://pinklemon-nails.ru/baumanskaya")
    name = classify_hook("Вишня Таганская")
    ogrn = classify_hook("1147746349552")
    resolver = ScriptedResolver(
        {
            pink.normalized: [
                VenueCandidate(
                    "1", "Pinklemon", "https://pinklemon-nails.ru/baumanskaya"
                )
            ],
            name.normalized: [
                VenueCandidate("2", "Вишня", "https://example.com/vishnya")
            ],
            ogrn.normalized: [
                VenueCandidate("3", "I LIKE NAILS", "https://example.com/ogrn")
            ],
        }
    )
    outcome = resolve_intake(
        [
            "https://pinklemon-nails.ru/baumanskaya",
            "Вишня Таганская",
            "1147746349552",
        ],
        resolver,
    )
    assert outcome.status is IntakeStatus.READY
    assert outcome.chosen_venues is not None
    assert len(outcome.chosen_venues) == 3
    assert {v.venue_id for v in outcome.chosen_venues} == {"1", "2", "3"}


def test_candidate_label_chain_includes_address() -> None:
    same_name = "I like nails, студия маникюра"
    first = VenueCandidate(
        "twogis:a",
        same_name,
        "https://2gis.ru/firm/a",
        "twogis",
        "Москва, Бауманская",
    )
    second = VenueCandidate(
        "twogis:b",
        same_name,
        "https://2gis.ru/firm/b",
        "twogis",
        "Москва, Таганская",
    )
    assert "Москва, Бауманская" in candidate_label(first)
    assert "https://2gis.ru/firm/a" in candidate_label(first)
    assert "Москва, Таганская" in candidate_label(second)
    assert "https://2gis.ru/firm/b" in candidate_label(second)


def test_candidate_label_without_address_keeps_title_and_link() -> None:
    item = VenueCandidate(
        "twogis:a",
        "I like nails, студия маникюра",
        "https://2gis.ru/firm/a",
        "twogis",
    )
    assert candidate_label(item) == (
        "I like nails, студия маникюра — https://2gis.ru/firm/a"
    )


def test_app_accepts_three_hooks_without_report() -> None:
    text = (ROOT / "src" / "salon_compare" / "app.py").read_text(encoding="utf-8")
    lowered = text.lower()
    assert "зацепк" in lowered
    assert text.count("st.text_input") >= 3
    assert "сравнительн" not in lowered
