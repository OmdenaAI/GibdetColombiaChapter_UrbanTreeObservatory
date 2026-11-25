"""Set each species' recommended planting sites from the suitability matrix.

    python manage.py load_planting_site_suitability [--file PATH] [--dry-run]

The file (default ``apps/taxonomy/data/planting_site_suitability.csv``) codes, for each
species of the *Manual de arborización para el departamento del Tolima* (Cortolima –
Jardín Botánico San Jorge, 2017), every planting site of the census from the text of its
"Localización recomendada" section:

- ``A`` apt: the text recommends the site (or "green areas" in general, for park and
  green strip);
- ``C`` conditional: allowed with a condition the census does not record (a minimum
  width, wide front gardens, large containers, non-mixed medians...);
- ``N`` not apt: discouraged, or excluded by an explicit restriction (roots that lift
  sidewalks or damage the road -> sidewalk and tree pit; "not near houses" -> front
  garden; "only wide spaces" -> sidewalk and tree pit);
- ``?`` the text does not address the site.

Columns: ``species`` (genus and species, as the platform names it) and one per site code
of ``BiodiversityRecord.PlantingSite``. A species' recommended sites are those coded A or
C. The matrix is the project's coding, not the manual's text (which is not in this
repository). Species of the platform not in the file are left untouched; a species in
the file that the platform lacks is reported. Idempotent: only differences are written.
"""

import csv
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from apps.biodiversity.models import BiodiversityRecord
from apps.taxonomy.models import Species

DEFAULT_FILE = (
    Path(__file__).resolve().parents[2] / "data" / "planting_site_suitability.csv"
)
SITES = list(BiodiversityRecord.PlantingSite.values)
RECOMMENDED = {"A", "C"}
CODES = RECOMMENDED | {"N", "?"}


def read_matrix(path):
    """{species name: [recommended site codes, in the PlantingSite order]}."""
    try:
        with open(path, encoding="utf-8-sig", newline="") as f:
            reader = csv.DictReader(f)
            missing = {"species", *SITES} - set(reader.fieldnames or [])
            if missing:
                raise CommandError(f"missing columns: {', '.join(sorted(missing))}")
            rows = list(reader)
    except OSError as e:
        raise CommandError(e) from e
    matrix = {}
    for line, row in enumerate(rows, start=2):
        bad = {row[s] for s in SITES} - CODES
        if bad:
            raise CommandError(f"line {line}: unknown code {', '.join(sorted(bad))}")
        name = row["species"].strip()
        if name in matrix:
            raise CommandError(f"line {line}: {name} is repeated")
        matrix[name] = [s for s in SITES if row[s] in RECOMMENDED]
    return matrix


class Command(BaseCommand):
    help = "Set each species' recommended planting sites from the suitability matrix."

    def add_arguments(self, parser):
        parser.add_argument("--file", type=Path, default=DEFAULT_FILE)
        parser.add_argument("--dry-run", action="store_true")

    def handle(self, file, dry_run, **options):
        matrix = read_matrix(file)
        species = {
            s.scientific_name: s for s in Species.objects.select_related("genus")
        }
        changed = [
            s
            for name, sites in matrix.items()
            if (s := species.get(name)) and s.recommended_planting_sites != sites
        ]
        for s in changed:
            s.recommended_planting_sites = matrix[s.scientific_name]
        with transaction.atomic():
            Species.objects.bulk_update(changed, ["recommended_planting_sites"])
            if dry_run:
                transaction.set_rollback(True)

        unknown = sorted(set(matrix) - set(species))
        with_sites = sum(1 for sites in matrix.values() if sites)
        self.stdout.write(
            f"{len(matrix)} species in the matrix, {with_sites} with a recommended site; "
            f"{'would update' if dry_run else 'updated'} {len(changed)}."
        )
        if unknown:
            self.stdout.write(f"Not in the platform: {', '.join(unknown)}")
