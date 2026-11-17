"""Load the species sheets of the Tolima arborization manual into ``ManualEntry``.

    python manage.py load_manual_tolima [--file PATH]

The JSON file (default ``apps/taxonomy/data/manual_tolima.json``) is produced by
``scripts/manual_tolima/extract.py`` from a copy of the manual's PDF and reviewed by hand:
each entry names the catalog species it belongs to in ``"species"`` (scientific name as in
the catalog). Loading is idempotent: entries are created or updated per species; species
not found are reported.

The file is not in the repository (it is ignored by git): the manual's text belongs to
Cortolima and its license is unknown. Generate it locally (see ``scripts/README.md``).
"""

import json
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.db.models import Value
from django.db.models.functions import Concat

from apps.taxonomy.models import ManualEntry, Species

DEFAULT_FILE = Path(__file__).resolve().parents[2] / "data" / "manual_tolima.json"
FIELDS = ["title", "scientific_name", "family"]


class Command(BaseCommand):
    help = "Load the Tolima arborization manual's species sheets."

    def add_arguments(self, parser):
        parser.add_argument("--file", default=str(DEFAULT_FILE))

    def handle(self, *args, **options):
        path = Path(options["file"])
        if not path.exists():
            raise CommandError(
                f"File not found: {path}. The manual's text is not in the repository; "
                "generate the file from the PDF (see scripts/README.md)."
            )
        entries = json.loads(path.read_text(encoding="utf-8"))
        by_name = {
            s.full: s
            for s in Species.objects.annotate(
                full=Concat("genus__name", Value(" "), "name")
            )
        }
        created = updated = 0
        missing = []
        with transaction.atomic():
            for e in entries:
                species = by_name.get(e["species"])
                if species is None:
                    missing.append(e["species"])
                    continue
                _, was_created = ManualEntry.objects.update_or_create(
                    species=species,
                    defaults={
                        **{f: e.get(f, "") for f in FIELDS},
                        "header": e["header"],
                        "sections": e["sections"],
                        "page_start": e["pages"][0],
                        "page_end": e["pages"][1],
                    },
                )
                created += was_created
                updated += not was_created
        self.stdout.write(
            self.style.SUCCESS(f"Manual entries: {created} created, {updated} updated.")
        )
        if missing:
            self.stdout.write(
                self.style.WARNING(
                    f"{len(missing)} species not in the catalog: {', '.join(missing)}"
                )
            )
