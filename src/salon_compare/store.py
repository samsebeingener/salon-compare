"""SQLite разборы. Ключи API в файл не пишем."""

from __future__ import annotations

import json
import sqlite3
from collections.abc import Callable, Mapping, Sequence
from datetime import UTC, datetime
from pathlib import Path

from salon_compare.collect import PlaceRecord
from salon_compare.legal import LegalOrg
from salon_compare.llm import LlmUsage
from salon_compare.report import ModelVerdict


def default_db_path() -> Path:
    return Path(__file__).resolve().parents[2] / "data" / "salon-compare.sqlite"


def _connect(path: Path) -> sqlite3.Connection:
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path)
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS runs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            created_at TEXT NOT NULL,
            payload TEXT NOT NULL
        )
        """
    )
    return conn


def _pack_rows(rows: Sequence[PlaceRecord]) -> list[dict[str, object]]:
    packed: list[dict[str, object]] = []
    for row in rows:
        data = row.model_dump(mode="json")
        data["legal_candidates"] = [
            {"ogrn": item.ogrn, "title": item.title, "source_url": item.source_url}
            for item in row.legal_candidates
        ]
        packed.append(data)
    return packed


def _dump_rows(
    rows: Sequence[PlaceRecord],
    usage: LlmUsage | None = None,
    verdict: ModelVerdict | None = None,
) -> str:
    payload: dict[str, object] = {
        "rows": _pack_rows(rows),
        "usage": usage.model_dump() if usage is not None else None,
        "verdict": verdict.model_dump() if verdict is not None else None,
    }
    return json.dumps(payload, ensure_ascii=False)


def _payload_parts(
    raw: str,
) -> tuple[
    list[dict[str, object]],
    dict[str, object] | None,
    dict[str, object] | None,
]:
    data = json.loads(raw)
    if isinstance(data, list):
        items = [item for item in data if isinstance(item, dict)]
        return items, None, None
    if isinstance(data, dict):
        rows = data.get("rows")
        usage = data.get("usage")
        verdict = data.get("verdict")
        items = rows if isinstance(rows, list) else []
        usage_dict = usage if isinstance(usage, dict) else None
        verdict_dict = verdict if isinstance(verdict, dict) else None
        packed_rows = [item for item in items if isinstance(item, dict)]
        return packed_rows, usage_dict, verdict_dict
    return [], None, None


def _row_dicts(raw: str) -> tuple[list[dict[str, object]], dict[str, object] | None]:
    items, usage, _verdict = _payload_parts(raw)
    return items, usage


def _encode_payload(
    rows: list[dict[str, object]],
    usage: dict[str, object] | None,
    verdict: dict[str, object] | None,
) -> str:
    return json.dumps(
        {"rows": rows, "usage": usage, "verdict": verdict},
        ensure_ascii=False,
    )


def _load_rows(raw: str) -> list[PlaceRecord]:
    items, _usage, _verdict = _payload_parts(raw)
    rows: list[PlaceRecord] = []
    for item in items:
        parsed: list[LegalOrg] = []
        cands = item.get("legal_candidates") or []
        if isinstance(cands, list):
            for cand in cands:
                if isinstance(cand, dict):
                    parsed.append(
                        LegalOrg(
                            str(cand.get("ogrn", "")),
                            str(cand.get("title", "")),
                            str(cand.get("source_url", "")),
                        )
                    )
        item["legal_candidates"] = parsed
        rows.append(PlaceRecord.model_validate(item))
    return rows


def save_run(
    rows: Sequence[PlaceRecord],
    path: Path | None = None,
    usage: LlmUsage | None = None,
    verdict: ModelVerdict | None = None,
) -> int:
    db = path or default_db_path()
    created = datetime.now(UTC).replace(microsecond=0).isoformat()
    with _connect(db) as conn:
        cursor = conn.execute(
            "INSERT INTO runs (created_at, payload) VALUES (?, ?)",
            (created, _dump_rows(rows, usage, verdict)),
        )
        conn.commit()
        run_id = cursor.lastrowid
    if run_id is None:
        raise RuntimeError("sqlite insert returned no id")
    return int(run_id)


def load_run(run_id: int, path: Path | None = None) -> list[PlaceRecord] | None:
    db = path or default_db_path()
    if not db.is_file():
        return None
    with _connect(db) as conn:
        found = conn.execute(
            "SELECT payload FROM runs WHERE id = ?",
            (run_id,),
        ).fetchone()
    if found is None:
        return None
    try:
        return _load_rows(str(found[0]))
    except (json.JSONDecodeError, ValueError, TypeError):
        return None


def load_run_usage(run_id: int, path: Path | None = None) -> LlmUsage | None:
    db = path or default_db_path()
    if not db.is_file():
        return None
    with _connect(db) as conn:
        found = conn.execute(
            "SELECT payload FROM runs WHERE id = ?",
            (run_id,),
        ).fetchone()
    if found is None:
        return None
    try:
        _rows, usage = _row_dicts(str(found[0]))
    except (json.JSONDecodeError, ValueError, TypeError):
        return None
    if usage is None:
        return None
    try:
        parsed = LlmUsage.model_validate(usage)
    except (ValueError, TypeError):
        return None
    if parsed.prompt_tokens is None and parsed.completion_tokens is None:
        if parsed.total_tokens is None and parsed.cost is None:
            return None
    return parsed


def load_run_verdict(run_id: int, path: Path | None = None) -> ModelVerdict | None:
    db = path or default_db_path()
    if not db.is_file():
        return None
    with _connect(db) as conn:
        found = conn.execute(
            "SELECT payload FROM runs WHERE id = ?",
            (run_id,),
        ).fetchone()
    if found is None:
        return None
    try:
        _rows, _usage, verdict = _payload_parts(str(found[0]))
    except (json.JSONDecodeError, ValueError, TypeError):
        return None
    if verdict is None:
        return None
    try:
        return ModelVerdict.model_validate(verdict)
    except (ValueError, TypeError):
        return None


def update_run(
    run_id: int,
    rows: Sequence[PlaceRecord],
    path: Path | None = None,
) -> None:
    db = path or default_db_path()
    if not db.is_file():
        return
    with _connect(db) as conn:
        found = conn.execute(
            "SELECT payload FROM runs WHERE id = ?",
            (run_id,),
        ).fetchone()
        if found is None:
            return
        try:
            _old, usage, verdict = _payload_parts(str(found[0]))
        except (json.JSONDecodeError, ValueError, TypeError):
            usage = None
            verdict = None
        conn.execute(
            "UPDATE runs SET payload = ? WHERE id = ?",
            (_encode_payload(_pack_rows(rows), usage, verdict), run_id),
        )
        conn.commit()


def save_run_usage(run_id: int, usage: LlmUsage, path: Path | None = None) -> None:
    db = path or default_db_path()
    if not db.is_file():
        return
    with _connect(db) as conn:
        found = conn.execute(
            "SELECT payload FROM runs WHERE id = ?",
            (run_id,),
        ).fetchone()
        if found is None:
            return
        try:
            rows, _old, verdict = _payload_parts(str(found[0]))
        except (json.JSONDecodeError, ValueError, TypeError):
            return
        conn.execute(
            "UPDATE runs SET payload = ? WHERE id = ?",
            (_encode_payload(rows, usage.model_dump(), verdict), run_id),
        )
        conn.commit()


def save_run_verdict(
    run_id: int,
    verdict: ModelVerdict,
    path: Path | None = None,
) -> None:
    db = path or default_db_path()
    if not db.is_file():
        return
    with _connect(db) as conn:
        found = conn.execute(
            "SELECT payload FROM runs WHERE id = ?",
            (run_id,),
        ).fetchone()
        if found is None:
            return
        try:
            rows, usage, _old = _payload_parts(str(found[0]))
        except (json.JSONDecodeError, ValueError, TypeError):
            return
        conn.execute(
            "UPDATE runs SET payload = ? WHERE id = ?",
            (_encode_payload(rows, usage, verdict.model_dump()), run_id),
        )
        conn.commit()


def titles_from_payload(raw: str) -> tuple[str, ...]:
    items, _usage = _row_dicts(raw)
    titles: list[str] = []
    for item in items:
        title = item.get("title")
        if isinstance(title, str) and title.strip():
            titles.append(title.strip())
        else:
            titles.append("без названия")
    return tuple(titles)


def format_run_date(created_at: str) -> str:
    text = created_at.strip()
    try:
        parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError:
        return text
    return parsed.strftime("%Y-%m-%d %H:%M")


def run_select_label(run_id: int, created_at: str, titles: Sequence[str]) -> str:
    names = " / ".join(titles) if titles else "без названий"
    return f"#{run_id} — {format_run_date(created_at)} — {names}"


def list_runs(path: Path | None = None) -> list[tuple[int, str]]:
    db = path or default_db_path()
    if not db.is_file():
        return []
    with _connect(db) as conn:
        found = conn.execute(
            "SELECT id, created_at, payload FROM runs ORDER BY id DESC LIMIT 20"
        ).fetchall()
    listed: list[tuple[int, str]] = []
    for item in found:
        run_id = int(item[0])
        created_at = str(item[1])
        try:
            titles = titles_from_payload(str(item[2]))
        except (json.JSONDecodeError, ValueError, TypeError):
            titles = ()
        listed.append((run_id, run_select_label(run_id, created_at, titles)))
    return listed


COLLECT_CACHE_VERSION = "2026-09-03-hide-review-fields"


def collect_cache_key(
    venue_ids: Sequence[str],
    legal_choices: Mapping[str, str],
) -> tuple[str, tuple[str, ...], tuple[tuple[str, str], ...]]:
    return (
        COLLECT_CACHE_VERSION,
        tuple(venue_ids),
        tuple(sorted(legal_choices.items())),
    )


def rows_from_cache(
    cache: dict[object, list[PlaceRecord]],
    key: object,
    factory: Callable[[], list[PlaceRecord]],
) -> tuple[list[PlaceRecord], bool]:
    cached = cache.get(key)
    if cached is not None:
        return cached, False
    rows = factory()
    cache[key] = rows
    return rows, True
