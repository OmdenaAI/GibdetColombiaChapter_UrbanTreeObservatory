"""Urban forest indicators for the frontend's Analytics page.

Each block answers one management question about the census:

- ``origin``: how much of it is native?
- ``comunas``: where the trees are, per hectare and per 1,000 inhabitants. Trees are
  placed in a comuna by their coordinates (PostGIS point-in-polygon), not by the
  census' neighborhood field, which leaves ~6,700 trees in an "unknown" comuna.
- ``species_health``: which common species show the most sick, critical or dead trees.
- ``threatened``: trees of species in a threatened IUCN category.

The whole payload is cached: the census changes rarely and the spatial join takes a
few seconds.
"""

from django.core.cache import cache
from django.db import connection
from django.db.models import Count, Q

from apps.biodiversity.models import BiodiversityRecord

from .models import Observation

CACHE_KEY = "reports:analytics:v2"
CACHE_SECONDS = 60 * 60

TOP_SPECIES = 10

ORIGIN_GROUPS = {
    "native": ["NT", "EN", "NC"],
    "introduced": ["CU", "NU", "NL"],
    "not_identified": ["NI"],
}

ISSUES = ["SI", "CR", "DE"]  # sick, critical, dead
THREATENED = ["CR", "EN", "VU"]


def _pct(part, total, digits=1):
    return round(100 * part / total, digits) if total else None


def _fetch(sql, params=None):
    with connection.cursor() as cursor:
        cursor.execute(sql, params or [])
        columns = [c[0] for c in cursor.description]
        return [dict(zip(columns, row, strict=True)) for row in cursor.fetchall()]


def _origin(total):
    counts = dict(
        BiodiversityRecord.objects.values_list("species__origin")
        .annotate(n=Count("id"))
        .values_list("species__origin", "n")
    )
    return [
        {
            "group": group,
            "count": sum(counts.get(c, 0) for c in codes),
            "percent": _pct(sum(counts.get(c, 0) for c in codes), total),
        }
        for group, codes in ORIGIN_GROUPS.items()
    ]


def _comunas():
    """Trees per comuna by location (PostGIS), with density and health."""
    rows = _fetch(
        """
        WITH placed AS (
            -- One comuna per tree, also for points on a shared border.
            SELECT DISTINCT ON (r.id) r.id, l.id AS locality_id
            FROM biodiversity_biodiversityrecord r
            JOIN places_locality l
              ON l.boundary IS NOT NULL AND ST_Intersects(l.boundary, r.location)
            ORDER BY r.id, l.id
        )
        SELECT l.id, l.name, l.population_2019 AS population,
               ST_Area(l.boundary) / 10000.0 AS area_ha,
               count(p.id) AS trees,
               count(p.id) FILTER (WHERE o.phytosanitary_status = ANY(%s)) AS issues
        FROM places_locality l
        LEFT JOIN placed p ON p.locality_id = l.id
        LEFT JOIN reports_observation o ON o.biodiversity_record_id = p.id
        WHERE l.boundary IS NOT NULL
        GROUP BY l.id
        ORDER BY l.id
        """,
        [ISSUES],
    )
    total = BiodiversityRecord.objects.count()
    placed = sum(r["trees"] for r in rows)
    unknown = BiodiversityRecord.objects.filter(
        neighborhood__locality__boundary__isnull=True
    ).count()
    return {
        "results": [
            {
                "id": r["id"],
                "name": r["name"],
                "trees": r["trees"],
                "area_ha": round(r["area_ha"], 1),
                "population": r["population"],
                "trees_per_ha": round(r["trees"] / r["area_ha"], 1)
                if r["area_ha"]
                else None,
                "trees_per_1000_inhabitants": (
                    round(1000 * r["trees"] / r["population"])
                    if r["population"]
                    else None
                ),
                "issues_percent": _pct(r["issues"], r["trees"]),
            }
            for r in rows
        ],
        "outside_comunas": total - placed,
        "unknown_comuna_in_census": unknown,
    }


def _species_health():
    top_ids = list(
        BiodiversityRecord.objects.values("species_id")
        .annotate(n=Count("id"))
        .order_by("-n")
        .values_list("species_id", flat=True)[:TOP_SPECIES]
    )
    rows = (
        Observation.objects.filter(biodiversity_record__species_id__in=top_ids)
        .values(
            "biodiversity_record__species_id",
            "biodiversity_record__species__genus__name",
            "biodiversity_record__species__name",
        )
        .annotate(
            n=Count("biodiversity_record", distinct=True),
            sick=Count("id", filter=Q(phytosanitary_status="SI")),
            critical=Count("id", filter=Q(phytosanitary_status="CR")),
            dead=Count("id", filter=Q(phytosanitary_status="DE")),
        )
    )
    out = [
        {
            "name": f"{r['biodiversity_record__species__genus__name']} "
            f"{r['biodiversity_record__species__name']}",
            "trees": r["n"],
            "sick_percent": _pct(r["sick"], r["n"]),
            "critical_percent": _pct(r["critical"], r["n"]),
            "dead_percent": _pct(r["dead"], r["n"]),
        }
        for r in rows
    ]
    out.sort(
        key=lambda r: -(r["sick_percent"] + r["critical_percent"] + r["dead_percent"])
    )
    return out


def _threatened():
    rows = (
        BiodiversityRecord.objects.filter(species__iucn_status__in=THREATENED)
        .values("species__genus__name", "species__name", "species__iucn_status")
        .annotate(n=Count("id"))
        .order_by("-n")
    )
    by_status = dict.fromkeys(THREATENED, 0)
    for r in rows:
        by_status[r["species__iucn_status"]] += r["n"]
    return {
        "by_status": [{"status": s, "count": n} for s, n in by_status.items()],
        "species": [
            {
                "name": f"{r['species__genus__name']} {r['species__name']}",
                "status": r["species__iucn_status"],
                "count": r["n"],
            }
            for r in rows[:8]
        ],
        "species_count": rows.count(),
    }


def _summary():
    total = BiodiversityRecord.objects.count()
    issues = Observation.objects.filter(phytosanitary_status__in=ISSUES).count()
    origin = _origin(total)
    comunas = _comunas()
    population = sum(c["population"] or 0 for c in comunas["results"])
    return {
        "total_trees": total,
        "population": population,
        "trees_per_1000_inhabitants": round(1000 * total / population)
        if population
        else None,
        "issues_percent": _pct(issues, total),
        "origin": origin,
        "comunas": comunas,
        "species_health": _species_health(),
        "threatened": _threatened(),
    }


def analytics_summary(refresh=False):
    data = None if refresh else cache.get(CACHE_KEY)
    if data is None:
        data = _summary()
        cache.set(CACHE_KEY, data, CACHE_SECONDS)
    return data
