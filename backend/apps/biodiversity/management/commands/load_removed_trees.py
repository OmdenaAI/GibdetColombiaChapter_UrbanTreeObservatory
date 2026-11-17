"""Mark the trees that no longer exist, from a versioned CSV.

    python manage.py load_removed_trees [--file PATH] [--dry-run]

The file (default ``apps/biodiversity/data/removed_trees.csv``) has the columns
``id, removed_on (YYYY-MM-DD), reason, note``; ``reason`` is one of ``felled``, ``fallen``,
``dead_standing``, ``transplanted``, ``other``. Each listed tree gets status removed with that
date, reason and note: its census data stays in the database, but the platform no longer
shows it nor counts it. Running it again changes nothing (only differences are written).

The whole file is checked before anything is written: an unknown id, a bad date or reason
stops the command with every problem listed.
"""

import csv
import datetime
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone

from apps.biodiversity.models import BiodiversityRecord

DEFAULT_FILE = Path(__file__).resolve().parents[2] / "data" / "removed_trees.csv"
REASONS = {r.name.lower(): r.value for r in BiodiversityRecord.RemovalReason}
COLUMNS = ["id", "removed_on", "reason", "note"]


def read_rows(path):
    """Validated rows ``{id: (date, reason code, note)}``; raises CommandError."""
    with open(path, encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        if reader.fieldnames != COLUMNS:
            raise CommandError(f"Columns must be {COLUMNS}, found {reader.fieldnames}.")
        rows, problems = {}, []
        for line, row in enumerate(reader, start=2):
            try:
                tree_id = int(row["id"])
            except ValueError:
                problems.append(f"line {line}: bad id {row['id']!r}")
                continue
            try:
                date = datetime.date.fromisoformat(row["removed_on"].strip())
            except ValueError:
                problems.append(f"line {line}: bad date {row['removed_on']!r}")
                continue
            reason = REASONS.get(row["reason"].strip().lower())
            if reason is None:
                problems.append(
                    f"line {line}: reason {row['reason']!r} is not one of "
                    f"{', '.join(REASONS)}"
                )
                continue
            if tree_id in rows:
                problems.append(f"line {line}: id {tree_id} is repeated")
                continue
            rows[tree_id] = (date, reason, row["note"].strip())
    known = set(
        BiodiversityRecord.all_objects.filter(id__in=rows).values_list("id", flat=True)
    )
    problems += [f"id {i} does not exist" for i in sorted(set(rows) - known)]
    if problems:
        raise CommandError("Nothing was changed:\n  " + "\n  ".join(problems))
    return rows


class Command(BaseCommand):
    help = "Mark trees that no longer exist (felled, fallen...) from a CSV."

    def add_arguments(self, parser):
        parser.add_argument("--file", type=Path, default=DEFAULT_FILE)
        parser.add_argument(
            "--dry-run", action="store_true", help="Report without writing."
        )

    def handle(self, *args, file, dry_run, **options):
        rows = read_rows(file)
        records = BiodiversityRecord.all_objects.filter(id__in=rows).order_by("id")
        changed = []
        for record in records:
            date, reason, note = rows[record.id]
            new = (BiodiversityRecord.Status.REMOVED, date, reason, note)
            old = (
                record.status,
                record.removed_on,
                record.removal_reason,
                record.removal_note,
            )
            if old != new:
                (
                    record.status,
                    record.removed_on,
                    record.removal_reason,
                    record.removal_note,
                ) = new
                changed.append(record)

        verb = "Would mark" if dry_run else "Marked"
        if changed and not dry_run:
            now = timezone.now()
            for record in changed:
                record.updated_at = now
            with transaction.atomic():
                BiodiversityRecord.all_objects.bulk_update(
                    changed,
                    [
                        "status",
                        "removed_on",
                        "removal_reason",
                        "removal_note",
                        "updated_at",
                    ],
                )
        self.stdout.write(
            f"{verb} {len(changed)} trees as removed "
            f"({len(rows) - len(changed)} already up to date)."
        )
        if changed:
            self.stdout.write("  ids: " + ", ".join(str(r.id) for r in changed))
