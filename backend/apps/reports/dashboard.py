"""Figures for the frontend dashboard, computed from the census, taxonomy and climate data.

Everything is aggregated in the database; one call runs about a dozen grouped queries.
Codes (phytosanitary status, ...) are returned as-is so the client can label them.
"""

import datetime

from django.db.models import Avg, Count, Max, Q, Sum
from django.db.models.functions import ExtractYear, TruncMonth

from apps.biodiversity.models import BiodiversityRecord
from apps.climate.models import Climate, Station
from apps.places.models import Locality
from apps.places.statistics import tree_statistics
from apps.taxonomy.models import Species

from .models import Measurement, Observation

# Census dates before this year are data-entry errors (e.g. 1899).
FIRST_VALID_YEAR = 1950

# Total-height histogram bins, in meters: [low, high).
HEIGHT_BINS = [(0, 5), (5, 10), (10, 15), (15, 20), (20, 25), (25, None)]

TOP_SPECIES = 5
RECENT_RECORDS = 5
TEMPERATURE_MONTHS = 12


def _round(value, digits=2):
    return round(value, digits) if value is not None else None


def _trees_per_capita(total_trees):
    population = Locality.objects.aggregate(p=Sum("population_2019"))["p"]
    return {
        "population": population,
        "value": _round(total_trees / population) if population else None,
    }


def _health():
    rows = Observation.objects.values("phytosanitary_status").annotate(n=Count("id"))
    return {row["phytosanitary_status"]: row["n"] for row in rows}


def _top_species(total_trees):
    rows = list(
        BiodiversityRecord.objects.values("species_id")
        .annotate(n=Count("id"))
        .order_by("-n")[:TOP_SPECIES]
    )
    names = {
        s.id: s
        for s in Species.objects.select_related("genus").filter(
            id__in=[r["species_id"] for r in rows]
        )
    }
    return [
        {
            "species_id": r["species_id"],
            "scientific_name": names[r["species_id"]].scientific_name,
            "count": r["n"],
            "percent": _round(100 * r["n"] / total_trees) if total_trees else 0,
        }
        for r in rows
    ]


def _records_by_year():
    rows = (
        BiodiversityRecord.objects.annotate(year=ExtractYear("date"))
        .values("year")
        .annotate(n=Count("id"))
        .order_by("year")
    )
    years, invalid = [], 0
    for r in rows:
        if r["year"] is None or r["year"] < FIRST_VALID_YEAR:
            invalid += r["n"]
        else:
            years.append({"year": r["year"], "count": r["n"]})
    return {"years": years, "invalid_dates": invalid}


def _height_distribution():
    heights = Measurement.objects.filter(
        attribute=Measurement.MeasuredAttribute.TOTAL_HEIGHT
    )
    aggregates = {}
    for low, high in HEIGHT_BINS:
        cond = Q(value__gte=low) if high is None else Q(value__gte=low, value__lt=high)
        aggregates[f"{low}"] = Count("id", filter=cond)
    counts = heights.aggregate(**aggregates)
    return [
        {"from_m": low, "to_m": high, "count": counts[f"{low}"]}
        for low, high in HEIGHT_BINS
    ]


def _localities():
    stats = tree_statistics("neighborhood__locality_id")
    return [
        {"id": loc.id, "name": loc.name, **stats[loc.id]}
        for loc in Locality.objects.order_by("id")
        if loc.id in stats
    ]


def _functional_groups():
    rows = (
        BiodiversityRecord.objects.values("species__functional_group__group_id")
        .annotate(n=Count("id"))
        .order_by("species__functional_group__group_id")
    )
    return [
        {"group": r["species__functional_group__group_id"], "count": r["n"]}
        for r in rows
    ]


def _temperature():
    """Monthly mean per station over the last 12 months with data.

    One series per station: stations report in different periods and at very different
    rates (31 to ~1400 readings a month) and altitudes, so a single mean of all readings
    would mostly show which stations happened to report.
    """
    last = Climate.objects.aggregate(d=Max("date"))["d"]
    if last is None:
        return {"months": [], "stations": []}
    start = (last.replace(day=1) - datetime.timedelta(days=330)).replace(day=1)
    rows = (
        Climate.objects.filter(date__gte=start)
        .annotate(month=TruncMonth("date"))
        .values("month", "station__name")
        .annotate(avg=Avg("value"))
        .order_by("month")
    )
    months = sorted({r["month"].strftime("%Y-%m") for r in rows})[-TEMPERATURE_MONTHS:]
    series = {}
    for r in rows:
        month = r["month"].strftime("%Y-%m")
        if month in months:
            name = r["station__name"].strip()
            series.setdefault(name, {})[month] = _round(r["avg"], 1)
    return {
        "months": months,
        "stations": [
            {"station": name, "values": [values.get(m) for m in months]}
            for name, values in sorted(series.items())
        ],
    }


def _recent_records():
    records = list(
        BiodiversityRecord.objects.select_related(
            "species__genus", "neighborhood__locality"
        )
        .exclude(date__isnull=True)
        .order_by("-date", "-id")[:RECENT_RECORDS]
    )
    ids = [r.id for r in records]
    heights = dict(
        Measurement.objects.filter(
            biodiversity_record_id__in=ids,
            attribute=Measurement.MeasuredAttribute.TOTAL_HEIGHT,
        ).values_list("biodiversity_record_id", "value")
    )
    health = dict(
        Observation.objects.filter(biodiversity_record_id__in=ids).values_list(
            "biodiversity_record_id", "phytosanitary_status"
        )
    )
    return [
        {
            "id": r.id,
            "scientific_name": r.species.scientific_name,
            "common_name": r.common_name,
            "date": r.date,
            "height_m": _round(heights.get(r.id)),
            "phytosanitary_status": health.get(r.id),
            "neighborhood": r.neighborhood.name,
            "locality": r.neighborhood.locality.name,
        }
        for r in records
    ]


def _recent_climate():
    """Latest reading of every station."""
    out = []
    for station in Station.objects.order_by("name"):
        last = station.climate_data.order_by("-date").first()
        if last:
            out.append(
                {
                    "station": station.name.strip(),
                    "code": station.code,
                    "date": last.date,
                    "value": last.value,
                    "unit": last.measure_unit,
                    "sensor": last.sensor,
                }
            )
    return out


def dashboard_summary():
    overall = tree_statistics()
    return {
        "overall": overall,
        "trees_per_capita": _trees_per_capita(overall["total_trees"]),
        "phytosanitary_status": _health(),
        "top_species": _top_species(overall["total_trees"]),
        "records_by_year": _records_by_year(),
        "height_distribution": _height_distribution(),
        "localities": _localities(),
        "functional_groups": _functional_groups(),
        "monthly_temperature": _temperature(),
        "recent_records": _recent_records(),
        "recent_climate": _recent_climate(),
    }
