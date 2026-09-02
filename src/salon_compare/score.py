"""Индекс 40/25/20/15. Нет данных — не ноль."""

from __future__ import annotations

import re
from datetime import date
from typing import Protocol

from pydantic import BaseModel, ConfigDict

from salon_compare.collect import SourcedField, Trust

_DOT_DATE = re.compile(r"(\d{2})\.(\d{2})\.(\d{4})")
_ISO_DATE = re.compile(r"(\d{4})-(\d{2})-(\d{2})")

WEIGHTS = {
    "reputation": 0.40,
    "stability": 0.25,
    "location": 0.20,
    "scale": 0.15,
}
MAX_POINTS = {
    "reputation": 3,
    "stability": 4,
    "location": 3,
    "scale": 3,
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
    twogis_review_count: SourcedField
    egrul_registered_at: SourcedField
    fedresurs: SourcedField
    kad: SourcedField


def score_place(row: _Fields, as_of: date | None = None) -> PlaceScore:
    today = as_of or date.today()
    reputation = _reputation(row, today)
    stability = _stability(row, today)
    location = BlockScore(
        name="location",
        weight=WEIGHTS["location"],
        points=None,
        reason="тип точки (улица/ТЦ/ЖК) не найден",
    )
    scale = BlockScore(
        name="scale",
        weight=WEIGHTS["scale"],
        points=None,
        reason="число мастеров и прайс не найдены",
    )
    blocks = (reputation, stability, location, scale)
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
            "scale": "масштаб",
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


def _reputation(row: _Fields, as_of: date) -> BlockScore:
    weight = WEIGHTS["reputation"]
    chosen = _numeric(row.twogis_rating)
    if chosen is None:
        return BlockScore(
            name="reputation",
            weight=weight,
            points=None,
            reason="рейтинг карт не найден",
        )
    if _too_negative(row, "twogis"):
        return BlockScore(
            name="reputation",
            weight=weight,
            points=0,
            reason="много минусов в разбивке",
        )
    fresh = _fresh_90(row, "twogis", as_of)
    count = _numeric(row.twogis_review_count)
    if chosen > 4.5 and fresh and count is not None and count >= 10:
        return BlockScore(
            name="reputation",
            weight=weight,
            points=3,
            reason="рейтинг выше 4.5 и отзывы за 90 дней",
        )
    if chosen >= 4.0:
        reason = "рейтинг без даты свежести, +3 не ставим"
        if fresh:
            reason = "рейтинг 4.0–4.5 или мало отзывов"
        return BlockScore(
            name="reputation",
            weight=weight,
            points=2,
            reason=reason,
        )
    return BlockScore(
        name="reputation",
        weight=weight,
        points=1,
        reason="рейтинг ниже 4.0",
    )


def _review_day(row: _Fields, name: str) -> date | None:
    field = getattr(row, name, None)
    if not isinstance(field, SourcedField):
        return None
    if field.trust is Trust.MISSING or field.value is None:
        return None
    return _parse_date(str(field.value))


def _fresh_90(row: _Fields, prefix: str, today: date) -> bool:
    flag = getattr(row, f"{prefix}_reviews_90d", None)
    if isinstance(flag, SourcedField) and str(flag.value).lower() == "да":
        return True
    day = _review_day(row, f"{prefix}_last_review")
    if day is None:
        return False
    return (today - day).days <= 90


def _too_negative(row: _Fields, prefix: str) -> bool:
    field = getattr(row, f"{prefix}_plus_minus", None)
    if not isinstance(field, SourcedField) or field.value is None:
        return False
    match = re.search(
        r"(\d+)\s*плюс\s*/\s*(\d+)\s*минус",
        str(field.value),
        re.IGNORECASE,
    )
    if not match:
        return False
    plus_n = int(match.group(1))
    minus_n = int(match.group(2))
    return minus_n > 0 and minus_n >= plus_n


def _stability(row: _Fields, as_of: date) -> BlockScore:
    weight = WEIGHTS["stability"]
    if row.fedresurs.trust is not Trust.FOUND or row.kad.trust is not Trust.FOUND:
        return BlockScore(
            name="stability",
            weight=weight,
            points=None,
            reason="Федресурс и КАД не открылись, устойчивость не считаем",
        )
    age = _age_points(row.egrul_registered_at, as_of)
    courts = _court_points(row.fedresurs, row.kad)
    if age is None and courts is None:
        return BlockScore(
            name="stability",
            weight=weight,
            points=None,
            reason="реестры открылись, но возраста и сигнала судов нет",
        )
    points = (age or 0) + (courts or 0)
    bits: list[str] = []
    if age is not None:
        bits.append(f"возраст {age:+d}")
    if courts is not None:
        bits.append(f"суды {courts:+d}")
    return BlockScore(
        name="stability",
        weight=weight,
        points=points,
        reason="; ".join(bits),
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


def _court_points(fedresurs: SourcedField, kad: SourcedField) -> int | None:
    fed = _text(fedresurs)
    kad_text = _text(kad)
    blob = f"{fed} {kad_text}"
    if "банкрот" in blob or "есть дела" in blob:
        return -2
    if "не обнаружено" in fed and "не обнаружено" in kad_text:
        return 1
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
