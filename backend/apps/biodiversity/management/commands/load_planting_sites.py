"""Give each census tree its planting site (``emplazamiento``) from the original census.

    python manage.py load_planting_sites [--file PATH] [--dry-run]

The file (default ``apps/biodiversity/data/planting_sites.csv``, the columns ``num_arbol,
X, Y, emplazamiento`` of the Cortolima census ``data/csv/urban_tree_census_ibague.csv``;
that file works too) is matched to the trees by position, not by code: the census code
is not always the tree's id, while every tree sits exactly on its census point. X and Y
are MAGNA-SIRGAS / Colombia Bogotá (EPSG:3116) metres written without the decimal point
(``8828670887`` is 882867.0887): the integer part is always six digits.

A tree takes the site of the census points within ``--tolerance`` metres (1 cm: a tree
and its census point coincide). Where several
census trees share a point and their sites differ, the tree's site cannot be told and is
left empty. Trees added after the census keep theirs. Idempotent: only differences are
written.
"""

import csv
from collections import Counter
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError
from django.db import connection, transaction

from apps.biodiversity.models import BiodiversityRecord

DEFAULT_FILE = Path(__file__).resolve().parents[2] / "data" / "planting_sites.csv"
P = BiodiversityRecord.PlantingSite
SITES = {
    "Parque": P.PARK,
    "Anden": P.SIDEWALK,
    "Separador_vial": P.MEDIAN,
    "Zona_blanda": P.GREEN_STRIP,
    "Alcorque": P.TREE_PIT,
    "Antejardin": P.FRONT_GARDEN,
    "Glorieta": P.ROUNDABOUT,
}
CENSUS_SRID = 3116

MATCH = """
WITH census AS (
    SELECT ST_Transform(ST_SetSRID(ST_MakePoint(x, y), %(srid)s), 4326)::geography AS g,
           site
    FROM unnest(%(x)s::float8[], %(y)s::float8[], %(site)s::text[]) AS c(x, y, site)
)
SELECT r.id, array_agg(DISTINCT c.site) AS sites
FROM biodiversity_biodiversityrecord r
JOIN census c ON ST_DWithin(r.location, c.g, %(tolerance)s)
GROUP BY r.id
"""


def metres(value):
    """``8828670887`` -> 882867.0887 (six integer digits)."""
    value = value.strip()
    if "." in value:
        return float(value)
    if not value.isdigit() or len(value) < 6:
        raise ValueError(value)
    return float(f"{value[:6]}.{value[6:] or 0}")


def read_points(path):
    try:
        with open(path, encoding="utf-8-sig", newline="") as f:
            rows = list(csv.DictReader(f))
    except OSError as e:
        raise CommandError(e) from e
    xs, ys, sites, problems = [], [], [], []
    for line, row in enumerate(rows, start=2):
        try:
            x, y = metres(row["X"]), metres(row["Y"])
            site = SITES[row["emplazamiento"]]
        except KeyError as e:
            raise CommandError(f"line {line}: missing column or unknown site {e}") from e
        except ValueError as e:
            problems.append(f"line {line}: bad coordinate {e}")
            continue
        xs.append(x)
        ys.append(y)
        sites.append(site)
    if problems:
        raise CommandError("\n".join(problems[:20]))
    return xs, ys, sites


class Command(BaseCommand):
    help = "Set each census tree's planting site from the original census, by position."

    def add_arguments(self, parser):
        parser.add_argument("--file", type=Path, default=DEFAULT_FILE)
        parser.add_argument("--tolerance", type=float, default=0.01, help="Metres.")
        parser.add_argument("--dry-run", action="store_true")

    def handle(self, file, tolerance, dry_run, **options):
        xs, ys, sites = read_points(file)
        with connection.cursor() as cur:
            cur.execute(
                MATCH,
                {
                    "srid": CENSUS_SRID,
                    "x": xs,
                    "y": ys,
                    "site": sites,
                    "tolerance": tolerance,
                },
            )
            matched = dict(cur.fetchall())

        site_of = {rid: s[0] for rid, s in matched.items() if len(s) == 1}
        ambiguous = [rid for rid, s in matched.items() if len(s) > 1]
        current = dict(
            BiodiversityRecord.all_objects.values_list("id", "planting_site")
        )
        wanted = {rid: "" for rid in ambiguous} | site_of
        changes = {rid: s for rid, s in wanted.items() if current.get(rid) != s}

        with transaction.atomic():
            records = BiodiversityRecord.all_objects.in_bulk(list(changes))
            for rid, record in records.items():
                record.planting_site = changes[rid]
            BiodiversityRecord.all_objects.bulk_update(
                records.values(), ["planting_site"], batch_size=2000
            )
            if dry_run:
                transaction.set_rollback(True)

        unmatched = len(current) - len(matched)
        counts = Counter(site_of.values())
        self.stdout.write(
            f"{len(xs)} census points; {len(site_of)} trees with a site "
            f"({', '.join(f'{k} {v}' for k, v in counts.most_common())}), "
            f"{len(ambiguous)} on a shared point with different sites (left empty), "
            f"{unmatched} without a census point."
        )
        self.stdout.write(
            f"{'Would update' if dry_run else 'Updated'} {len(changes)} trees."
        )
