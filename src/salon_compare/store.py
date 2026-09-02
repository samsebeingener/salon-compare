"""SQLite разборы. Ключи API в файл не пишем."""

from __future__ import annotations

import json
import sqlite3
from collections.abc import Callable, Mapping, Sequence
from datetime import UTC, datetime
from pathlib import Path

from salon_compare.collect import PlaceRecord
from salon_compare.legal import LegalOrg


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


def _dump_rows(rows: Sequence[PlaceRecord]) -> str:
    payload: list[dict[str, object]] = []
    for row in rows:
        data = row.model_dump(mode="json")
        data["legal_candidates"] = [
            {"ogrn": item.ogrn, "title": item.title, "source_url": item.source_url}
            for item in row.legal_candidates
        ]
        payload.append(data)
    return json.dumps(payload, ensure_ascii=False)


def _load_rows(raw: str) -> list[PlaceRecord]:
    items = json.loads(raw)
    rows: list[PlaceRecord] = []
    if not isinstance(items, list):
        return rows
    for item in items:
        if not isinstance(item, dict):
            continue
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


def save_run(rows: Sequence[PlaceRecord], path: Path | None = None) -> int:
    db = path or default_db_path()
    created = datetime.now(UTC).replace(microsecond=0).isoformat()
    with _connect(db) as conn:
        cursor = conn.execute(
            "INSERT INTO runs (created_at, payload) VALUES (?, ?)",
            (created, _dump_rows(rows)),
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
