"""Tree statistics per place, computed from biodiversity records and their measurements."""

from django.db.models import Avg, Count, F

from apps.biodiversity.models import BiodiversityRecord
from apps.reports.models import Measurement


def _round(value):
    return round(value, 2) if value is not None else None


def tree_statistics(group_field=None, records_filter=None):
    """Return tree statistics grouped by a BiodiversityRecord field.

    ``group_field`` is a lookup from BiodiversityRecord, e.g. ``"neighborhood_id"`` or
    ``"neighborhood__locality_id"``; ``None`` returns the city-wide totals.

    Each entry has ``total_trees`` (records), ``species_count`` (distinct species) and
    ``avg_height_m`` (mean of the records' total-height measurements, ``None`` without any).
    Two grouped queries, whatever the number of places. ``records_filter`` (a dict of
    BiodiversityRecord lookups) restricts the records, e.g. ``{"neighborhood_id__in": ids}``.
    """
    records_filter = records_filter or {}
    records = BiodiversityRecord.objects.filter(**records_filter)
    heights = Measurement.objects.filter(
        attribute=Measurement.MeasuredAttribute.TOTAL_HEIGHT,
        **{f"biodiversity_record__{k}": v for k, v in records_filter.items()},
    )

    if group_field is None:
        counts = records.aggregate(
            total_trees=Count("id"), species_count=Count("species", distinct=True)
        )
        avg = heights.aggregate(avg=Avg("value"))["avg"]
        return {**counts, "avg_height_m": _round(avg)}

    counts = records.values(key=F(group_field)).annotate(
        total_trees=Count("id"), species_count=Count("species", distinct=True)
    )
    avgs = {
        row["key"]: row["avg"]
        for row in heights.values(
            key=F(f"biodiversity_record__{group_field}")
        ).annotate(avg=Avg("value"))
    }
    return {
        row["key"]: {
            "total_trees": row["total_trees"],
            "species_count": row["species_count"],
            "avg_height_m": _round(avgs.get(row["key"])),
        }
        for row in counts
        if row["key"] is not None
    }


EMPTY = {"total_trees": 0, "species_count": 0, "avg_height_m": None}


def statistics_response(ids, group_field):
    """Payload for the ``statistics`` actions: one entry per id (zeros when it has no
    trees), plus the city-wide totals under ``overall``."""
    by_id = tree_statistics(group_field)
    return {
        "overall": tree_statistics(),
        "results": [{"id": pk, **by_id.get(pk, EMPTY)} for pk in ids],
    }
