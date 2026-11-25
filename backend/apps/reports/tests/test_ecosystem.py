"""Ecosystem services per tree (``apps.reports.ecosystem``)."""

import json
import math

import pytest
from django.core.management import call_command

from apps.reports.ecosystem import (
    CURVES_FILE,
    LEAF_STORAGE_MM,
    RainCurves,
    WoodDensity,
    agb_chave2005,
    carbon_kg,
    compute,
    leaf_area_index,
)
from apps.reports.factories import MeasurementFactory, ObservationFactory
from apps.reports.models import EcosystemService


@pytest.fixture
def curves(tmp_path):
    """Two pixels; interception grows 1:1 with storage up to 2 mm, then stays at 100."""
    path = tmp_path / "curves.json"
    pixel = {"interception_mm": [0.0, 50.0, 100.0, 100.0], "station": "X", "F": 1.0}
    path.write_text(
        json.dumps(
            {
                "years": [2022],
                "s_grid_mm": {"start": 0.0, "stop": 3.0, "num": 4},
                "pixels": [
                    {**pixel, "lat": 4.40, "lon": -75.20},
                    {
                        **pixel,
                        "lat": 4.45,
                        "lon": -75.10,
                        "interception_mm": [0.0, 10.0, 20.0, 30.0],
                    },
                ],
            }
        )
    )
    return RainCurves(path)


@pytest.fixture
def wood(tmp_path):
    path = tmp_path / "wood.json"
    path.write_text(
        json.dumps(
            {
                "species": {"Tabebuia rosea": 0.55, "Thevetia peruviana": 0.6},
                "genus": {"Tabebuia": 0.65, "Ficus": 0.45},
                "family": {"Bignoniaceae": 0.58, "Moraceae": 0.5},
            }
        )
    )
    return WoodDensity(path)


def tree(i, **kw):
    base = {
        "id": i,
        "species": 1,
        "genus": "Tabebuia",
        "family": "Bignoniaceae",
        "lon": -75.2,
        "lat": 4.4,
        "status": "HE",
    }
    return {**base, **kw}


class TestFormulas:
    def test_chave_2005_moist_without_height(self):
        ln = math.log(30)
        expected = 0.6 * math.exp(-1.499 + 2.148 * ln + 0.207 * ln**2 - 0.0281 * ln**3)
        assert agb_chave2005(30, 0.6) == pytest.approx(expected)
        assert carbon_kg(100) == pytest.approx(100 * 1.26 * 0.8 * 0.47)

    def test_leaf_area_index_stays_within_calibration(self):
        # Height/width ratio clamped to 0.5-2: a 20 m tall, 4 m wide crown = 8 m tall.
        assert leaf_area_index(20, 4) == pytest.approx(leaf_area_index(8, 4))
        # Above 10 m of crown, the index of a 10 m crown.
        assert leaf_area_index(15, 15) == pytest.approx(leaf_area_index(10, 10))
        assert 1 < leaf_area_index(4, 5) < 8

    def test_rain_curve_interpolation(self, curves):
        assert curves.nearest(-75.21, 4.41) == 0
        assert curves.nearest(-75.09, 4.46) == 1
        assert curves.interception_mm(0, 0.5) == pytest.approx(25)
        assert curves.interception_mm(0, 99) == pytest.approx(100)  # clamped

    def test_wood_density_from_species_to_family(self, wood):
        assert wood.lookup("Tabebuia", "rosea", "Bignoniaceae") == (0.55, "species")
        # The census keeps the synonym's genus in the epithet.
        assert wood.lookup("Cascabela", "Thevetia peruviana", "Apocynaceae") == (
            0.6,
            "species",
        )
        assert wood.lookup("Tabebuia", "chrysantha", "Bignoniaceae") == (0.65, "genus")
        assert wood.lookup("Jacaranda", "mimosifolia", "Bignoniaceae") == (
            0.58,
            "family",
        )
        assert wood.lookup("Xyz", "abc", "Unknown") == (None, None)

    def test_shipped_wood_density_table(self):
        w = WoodDensity()
        assert len(w.species) > 8000
        assert all(0.08 <= v <= 1.4 for v in w.genus.values())

    def test_shipped_curves_cover_ibague(self):
        c = RainCurves(CURVES_FILE)
        assert c.years == [2022, 2023, 2025]
        assert len(c.pixels) == 10
        for p in c.pixels:
            assert p["interception_mm"][0] == 0
            # Interception never exceeds the rain.
            assert max(p["interception_mm"]) < p["annual_rain_mm"]


class TestCompute:
    def test_values_and_imputation(self, curves, wood):
        trees = [
            tree(1, dbh=20.0, ht=8.0, th=2.0, cd=4.0, wd=0.5),
            tree(2, dbh=40.0, ht=10.0, th=2.0, cd=8.0, wd=None, species_name="rosea"),
            # Impossible crown (> 4 × height) and missing DBH: species medians.
            tree(3, dbh=None, ht=5.0, th=6.0, cd=25.0, wd=0.7),
            tree(4, family="Arecaceae", genus="Dypsis", species=2, dbh=10.0, ht=4.0),
            tree(5, family="Cactaceae", genus="Opuntia", species=3, dbh=10.0, ht=2.0),
            tree(6, dbh=20.0, ht=8.0, th=2.0, cd=4.0, wd=0.5, status="DE"),
            tree(7, family="Caricaceae", genus="Carica", species=4, dbh=15.0, ht=4.0),
            # Wood density of a taxon missing from the database: census median.
            tree(8, family="Unknown", genus="Xyz", species=5, dbh=20.0, wd=None),
        ]
        out = {r["biodiversity_record_id"]: r for r in compute(trees, curves, wood)}

        assert out[1]["carbon_kg"] == pytest.approx(carbon_kg(agb_chave2005(20, 0.5)))
        assert out[1]["imputed"] == ""
        assert out[1]["crown_area_m2"] == pytest.approx(math.pi * 4)
        lai = leaf_area_index(6.0, 4.0)
        assert out[1]["leaf_area_index"] == pytest.approx(lai)
        mm = curves.interception_mm(0, LEAF_STORAGE_MM * lai)
        assert out[1]["rain_interception_m3"] == pytest.approx(math.pi * 4 * mm / 1000)

        assert (
            "wood density (species, Global Wood Density Database)" in out[2]["imputed"]
        )
        assert out[2]["carbon_kg"] == pytest.approx(carbon_kg(agb_chave2005(40, 0.55)))
        assert "DBH" in out[3]["imputed"] and "crown diameter" in out[3]["imputed"]
        assert "crown height" in out[3]["imputed"]  # trunk taller than the tree
        assert out[4]["carbon_kg"] == pytest.approx(carbon_kg(10 + 6.4 * 4))  # palm
        assert out[5]["carbon_kg"] == 0  # non-woody
        assert out[6]["leaf_area_index"] == 0 and out[6]["rain_interception_m3"] == 0
        assert out[7]["carbon_kg"] == 0  # papaya: non-woody
        median = 0.5  # of the census densities 0.5, 0.7 and 0.5 (before any filling)
        assert "wood density (census median)" in out[8]["imputed"]
        assert out[8]["carbon_kg"] == pytest.approx(
            carbon_kg(agb_chave2005(20, median))
        )

    def test_without_any_crown_data_there_is_no_interception(self, curves, wood):
        out = compute([tree(1, dbh=20.0, ht=8.0, wd=0.5)], curves, wood)[0]
        assert out["rain_interception_m3"] is None
        assert out["carbon_kg"] == pytest.approx(carbon_kg(agb_chave2005(20, 0.5)))


@pytest.mark.django_db
def test_command_stores_one_row_per_active_tree(biodiversity_record):
    measured = (("DBH", 30.0), ("HT", 9.0), ("TH", 3.0), ("CD", 6.0), ("WD", 0.6))
    for attribute, value in measured:
        MeasurementFactory(
            biodiversity_record=biodiversity_record, attribute=attribute, value=value
        )
    ObservationFactory(biodiversity_record=biodiversity_record)
    call_command("compute_ecosystem_services")
    call_command("compute_ecosystem_services")  # idempotent

    es = EcosystemService.objects.get()
    assert es.biodiversity_record_id == biodiversity_record.id
    assert es.carbon_kg > 0 and es.rain_interception_m3 > 0
