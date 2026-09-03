"""Индекс 50/25/25. Нет данных — не ноль. Федресурс и КАД не входят."""

from __future__ import annotations

import re
from datetime import date
from typing import Protocol

from pydantic import BaseModel, ConfigDict

from salon_compare.collect import SourcedField, Trust

_DOT_DATE = re.compile(r"(\d{2})\.(\d{2})\.(\d{4})")
_ISO_DATE = re.compile(r"(\d{4})-(\d{2})-(\d{2})")
_METRO_METERS = re.compile(r",\s*(\d+)\s*м")

WEIGHTS = {
    "reputation": 0.50,
    "stability": 0.25,
    "location": 0.25,
}
MAX_POINTS = {
    "reputation": 3,
    "stability": 3,
    "location": 3,
}


class BlockScore(BaseModel):
    model_config = ConfigDict(frozen=True)

    name: str
    weight: float
    points: int | None
    reason: str


class PlaceScore(BaseModel):
    model_config = ConfigDict(frozen=True)

    index: float | None
    note: str
    blocks: tuple[BlockScore, ...]


class _Fields(Protocol):
    twogis_rating: SourcedField
    egrul_registered_at: SourcedField
    egrul_status: SourcedField


def score_place(row: _Fields, as_of: date | None = None) -> PlaceScore:
    today = as_of or date.today()
    reputation = _reputation(row)
    stability = _stability(row, today)
    location = _location(row)
    blocks = (reputation, stability, location)
    if getattr(row, "unreliable", False):
        return PlaceScore(
            index=None,
            note="Объект помечен как недостоверный.",
            blocks=blocks,
        )
    total = 0.0
    used = False
    for item in blocks:
        if item.points is None:
            continue
        used = True
        ceiling = MAX_POINTS[item.name]
        total += 100 * item.weight * (item.points / ceiling)
    if not used:
        return PlaceScore(
            index=None,
            note="Индекс не найден: нет блоков с данными.",
            blocks=blocks,
        )
    holes = [item.name for item in blocks if item.points is None]
    note = "Ориентир, не инвестиционный совет."
    if holes:
        labels = {
            "reputation": "репутация",
            "stability": "устойчивость",
            "location": "локация",
        }
        named = ", ".join(labels[name] for name in holes)
        note = (
            f"Частичный индекс, без блоков: {named}. Ориентир, не инвестиционный совет."
        )
    return PlaceScore(index=round(total, 1), note=note, blocks=blocks)


def _numeric(field: SourcedField) -> float | None:
    if field.trust is Trust.MISSING or field.value is None:
        return None
    if isinstance(field.value, int | float) and not isinstance(field.value, bool):
        return float(field.value)
    return None


def _text(field: SourcedField) -> str:
    if field.trust is Trust.MISSING or field.value is None:
        return ""
    return str(field.value).lower()


def _reputation(row: _Fields) -> BlockScore:
    weight = WEIGHTS["reputation"]
    chosen = _numeric(row.twogis_rating)
    if chosen is None:
        return BlockScore(
            name="reputation",
            weight=weight,
            points=None,
            reason="рейтинг карт не найден",
        )
    if chosen > 4.5:
        return BlockScore(
            name="reputation",
            weight=weight,
            points=3,
            reason="рейтинг выше 4.5",
        )
    if chosen >= 4.0:
        return BlockScore(
            name="reputation",
            weight=weight,
            points=2,
            reason="рейтинг 4.0–4.5",
        )
    return BlockScore(
        name="reputation",
        weight=weight,
        points=1,
        reason="рейтинг ниже 4.0",
    )


def _stability(row: _Fields, as_of: date) -> BlockScore:
    weight = WEIGHTS["stability"]
    status = _text(row.egrul_status)
    dead = "ликвидирован" in status or "не действует" in status
    age = _age_points(row.egrul_registered_at, as_of)
    if dead:
        if age is None and not status:
            return BlockScore(
                name="stability",
                weight=weight,
                points=None,
                reason="дата регистрации не найдена",
            )
        return BlockScore(
            name="stability",
            weight=weight,
            points=0,
            reason="статус не действует",
        )
    if age is None:
        return BlockScore(
            name="stability",
            weight=weight,
            points=None,
            reason="дата регистрации не найдена",
        )
    return BlockScore(
        name="stability",
        weight=weight,
        points=age,
        reason=f"возраст {age:+d}",
    )


def _age_points(field: SourcedField, as_of: date) -> int | None:
    if field.trust is Trust.MISSING or field.value is None:
        return None
    registered = _parse_date(str(field.value))
    if registered is None:
        return None
    years = (as_of - registered).days / 365.25
    if years > 5:
        return 3
    if years >= 3:
        return 2
    return 1


def _location(row: _Fields) -> BlockScore:
    weight = WEIGHTS["location"]
    metro_pts = _metro_points(row)
    vs_pts = _neighbor_vs_points(row)
    if metro_pts is None and vs_pts is None:
        return BlockScore(
            name="location",
            weight=weight,
            points=None,
            reason="метро и сравнение с соседями не найдены",
        )
    points = min(3, (metro_pts or 0) + (vs_pts or 0))
    bits: list[str] = []
    if metro_pts is not None:
        bits.append(f"метро {metro_pts:+d}")
    if vs_pts is not None:
        bits.append(f"соседи {vs_pts:+d}")
    return BlockScore(
        name="location",
        weight=weight,
        points=points,
        reason="; ".join(bits),
    )


def _metro_points(row: _Fields) -> int | None:
    field = getattr(row, "metro", None)
    if not isinstance(field, SourcedField):
        return None
    if field.trust is Trust.MISSING or field.value is None:
        return None
    raw = str(field.value)
    match = _METRO_METERS.search(raw)
    if match is None:
        return 1
    meters = int(match.group(1))
    if meters <= 400:
        return 2
    if meters <= 800:
        return 1
    return 1


def _neighbor_vs_points(row: _Fields) -> int | None:
    field = getattr(row, "neighbor_vs", None)
    if not isinstance(field, SourcedField):
        return None
    if field.trust is Trust.MISSING or field.value is None:
        return None
    value = str(field.value).casefold()
    if value == "ниже":
        return 1
    if value == "выше":
        return 0
    return None


def _parse_date(raw: str) -> date | None:
    dotted = _DOT_DATE.search(raw)
    if dotted:
        day, month, year = (int(part) for part in dotted.groups())
        return date(year, month, day)
    iso = _ISO_DATE.search(raw)
    if iso:
        year, month, day = (int(part) for part in iso.groups())
        return date(year, month, day)
    return None
