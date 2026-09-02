import json
import sqlite3
from pathlib import Path

from salon_compare.collect import PlaceRecord, SourcedField
from salon_compare.store import load_run

ROOT = Path(__file__).resolve().parents[1]


def test_env_example_has_no_yandex_key() -> None:
    text = (ROOT / ".env.example").read_text(encoding="utf-8")
    assert "TWOGIS_API_KEY" in text
    assert "YANDEX_MAPS_API_KEY" not in text


def test_compose_has_no_yandex_key() -> None:
    text = (ROOT / "compose.yaml").read_text(encoding="utf-8")
    assert "TWOGIS_API_KEY" in text
    assert "YANDEX_MAPS_API_KEY" not in text


def test_maps_http_has_no_yandex_places() -> None:
    text = (ROOT / "src" / "salon_compare" / "maps_http.py").read_text(
        encoding="utf-8"
    )
    assert "YandexPlacesApi" not in text
    assert "search-maps.yandex.ru" not in text
    assert "YANDEX_MAPS_API_KEY" not in text


def test_place_record_has_no_yandex_fields() -> None:
    names = PlaceRecord.model_fields
    assert "yandex_rating" not in names
    assert "yandex_review_count" not in names
    assert "yandex_last_review" not in names
    assert "yandex_reviews_90d" not in names
    assert "yandex_plus_minus" not in names


def test_app_table_has_no_yandex_columns() -> None:
    text = (ROOT / "src" / "salon_compare" / "app.py").read_text(encoding="utf-8")
    assert "Яндекс рейтинг" not in text
    assert "Яндекс отзывы" not in text
    assert 'map_api_from_env("yandex")' not in text


def test_score_does_not_wait_for_second_map() -> None:
    text = (ROOT / "src" / "salon_compare" / "score.py").read_text(encoding="utf-8")
    assert "не ясно какой свежее" not in text
    assert "yandex_rating" not in text


def test_legacy_sqlite_yandex_keys_still_load(tmp_path: Path) -> None:
    gap = SourcedField().model_dump()
    row = {
        "venue_id": "v1",
        "title": "Студия",
        "yandex_rating": {
            "value": 4.9,
            "source_url": "https://yandex.example",
            "trust": "found",
        },
        "yandex_review_count": {
            "value": None,
            "source_url": None,
            "trust": "missing",
        },
        "twogis_rating": {
            "value": 4.1,
            "source_url": "https://2gis.example",
            "trust": "found",
        },
        "twogis_review_count": gap,
        "address": gap,
        "neighbor_count": gap,
        "neighbor_vs": gap,
        "site_about": gap,
        "egrul_registered_at": gap,
        "egrul_status": gap,
        "egrul_activity": gap,
        "fedresurs": gap,
        "kad": gap,
        "legal_candidates": [],
    }
    path = tmp_path / "legacy.sqlite"
    conn = sqlite3.connect(path)
    conn.execute(
        """
        CREATE TABLE runs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            created_at TEXT NOT NULL,
            payload TEXT NOT NULL
        )
        """
    )
    conn.execute(
        "INSERT INTO runs (created_at, payload) VALUES (?, ?)",
        (
            "2026-09-02T00:00:00+00:00",
            json.dumps({"rows": [row], "usage": None}),
        ),
    )
    conn.commit()
    conn.close()
    loaded = load_run(1, path)
    assert loaded is not None
    assert loaded[0].title == "Студия"
    assert loaded[0].twogis_rating.value == 4.1
    assert "yandex_rating" not in type(loaded[0]).model_fields
