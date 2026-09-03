"""Карточки, правка полей, разбор JSON модели. Без сети."""

from __future__ import annotations

import json
import re
from datetime import date
from typing import TypedDict

from pydantic import BaseModel, ConfigDict, ValidationError

from salon_compare.collect import PlaceRecord, SourcedField, Trust
from salon_compare.llm import LlmClient
from salon_compare.score import MAX_POINTS, PlaceScore, score_place

MODEL_DISCLAIMER = "текст модели, не инвестиционный совет"
HUMAN_SOURCE = "правка человека"

FIELD_LABELS: tuple[tuple[str, str], ...] = (
    ("twogis_rating", "2ГИС рейтинг"),
    ("hours", "Часы"),
    ("district", "Район"),
    ("metro", "Метро"),
    ("address", "Адрес"),
    ("neighbor_count", "Соседи 500 м"),
    ("neighbor_vs", "Соседи выше/ниже"),
    ("site_about", "Сайт «о нас»"),
    ("egrul_registered_at", "ЕГРЮЛ/ЕГРИП дата"),
    ("egrul_status", "ЕГРЮЛ/ЕГРИП статус"),
    ("egrul_activity", "ЕГРЮЛ/ЕГРИП деятельность"),
)

EDITABLE_FIELDS: tuple[str, ...] = tuple(name for name, _ in FIELD_LABELS)

EVIDENCE_FIELD_LABELS: tuple[tuple[str, str], ...] = (
    ("twogis_rating", "2ГИС рейтинг"),
    ("twogis_review_count", "2ГИС число отзывов"),
    ("hours", "Часы"),
    ("district", "Район"),
    ("metro", "Метро"),
    ("address", "Адрес"),
    ("neighbor_count", "Соседи 500 м"),
    ("neighbor_vs", "Соседи выше/ниже"),
    ("site_about", "Сайт «о нас»"),
    ("egrul_registered_at", "ЕГРЮЛ/ЕГРИП дата"),
    ("egrul_status", "ЕГРЮЛ/ЕГРИП статус"),
    ("egrul_activity", "ЕГРЮЛ/ЕГРИП деятельность"),
    ("fedresurs", "Федресурс"),
    ("kad", "КАД арбитраж"),
    ("twogis_last_review", "2ГИС дата последнего отзыва"),
    ("twogis_reviews_90d", "2ГИС отзывы за 90 дней"),
    ("twogis_plus_minus", "2ГИС плюс/минус"),
)

_BLOCK_LABELS = {
    "reputation": "репутация",
    "stability": "устойчивость",
    "location": "локация",
}

LLM_SYSTEM_PROMPT = "\n".join(
    [
        "Ты — старший аналитик стратегического консалтинга.",
        "Пишешь краткую сравнительную записку для инвестора,",
        "который выбирает, какую из трёх маникюрных точек смотреть первой.",
        "",
        "ИСТОЧНИК ИСТИНЫ — только JSON-досье в сообщении пользователя.",
        "Это закрытый пакет фактов на дату meta.as_of.",
        "У тебя нет доступа к интернету, если meta.external_research пуст.",
        "",
        "ЗАПРЕЩЕНО:",
        "- придумывать цифры, даты, рейтинги, статусы, адреса,",
        "  число отзывов, долги, выручку;",
        "- подставлять 0 или «среднее» вместо missing;",
        "- писать «покупай», «рекомендую купить», «лучший выбор без оговорок»;",
        "- ссылаться на факты вне досье, если meta.external_research пуст;",
        "- рекомендовать объект с unreliable=true или index=null как лидера;",
        "- менять или пересчитывать index — только цитировать из досье.",
        "",
        "ОБЯЗАТЕЛЬНО:",
        "- каждое число в тексте должно совпадать с value",
        "  в evidence или index/score_blocks;",
        "- при сравнении называй конкретные точки по title;",
        "- указывай уровень доверия (found/weak/missing), где это влияет на вывод;",
        "- если поле missing — пиши «не найдено», не достраивай;",
        "- если index_note содержит «частичный» — явно оговори ограничение;",
        "- для полей с source_url в скобках указывай источник: (источник: URL)",
        "  или (источник: правка человека);",
        "- compared_index — index лидера из досье или null,",
        "  если лидера назвать нельзя;",
        "- тон: деловой, сжатый — вывод → сравнение → риски; без эмодзи и маркетинга.",
        "",
        "ФОРМАТ ОТВЕТА: только валидный JSON без markdown и пояснений.",
        "Ключи: interesting, why_better, breaks_if, compared_index.",
    ]
)

_JSON_FENCE = re.compile(r"^```(?:json)?\s*|\s*```$", re.IGNORECASE | re.MULTILINE)

SITE_ABOUT_PREVIEW = 80

_NUMERIC_FIELDS = {
    "twogis_rating",
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
    text = _strip_json_fence(raw.strip())
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


def _strip_json_fence(text: str) -> str:
    stripped = text.strip()
    if stripped.startswith("```"):
        lines = stripped.splitlines()
        if lines and lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        return "\n".join(lines).strip()
    return _JSON_FENCE.sub("", stripped).strip()


def _field_text(field: SourcedField) -> str:
    if field.trust is Trust.MISSING or field.value is None:
        return "не найдено"
    if field.trust is Trust.WEAK:
        return f"{field.value} · слабо"
    return str(field.value)


def collapse_text(value: object) -> str:
    return " ".join(str(value).split())


def display_value(name: str, value: object) -> str:
    text = collapse_text(value)
    if name == "site_about" and len(text) > SITE_ABOUT_PREVIEW:
        return text[: SITE_ABOUT_PREVIEW - 1] + "…"
    return text


def field_sources(row: PlaceRecord, name: str) -> tuple[str, ...]:
    if name.startswith("egrul_") and row.legal_candidates:
        return tuple(
            item.source_url for item in row.legal_candidates if item.source_url
        )
    field = getattr(row, name)
    if isinstance(field, SourcedField) and field.source_url:
        return (field.source_url,)
    return ()


def footnote_map(rows: list[PlaceRecord]) -> dict[str, int]:
    mapping: dict[str, int] = {}
    next_n = 1
    for name, _label in FIELD_LABELS:
        for row in rows:
            for url in field_sources(row, name):
                if url not in mapping:
                    mapping[url] = next_n
                    next_n += 1
    return mapping


def footnote_marks(urls: tuple[str, ...], mapping: dict[str, int]) -> str:
    seen: list[int] = []
    for url in urls:
        number = mapping[url]
        if number not in seen:
            seen.append(number)
    return "".join(f"[{item}]" for item in seen)


def table_cell(row: PlaceRecord, name: str, mapping: dict[str, int]) -> str:
    sources = field_sources(row, name)
    marks = footnote_marks(sources, mapping)
    if name.startswith("egrul_") and row.legal_candidates:
        return f"уточните юрлицо {marks}".rstrip()
    field = getattr(row, name)
    if not isinstance(field, SourcedField):
        return "не найдено"
    if field.trust is Trust.MISSING or field.value is None:
        return "не найдено"
    body = display_value(name, field.value)
    if field.trust is Trust.WEAK:
        body = f"{body} · слабо"
    if marks:
        return f"{body} {marks}"
    return body


def footnote_lines(mapping: dict[str, int]) -> list[tuple[int, str]]:
    return sorted((number, url) for url, number in mapping.items())


def cell_help(row: PlaceRecord, name: str) -> str:
    field = getattr(row, name)
    if (
        name == "site_about"
        and isinstance(field, SourcedField)
        and field.value is not None
    ):
        return collapse_text(field.value)
    return "Править значение"


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
    if not raw.strip():
        edited = SourcedField()
    else:
        edited = SourcedField(
            value=_coerce_edit(name, raw),
            source_url=HUMAN_SOURCE,
            trust=Trust.WEAK,
        )
    return row.model_copy(update={name: edited})


def mark_unreliable(row: PlaceRecord) -> PlaceRecord:
    return row.model_copy(update={"unreliable": True})


def _evidence_entry(name: str, label: str, field: SourcedField) -> dict[str, object]:
    missing = field.trust is Trust.MISSING or field.value is None
    return {
        "label": label,
        "value": None if missing else field.value,
        "trust": field.trust.value,
        "source_url": field.source_url,
    }


def _venue_dossier(row: PlaceRecord, as_of: date | None) -> dict[str, object]:
    scored = score_place(row, as_of=as_of)
    evidence: dict[str, object] = {}
    missing_fields: list[str] = []
    for name, label in EVIDENCE_FIELD_LABELS:
        field = getattr(row, name)
        if not isinstance(field, SourcedField):
            continue
        evidence[name] = _evidence_entry(name, label, field)
        if field.trust is Trust.MISSING or field.value is None:
            missing_fields.append(name)
    score_blocks = [
        {
            "block": item.name,
            "label": _BLOCK_LABELS.get(item.name, item.name),
            "weight": item.weight,
            "points": item.points,
            "max": MAX_POINTS[item.name],
            "reason": item.reason,
        }
        for item in scored.blocks
    ]
    return {
        "venue_id": row.venue_id,
        "title": row.title,
        "index": scored.index,
        "index_note": scored.note,
        "unreliable": row.unreliable,
        "score_blocks": score_blocks,
        "evidence": evidence,
        "missing_fields": missing_fields,
    }


def build_evidence_dossier(
    rows: list[PlaceRecord],
    as_of: date | None = None,
) -> dict[str, object]:
    today = as_of or date.today()
    return {
        "meta": {
            "as_of": today.isoformat(),
            "market": "Москва и ближайшее Подмосковье (МЦД)",
            "segment": "маникюрные студии, сравнение трёх точек",
            "methodology": {
                "formula": "50% репутация · 25% устойчивость · 25% локация",
                "disclaimer": "ориентир здоровья бизнеса, не инвестиционный совет",
            },
            "trust_legend": {
                "found": "подтверждено первоисточником",
                "weak": "слабо / не подтверждено / правка человека",
                "missing": "не найдено — не интерпретировать как ноль",
            },
            "external_research": [],
        },
        "venues": [_venue_dossier(row, today) for row in rows],
    }


def build_user_prompt(dossier: dict[str, object]) -> str:
    facts = json.dumps(dossier, ensure_ascii=False)
    return (
        "Подготовь сравнительную записку по трём маникюрным точкам.\n\n"
        "Задача инвестора: понять, какую точку смотреть первой и почему — "
        "только на основе досье.\n\n"
        "Структура ответа:\n"
        "1) interesting — 1–2 предложения: приоритетная точка "
        "(или «однозначного лидера нет») и главный драйвер.\n"
        "2) why_better — 3–5 предложений: сравнение с двумя другими по блокам "
        "репутация/устойчивость/локация; только факты из evidence и index; "
        "отметь пробелы данных.\n"
        "3) breaks_if — 2–4 условия, при которых вывод перестаёт быть верным; "
        "включи критичные data gaps.\n"
        "4) compared_index — index лидера из досье (число) или null.\n\n"
        f"Досье:\n{facts}"
    )


def build_prompt(rows: list[PlaceRecord], as_of: date | None = None) -> str:
    return build_user_prompt(build_evidence_dossier(rows, as_of=as_of))


def _allowed_indexes(
    rows: list[PlaceRecord],
    as_of: date | None,
) -> set[float]:
    allowed: set[float] = set()
    for row in rows:
        if row.unreliable:
            continue
        scored = score_place(row, as_of=as_of)
        if scored.index is not None:
            allowed.add(scored.index)
    return allowed


def validate_verdict(
    verdict: ModelVerdict,
    rows: list[PlaceRecord],
    as_of: date | None = None,
) -> ModelVerdict | None:
    if verdict.compared_index is None:
        return verdict
    allowed = _allowed_indexes(rows, as_of)
    if not allowed:
        return None
    if verdict.compared_index in allowed:
        return verdict
    return None


def complete_verdict(
    rows: list[PlaceRecord],
    llm: LlmClient,
    as_of: date | None = None,
) -> ModelVerdict | None:
    dossier = build_evidence_dossier(rows, as_of=as_of)
    raw = llm.complete(build_user_prompt(dossier), system=LLM_SYSTEM_PROMPT)
    parsed = parse_verdict(raw)
    if parsed is None:
        return None
    return validate_verdict(parsed, rows, as_of=as_of)


def rows_fingerprint(rows: list[PlaceRecord]) -> str:
    return json.dumps(
        [row.model_dump(mode="json") for row in rows],
        sort_keys=True,
        ensure_ascii=False,
    )
