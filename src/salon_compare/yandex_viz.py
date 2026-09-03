"""Яндекс JS API: карта точек только для просмотра, без влияния на индекс."""

from __future__ import annotations

import json
import os
from dataclasses import dataclass

import httpx

from salon_compare.collect import (
    PlaceRecord,
    Trust,
    as_sourced_field,
    coerce_place_record,
)

_MOSCOW_CENTER = (55.751244, 37.618423)
_DEFAULT_ZOOM = 13
_SINGLE_POINT_ZOOM = 15
_MIN_FIT_ZOOM = 13
_GEOCODE_URL = "https://geocode-maps.yandex.ru/1.x/"


@dataclass(frozen=True)
class MapViewport:
    center_lat: float
    center_lon: float
    zoom: int


@dataclass(frozen=True)
class MapPoint:
    title: str
    address: str | None
    lat: float | None
    lon: float | None


@dataclass(frozen=True)
class MapResolveStats:
    placed: int
    total: int
    missing_titles: tuple[str, ...]


def yandex_maps_js_key() -> str:
    return os.environ.get("YANDEX_MAPS_JS_API_KEY", "").strip()


def yandex_geocoder_key() -> str:
    return os.environ.get("YANDEX_GEOCODER_API_KEY", "").strip()


def markers_from_rows(rows: list[PlaceRecord]) -> list[MapPoint]:
    points: list[MapPoint] = []
    for row in rows:
        coerced = coerce_place_record(row)
        item = coerced if coerced is not None else row
        address_field = as_sourced_field(item.address)
        address: str | None = None
        if (
            address_field is not None
            and address_field.trust is not Trust.MISSING
            and address_field.value is not None
        ):
            address = str(address_field.value).strip() or None
        lat = getattr(item, "map_lat", None)
        lon = getattr(item, "map_lon", None)
        points.append(
            MapPoint(
                title=item.title,
                address=address,
                lat=lat,
                lon=lon,
            )
        )
    return points


def has_map_data(points: list[MapPoint]) -> bool:
    for point in points:
        if point.lat is not None and point.lon is not None:
            return True
        if point.address:
            return True
        if point.title.strip():
            return True
    return False


def parse_geocode_response(payload: object) -> tuple[float, float] | None:
    if not isinstance(payload, dict):
        return None
    response = payload.get("response")
    if not isinstance(response, dict):
        return None
    collection = response.get("GeoObjectCollection")
    if not isinstance(collection, dict):
        return None
    members = collection.get("featureMember")
    if not isinstance(members, list) or not members:
        return None
    first = members[0]
    if not isinstance(first, dict):
        return None
    geo = first.get("GeoObject")
    if not isinstance(geo, dict):
        return None
    point = geo.get("Point")
    if not isinstance(point, dict):
        return None
    pos = point.get("pos")
    if not isinstance(pos, str):
        return None
    parts = pos.split()
    if len(parts) != 2:
        return None
    try:
        lon = float(parts[0])
        lat = float(parts[1])
    except ValueError:
        return None
    return lat, lon


def geocode_yandex_http(query: str, api_key: str) -> tuple[float, float] | None:
    text = query.strip()
    if not text or not api_key:
        return None
    try:
        response = httpx.get(
            _GEOCODE_URL,
            params={
                "apikey": api_key,
                "geocode": text,
                "format": "json",
                "results": 1,
            },
            timeout=10.0,
            trust_env=False,
        )
    except (httpx.HTTPError, OSError):
        return None
    if response.status_code >= 400:
        return None
    try:
        payload = response.json()
    except ValueError:
        return None
    return parse_geocode_response(payload)


def _geocode_queries(point: MapPoint) -> list[str]:
    queries: list[str] = []
    if point.address:
        address = point.address
        if "москва" not in address.casefold():
            address = f"Москва, {address}"
        queries.append(address)
    title = point.title.strip()
    if title:
        queries.append(f"Москва, {title}")
    unique: list[str] = []
    for item in queries:
        if item not in unique:
            unique.append(item)
    return unique


def resolve_marker_coords(
    points: list[MapPoint],
    api_key: str,
) -> tuple[list[MapPoint], MapResolveStats]:
    resolved: list[MapPoint] = []
    missing: list[str] = []
    for point in points:
        if point.lat is not None and point.lon is not None:
            resolved.append(point)
            continue
        coords: tuple[float, float] | None = None
        for query in _geocode_queries(point):
            coords = geocode_yandex_http(query, api_key)
            if coords is not None:
                break
        if coords is None:
            missing.append(point.title)
            resolved.append(point)
            continue
        lat, lon = coords
        resolved.append(
            MapPoint(
                title=point.title,
                address=point.address,
                lat=lat,
                lon=lon,
            )
        )
    placed = sum(
        1 for point in resolved if point.lat is not None and point.lon is not None
    )
    return resolved, MapResolveStats(
        placed=placed,
        total=len(points),
        missing_titles=tuple(missing),
    )


def _plottable(points: list[MapPoint]) -> list[MapPoint]:
    return [
        point for point in points if point.lat is not None and point.lon is not None
    ]


def compute_map_viewport(points: list[MapPoint]) -> MapViewport:
    mapped = _plottable(points)
    if not mapped:
        center_lat, center_lon = _MOSCOW_CENTER
        return MapViewport(
            center_lat=center_lat,
            center_lon=center_lon,
            zoom=_DEFAULT_ZOOM,
        )

    lats = [point.lat for point in mapped if point.lat is not None]
    lons = [point.lon for point in mapped if point.lon is not None]
    center_lat = sum(lats) / len(lats)
    center_lon = sum(lons) / len(lons)

    if len(mapped) == 1:
        return MapViewport(
            center_lat=center_lat,
            center_lon=center_lon,
            zoom=_SINGLE_POINT_ZOOM,
        )

    lat_span = max(lats) - min(lats)
    lon_span = max(lons) - min(lons)
    span = max(lat_span, lon_span, 0.004)

    if span < 0.006:
        zoom = 15
    elif span < 0.015:
        zoom = 14
    elif span < 0.04:
        zoom = 13
    elif span < 0.08:
        zoom = 12
    else:
        zoom = 11

    return MapViewport(
        center_lat=center_lat,
        center_lon=center_lon,
        zoom=max(zoom, _MIN_FIT_ZOOM),
    )


def _empty_map_html(message: str) -> str:
    safe = json.dumps(message, ensure_ascii=False)
    return f"""<!DOCTYPE html>
<html lang="ru">
<head>
  <meta charset="utf-8" />
  <style>
    body {{
      margin: 0;
      font-family: sans-serif;
      display: flex;
      align-items: center;
      justify-content: center;
      height: 100vh;
      color: #444;
      padding: 1rem;
      text-align: center;
    }}
  </style>
</head>
<body><p id="msg"></p>
<script>document.getElementById("msg").textContent = {safe};</script>
</body>
</html>"""


def build_yandex_map_html(points: list[MapPoint], api_key: str) -> str:
    mapped = _plottable(points)
    if not mapped:
        return _empty_map_html(
            "Метки не поставлены: нет координат 2ГИС и геокодер не нашёл адрес."
        )
    payload = json.dumps(
        [
            {
                "title": point.title,
                "address": point.address,
                "lat": point.lat,
                "lon": point.lon,
            }
            for point in mapped
        ],
        ensure_ascii=False,
    )
    viewport = compute_map_viewport(mapped)
    return f"""<!DOCTYPE html>
<html lang="ru">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <script src="https://api-maps.yandex.ru/2.1/?apikey={api_key}&lang=ru_RU"></script>
  <style>
    html, body, #map {{ margin: 0; padding: 0; width: 100%; height: 100%; }}
  </style>
</head>
<body>
  <div id="map"></div>
  <script>
    const POINTS = {payload};
    const COLORS = ["#E53935", "#43A047", "#1E88E5"];
    const MIN_ZOOM = {_MIN_FIT_ZOOM};
    const SINGLE_ZOOM = {_SINGLE_POINT_ZOOM};

    ymaps.ready(function () {{
      const map = new ymaps.Map("map", {{
        center: [{viewport.center_lat}, {viewport.center_lon}],
        zoom: {viewport.zoom},
        controls: ["zoomControl", "typeSelector", "fullscreenControl"],
      }});
      const collection = new ymaps.GeoObjectCollection();
      POINTS.forEach(function (point, index) {{
        collection.add(new ymaps.Placemark(
          [point.lat, point.lon],
          {{
            balloonContentHeader: point.title,
            balloonContentBody: point.address || "адрес не найден",
          }},
          {{ preset: "islands#circleIcon", iconColor: COLORS[index % COLORS.length] }}
        ));
      }});
      map.geoObjects.add(collection);
      if (POINTS.length === 1) {{
        map.setCenter([POINTS[0].lat, POINTS[0].lon], SINGLE_ZOOM);
        return;
      }}
      const bounds = collection.getBounds();
      if (!bounds) {{
        return;
      }}
      map.setBounds(bounds, {{
        checkZoomRange: true,
        zoomMargin: 48,
      }}).then(function () {{
        if (map.getZoom() < MIN_ZOOM) {{
          map.setZoom(MIN_ZOOM);
        }}
      }});
    }});
  </script>
</body>
</html>"""
