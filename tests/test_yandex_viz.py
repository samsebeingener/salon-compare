from pytest import MonkeyPatch

from salon_compare.collect import PlaceRecord, SourcedField, Trust, coerce_place_record
from salon_compare.yandex_viz import (
    MapPoint,
    build_yandex_map_html,
    compute_map_viewport,
    geocode_yandex_http,
    has_map_data,
    markers_from_rows,
    parse_geocode_response,
    resolve_marker_coords,
    yandex_geocoder_key,
    yandex_maps_js_key,
)


def _row(
    *,
    title: str = "Салон",
    address: str | None = None,
    lat: float | None = None,
    lon: float | None = None,
) -> PlaceRecord:
    gap = SourcedField()
    address_field = (
        SourcedField(
            value=address, trust=Trust.FOUND, source_url="https://2gis.example"
        )
        if address
        else gap
    )
    return PlaceRecord(
        venue_id="v1",
        title=title,
        twogis_rating=gap,
        twogis_review_count=gap,
        address=address_field,
        neighbor_count=gap,
        neighbor_vs=gap,
        site_about=gap,
        egrul_registered_at=gap,
        egrul_status=gap,
        egrul_activity=gap,
        fedresurs=gap,
        kad=gap,
        map_lat=lat,
        map_lon=lon,
    )


def test_markers_from_rows_uses_coords_and_address() -> None:
    rows = [
        _row(title="A", address="ул. Баумана, 1", lat=55.77, lon=37.68),
        _row(title="B"),
    ]
    points = markers_from_rows(rows)
    assert points[0].title == "A"
    assert points[0].address == "ул. Баумана, 1"
    assert points[0].lat == 55.77
    assert points[0].lon == 37.68
    assert points[1].address is None


def test_has_map_data_true_for_coords_or_address() -> None:
    assert has_map_data([markers_from_rows([_row(lat=55.0, lon=37.0)])[0]])
    assert has_map_data([markers_from_rows([_row(address="Москва")])[0]])
    assert has_map_data([markers_from_rows([_row(title="Вишня")])[0]])
    assert not has_map_data([MapPoint(" ", None, None, None)])


def test_parse_geocode_response_reads_lon_lat() -> None:
    payload = {
        "response": {
            "GeoObjectCollection": {
                "featureMember": [
                    {"GeoObject": {"Point": {"pos": "37.618423 55.751244"}}}
                ]
            }
        }
    }
    assert parse_geocode_response(payload) == (55.751244, 37.618423)


def test_resolve_marker_coords_keeps_twogis_coords(monkeypatch: MonkeyPatch) -> None:
    def fail_geocode(*_args: object, **_kwargs: object) -> None:
        raise AssertionError("geocode should not run when coords exist")

    monkeypatch.setattr(
        "salon_compare.yandex_viz.geocode_yandex_http",
        fail_geocode,
    )
    points = markers_from_rows([_row(lat=55.74, lon=37.65)])
    resolved, stats = resolve_marker_coords(points, "key")
    assert stats.placed == 1
    assert resolved[0].lat == 55.74


def test_build_yandex_map_html_embeds_coords_without_client_geocode() -> None:
    row = _row(title="Вишня", address="Таганская", lat=55.74, lon=37.65)
    html = build_yandex_map_html(markers_from_rows([row]), "test-key-123")
    assert "apikey=test-key-123" in html
    assert "Вишня" in html
    assert "55.74" in html
    assert "ymaps.ready" in html
    assert "resolvePoint" not in html
    assert "zoom: 15" in html
    assert "SINGLE_ZOOM" in html


def test_compute_map_viewport_single_point_is_close() -> None:
    point = MapPoint("Вишня", "Таганская", 55.74, 37.65)
    viewport = compute_map_viewport([point])
    assert viewport.zoom == 15
    assert viewport.center_lat == 55.74
    assert viewport.center_lon == 37.65


def test_compute_map_viewport_cluster_never_below_min_zoom() -> None:
    points = [
        MapPoint("A", None, 55.740, 37.650),
        MapPoint("B", None, 55.745, 37.655),
        MapPoint("C", None, 55.748, 37.658),
    ]
    viewport = compute_map_viewport(points)
    assert viewport.zoom >= 13


def test_build_yandex_map_html_empty_without_coords() -> None:
    html = build_yandex_map_html(
        [MapPoint("X", "адрес", None, None)],
        "test-key-123",
    )
    assert "Метки не поставлены" in html


def test_markers_from_rows_legacy_payload_without_map_coords() -> None:
    data = _row(address="ул. Таганская, 1").model_dump()
    data.pop("map_lat", None)
    data.pop("map_lon", None)
    row = coerce_place_record(data)
    assert row is not None
    points = markers_from_rows([row])
    assert points[0].address == "ул. Таганская, 1"
    assert points[0].lat is None


def test_geocode_yandex_http_returns_none_on_http_error(
    monkeypatch: MonkeyPatch,
) -> None:
    def broken_get(*_args: object, **_kwargs: object) -> None:
        raise OSError("offline")

    monkeypatch.setattr("salon_compare.yandex_viz.httpx.get", broken_get)
    assert geocode_yandex_http("Moscow", "key") is None


def test_yandex_keys_read_separate_env(monkeypatch: MonkeyPatch) -> None:
    monkeypatch.setenv("YANDEX_MAPS_JS_API_KEY", " js-key ")
    monkeypatch.setenv("YANDEX_GEOCODER_API_KEY", " geo-key ")
    assert yandex_maps_js_key() == "js-key"
    assert yandex_geocoder_key() == "geo-key"


def test_resolve_marker_coords_uses_geocoder_key_for_address(
    monkeypatch: MonkeyPatch,
) -> None:
    calls: list[str] = []

    def fake_geocode(query: str, api_key: str) -> tuple[float, float] | None:
        calls.append(api_key)
        return (55.75, 37.62)

    monkeypatch.setattr(
        "salon_compare.yandex_viz.geocode_yandex_http",
        fake_geocode,
    )
    points = markers_from_rows([_row(title="Салон", address="Таганская, 1")])
    resolved, stats = resolve_marker_coords(points, "geocoder-only-key")
    assert stats.placed == 1
    assert calls == ["geocoder-only-key"]
    assert resolved[0].lat == 55.75
