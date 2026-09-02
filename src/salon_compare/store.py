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


def _dump_rows(rows: Sequence[PlaceRecord], usage: LlmUsage | None = None) -> str:
    payload: dict[str, object] = {
        "rows": [],
        "usage": usage.model_dump() if usage is not None else None,
    }
    packed: list[dict[str, object]] = []
    for row in rows:
        data = row.model_dump(mode="json")
        data["legal_candidates"] = [
            {"ogrn": item.ogrn, "title": item.title, "source_url": item.source_url}
            for item in row.legal_candidates
        ]
        packed.append(data)
    payload["rows"] = packed
    return json.dumps(payload, ensure_ascii=False)


def _row_dicts(raw: str) -> tuple[list[dict[str, object]], dict[str, object] | None]:
    data = json.loads(raw)
    if isinstance(data, list):
        return [item for item in data if isinstance(item, dict)], None
    if isinstance(data, dict):
        rows = data.get("rows")
        usage = data.get("usage")
        items = rows if isinstance(rows, list) else []
        usage_dict = usage if isinstance(usage, dict) else None
        return [item for item in items if isinstance(item, dict)], usage_dict
    return [], None


def _load_rows(raw: str) -> list[PlaceRecord]:
    items, _usage = _row_dicts(raw)
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
) -> int:
    db = path or default_db_path()
    created = datetime.now(UTC).replace(microsecond=0).isoformat()
    with _connect(db) as conn:
        cursor = conn.execute(
            "INSERT INTO runs (created_at, payload) VALUES (?, ?)",
            (created, _dump_rows(rows, usage)),
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
            rows, _old = _row_dicts(str(found[0]))
        except (json.JSONDecodeError, ValueError, TypeError):
            return
        payload = {"rows": rows, "usage": usage.model_dump()}
        conn.execute(
            "UPDATE runs SET payload = ? WHERE id = ?",
            (json.dumps(payload, ensure_ascii=False), run_id),
        )
        conn.commit()


def list_runs(path: Path | None = None) -> list[tuple[int, str]]:
    db = path or default_db_path()
    if not db.is_file():
        return []
    with _connect(db) as conn:
        found = conn.execute(
            "SELECT id, created_at FROM runs ORDER BY id DESC LIMIT 20"
        ).fetchall()
    return [(int(item[0]), str(item[1])) for item in found]


def collect_cache_key(
    venue_ids: Sequence[str],
    legal_choices: Mapping[str, str],
) -> tuple[tuple[str, ...], tuple[tuple[str, str], ...]]:
    return (tuple(venue_ids), tuple(sorted(legal_choices.items())))


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
