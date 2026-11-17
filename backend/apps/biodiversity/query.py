"""Tree queries from the map: filters and an area of interest, with downloads.

``POST /api/v1/biodiversity/inventory/query/`` with a JSON body::

    {
      "id": 123,                       # tree code (exact)
      "scientific_name": "ficus",      # contains, case-insensitive
      "common_name": "caucho",         # contains, case-insensitive
      "comuna": 7,                     # locality id
      "neighborhood": 245,             # barrio id
      "geometry": {...},               # GeoJSON Polygon or MultiPolygon (lon/lat, WGS84)
      "format": "json" | "csv" | "xlsx" | "geojson",
      "lang": "es" | "en"
    }

Every key is optional; they combine with AND. ``json`` (default) answers with the number of
trees, their points (up to ``MAX_POINTS``, to highlight them on the map) and the bounding box;
the other formats download every matching tree with all the inventory columns (the same as
the CSV export of the Trees page).

``GET /api/v1/biodiversity/inventory/options/``: comunas and barrios (id, name) for the
filter lists, without geometry.
"""

import json

from django.contrib.gis.gdal import GDALException
from django.contrib.gis.geos import GEOSException, GEOSGeometry
from django.http import FileResponse, StreamingHttpResponse
from django.utils import timezone

from apps.places.models import Locality, Neighborhood

from .models import BiodiversityRecord

FORMATS = {"json", "csv", "xlsx", "geojson"}
MAX_POINTS = 20000
MAX_VERTICES = 20000
TEXT_FIELDS = {"scientific_name": 120, "common_name": 120}
XLSX_TYPE = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"


class QueryError(ValueError):
    """A bad request body; the message is returned to the client."""


def _int(data, key):
    value = data.get(key)
    if value in (None, ""):
        return None
    if isinstance(value, bool) or not isinstance(value, (int, str)):
        raise QueryError(f"'{key}' must be an integer.")
    try:
        number = int(value)
    except ValueError as exc:
        raise QueryError(f"'{key}' must be an integer.") from exc
    if number < 1:
        raise QueryError(f"'{key}' must be a positive integer.")
    return number


def _geometry(data):
    raw = data.get("geometry")
    if raw in (None, ""):
        return None
    if not isinstance(raw, dict) or raw.get("type") not in ("Polygon", "MultiPolygon"):
        raise QueryError("'geometry' must be a GeoJSON Polygon or MultiPolygon.")
    try:
        geom = GEOSGeometry(json.dumps(raw), srid=4326)
    except (GDALException, GEOSException, ValueError, TypeError) as exc:
        raise QueryError("'geometry' is not valid GeoJSON.") from exc
    if geom.num_coords > MAX_VERTICES:
        raise QueryError(f"'geometry' has more than {MAX_VERTICES} vertices.")
    if geom.empty:
        raise QueryError("'geometry' is empty.")
    if not geom.valid:
        # Self-intersecting drawings are common; repair instead of refusing them.
        geom = geom.make_valid()
        if geom.geom_type not in ("Polygon", "MultiPolygon", "GeometryCollection"):
            raise QueryError("'geometry' does not enclose an area.")
    return geom


def parse(data):
    """Validated query parameters from the request body."""
    if not isinstance(data, dict):
        raise QueryError("The body must be a JSON object.")
    params = {
        "id": _int(data, "id"),
        "comuna": _int(data, "comuna"),
        "neighborhood": _int(data, "neighborhood"),
        "geometry": _geometry(data),
    }
    for key, max_len in TEXT_FIELDS.items():
        value = data.get(key) or ""
        if not isinstance(value, str) or len(value) > max_len:
            raise QueryError(f"'{key}' must be a text of up to {max_len} characters.")
        params[key] = value.strip()
    fmt = data.get("format") or "json"
    if fmt not in FORMATS:
        raise QueryError(f"'format' must be one of: {', '.join(sorted(FORMATS))}.")
    params["format"] = fmt
    return params


def filter_trees(queryset, params):
    """``queryset`` must be annotated with ``scientific_name`` (see ``inventory_queryset``)."""
    if params["id"]:
        queryset = queryset.filter(id=params["id"])
    if params["scientific_name"]:
        queryset = queryset.filter(scientific_name__icontains=params["scientific_name"])
    if params["common_name"]:
        queryset = queryset.filter(common_name__icontains=params["common_name"])
    if params["comuna"]:
        queryset = queryset.filter(neighborhood__locality_id=params["comuna"])
    if params["neighborhood"]:
        queryset = queryset.filter(neighborhood_id=params["neighborhood"])
    if params["geometry"] is not None:
        queryset = queryset.filter(location__intersects=params["geometry"])
    return queryset


def summary(queryset):
    """Count, points to highlight (``[id, lat, lon]``) and bounding box of the result."""
    count = queryset.count()
    points = [
        [rid, round(loc.y, 7), round(loc.x, 7)]
        for rid, loc in queryset.order_by("id").values_list("id", "location")[
            :MAX_POINTS
        ]
        if loc is not None
    ]
    bbox = None
    if points:
        lats = [p[1] for p in points]
        lons = [p[2] for p in points]
        bbox = [min(lons), min(lats), max(lons), max(lats)]
    return {
        "count": count,
        "points": points,
        "truncated": count > len(points),
        "bbox": bbox,
    }


def _stamp():
    return timezone.now().strftime("%Y-%m-%d")


def xlsx_response(rows, name):
    from .xlsx import write_xlsx

    response = FileResponse(
        write_xlsx(rows, sheet_name="trees"),
        as_attachment=True,
        filename=f"{name}-{_stamp()}.xlsx",
        content_type=XLSX_TYPE,
    )
    return response


def _json_value(value):
    if value is None or isinstance(value, (int, float, str)):
        return value
    return str(value)


def _features(rows):
    rows = iter(rows)
    header = next(rows)
    lat, lon = header.index("latitude"), header.index("longitude")
    first = True
    for row in rows:
        props = {k: _json_value(v) for k, v in zip(header, row, strict=True) if v != ""}
        geometry = (
            {"type": "Point", "coordinates": [row[lon], row[lat]]}
            if row[lat] != "" and row[lon] != ""
            else None
        )
        feature = {"type": "Feature", "geometry": geometry, "properties": props}
        yield ("" if first else ",") + json.dumps(feature, ensure_ascii=False)
        first = False


def geojson_response(rows, name):
    def stream():
        yield '{"type":"FeatureCollection","features":['
        yield from _features(rows)
        yield "]}"

    response = StreamingHttpResponse(stream(), content_type="application/geo+json")
    response["Content-Disposition"] = (
        f'attachment; filename="{name}-{_stamp()}.geojson"'
    )
    return response


def options():
    """Comunas and barrios with trees, for the filter lists."""
    with_trees = BiodiversityRecord.objects.values("neighborhood_id")
    hoods = list(
        Neighborhood.objects.filter(id__in=with_trees)
        .order_by("name")
        .values("id", "name", "locality_id")
    )
    used = {h["locality_id"] for h in hoods}
    comunas = list(
        Locality.objects.filter(id__in=used).order_by("id").values("id", "name")
    )
    return {
        "comunas": comunas,
        "neighborhoods": [
            {"id": h["id"], "name": h["name"], "comuna": h["locality_id"]}
            for h in hoods
        ],
    }


def language(data, default):
    lang = data.get("lang") if isinstance(data, dict) else None
    return lang if lang in ("es", "en") else default
