"""Гибридный добор MISSING полей: один LLM-вызов на точку, парсеры не трогаем."""

from __future__ import annotations

import json
import re

from pydantic import BaseModel, ConfigDict, ValidationError

from salon_compare.collect import PlaceRecord, SourcedField, Trust, as_sourced_field
from salon_compare.llm import LlmClient, LlmUsage

EXTRACT_FIELDS: tuple[str, ...] = ("site_about", "egrul_activity")
MODEL_SOURCE = "модель"

_JSON_FENCE = re.compile(r"^```(?:json)?\s*|\s*```$", re.IGNORECASE | re.MULTILINE)
_SYSTEM = "Отвечай только JSON без пояснений."


class ExtractPatch(BaseModel):
    model_config = ConfigDict(extra="ignore")

    site_about: str | None = None
    egrul_activity: str | None = None
    source_quote: str | None = None


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


def parse_extract(raw: str) -> ExtractPatch | None:
    text = _strip_json_fence(raw.strip())
    if not text:
        return None
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        return None
    if not isinstance(data, dict):
        return None
    try:
        return ExtractPatch.model_validate(data)
    except ValidationError:
        return None


def gaps_for(row: PlaceRecord) -> list[str]:
    names: list[str] = []
    for name in EXTRACT_FIELDS:
        field = as_sourced_field(getattr(row, name, None))
        if field is None or field.trust == Trust.MISSING or field.value is None:
            names.append(name)
    return names


def apply_extract(row: PlaceRecord, patch: ExtractPatch) -> PlaceRecord:
    gaps = set(gaps_for(row))
    updates: dict[str, SourcedField] = {}
    for name in EXTRACT_FIELDS:
        if name not in gaps:
            continue
        raw = getattr(patch, name)
        if not isinstance(raw, str) or not raw.strip():
            continue
        updates[name] = SourcedField(
            value=raw.strip(),
            source_url=MODEL_SOURCE,
            trust=Trust.WEAK,
        )
    if not updates:
        return row
    return row.model_copy(update=updates)


def _prompt(gaps: list[str], context: str) -> str:
    wanted = ", ".join(gaps)
    return (
        "Извлеки только запрошенные поля из контекста. "
        "Верни JSON без markdown. "
        f"Ключи только из списка: {wanted}. "
        "Необязательный ключ source_quote — короткая цитата из контекста. "
        "Не выдумывай факты вне контекста. Нет данных — не включай ключ.\n\n"
        f"Контекст:\n{context}"
    )


def extract_context(row: PlaceRecord) -> str:
    parts: list[str] = []
    about = as_sourced_field(row.site_about)
    if about is not None and about.value is not None:
        parts.append(f"site_about: {about.value}")
    for name in (
        "egrul_registered_at",
        "egrul_status",
        "egrul_activity",
        "fedresurs",
        "kad",
        "efrsb",
    ):
        field = as_sourced_field(getattr(row, name, None))
        if field is None or field.value is None:
            continue
        parts.append(f"{name}: {field.value}")
    return "\n".join(parts)


def extract_missing(
    row: PlaceRecord,
    llm: LlmClient,
    context: str,
) -> tuple[PlaceRecord, LlmUsage]:
    gaps = gaps_for(row)
    if not gaps:
        return row, LlmUsage()
    raw = llm.complete(_prompt(gaps, context), system=_SYSTEM)
    patch = parse_extract(raw)
    usage = llm.last_usage()
    if patch is None:
        return row, usage
    return apply_extract(row, patch), usage
