"""Карточки, правка полей, разбор JSON модели. Без сети."""

from __future__ import annotations

import json
from typing import TypedDict

from pydantic import BaseModel, ConfigDict, ValidationError

from salon_compare.collect import PlaceRecord, SourcedField, Trust
from salon_compare.llm import LlmClient
from salon_compare.score import PlaceScore, score_place

MODEL_DISCLAIMER = "текст модели, не инвестиционный совет"
HUMAN_SOURCE = "правка человека"

FIELD_LABELS: tuple[tuple[str, str], ...] = (
    ("yandex_rating", "Яндекс рейтинг"),
    ("yandex_review_count", "Яндекс отзывы"),
    ("twogis_rating", "2ГИС рейтинг"),
    ("twogis_review_count", "2ГИС отзывы"),
    ("hours", "Часы"),
    ("district", "Район"),
    ("metro", "Метро"),
    ("yandex_last_review", "Яндекс последний отзыв"),
    ("yandex_reviews_90d", "Яндекс отзывы за 90 дней"),
    ("yandex_plus_minus", "Яндекс плюс/минус"),
    ("twogis_last_review", "2ГИС последний отзыв"),
    ("twogis_reviews_90d", "2ГИС отзывы за 90 дней"),
    ("twogis_plus_minus", "2ГИС плюс/минус"),
    ("address", "Адрес"),
    ("neighbor_count", "Соседи 500 м"),
    ("neighbor_vs", "Рейтинг соседей"),
    ("site_about", "Сайт «о нас»"),
    ("egrul_registered_at", "ЕГРЮЛ дата"),
    ("egrul_status", "ЕГРЮЛ статус"),
    ("egrul_activity", "ЕГРЮЛ деятельность"),
    ("fedresurs", "Федресурс"),
    ("kad", "КАД"),
)

EDITABLE_FIELDS: tuple[str, ...] = tuple(name for name, _ in FIELD_LABELS)

_NUMERIC_FIELDS = {
    "yandex_rating",
    "yandex_review_count",
    "twogis_rating",
    "twogis_review_count",
    "neighbor_count",
}


class ModelVerdict(BaseModel):
    model_config = ConfigDict(extra="ignore")

    interesting: str
    why_better: str
    breaks_if: str
    compared_index: float | None = None


class FieldView(TypedDict):
    label: str
    value: float | int | str | None
    source_url: str | None
    trust: str
    text: str


class CardView(TypedDict):
    title: str
    index: float | None
    note: str
    unreliable: bool
    fields: list[FieldView]
    missing: list[str]


def parse_verdict(raw: str) -> ModelVerdict | None:
    text = raw.strip()
    if not text:
        return None
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        return None
    if not isinstance(data, dict) or not data:
        return None
    try:
        return ModelVerdict.model_validate(data)
    except ValidationError:
        return None


def _field_text(field: SourcedField) -> str:
    if field.trust is Trust.MISSING or field.value is None:
        return "не найдено"
    link = f" · {field.source_url}" if field.source_url else ""
    if field.trust is Trust.WEAK:
        return f"{field.value} · слабо{link}"
    if field.source_url:
        return f"{field.value}{link}"
    return str(field.value)


def card_payload(row: PlaceRecord, score: PlaceScore) -> CardView:
    fields: list[FieldView] = []
    missing: list[str] = []
    for name, label in FIELD_LABELS:
        field = getattr(row, name)
        if not isinstance(field, SourcedField):
            continue
        if field.trust is Trust.MISSING or field.value is None:
            missing.append(label)
        fields.append(
            {
                "label": label,
                "value": field.value,
                "source_url": field.source_url,
                "trust": field.trust.value,
                "text": _field_text(field),
            }
        )
    return {
        "title": row.title,
        "index": score.index,
        "note": score.note,
        "unreliable": row.unreliable,
        "fields": fields,
        "missing": missing,
    }


def _coerce_edit(name: str, raw: str) -> float | int | str:
    text = raw.strip()
    if name not in _NUMERIC_FIELDS:
        return text
    try:
        number = float(text)
    except ValueError:
        return text
    if name.endswith("count") and number.is_integer():
        return int(number)
    return number


def patch_field(row: PlaceRecord, name: str, raw: str) -> PlaceRecord:
    if name not in EDITABLE_FIELDS:
        raise ValueError(name)
    edited = SourcedField(
        value=_coerce_edit(name, raw),
        source_url=HUMAN_SOURCE,
        trust=Trust.WEAK,
    )
    return row.model_copy(update={name: edited})


def mark_unreliable(row: PlaceRecord) -> PlaceRecord:
    return row.model_copy(update={"unreliable": True})


def build_prompt(rows: list[PlaceRecord]) -> str:
    payload: list[dict[str, object]] = []
    for row in rows:
        scored = score_place(row)
        item: dict[str, object] = {
            "title": row.title,
            "index": scored.index,
            "note": scored.note,
            "unreliable": row.unreliable,
        }
        for name, _label in FIELD_LABELS:
            field = getattr(row, name)
            if isinstance(field, SourcedField) and field.trust is not Trust.MISSING:
                item[name] = field.value
        payload.append(item)
    facts = json.dumps(payload, ensure_ascii=False)
    return (
        "Сравни три маникюрные точки только по JSON ниже. "
        "Не советуй покупать. Не выдумывай поля, которых нет. "
        "Ответь JSON с ключами interesting, why_better, breaks_if "
        "и compared_index (индекс выбранной точки или null).\n"
        f"{facts}"
    )


def complete_verdict(rows: list[PlaceRecord], llm: LlmClient) -> ModelVerdict | None:
    raw = llm.complete(build_prompt(rows))
    return parse_verdict(raw)


def rows_fingerprint(rows: list[PlaceRecord]) -> str:
    return json.dumps(
        [row.model_dump(mode="json") for row in rows],
        sort_keys=True,
        ensure_ascii=False,
    )
