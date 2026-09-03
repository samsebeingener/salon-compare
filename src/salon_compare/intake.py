"""Разбор трёх зацепок: неоднозначность и дубли точек, без сбора карт."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from enum import StrEnum
from typing import Protocol

from salon_compare.hooks import ClassifiedHook, classify_hook

MISSING_VENUE_ID = "__missing__"
MISSING_VENUE_LABEL = "Нужный вариант не найден. Попробуйте добавить иные зацепки."


class IntakeStatus(StrEnum):
    NEED_THREE = "need_three"
    NEED_DISAMBIGUATION = "need_disambiguation"
    DUPLICATE_VENUES = "duplicate_venues"
    READY = "ready"


@dataclass(frozen=True)
class VenueCandidate:
    venue_id: str
    title: str
    source_url: str
    provider: str = "unknown"
    address: str | None = None


def candidate_label(item: VenueCandidate) -> str:
    if item.address:
        return f"{item.title} — {item.address} — {item.source_url}"
    return f"{item.title} — {item.source_url}"


class VenueResolver(Protocol):
    def resolve(self, hook: ClassifiedHook) -> list[VenueCandidate]: ...


@dataclass(frozen=True)
class IntakeOutcome:
    status: IntakeStatus
    classified: list[ClassifiedHook]
    candidates_by_slot: list[list[VenueCandidate]]
    message: str
    chosen_venues: tuple[VenueCandidate, ...] | None


def _finish_slots(
    classified: list[ClassifiedHook],
    slots: list[list[VenueCandidate]],
) -> IntakeOutcome:
    if any(len(slot) != 1 for slot in slots):
        return IntakeOutcome(
            IntakeStatus.NEED_DISAMBIGUATION,
            classified,
            slots,
            "Уточните точку по ссылкам. Сами не выбираем.",
            None,
        )
    chosen = tuple(slot[0] for slot in slots)
    seen: dict[str, VenueCandidate] = {}
    for candidate in chosen:
        if candidate.venue_id in seen:
            first = seen[candidate.venue_id]
            return IntakeOutcome(
                IntakeStatus.DUPLICATE_VENUES,
                classified,
                slots,
                (
                    "Это одна точка. Замените одну зацепку. "
                    f"{first.source_url} {candidate.source_url}"
                ),
                None,
            )
        seen[candidate.venue_id] = candidate
    return IntakeOutcome(
        IntakeStatus.READY,
        classified,
        slots,
        "Разные точки.",
        chosen,
    )


def resolve_intake(raw_hooks: Sequence[str], resolver: VenueResolver) -> IntakeOutcome:
    filled = [item.strip() for item in raw_hooks if item.strip()]
    classified = [classify_hook(item) for item in filled]
    if len(filled) != 3:
        return IntakeOutcome(
            IntakeStatus.NEED_THREE,
            classified,
            [],
            "Нужны три зацепки.",
            None,
        )
    slots = [list(resolver.resolve(hook)) for hook in classified]
    return IntakeOutcome(
        IntakeStatus.NEED_DISAMBIGUATION,
        classified,
        slots,
        "Уточните точку по ссылкам. Сами не выбираем.",
        None,
    )


def apply_slot_choices(
    outcome: IntakeOutcome,
    choices: dict[int, str],
) -> IntakeOutcome:
    hooks: list[ClassifiedHook] = []
    slots: list[list[VenueCandidate]] = []
    for index, slot in enumerate(outcome.candidates_by_slot):
        if len(slot) == 0:
            continue
        choice = choices.get(index)
        if choice == MISSING_VENUE_ID:
            continue
        picked = [item for item in slot if item.venue_id == choice]
        if len(picked) != 1:
            return IntakeOutcome(
                IntakeStatus.NEED_DISAMBIGUATION,
                outcome.classified,
                outcome.candidates_by_slot,
                "Выберите точку по ссылке. Сами не выбираем.",
                None,
            )
        hooks.append(outcome.classified[index])
        slots.append(picked)
    if len(slots) < 2:
        return IntakeOutcome(
            IntakeStatus.NEED_DISAMBIGUATION,
            outcome.classified,
            outcome.candidates_by_slot,
            MISSING_VENUE_LABEL + " Для сравнения нужны хотя бы две точки.",
            None,
        )
    return _finish_slots(hooks, slots)


def replace_slot_search(
    outcome: IntakeOutcome,
    slot_index: int,
    raw: str,
    resolver: VenueResolver,
) -> IntakeOutcome:
    query = raw.strip()
    if slot_index < 0 or slot_index >= len(outcome.classified) or not query:
        return IntakeOutcome(
            IntakeStatus.NEED_DISAMBIGUATION,
            outcome.classified,
            outcome.candidates_by_slot,
            "Укажите новую зацепку для этой точки.",
            None,
        )
    classified = list(outcome.classified)
    classified[slot_index] = classify_hook(query)
    slots = [list(slot) for slot in outcome.candidates_by_slot]
    slots[slot_index] = list(resolver.resolve(classified[slot_index]))
    return IntakeOutcome(
        IntakeStatus.NEED_DISAMBIGUATION,
        classified,
        slots,
        "Уточните точку по ссылкам. Сами не выбираем.",
        None,
    )
