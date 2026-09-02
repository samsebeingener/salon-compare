from __future__ import annotations

from pathlib import Path

from salon_compare.hooks import classify_hook, search_query
from salon_compare.intake import (
    IntakeStatus,
    VenueCandidate,
    apply_slot_choices,
    resolve_intake,
)
from salon_compare.maps_parse import candidates_from_twogis_items, item_by_id
from salon_compare.resolver import MapsSearchResolver

ROOT = Path(__file__).resolve().parents[1]

PINK = "https://pinklemon-nails.ru/baumanskaya"
VISHNYA = "Вишня Таганская"
OGRN = "1147746349552"


class FakeCatalog:
    def __init__(self, mapping: dict[str, list[VenueCandidate]]) -> None:
        self.mapping = mapping
        self.queries: list[str] = []

    def search(self, query: str) -> list[VenueCandidate]:
        self.queries.append(query)
        return list(self.mapping.get(query, []))


def test_search_query_uses_domain_and_digits() -> None:
    assert search_query(classify_hook(PINK)) == "pinklemon-nails.ru"
    assert search_query(classify_hook(OGRN)) == OGRN
    assert search_query(classify_hook(VISHNYA)) == VISHNYA


def test_two_map_cards_ask_confirm_not_ready() -> None:
    pink_hook = classify_hook(PINK)
    name_hook = classify_hook(VISHNYA)
    ogrn_hook = classify_hook(OGRN)
    a = VenueCandidate("twogis:a", "Вишня 1", "https://2gis.ru/firm/a", "twogis")
    b = VenueCandidate("twogis:b", "Вишня 2", "https://2gis.ru/firm/b", "twogis")
    catalog = FakeCatalog(
        {
            search_query(pink_hook): [
                VenueCandidate("twogis:p", "Pinklemon", PINK, "twogis")
            ],
            search_query(name_hook): [a, b],
            search_query(ogrn_hook): [
                VenueCandidate(
                    "twogis:o", "I LIKE NAILS", "https://2gis.ru/firm/o", "twogis"
                )
            ],
        }
    )
    outcome = resolve_intake(
        [PINK, VISHNYA, OGRN],
        MapsSearchResolver(catalog, FakeCatalog({})),
    )
    assert outcome.status is IntakeStatus.NEED_DISAMBIGUATION
    assert outcome.chosen_venues is None
    links = [c.source_url for slot in outcome.candidates_by_slot for c in slot]
    assert "https://2gis.ru/firm/a" in links
    assert "https://2gis.ru/firm/b" in links


def test_confirming_one_card_makes_ready() -> None:
    a = VenueCandidate("twogis:a", "Вишня 1", "https://2gis.ru/firm/a", "twogis")
    b = VenueCandidate("twogis:b", "Вишня 2", "https://2gis.ru/firm/b", "twogis")
    one = VenueCandidate("twogis:1", "Одна", "https://2gis.ru/firm/1", "twogis")
    two = VenueCandidate("twogis:2", "Две", "https://2gis.ru/firm/2", "twogis")
    outcome = resolve_intake(
        [PINK, VISHNYA, OGRN],
        MapsSearchResolver(
            FakeCatalog(
                {
                    search_query(classify_hook(PINK)): [one],
                    search_query(classify_hook(VISHNYA)): [a, b],
                    search_query(classify_hook(OGRN)): [two],
                }
            ),
            FakeCatalog({}),
        ),
    )
    confirmed = apply_slot_choices(outcome, {1: "twogis:b"})
    assert confirmed.status is IntakeStatus.READY
    assert confirmed.chosen_venues is not None
    assert confirmed.chosen_venues[1].venue_id == "twogis:b"


def test_maps_link_is_single_candidate_without_search() -> None:
    catalog = FakeCatalog({})
    hook = classify_hook("https://2gis.ru/moscow/firm/12345")
    resolver = MapsSearchResolver(catalog, FakeCatalog({}))
    found = resolver.resolve(hook)
    assert len(found) == 1
    assert found[0].venue_id == "twogis:12345"
    assert catalog.queries == []


def test_twogis_keeps_all_search_hits_and_picks_by_id() -> None:
    items: list[dict[str, object]] = [
        {"id": "aaa", "name": "Первая"},
        {"id": "bbb", "name": "Вторая"},
    ]
    found = candidates_from_twogis_items(items)
    assert len(found) == 2
    picked = item_by_id(items, "bbb")
    assert picked is not None
    assert picked["name"] == "Вторая"


def test_app_uses_search_resolver_and_confirmation() -> None:
    text = (ROOT / "src" / "salon_compare" / "app.py").read_text(encoding="utf-8")
    assert "MapsSearchResolver" in text
    assert "PassthroughResolver" not in text
    assert "st.radio" in text
    assert "apply_slot_choices" in text


def test_compose_forwards_map_keys() -> None:
    text = (ROOT / "compose.yaml").read_text(encoding="utf-8")
    assert "TWOGIS_API_KEY" in text
    assert "YANDEX_MAPS_API_KEY" in text
    assert "LLM_API_KEY" in text
