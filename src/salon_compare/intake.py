"""Разбор трёх зацепок: неоднозначность и дубли точек, без сбора карт."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from enum import StrEnum
from typing import Protocol

from salon_compare.hooks import ClassifiedHook, HookKind, classify_hook


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


class VenueResolver(Protocol):
    def resolve(self, hook: ClassifiedHook) -> list[VenueCandidate]: ...


@dataclass(frozen=True)
class IntakeOutcome:
    status: IntakeStatus
    classified: list[ClassifiedHook]
    candidates_by_slot: list[list[VenueCandidate]]
    message: str
    chosen_venues: tuple[VenueCandidate, ...] | None


class PassthroughResolver:
    """Одна точка на зацепку по нормализованной строке. Поиск карт — следующий шаг."""

    def resolve(self, hook: ClassifiedHook) -> list[VenueCandidate]:
        url = (
            hook.normalized
            if hook.kind
            in {
                HookKind.WEBSITE,
                HookKind.MAPS_LINK,
                HookKind.BOOKING_LINK,
            }
            else f"https://local.invalid/{hook.kind}/{hook.normalized}"
        )
        venue_id = f"{hook.kind.value}:{hook.normalized}"
        return [VenueCandidate(venue_id, hook.raw.strip(), url)]


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
        "Три разные точки. Сбор данных ещё не включён.",
        chosen,
    )
