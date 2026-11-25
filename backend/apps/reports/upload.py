"""Update the tree database from a file sent on the Reports page.

The file has one row per tree (Excel, CSV, a zipped Shapefile or GeoJSON) and uses the
columns of the map's downloads, so a download can be edited and sent back. Only ``id`` is
required; an empty cell means "no change".

- ``id`` not in the database: a **new tree** with that code (it needs ``scientific_name``
  and a location; its barrio comes from ``neighborhood`` or from its location).
- ``id`` of an existing tree: its **data are updated** (common and scientific name, barrio,
  site, location, dates...).
- Measurements (``total_height_m``, ``dbh_cm``...) and observations (``phytosanitary_status``,
  ...) are **added** as new rows dated ``measurement_date``, when they differ from the
  tree's latest ones: the previous values stay as its history.

``check`` reads and validates the whole file and returns what would change; nothing is
written while a row has an error. ``apply`` writes the same changes in one transaction.
"""

import contextlib
import csv
import datetime
import io
import json
import math
import re
import shutil
import tempfile
import unicodedata
import zipfile
from dataclasses import dataclass, field
from pathlib import Path

from django.contrib.gis.gdal import DataSource, GDALException
from django.contrib.gis.gdal.libgdal import lgdal
from django.contrib.gis.geos import Point
from django.db import connection, transaction
from django.utils import timezone, translation
from django.utils.translation import gettext as _

from apps.biodiversity.models import BiodiversityRecord
from apps.places.models import Neighborhood, Site
from apps.taxonomy.models import Species

from .models import Measurement, Observation, refresh_latest

MAX_BYTES = 20 * 1024 * 1024
MAX_ROWS = 20_000
MAX_ERRORS = 200  # listed in the summary (all are counted)
MAX_CHANGES = 300  # listed in the summary (all are counted)
# Locations farther than this (degrees, ~5 km) from every comuna are refused: it catches
# swapped latitude / longitude and points of another city.
MAX_DISTANCE_DEG = 0.05

FORMATS = {
    ".xlsx": "xlsx",
    ".csv": "csv",
    ".zip": "shapefile",
    ".geojson": "geojson",
    ".json": "geojson",
}

MEASUREMENTS = {
    "total_height_m": (Measurement.MeasuredAttribute.TOTAL_HEIGHT, "m"),
    "dbh_cm": (Measurement.MeasuredAttribute.DIAMETER_BH, "cm"),
    "trunk_height_m": (Measurement.MeasuredAttribute.TRUNK_HEIGHT, "m"),
    "crown_diameter_m": (Measurement.MeasuredAttribute.CROWN_DIAMETER, "m"),
    "volume_m3": (Measurement.MeasuredAttribute.VOLUME, "m3"),
    "wood_density_g_cm3": (Measurement.MeasuredAttribute.WOOD_DENSITY, "g/cm3"),
}
OBSERVATIONS = [
    "phytosanitary_status",
    "physical_condition",
    "foliage_density",
    "growth_phase",
    "photo_url",
]
TREE_COLUMNS = [
    "id",
    "common_name",
    "scientific_name",
    "neighborhood",
    "comuna",
    "site",
    "latitude",
    "longitude",
    "record_date",
    "recorded_by",
    "elevation_m",
]
DATE_COLUMN = "measurement_date"
COLUMNS = [*TREE_COLUMNS, *MEASUREMENTS, DATE_COLUMN, *OBSERVATIONS]
# Other names accepted for a column (the downloads call the date last_measurement_date).
ALIASES = {
    "last_measurement_date": DATE_COLUMN,
    "lat": "latitude",
    "lon": "longitude",
    "lng": "longitude",
}
# In the downloads but derived from other data: read, never written.
DERIVED = {"family"}

# The XLSX reader takes the first row as the header, whatever its cells hold.
lgdal.CPLSetConfigOption(b"OGR_XLSX_HEADERS", b"FORCE")


class UploadError(Exception):
    """The file cannot be read at all (as opposed to errors in some rows)."""


def file_format(name):
    return FORMATS.get(Path(name).suffix.lower())


def _key(text):
    """Header / name for matching: no accents, lower case, words joined by ``_``."""
    text = unicodedata.normalize("NFKD", str(text)).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]+", "_", text.lower()).strip("_")


def _column_names():
    names = {c: c for c in COLUMNS} | ALIASES | dict.fromkeys(DERIVED)
    # Shapefile (DBF) field names are cut at 10 characters.
    for name, column in list(names.items()):
        names.setdefault(name[:10], column)
    return names


COLUMN_NAMES = _column_names()


# --- Reading -----------------------------------------------------------------------------


@dataclass
class Table:
    """The file's rows: ``rows`` are ``(row number, {column: value}, geometry)``; the
    geometry is ``(lon, lat)``, a geometry type name that is not a point, or ``None``."""

    columns: list
    ignored: list
    rows: list
    by_feature: bool  # numbered by feature (GeoJSON, Shapefile) instead of by line


def read_table(path, fmt):
    readers = {
        "csv": _read_csv,
        "xlsx": _read_xlsx,
        "geojson": _read_geojson,
        "shapefile": _read_shapefile,
    }
    header, rows = readers[fmt](path)
    columns, ignored, seen = {}, [], {}
    for name in header:
        column = COLUMN_NAMES.get(_key(name), "unknown")
        if column == "unknown":
            ignored.append(name)
        elif column is not None:
            if column in seen:
                raise UploadError(
                    _("Columns “%(a)s” and “%(b)s” are the same column.")
                    % {"a": seen[column], "b": name}
                )
            seen[column] = name
            columns[name] = column
    if "id" not in seen:
        raise UploadError(_("The file has no “id” column (the tree code)."))
    out = []
    for number, values, geometry in rows:
        if len(out) == MAX_ROWS:
            raise UploadError(
                _("The file has more than %(n)s rows; split it.") % {"n": MAX_ROWS}
            )
        cells = {columns[k]: v for k, v in values.items() if k in columns}
        if all(_blank(v) for v in cells.values()) and geometry is None:
            continue
        out.append((number, cells, geometry))
    if not out:
        raise UploadError(_("The file has no rows."))
    return Table(list(seen), ignored, out, by_feature=fmt in {"geojson", "shapefile"})


def _read_csv(path):
    raw = Path(path).read_bytes()
    try:
        text = raw.decode("utf-8-sig")
    except UnicodeDecodeError:
        text = raw.decode("cp1252")  # Excel's "CSV" in Spanish Windows
    try:
        dialect = csv.Sniffer().sniff(text[:4096], delimiters=",;\t")
    except csv.Error:
        dialect = csv.excel
    reader = csv.reader(io.StringIO(text), dialect)
    header = next(reader, None)
    if not header:
        raise UploadError(_("The file is empty."))
    rows = (
        (line, dict(zip(header, cells, strict=False)), None)
        for line, cells in enumerate(reader, start=2)
    )
    return header, rows


def _open_layer(path):
    try:
        source = DataSource(str(path))
    except GDALException as e:
        raise UploadError(_("The file could not be read.")) from e
    if not len(source):
        raise UploadError(_("The file has no data."))
    return source, source[0]


def _read_xlsx(path):
    source, layer = _open_layer(path)
    header = list(layer.fields)

    def rows():
        _keep = source  # the layer is only valid while its data source lives
        for number, feature in enumerate(layer, start=2):
            yield number, {n: feature.get(n) for n in header}, None
        del _keep

    return header, rows()


def _read_shapefile(path):
    try:
        with zipfile.ZipFile(path) as zf:
            shps = [n for n in zf.namelist() if n.lower().endswith(".shp")]
    except zipfile.BadZipFile as e:
        raise UploadError(_("The file is not a valid .zip.")) from e
    if len(shps) != 1:
        raise UploadError(
            _("The .zip must hold one Shapefile (.shp with its .dbf, .shx and .prj).")
        )
    source, layer = _open_layer(f"/vsizip/{Path(path).resolve()}/{shps[0]}")
    header = list(layer.fields)
    srs = layer.srs

    def rows():
        _keep = source
        for number, feature in enumerate(layer, start=1):
            yield number, {n: feature.get(n) for n in header}, _ogr_point(feature, srs)
        del _keep

    return header, rows()


def _ogr_point(feature, srs):
    try:
        geom = feature.geom
    except GDALException:
        return None
    if geom is None or geom.empty:
        return None
    if geom.geom_type.name not in {"Point", "Point25D"}:
        return geom.geom_type.name
    if srs is not None and srs.srid != 4326:
        geom.transform(4326)
    return (geom.x, geom.y)


def _read_geojson(path):
    features = _geojson_features(path)
    header = []
    for f in features:
        for k in f.get("properties") or {}:
            if k not in header:
                header.append(k)
    if "id" not in header and any("id" in f for f in features):
        header.insert(0, "id")

    def rows():
        for number, f in enumerate(features, start=1):
            props = dict(f.get("properties") or {})
            if "id" not in props and "id" in f:
                props["id"] = f["id"]
            yield number, props, _geojson_point(f.get("geometry"))

    return header, rows()


def _geojson_features(path):
    invalid = UploadError(_("The file is not valid GeoJSON."))
    try:
        data = json.loads(Path(path).read_bytes().decode("utf-8-sig"))
    except (UnicodeDecodeError, json.JSONDecodeError) as e:
        raise invalid from e
    if not isinstance(data, dict):
        raise invalid
    crs = json.dumps(data.get("crs") or "")
    if data.get("crs") and "4326" not in crs and "CRS84" not in crs:
        raise UploadError(_("The GeoJSON must use longitude / latitude (WGS 84)."))
    features = (
        data.get("features") if data.get("type") == "FeatureCollection" else [data]
    )
    if not isinstance(features, list) or not all(
        isinstance(f, dict) and f.get("type") == "Feature" for f in features
    ):
        raise invalid
    return features


def _geojson_point(geometry):
    if not isinstance(geometry, dict):
        return None
    if geometry.get("type") != "Point":
        return str(geometry.get("type"))
    coords = geometry.get("coordinates")
    try:
        return (float(coords[0]), float(coords[1]))
    except (TypeError, ValueError, IndexError):
        return "Point"


# --- Values ------------------------------------------------------------------------------


class RowError(Exception):
    def __init__(self, column, message):
        super().__init__(message)
        self.column = column


def _blank(value):
    return (
        value is None
        or (isinstance(value, str) and not value.strip())
        or (isinstance(value, float) and math.isnan(value))
    )


def _text(value, column, max_length):
    text = str(value).strip()
    if isinstance(value, float) and value.is_integer():
        text = str(int(value))
    if len(text) > max_length:
        raise RowError(column, _("At most %(n)s characters.") % {"n": max_length})
    return text


def _number(value, column, minimum=None):
    if isinstance(value, bool):
        raise RowError(column, _("“%(v)s” is not a number.") % {"v": value})
    if isinstance(value, (int, float)):
        number = float(value)
    else:
        text = str(value).strip().replace(" ", "")
        if "," in text and "." not in text:
            text = text.replace(",", ".")  # decimal comma
        try:
            number = float(text)
        except ValueError:
            raise RowError(
                column, _("“%(v)s” is not a number.") % {"v": value}
            ) from None
    if not math.isfinite(number):
        raise RowError(column, _("“%(v)s” is not a number.") % {"v": value})
    if minimum is not None and number < minimum:
        raise RowError(column, _("It cannot be negative."))
    return number


def _tree_id(value):
    if _blank(value):
        raise RowError("id", _("The tree code is missing."))
    try:
        number = _number(value, "id")
    except RowError:
        number = 0.5
    if not number.is_integer() or not 0 < number < 2**31:
        raise RowError("id", _("“%(v)s” is not a valid tree code.") % {"v": value})
    return int(number)


def _date(value, column):
    if isinstance(value, datetime.datetime):
        return value.date()
    if isinstance(value, datetime.date):
        return value
    text = str(value).strip()
    for pattern in ("%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y", "%Y/%m/%d"):
        try:
            date = datetime.datetime.strptime(text[:10], pattern).date()
        except ValueError:
            continue
        if date > timezone.localdate():
            raise RowError(column, _("The date is in the future."))
        return date
    raise RowError(
        column,
        _("“%(v)s” is not a date (use YYYY-MM-DD or DD/MM/YYYY).") % {"v": value},
    )


def _choices(model_field):
    """Accepted spellings (code, English and Spanish label) -> code."""
    out = {}
    for code, label in model_field.flatchoices:
        out[_key(code)] = code
        for lang in ("en", "es"):
            with translation.override(lang):
                out[_key(label)] = code
    return out


# --- Plan --------------------------------------------------------------------------------


@dataclass
class TreePlan:
    row: int
    id: int
    create: bool
    fields: dict = field(default_factory=dict)  # model field -> new value
    shown: list = field(default_factory=list)  # [{"field", "old", "new"}]
    measurements: list = field(default_factory=list)  # [(attribute, value, unit)]
    observation: dict = field(default_factory=dict)  # changed field -> code
    date: datetime.date | None = None
    locate: tuple | None = None  # (lon, lat): barrio from the location (new trees)

    def change(self, name, column, new, old, shown_new=None, shown_old=None):
        """Set a tree field when it differs (always for a new tree), and show it."""
        if not self.create and new == old:
            return
        self.fields[name] = new
        self.shown.append(
            {
                "field": column,
                "old": "" if self.create else _shown(shown_old, old),
                "new": _shown(shown_new, new),
            }
        )

    @property
    def changed(self):
        return self.create or self.fields or self.measurements or self.observation


@dataclass
class Plan:
    format: str
    table: Table
    trees: list = field(default_factory=list)
    errors: list = field(default_factory=list)

    def error(self, row, column, message):
        self.errors.append({"row": row, "column": column, "message": str(message)})

    def summary(self):
        changed = [t for t in self.trees if t.changed]
        return {
            "format": self.format,
            "rows": len(self.table.rows),
            "numbered_by": "feature" if self.table.by_feature else "line",
            "columns": self.table.columns,
            "ignored_columns": self.table.ignored,
            "counts": {
                "created": sum(t.create for t in self.trees),
                "updated": sum(bool(not t.create and t.fields) for t in self.trees),
                "unchanged": len(self.trees) - len(changed),
                "measurements": sum(len(t.measurements) for t in self.trees),
                "observations": sum(bool(t.observation) for t in self.trees),
            },
            "error_count": len(self.errors),
            "errors": sorted(self.errors, key=lambda e: e["row"])[:MAX_ERRORS],
            "changes": [
                {
                    "row": t.row,
                    "id": t.id,
                    "action": "create" if t.create else "update",
                    "date": t.date.isoformat() if t.date else None,
                    "fields": t.shown,
                }
                for t in changed[:MAX_CHANGES]
            ],
        }


class _Catalog:
    """Names in the database, for matching the file's values."""

    def __init__(self):
        self.species = {
            _key(f"{genus} {name}"): (pk, f"{genus} {name}")
            for pk, genus, name in Species.objects.values_list(
                "id", "genus__name", "name"
            )
        }
        self.neighborhoods = {}
        for pk, name, comuna in Neighborhood.objects.values_list(
            "id", "name", "locality__name"
        ):
            self.neighborhoods.setdefault(_key(name), []).append((pk, name, comuna))
        self.sites = {}
        for pk, name in Site.objects.values_list("id", "name"):
            self.sites.setdefault(_key(name), []).append((pk, name))
        unknown = self.neighborhoods.get("desconocido", [])
        self.unknown_neighborhood = unknown[0] if len(unknown) == 1 else None
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT ST_XMin(e), ST_YMin(e), ST_XMax(e), ST_YMax(e) "
                "FROM (SELECT ST_Extent(boundary::geometry) e FROM places_locality) s"
            )
            extent = cursor.fetchone()
        self.extent = extent if extent and extent[0] is not None else None
        self.choices = {
            name: _choices(Observation._meta.get_field(name))
            for name in OBSERVATIONS
            if name != "photo_url"
        }

    def near(self, lon, lat):
        if self.extent is None:
            return True
        x0, y0, x1, y1 = self.extent
        d = MAX_DISTANCE_DEG
        return x0 - d <= lon <= x1 + d and y0 - d <= lat <= y1 + d


def _label(model, name, code):
    if code in (None, ""):
        return ""
    return str(dict(model._meta.get_field(name).flatchoices).get(code, code))


def check(path, fmt, user=None):
    """Read and validate the file; the returned ``Plan`` says what ``apply`` would do."""
    table = read_table(path, fmt)
    plan = Plan(fmt, table)
    catalog = _Catalog()

    ids, seen = {}, {}
    for number, cells, _geometry in table.rows:
        try:
            tree_id = _tree_id(cells.get("id"))
        except RowError as e:
            plan.error(number, e.column, e)
            continue
        if tree_id in seen:
            plan.error(
                number,
                "id",
                _("Tree %(id)s is also in row %(row)s.")
                % {"id": tree_id, "row": seen[tree_id]},
            )
            continue
        seen[tree_id] = number
        ids[number] = tree_id

    existing = {
        r["id"]: r
        for r in BiodiversityRecord.all_objects.filter(id__in=ids.values()).values(
            "id",
            "status",
            "common_name",
            "species_id",
            "species__genus__name",
            "species__name",
            "neighborhood_id",
            "neighborhood__name",
            "site_id",
            "site__name",
            "location",
            "date",
            "recorded_by",
            "elevation_m",
        )
    }
    latest_measurements = {
        (rid, attribute): value
        for rid, attribute, value in Measurement.all_objects.filter(
            biodiversity_record_id__in=existing, is_latest=True
        ).values_list("biodiversity_record_id", "attribute", "value")
    }
    latest_observations = {
        o.biodiversity_record_id: o
        for o in Observation.all_objects.filter(
            biodiversity_record_id__in=existing, is_latest=True
        )
    }
    recorded_by = (user.get_full_name() or user.get_username())[:50] if user else ""

    for number, cells, geometry in table.rows:
        if number not in ids:
            continue
        tree = TreePlan(number, ids[number], create=ids[number] not in existing)
        try:
            _plan_tree(
                tree,
                cells,
                geometry,
                existing.get(tree.id),
                catalog,
                latest_measurements,
                latest_observations.get(tree.id),
                recorded_by,
            )
        except RowError as e:
            plan.error(number, e.column, e)
            continue
        plan.trees.append(tree)

    _locate_new_trees(plan, catalog)
    return plan


def _plan_tree(tree, cells, geometry, current, catalog, measures, observation, by):
    get = {k: v for k, v in cells.items() if not _blank(v)}
    if current and current["status"] != BiodiversityRecord.Status.ACTIVE:
        raise RowError(
            "id",
            _("Tree %(id)s is marked as removed; reactivate it in the admin first.")
            % {"id": tree.id},
        )
    cur = current or {}
    _plan_names(tree, get, cur, catalog)
    _plan_location(tree, get, geometry, cur, catalog)
    _plan_record(tree, get, cur, by)
    _plan_measurements(tree, get, measures)
    _plan_observation(tree, get, observation, catalog)
    if tree.measurements or tree.observation:
        if DATE_COLUMN in get:
            tree.date = _date(get[DATE_COLUMN], DATE_COLUMN)
        elif tree.create and tree.fields.get("date"):
            tree.date = tree.fields["date"]
        else:
            raise RowError(
                DATE_COLUMN, _("New measurements and observations need their date.")
            )


def _plan_names(tree, get, cur, catalog):
    if "common_name" in get:
        new = _text(get["common_name"], "common_name", 100)
        tree.change("common_name", "common_name", new, cur.get("common_name"))
    if "scientific_name" in get:
        found = catalog.species.get(_key(get["scientific_name"]))
        if not found:
            raise RowError(
                "scientific_name",
                _("“%(v)s” is not in the species catalog.")
                % {"v": get["scientific_name"]},
            )
        old_name = (
            f"{cur['species__genus__name']} {cur['species__name']}" if cur else ""
        )
        tree.change(
            "species_id",
            "scientific_name",
            found[0],
            cur.get("species_id"),
            found[1],
            old_name,
        )
    elif tree.create:
        raise RowError("scientific_name", _("A new tree needs its scientific name."))
    if "neighborhood" in get:
        hood = _neighborhood(catalog, get["neighborhood"], get.get("comuna"))
        tree.change(
            "neighborhood_id",
            "neighborhood",
            hood[0],
            cur.get("neighborhood_id"),
            hood[1],
            cur.get("neighborhood__name"),
        )
    if "site" in get:
        sites = catalog.sites.get(_key(get["site"]), [])
        if len(sites) != 1:
            raise RowError(
                "site", _("“%(v)s” is not a known site.") % {"v": get["site"]}
            )
        tree.change(
            "site_id",
            "site",
            sites[0][0],
            cur.get("site_id"),
            sites[0][1],
            cur.get("site__name"),
        )


def _plan_location(tree, get, geometry, cur, catalog):
    point = _location(get, geometry)
    if point is None:
        if tree.create:
            raise RowError(
                "latitude", _("A new tree needs its latitude and longitude.")
            )
        return
    lon, lat = point
    if not catalog.near(lon, lat):
        raise RowError(
            "latitude",
            _(
                "%(lat)s, %(lon)s is not in Ibagué (are latitude and longitude "
                "swapped?)."
            )
            % {"lat": lat, "lon": lon},
        )
    old = cur.get("location")
    moved = old is None or abs(old.x - lon) > 1e-7 or abs(old.y - lat) > 1e-7
    if tree.create or moved:
        tree.change(
            "location",
            "latitude, longitude",
            (lon, lat),
            None,
            f"{lat:.6f}, {lon:.6f}",
            f"{old.y:.6f}, {old.x:.6f}" if old else "",
        )
    if tree.create and "neighborhood_id" not in tree.fields:
        tree.locate = point


def _plan_record(tree, get, cur, by):
    if "record_date" in get:
        new = _date(get["record_date"], "record_date")
        tree.change("date", "record_date", new, cur.get("date"))
    if "recorded_by" in get:
        new = _text(get["recorded_by"], "recorded_by", 50)
        tree.change("recorded_by", "recorded_by", new, cur.get("recorded_by"))
    elif tree.create and by:
        tree.change("recorded_by", "recorded_by", by, None)
    if "elevation_m" in get:
        new = _number(get["elevation_m"], "elevation_m")
        tree.change("elevation_m", "elevation_m", new, cur.get("elevation_m"))


def _plan_measurements(tree, get, measures):
    for column, (attribute, unit) in MEASUREMENTS.items():
        if column not in get:
            continue
        value = _number(get[column], column, minimum=0)
        old = measures.get((tree.id, attribute))
        if old is None or abs(old - value) > 1e-9:
            tree.measurements.append((attribute, value, unit))
            tree.shown.append(
                {"field": column, "old": _shown(None, old), "new": _shown(None, value)}
            )


def _plan_observation(tree, get, observation, catalog):
    for column in OBSERVATIONS:
        if column not in get:
            continue
        new = _observation_value(column, get[column], catalog)
        old = getattr(observation, column, None) if observation else None
        if new == old:
            continue
        tree.observation[column] = new
        if column == "photo_url":
            shown = {"old": old or "", "new": new}
        else:
            shown = {
                "old": _label(Observation, column, old),
                "new": _label(Observation, column, new),
            }
        tree.shown.append({"field": column, **shown})


def _observation_value(column, value, catalog):
    if column == "photo_url":
        return _text(value, column, 255)
    raw = int(value) if isinstance(value, float) and value.is_integer() else value
    code = catalog.choices[column].get(_key(raw))  # growth phase may be a number
    if code is None:
        labels = Observation._meta.get_field(column).flatchoices
        raise RowError(
            column,
            _("“%(v)s” is not a valid value; use one of: %(values)s.")
            % {"v": value, "values": ", ".join(str(lb) for _c, lb in labels)},
        )
    return code


def _shown(display, value):
    if display is not None:
        return str(display)
    if value is None:
        return ""
    if isinstance(value, float):
        return f"{value:g}"
    return str(value)


def _neighborhood(catalog, name, comuna):
    found = catalog.neighborhoods.get(_key(name), [])
    if comuna and len(found) > 1:
        found = [f for f in found if _key(f[2]) == _key(comuna)]
    if not found:
        raise RowError(
            "neighborhood", _("“%(v)s” is not a known barrio.") % {"v": name}
        )
    if len(found) > 1:
        raise RowError(
            "neighborhood",
            _("There are several barrios “%(v)s”; add the comuna column.")
            % {"v": name},
        )
    return found[0]


def _location(get, geometry):
    if isinstance(geometry, str):
        raise RowError(
            "geometry",
            _("The geometry is a %(type)s, not a point.") % {"type": geometry},
        )
    if geometry:
        lon, lat = geometry
    elif "latitude" in get or "longitude" in get:
        if "latitude" not in get or "longitude" not in get:
            raise RowError("latitude", _("Give both latitude and longitude."))
        lat = _number(get["latitude"], "latitude")
        lon = _number(get["longitude"], "longitude")
    else:
        return None
    if not (-90 <= lat <= 90 and -180 <= lon <= 180):
        raise RowError("latitude", _("Latitude or longitude out of range."))
    return lon, lat


def _locate_new_trees(plan, catalog):
    """Barrio of the new trees without a ``neighborhood`` column, from their location."""
    pending = [t for t in plan.trees if t.create and t.locate]
    if not pending:
        return
    with connection.cursor() as cursor:
        cursor.execute(
            """
            SELECT DISTINCT ON (p.i) p.i, n.id, n.name
            FROM unnest(%s::int[], %s::float8[], %s::float8[]) AS p(i, lon, lat)
            JOIN places_neighborhood n
              ON n.boundary IS NOT NULL
             AND ST_Intersects(n.boundary::geometry,
                               ST_SetSRID(ST_MakePoint(p.lon, p.lat), 4326))
            ORDER BY p.i, n.id
            """,
            [
                list(range(len(pending))),
                [t.locate[0] for t in pending],
                [t.locate[1] for t in pending],
            ],
        )
        found = {i: (pk, name) for i, pk, name in cursor.fetchall()}
    for i, tree in enumerate(pending):
        hood = found.get(i) or (
            catalog.unknown_neighborhood[:2] if catalog.unknown_neighborhood else None
        )
        if hood is None:
            plan.error(tree.row, "neighborhood", _("No barrio contains this location."))
            plan.trees.remove(tree)
            continue
        tree.fields["neighborhood_id"] = hood[0]
        tree.shown.append({"field": "neighborhood", "old": "", "new": hood[1]})


# --- Writing -----------------------------------------------------------------------------

OBSERVATION_COPY_SKIP = {
    "id",
    "uuid",
    "created_at",
    "updated_at",
    "biodiversity_record",
    "is_latest",
    "date",
    "study",
}


@transaction.atomic
def apply(plan):
    """Write the plan (it must have no errors); returns the ids of the trees changed."""
    assert not plan.errors
    trees = [t for t in plan.trees if t.changed]
    now = timezone.now()

    def values(tree):
        out = dict(tree.fields)
        if "location" in out:
            out["location"] = Point(*out["location"], srid=4326)
        return out

    new = [BiodiversityRecord(id=t.id, **values(t)) for t in trees if t.create]
    BiodiversityRecord.all_objects.bulk_create(new)
    if new:
        with connection.cursor() as cursor:
            table = BiodiversityRecord._meta.db_table
            cursor.execute(
                f"SELECT setval(pg_get_serial_sequence('{table}', 'id'), "
                f"(SELECT MAX(id) FROM {table}))"
            )

    edited = {t.id: values(t) for t in trees if not t.create and t.fields}
    records = BiodiversityRecord.all_objects.in_bulk(list(edited))
    names = {"updated_at"}
    for pk, fields in edited.items():
        for name, value in fields.items():
            setattr(records[pk], name, value)
            names.add(name)
        records[pk].updated_at = now
    BiodiversityRecord.all_objects.bulk_update(records.values(), sorted(names))

    Measurement.all_objects.bulk_create(
        Measurement(
            biodiversity_record_id=t.id,
            attribute=attribute,
            value=value,
            unit=unit,
            date=t.date,
        )
        for t in trees
        for attribute, value, unit in t.measurements
    )

    observed = [t for t in trees if t.observation]
    previous = {
        o.biodiversity_record_id: o
        for o in Observation.all_objects.filter(
            biodiversity_record_id__in=[t.id for t in observed], is_latest=True
        )
    }
    copied = [
        f.attname
        for f in Observation._meta.concrete_fields
        if f.name not in OBSERVATION_COPY_SKIP
    ]
    observations = []
    for t in observed:
        base = previous.get(t.id)
        fields = {name: getattr(base, name) for name in copied} if base else {}
        fields.update(t.observation)
        observations.append(
            Observation(biodiversity_record_id=t.id, date=t.date, **fields)
        )
    Observation.all_objects.bulk_create(observations)

    changed = [t.id for t in trees]
    refresh_latest(changed)
    return changed


@contextlib.contextmanager
def local_copy(field_file, suffix):
    """The stored file as a local path (the storage may be remote, e.g. S3)."""
    with tempfile.NamedTemporaryFile(suffix=suffix) as tmp:
        with field_file.open("rb") as src:
            shutil.copyfileobj(src, tmp)
        tmp.flush()
        yield tmp.name
