"""Study results: the ``import_study`` command and the per-tree indicators."""

import csv
import datetime
import json
import math
from pathlib import Path

import pytest
from django.core.management import CommandError, call_command
from django.urls import reverse
from django.utils import translation

from apps.reports.factories import MeasurementFactory, ObservationFactory
from apps.reports.management.commands.import_study import MEASUREMENTS
from apps.reports.metrics import tree_metrics
from apps.reports.models import Assessment, Measurement, Observation, Study

A = Measurement.MeasuredAttribute
STUDY_DATE = datetime.date(2025, 7, 22)
STUDY = {
    "slug": "test-2025",
    "title": "Evaluación instrumental",
    "authors": "A. Autor",
    "institution": "Universidad",
    "year": 2025,
    "date": str(STUDY_DATE),
    "citation": "Autor, A. (2025). Evaluación instrumental.",
    "short_citation": "Autor (2025)",
    "methods": "",
    "notes": "",
}
ROW = {
    "match": "code",
    "match_distance_m": "",
    "study_code": "41126",
    "report_no": "16",
    "dbh_source": "report",
    "dbh_cm": "73.21",
    "total_height_m": "15.5",
    "trunk_height_m": "8",
    "crown_diameter_m": "7.9",
    "crown_diameter_ns_m": "9.6",
    "crown_diameter_ew_m": "6.2",
    "internal_damage_percent": "79",
    "transverse_velocity_m_s": "1266.27",
    "green_density_g_cm3": "0.86",
    "basic_density_g_cm3": "0.32",
    "dynamic_moe_mpa": "2905.75",
    "visual_risk": "Alto",
    "visual_risk_part": "Copa y ramas",
    "biomechanical_risk": "Alto",
    "tomography_level": "Muy alto",
    "damage_section_diameter_cm": "73.21",
    "damage_section_height_cm": "180",
    "tomography_sections": "1",
    "age_class": "Joven",
    "planting_site": "Separador",
    "crown_exposure_class": "",
    "crown_exposure_percent": "95",
    "notes": "Distribución irregular de copa",
}


def write_study(directory: Path, rows):
    directory.mkdir(exist_ok=True)
    (directory / "study.json").write_text(json.dumps(STUDY), encoding="utf-8")
    with (directory / "trees.csv").open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["record_id", *ROW])
        writer.writeheader()
        writer.writerows(rows)
    return directory


@pytest.fixture
def census_tree(biodiversity_record):
    """A tree with a 2017 census DBH and the species' database wood density."""
    MeasurementFactory(
        biodiversity_record=biodiversity_record,
        attribute=A.DIAMETER_BH,
        value=49.0,
        unit="cm",
        date=datetime.date(2017, 3, 11),
    )
    MeasurementFactory(
        biodiversity_record=biodiversity_record,
        attribute=A.WOOD_DENSITY,
        value=0.35,
        unit="g/cm3",
        method=Measurement.MeasurementMethod.WOOD_DENSITY_DB,
        date=None,
    )
    return biodiversity_record


@pytest.fixture
def study_dir(tmp_path, census_tree):
    return write_study(tmp_path / "study", [{"record_id": census_tree.id, **ROW}])


@pytest.mark.django_db
class TestImportStudy:
    def test_loads_measurements_and_assessment(self, study_dir, census_tree):
        call_command("import_study", study_dir)

        study = Study.objects.get(slug="test-2025")
        rows = Measurement.all_objects.filter(study=study)
        assert rows.count() == len(MEASUREMENTS)
        assert set(rows.values_list("date", flat=True)) == {STUDY_DATE}

        latest = {m.attribute: m for m in census_tree.measurements.all() if m.is_latest}
        assert latest[A.DIAMETER_BH].value == 73.21
        # The basic density measured on the tree replaces the species value...
        assert latest[A.WOOD_DENSITY].value == 0.32
        assert latest[A.WOOD_DENSITY].method == "IB"
        # ...which stays as history, like the census DBH.
        assert census_tree.measurements.filter(attribute=A.DIAMETER_BH).count() == 2

        a = Assessment.objects.get(biodiversity_record=census_tree)
        assert (a.visual_risk, a.biomechanical_risk, a.tomography_level) == (
            "HI",
            "HI",
            "VH",
        )
        assert (a.age_class, a.planting_site) == ("YO", "ME")
        assert a.crown_exposure_class is None and a.crown_exposure_percent == 95
        assert a.study_code == "41126 · N.º 16"
        assert a.notes == "Distribución irregular de copa"

    def test_is_idempotent(self, study_dir, census_tree):
        call_command("import_study", study_dir)
        call_command("import_study", study_dir)
        assert Measurement.all_objects.filter(study__isnull=False).count() == len(
            MEASUREMENTS
        )
        assert Assessment.objects.count() == 1
        assert census_tree.measurements.filter(is_latest=True, value=49.0).count() == 0

    def test_dry_run_writes_nothing(self, study_dir):
        call_command("import_study", study_dir, dry_run=True)
        assert not Study.objects.exists()
        assert not Assessment.objects.exists()

    def test_unknown_tree(self, tmp_path, census_tree):
        directory = write_study(tmp_path / "s", [{"record_id": 999999, **ROW}])
        with pytest.raises(CommandError, match="999999"):
            call_command("import_study", directory)

    def test_unknown_label(self, tmp_path, census_tree):
        row = {**ROW, "visual_risk": "Altísimo"}
        directory = write_study(tmp_path / "s", [{"record_id": census_tree.id, **row}])
        with pytest.raises(CommandError, match="visual_risk"):
            call_command("import_study", directory)
        assert not Study.objects.exists()

    def test_notes_record_how_the_tree_was_matched(self, tmp_path, census_tree):
        row = {
            **ROW,
            "match": "nearest",
            "match_distance_m": "9.1",
            "dbh_source": "spreadsheet (report copied the census)",
        }
        directory = write_study(tmp_path / "s", [{"record_id": census_tree.id, **row}])
        call_command("import_study", directory)
        notes = Assessment.objects.get().notes
        assert "9.1 m" in notes and "hoja de cálculo" in notes


@pytest.mark.django_db
class TestHealth:
    """The study writes a new observation: health from decay, condition from risk."""

    def load(self, tmp_path, tree, **changes):
        row = {**ROW, **changes}
        call_command(
            "import_study", write_study(tmp_path / "s", [{"record_id": tree.id, **row}])
        )
        return Observation.all_objects.get(biodiversity_record=tree, is_latest=True)

    def test_new_observation_keeps_the_census_fields(self, tmp_path, census_tree):
        ObservationFactory(
            biodiversity_record=census_tree,
            phytosanitary_status="HE",
            physical_condition="GO",
            foliage_density="DE",
            field_notes="census note",
            date=None,
        )
        o = self.load(tmp_path, census_tree)
        # 79 % of the section decayed, high visual and biomechanical risk.
        assert (o.phytosanitary_status, o.physical_condition) == ("CR", "PO")
        assert o.date == STUDY_DATE and o.study.slug == "test-2025"
        assert o.foliage_density == "DE"
        assert o.field_notes == "" and o.recorded_by == "A. Autor"
        # The census observation stays as history; reloading does not add rows.
        call_command("import_study", tmp_path / "s")
        assert (
            Observation.all_objects.filter(biodiversity_record=census_tree).count() == 2
        )

    @pytest.mark.parametrize(
        ("damage", "notes", "expected"),
        [
            ("50", "", "CR"),
            ("49", "", "SI"),
            ("10", "", "SI"),
            ("9", "", "HE"),
            ("0", "Evidencia pudricion en la poda", "SI"),
            ("0", "Presencia de epífitas", "HE"),
        ],
    )
    def test_health(self, tmp_path, census_tree, damage, notes, expected):
        o = self.load(
            tmp_path, census_tree, internal_damage_percent=damage, notes=notes
        )
        assert o.phytosanitary_status == expected

    @pytest.mark.parametrize(
        ("visual", "biomechanical", "expected"),
        [
            ("Bajo", "Extremo", "PO"),
            ("Alto", "Bajo", "PO"),
            ("Moderado", "Bajo", "FA"),
            ("Bajo", "Moderado", "FA"),
            ("Bajo", "Bajo", "GO"),
        ],
    )
    def test_condition(self, tmp_path, census_tree, visual, biomechanical, expected):
        o = self.load(
            tmp_path,
            census_tree,
            visual_risk=visual,
            biomechanical_risk=biomechanical,
        )
        assert o.physical_condition == expected


@pytest.mark.django_db
class TestMetrics:
    def metrics(self, tree):
        tree.refresh_from_db()
        measurements = list(tree.measurements.all())
        assessment = tree.assessments.first()
        with translation.override("en"):
            return {m["key"]: m for m in tree_metrics(tree, measurements, assessment)}

    def test_indicators(self, study_dir, census_tree):
        call_command("import_study", study_dir)
        m = self.metrics(census_tree)

        assert m["crown_area"]["value"] == pytest.approx(
            math.pi / 4 * 9.6 * 6.2, abs=0.05
        )
        assert m["live_crown_ratio"]["value"] == pytest.approx(48, abs=0.5)
        assert m["slenderness"]["value"] == pytest.approx(15.5 / 0.7321, abs=0.5)
        # 79 % damaged: t/R = 1 - sqrt(0.79) = 0.11, below Mattheck's 0.32.
        assert m["residual_wall"]["value"] == pytest.approx(0.11, abs=0.005)
        assert m["residual_wall"]["flag"] is True
        assert m["strength_loss"]["value"] == pytest.approx(70, abs=0.5)
        agb = 0.0673 * (0.32 * 73.21**2 * 15.5) ** 0.976
        assert m["biomass"]["value"] == pytest.approx(agb, abs=0.5)
        assert "measured on this tree" in m["biomass"]["note"]
        # Damage > 50 %, biomechanical high, visual high; one tree is its species'
        # mean, so MOE and density do not deviate: 3 of 5.
        assert (m["priority"]["value"], m["priority"]["unit"]) == (3, "/ 5")
        assert m["priority"]["flag"] is True

    def test_census_tree_uses_the_species_density(self, census_tree):
        MeasurementFactory(
            biodiversity_record=census_tree, attribute=A.TOTAL_HEIGHT, value=15.0
        )
        m = self.metrics(census_tree)
        assert "of the species" in m["biomass"]["note"]
        assert "residual_wall" not in m and "priority" not in m


@pytest.mark.django_db
def test_tree_detail_shows_study_data(api_client, study_dir, census_tree):
    call_command("import_study", study_dir)
    response = api_client.get(
        reverse("biodiversity:inventory-detail", args=[census_tree.id]), {"lang": "es"}
    )
    data = response.json()
    sources = {m["source"] for m in data["measurements"]}
    assert sources == {None, "Autor (2025)"}
    [assessment] = data["assessments"]
    assert assessment["study"] == "Autor (2025)"
    fields = {f["field"]: f.get("display", f["value"]) for f in assessment["fields"]}
    assert fields["visual_risk"] == "alto"
    assert "crown_exposure_class" not in fields  # empty fields are left out
    assert any(m["key"] == "residual_wall" for m in data["metrics"])
