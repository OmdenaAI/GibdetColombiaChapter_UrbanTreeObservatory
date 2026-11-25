"""Give census trees without a survey date the date their neighbours were measured.

The census spreadsheet stores some empty dates as 1899-12-30, the zero of Excel's date
serial numbers. Those trees take the most frequent census DBH date of the trees within
``--radius`` metres (ties: the earliest), since a field crew surveys a block on the
same days. The record's date and its census measurements are updated; study values,
which carry their own date, are not touched. The initial import runs it after loading
the census. Idempotent.

    python manage.py fix_census_dates [--radius 200] [--dry-run]
"""

import datetime

from django.core.management.base import BaseCommand
from django.db import connection, transaction

from apps.reports.models import refresh_latest

EXCEL_EPOCH = datetime.date(1899, 12, 30)

IMPUTE = """
WITH target AS (
    SELECT r.id, r.location
    FROM biodiversity_biodiversityrecord r
    WHERE r.date = %(epoch)s
),
votes AS (
    SELECT t.id, m.date, count(*) AS n
    FROM target t
    JOIN biodiversity_biodiversityrecord n ON n.id <> t.id
         AND ST_DWithin(n.location, t.location, %(radius)s)
    JOIN reports_measurement m ON m.biodiversity_record_id = n.id
         AND m.attribute = 'DBH' AND m.study_id IS NULL
         AND m.date IS NOT NULL AND m.date <> %(epoch)s
    GROUP BY t.id, m.date
)
SELECT DISTINCT ON (id) id, date, n
FROM votes
ORDER BY id, n DESC, date
"""


class Command(BaseCommand):
    help = "Date census trees with an empty (1899-12-30) date from their neighbours."

    def add_arguments(self, parser):
        parser.add_argument("--radius", type=float, default=200, help="Metres.")
        parser.add_argument("--dry-run", action="store_true")

    def handle(self, radius, dry_run, **options):
        with transaction.atomic():
            with connection.cursor() as cur:
                cur.execute(IMPUTE, {"epoch": EXCEL_EPOCH, "radius": radius})
                dates = cur.fetchall()
                for record_id, date, votes in dates:
                    cur.execute(
                        "UPDATE biodiversity_biodiversityrecord SET date = %s "
                        "WHERE id = %s",
                        [date, record_id],
                    )
                    cur.execute(
                        "UPDATE reports_measurement SET date = %s "
                        "WHERE biodiversity_record_id = %s AND study_id IS NULL "
                        "AND date = %s",
                        [date, record_id, EXCEL_EPOCH],
                    )
                    self.stdout.write(
                        f"tree {record_id}: {date} ({votes} neighbour measurements "
                        f"within {radius:g} m)"
                    )
            refresh_latest([record_id for record_id, _, _ in dates])
            if dry_run:
                transaction.set_rollback(True)
        self.stdout.write(
            f"{'Would date' if dry_run else 'Dated'} {len(dates)} trees from their "
            "neighbours."
        )
