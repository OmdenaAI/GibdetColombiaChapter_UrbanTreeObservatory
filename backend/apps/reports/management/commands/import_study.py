"""Load a study's per-tree results (``studies/<name>/study.json`` + ``trees.csv``).

The CSV is curated beforehand (see the study's README): one row per census tree, with
the values already reconciled between the study's sources. Loading is idempotent: the
study's previous measurements and assessments are replaced, the rest of each tree's
history is kept and the latest flags are recomputed.

    python manage.py import_study apps/reports/studies/torres_payares_2025 [--dry-run]
"""

import csv
import json
import re
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from apps.biodiversity.models import BiodiversityRecord
from apps.reports.models import (
    Assessment,
    Measurement,
    Observation,
    Study,
    refresh_latest,
)

A = Measurement.MeasuredAttribute
U = Measurement.MeasurementUnit
M = Measurement.MeasurementMethod

# CSV column -> (attribute, unit, method)
MEASUREMENTS = {
    "dbh_cm": (A.DIAMETER_BH, U.CENTIMETERS, M.DIAMETER_TAPE),
    "total_height_m": (A.TOTAL_HEIGHT, U.METERS, M.LASER_HYPSOMETER),
    "trunk_height_m": (A.TRUNK_HEIGHT, U.METERS, M.LASER_HYPSOMETER),
    "crown_diameter_m": (A.CROWN_DIAMETER, U.METERS, M.MEASURING_TAPE),
    "crown_diameter_ns_m": (A.CROWN_DIAMETER_NS, U.METERS, M.MEASURING_TAPE),
    "crown_diameter_ew_m": (A.CROWN_DIAMETER_EW, U.METERS, M.MEASURING_TAPE),
    "internal_damage_percent": (A.INTERNAL_DAMAGE, U.PERCENT, M.ACOUSTIC_TOMOGRAPHY),
    "transverse_velocity_m_s": (
        A.ACOUSTIC_VELOCITY,
        U.METERS_PER_SECOND,
        M.ACOUSTIC_TOMOGRAPHY,
    ),
    "green_density_g_cm3": (
        A.GREEN_DENSITY,
        U.GRAMS_PER_CUBIC_CM,
        M.INCREMENT_BORER,
    ),
    # Basic density (dry mass / green volume): the same quantity as the species value
    # of the wood density database, so it replaces it for this tree.
    "basic_density_g_cm3": (
        A.WOOD_DENSITY,
        U.GRAMS_PER_CUBIC_CM,
        M.INCREMENT_BORER,
    ),
    "dynamic_moe_mpa": (A.DYNAMIC_MOE, U.MEGAPASCALS, M.STRESS_WAVE),
}

R = Assessment.Risk
RISK = {"Bajo": R.LOW, "Moderado": R.MODERATE, "Alto": R.HIGH, "Extremo": R.EXTREME}
D = Assessment.DamageLevel
DAMAGE = {
    "Sin afectación": D.NONE,
    "Bajo": D.LOW,
    "Medio": D.MEDIUM,
    "Alto": D.HIGH,
    "Muy alto": D.VERY_HIGH,
}
G = Assessment.AgeClass
AGE = {
    "Joven": G.YOUNG,
    "Adulto": G.ADULT,
    "Maduro": G.MATURE,
    "Sobre maduro": G.OVERMATURE,
}
S = Assessment.PlantingSite
SITE = {
    "Parque": S.PARK,
    "Andén": S.SIDEWALK,
    "Separador": S.MEDIAN,
    "Zona blanda": S.GREEN_STRIP,
    "Alcorque": S.TREE_PIT,
}


# Health and structure from the study, written as a new observation of each tree:
# - phytosanitary status from the decay found by the tomography (rot is a sanitary
#   problem): critical from 50 % of the section, the report's intervention threshold;
#   sick from 10 %, or when the field notes describe rot, fungi, chlorosis or dead wood;
# - physical condition from the visual (EVA) and biomechanical risk: poor when either is
#   high or extreme, fair when either is moderate.
CRITICAL_DAMAGE = 50
SICK_DAMAGE = 10
SANITARY_SIGNS = re.compile(r"pudric|f[uú]ng|clorosis|madera muerta", re.IGNORECASE)
OBSERVATION_COPY_SKIP = {
    "id",
    "uuid",
    "created_at",
    "updated_at",
    "biodiversity_record",
    "is_latest",
    "date",
    "study",
    "field_notes",
    "recorded_by",
    "accompanying_collectors",
}


def _health(row):
    status = Observation.PhytosanitaryStatus
    damage = _number(row["internal_damage_percent"])
    if damage is not None and damage >= CRITICAL_DAMAGE:
        return status.CRITICAL
    if (damage is not None and damage >= SICK_DAMAGE) or SANITARY_SIGNS.search(
        row["notes"]
    ):
        return status.SICK
    return status.HEALTHY


def _condition(row):
    condition = Observation.PhysicalCondition
    risks = {row["visual_risk"], row["biomechanical_risk"]}
    if risks & {"Alto", "Extremo"}:
        return condition.POOR
    if "Moderado" in risks:
        return condition.FAIR
    return condition.GOOD


def _observations(study, rows):
    """A new observation per tree: the previous one's census fields, with the study's
    health and condition."""
    ids = [int(r["record_id"]) for r in rows]
    previous = {
        o.biodiversity_record_id: o
        for o in Observation.all_objects.filter(
            biodiversity_record_id__in=ids, is_latest=True
        )
    }
    copied = [
        f.attname
        for f in Observation._meta.concrete_fields
        if f.name not in OBSERVATION_COPY_SKIP
    ]
    out = []
    for row in rows:
        rid = int(row["record_id"])
        base = previous.get(rid)
        fields = {name: getattr(base, name) for name in copied} if base else {}
        fields.update(
            phytosanitary_status=_health(row),
            physical_condition=_condition(row),
            recorded_by=study.authors[:50],
        )
        out.append(
            Observation(
                biodiversity_record_id=rid, date=study.date, study=study, **fields
            )
        )
    return out


def _number(value):
    return float(value) if value not in ("", None) else None


def _int(value):
    return int(float(value)) if value not in ("", None) else None


def _choice(mapping, value, column, row_no):
    if not value:
        return ""
    try:
        return mapping[value]
    except KeyError:
        raise CommandError(f"row {row_no}: unknown {column} {value!r}") from None


def _notes(row):
    lines = [row["notes"]] if row["notes"] else []
    if row["match"] == "nearest":
        lines.append(
            f"El código {row['study_code']} del estudio no corresponde a este árbol del "
            f"censo; se asignó al árbol de la misma especie más cercano a sus "
            f"coordenadas ({row['match_distance_m']} m)."
        )
    elif row["match"] == "census_dbh":
        lines.append(
            f"Código {row['study_code']} asignado a este árbol: el DAP del estudio es el "
            f"de su censo ({row['match_distance_m']} m de las coordenadas del estudio)."
        )
    if row["dbh_source"] != "report":
        lines.append(f"DAP tomado de la hoja de cálculo: {row['dbh_source']}.")
    return "\n".join(lines)


class Command(BaseCommand):
    help = "Load a study's per-tree measurements and assessments."

    def add_arguments(self, parser):
        parser.add_argument("directory", type=Path)
        parser.add_argument(
            "--dry-run", action="store_true", help="Check the files, write nothing."
        )

    def handle(self, directory, dry_run, **options):
        try:
            meta = json.loads((directory / "study.json").read_text(encoding="utf-8"))
            with (directory / "trees.csv").open(encoding="utf-8", newline="") as f:
                rows = list(csv.DictReader(f))
        except (OSError, ValueError) as e:
            raise CommandError(e) from e

        ids = [int(r["record_id"]) for r in rows]
        if len(set(ids)) != len(ids):
            raise CommandError("a census tree appears twice in trees.csv")
        found = set(
            BiodiversityRecord.objects.filter(id__in=ids).values_list("id", flat=True)
        )
        if missing := sorted(set(ids) - found):
            raise CommandError(f"trees not in the census (or removed): {missing}")

        with transaction.atomic():
            study, _ = Study.objects.update_or_create(
                slug=meta.pop("slug"), defaults=meta
            )
            Measurement.all_objects.filter(study=study).delete()
            Assessment.objects.filter(study=study).delete()
            Observation.all_objects.filter(study=study).delete()
            refresh_latest(ids)  # the census observation is the latest again
            measurements, assessments = [], []
            for row_no, row in enumerate(rows, start=2):
                rid = int(row["record_id"])
                for column, (attribute, unit, method) in MEASUREMENTS.items():
                    value = _number(row[column])
                    if value is not None:
                        measurements.append(
                            Measurement(
                                biodiversity_record_id=rid,
                                attribute=attribute,
                                value=value,
                                unit=unit,
                                method=method,
                                date=study.date,
                                study=study,
                            )
                        )
                assessments.append(
                    Assessment(
                        biodiversity_record_id=rid,
                        study=study,
                        date=study.date,
                        study_code=f"{row['study_code']} · N.º {row['report_no']}",
                        visual_risk=_choice(
                            RISK, row["visual_risk"], "visual_risk", row_no
                        ),
                        visual_risk_part=row["visual_risk_part"],
                        biomechanical_risk=_choice(
                            RISK,
                            row["biomechanical_risk"],
                            "biomechanical_risk",
                            row_no,
                        ),
                        tomography_level=_choice(
                            DAMAGE, row["tomography_level"], "tomography_level", row_no
                        ),
                        damage_section_diameter_cm=_number(
                            row["damage_section_diameter_cm"]
                        ),
                        damage_section_height_cm=_number(
                            row["damage_section_height_cm"]
                        ),
                        tomography_sections=_int(row["tomography_sections"]),
                        age_class=_choice(AGE, row["age_class"], "age_class", row_no),
                        planting_site=_choice(
                            SITE, row["planting_site"], "planting_site", row_no
                        ),
                        crown_exposure_class=_int(row["crown_exposure_class"]),
                        crown_exposure_percent=_int(row["crown_exposure_percent"]),
                        notes=_notes(row),
                    )
                )
            Measurement.objects.bulk_create(measurements)
            Assessment.objects.bulk_create(assessments)
            observations = Observation.all_objects.bulk_create(
                _observations(study, rows)
            )
            refresh_latest(ids)
            if dry_run:
                transaction.set_rollback(True)

        self.stdout.write(
            f"{'Checked' if dry_run else 'Loaded'} {study}: {len(assessments)} trees, "
            f"{len(measurements)} measurements, {len(observations)} observations."
        )
