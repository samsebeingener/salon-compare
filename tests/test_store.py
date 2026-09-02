from __future__ import annotations

from pathlib import Path

from salon_compare.collect import PlaceRecord, SourcedField, Trust
from salon_compare.legal import LegalOrg
from salon_compare.store import (
    collect_cache_key,
    load_run,
    rows_from_cache,
    save_run,
)

ROOT = Path(__file__).resolve().parents[1]


def _gap() -> SourcedField:
    return SourcedField()


def _row() -> PlaceRecord:
    weak = SourcedField(
        value="действует",
        source_url="https://www.rusprofile.ru/id/7301223",
        trust=Trust.WEAK,
    )
    return PlaceRecord(
        venue_id="p1",
        title="Ногтевой Сервис",
        yandex_rating=_gap(),
        yandex_review_count=_gap(),
        twogis_rating=_gap(),
        twogis_review_count=_gap(),
        address=_gap(),
        neighbor_count=_gap(),
        neighbor_vs=_gap(),
        site_about=_gap(),
        egrul_registered_at=SourcedField(
            value="01.04.2014",
            source_url="https://www.rusprofile.ru/id/7301223",
            trust=Trust.WEAK,
        ),
        egrul_status=weak,
        egrul_activity=_gap(),
        fedresurs=_gap(),
        kad=_gap(),
        legal_candidates=(LegalOrg("1147746349552", "ООО", "https://egrul.example/1"),),
    )


def test_save_and_load_roundtrip(tmp_path: Path) -> None:
    path = tmp_path / "salon-compare.sqlite"
    run_id = save_run([_row()], path)
    listed = load_run(run_id, path)
    assert listed is not None
    assert len(listed) == 1
    place = listed[0]
    assert place.title == "Ногтевой Сервис"
    assert place.egrul_status.trust is Trust.WEAK
    assert place.egrul_status.value == "действует"
    assert place.egrul_registered_at.value == "01.04.2014"
    assert place.legal_candidates[0].ogrn == "1147746349552"
    assert path.is_file()


def test_load_does_not_need_html(tmp_path: Path) -> None:
    path = tmp_path / "db.sqlite"
    run_id = save_run([_row()], path)
    loaded = load_run(run_id, path)
    assert loaded is not None
    assert loaded[0].egrul_status.source_url is not None


def test_same_cache_key_skips_factory() -> None:
    calls = {"n": 0}

    def factory() -> list[PlaceRecord]:
        calls["n"] += 1
        return [_row()]

    key = collect_cache_key(["a", "b", "c"], {"a": "1"})
    cache: dict[object, list[PlaceRecord]] = {}
    first, wrote = rows_from_cache(cache, key, factory)
    second, wrote_again = rows_from_cache(cache, key, factory)
    assert wrote is True
    assert wrote_again is False
    assert calls["n"] == 1
    assert first[0].venue_id == second[0].venue_id


def test_app_opens_saved_without_new_search() -> None:
    text = (ROOT / "src" / "salon_compare" / "app.py").read_text(encoding="utf-8")
    lowered = text.lower()
    assert "сохранённый" in lowered or "сохраненный" in lowered
    assert "нового поиска нет" in lowered
    assert "save_run" in text
    assert "collected_rows" in text or "rows_from_cache" in text
    assert "покупай" not in lowered


def test_readme_mentions_sqlite() -> None:
    text = (ROOT / "README.md").read_text(encoding="utf-8").lower()
    assert "sqlite" in text
