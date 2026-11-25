"""Ecosystem services of every census tree: carbon stock and intercepted rain.

The same method as the analysis notebook ``03_servicios_ecosistemicos`` (article on the
Ibagué urban forest), run on the platform's data so that every tree, barrio, comuna and
the city show the same figures. ``compute_ecosystem_services`` stores one row per tree
(``EcosystemService``); the statistics endpoints sum them.

Carbon stock (kg C), a stock accumulated over the tree's life, not an annual flux:
- Woody trees: AGB = ρ · exp(−1.499 + 2.148 ln D + 0.207 (ln D)² − 0.0281 (ln D)³), D =
  DBH (cm), ρ = wood density (g/cm³). Chave et al. (2005), moist forest, without height;
  the same equation as Acuña-Simbaqueva et al. (2021) for Ibagué. Height is left out
  because the census estimated it by eye.
- Palms (Arecaceae): AGB = 10.0 + 6.4 · H (Frangi & Lugo, 1985).
- Non-woody families (dracaenas, yuccas, cacti, cycads, papaya...): no carbon.
- C = AGB · (1 + 0.26 roots; Cairns et al., 1997) · 0.8 (urban trees; Nowak, 1994)
  · 0.47 (carbon fraction; IPCC).

Intercepted rain (m³/year), conservative lower bound:
- Leaf area index from the crown (Nowak, 1996): ln(LA) = −4.3309 + 0.2942 Hc + 0.7312 Dc
  + 5.7217 · 0.83 − 0.0148 · π Dc (Hc + Dc) / 2, Hc = crown height, Dc = crown diameter;
  crown height/width kept within 0.5–2 and, above 10 m of crown, the index at 10 m.
  Dead trees: no leaves.
- Each rainy day the crown holds up to S = 0.2 mm × LAI (Wang et al., 2008, i-Tree Hydro)
  and dries before the next one. Interception (mm/year) = Σ min(P, S) over the days of
  2022, 2023 and 2025, read from the curve of the tree's rain pixel
  (``data/rain_interception_curves.json``: the daily series of the nearest IDEAM
  station scaled with the CHIRPS gradient). Volume = crown area × interception.
- No evaporation during the storm: measured interception of isolated urban trees is
  higher (Nytch et al., 2019: 19.7 % in San Juan, Puerto Rico), so this is a lower bound.

Missing or impossible inputs are filled as in the notebook (each one listed in
``imputed``): DBH and height with the species median; crown diameter (0, > 30 m or
> 4 × height) with the species median crown/DBH ratio; crown height (trunk ≥ total
height) with the species median crown proportion. Missing wood density comes from the
Global Wood Density Database (Chave et al., 2009; Zanne et al., 2009; the ``wdData`` table
of the BIOMASS R package, ``data/wood_density_gwdd.json``): the species mean, else the
genus mean, else the family mean, as in BIOMASS; else the census median.
"""

import bisect
import json
import math
from collections import defaultdict
from pathlib import Path
from statistics import median

from django.db import transaction
from django.utils.translation import gettext_noop

from apps.biodiversity.models import BiodiversityRecord

from .models import EcosystemService, Measurement, Observation

A = Measurement.MeasuredAttribute

# --- Carbon ---
CARBON_FRACTION = 0.47
ROOT_RATIO = 0.26
URBAN_FACTOR = 0.8
CO2_PER_C = 44 / 12
PALM_FAMILY = "Arecaceae"
NON_WOODY_FAMILIES = {
    "Asparagaceae",
    "Cactaceae",
    "Strelitziaceae",
    "Poaceae",
    "Araceae",
    "Pandanaceae",
    "Cycadaceae",
    "Musaceae",
    "Heliconiaceae",
    "Caricaceae",  # Carica papaya, a giant herb
}

# --- Leaf area and rain ---
SHADE = 0.83
CROWN_CALIBRATION_MAX = 10.0  # m
CROWN_RATIO = (0.5, 2.0)
LEAF_STORAGE_MM = 0.2
MAX_CROWN_DIAMETER = 30.0
MIN_CROWN_DIAMETER = 0.5
MIN_CROWN_HEIGHT = 0.1
DEAD = Observation.PhytosanitaryStatus.DEAD

# Names of the estimated inputs, stored in English in ``EcosystemService.imputed`` and
# translated when shown.
IMPUTED = {
    "dbh": gettext_noop("DBH"),
    "ht": gettext_noop("total height"),
    "cd": gettext_noop("crown diameter"),
    "crown_height": gettext_noop("crown height"),
    "wd_species": gettext_noop("wood density (species, Global Wood Density Database)"),
    "wd_genus": gettext_noop("wood density (genus, Global Wood Density Database)"),
    "wd_family": gettext_noop("wood density (family, Global Wood Density Database)"),
    "wd_overall": gettext_noop("wood density (census median)"),
}

DATA_DIR = Path(__file__).resolve().parent / "data"  # exported by the notebook
CURVES_FILE = DATA_DIR / "rain_interception_curves.json"
WOOD_DENSITY_FILE = DATA_DIR / "wood_density_gwdd.json"
LAT_REF = math.radians(4.4)  # Ibagué: degrees of longitude are shorter than of latitude


def agb_chave2005(dbh_cm, density):
    ln = math.log(dbh_cm)
    return density * math.exp(-1.499 + 2.148 * ln + 0.207 * ln**2 - 0.0281 * ln**3)


def agb_palm(height_m):
    return 10.0 + 6.4 * height_m


def carbon_kg(agb):
    return agb * (1 + ROOT_RATIO) * URBAN_FACTOR * CARBON_FRACTION


def leaf_area_index(crown_height, crown_diameter):
    """Leaf area per m² of crown projection (Nowak, 1996), within its calibration."""
    lo, hi = CROWN_RATIO
    d = min(crown_diameter, CROWN_CALIBRATION_MAX)
    h = min(max(crown_height / crown_diameter, lo), hi) * d
    c = math.pi * d * (h + d) / 2
    la = math.exp(-4.3309 + 0.2942 * h + 0.7312 * d + 5.7217 * SHADE - 0.0148 * c)
    return la / (math.pi * d**2 / 4)


class RainCurves:
    """Annual interception (mm per m² of crown) against crown storage, per rain pixel."""

    def __init__(self, path=CURVES_FILE):
        data = json.loads(Path(path).read_text(encoding="utf-8"))
        g = data["s_grid_mm"]
        step = (g["stop"] - g["start"]) / (g["num"] - 1)
        self.grid = [g["start"] + i * step for i in range(g["num"])]
        self.pixels = data["pixels"]
        self.years = data["years"]

    def nearest(self, lon, lat):
        return min(
            range(len(self.pixels)),
            key=lambda i: (self.pixels[i]["lat"] - lat) ** 2
            + ((self.pixels[i]["lon"] - lon) * math.cos(LAT_REF)) ** 2,
        )

    def interception_mm(self, pixel, storage_mm):
        """Linear interpolation of the pixel's curve (clamped to the grid)."""
        curve, grid = self.pixels[pixel]["interception_mm"], self.grid
        s = min(max(storage_mm, grid[0]), grid[-1])
        i = min(bisect.bisect_right(grid, s), len(grid) - 1)
        x0, x1 = grid[i - 1], grid[i]
        w = (s - x0) / (x1 - x0) if x1 > x0 else 0.0
        return curve[i - 1] + w * (curve[i] - curve[i - 1])


class WoodDensity:
    """Mean wood density (g/cm³) by species, genus and family."""

    def __init__(self, path=WOOD_DENSITY_FILE):
        data = json.loads(Path(path).read_text(encoding="utf-8"))
        self.species, self.genus, self.family = (
            data["species"],
            data["genus"],
            data["family"],
        )

    def lookup(self, genus, species, family):
        """(density, level) at the most specific level found, or (None, None).

        ``species`` is the census epithet; when it starts with a capitalized word (a
        genus name kept from a synonym, e.g. "Thevetia peruviana"), that binomial is
        tried too.
        """
        words = (species or "").split()
        names = [f"{genus} {words[0]}"] if words else []
        if len(words) > 1 and words[0][:1].isupper():
            names.append(f"{words[0]} {words[1]}")
        for name in names:
            if name in self.species:
                return self.species[name], "species"
        if genus in self.genus:
            return self.genus[genus], "genus"
        if family in self.family:
            return self.family[family], "family"
        return None, None


def _medians(rows, key, value):
    groups = defaultdict(list)
    for r in rows:
        v = value(r)
        if v is not None:
            groups[key(r)].append(v)
    return {k: median(v) for k, v in groups.items()}


def _overall(rows, value):
    values = [v for r in rows if (v := value(r)) is not None]
    return median(values) if values else None


def load_trees():
    """Active trees with what the method needs: taxonomy, place, latest measurements
    (whatever their source: census or study) and latest phytosanitary status."""
    trees = {
        r["id"]: {
            "id": r["id"],
            "species": r["species_id"],
            "species_name": r["species__name"],
            "genus": r["species__genus__name"],
            "family": r["species__genus__family__name"],
            "lon": r["location"].x,
            "lat": r["location"].y,
            "status": None,
        }
        for r in BiodiversityRecord.objects.values(
            "id",
            "species_id",
            "species__name",
            "species__genus__name",
            "species__genus__family__name",
            "location",
        )
    }
    names = {
        A.DIAMETER_BH: "dbh",
        A.TOTAL_HEIGHT: "ht",
        A.TRUNK_HEIGHT: "th",
        A.CROWN_DIAMETER: "cd",
        A.WOOD_DENSITY: "wd",
    }
    for record_id, attribute, value in Measurement.objects.filter(
        is_latest=True, attribute__in=names
    ).values_list("biodiversity_record_id", "attribute", "value"):
        if record_id in trees:
            trees[record_id][names[attribute]] = value
    for record_id, status in Observation.objects.filter(is_latest=True).values_list(
        "biodiversity_record_id", "phytosanitary_status"
    ):
        if record_id in trees:
            trees[record_id]["status"] = status
    return list(trees.values())


def _species_key(t):
    return t["species"]


def _fill(trees, key, value_key, fallback, label):
    """Fill missing ``value_key`` with the median of the tree's ``key`` group (genus,
    species...), or ``fallback`` when the group has no value."""
    med = _medians(trees, key, lambda t: t[value_key])
    for t in trees:
        if t[value_key] is None:
            v = med.get(key(t), fallback)
            if v is not None:
                t[value_key] = v
                t["imputed"].append(label)


def _fill_species_median(trees, k, label):
    _fill(trees, _species_key, k, _overall(trees, lambda t: t[k]), label)


def _fill_crown_diameter(trees):
    """Impossible crown diameters (0, > 30 m, > 4 × the measured height) and missing
    ones are re-estimated from the species median crown/DBH ratio."""
    for t in trees:
        cd, ht = t["cd"], t["ht"]
        if (
            cd is None
            or cd <= 0
            or cd > MAX_CROWN_DIAMETER
            or (ht is not None and cd > 4 * ht)
        ):
            t["cd"] = None

    def ratio(t):
        return t["cd"] / t["dbh"] if t["cd"] is not None and t["dbh"] else None

    by_species, overall = _medians(trees, _species_key, ratio), _overall(trees, ratio)
    for t in trees:
        r = by_species.get(t["species"], overall)
        if t["cd"] is None and r is not None and t["dbh"] is not None:
            t["cd"] = min(max(r * t["dbh"], MIN_CROWN_DIAMETER), MAX_CROWN_DIAMETER)
            t["imputed"].append(IMPUTED["cd"])


def _fill_crown_height(trees):
    """Crown height = total − trunk height; a trunk as tall as the tree leaves no crown,
    so the species median crown proportion is used instead."""

    def proportion(t):
        if t["th"] is None or not t["ht"] or t["th"] >= t["ht"]:
            return None
        return (t["ht"] - t["th"]) / t["ht"]

    by_species = _medians(trees, _species_key, proportion)
    overall = _overall(trees, proportion)
    for t in trees:
        fill = by_species.get(t["species"], overall)
        t["crown_height"] = None
        if proportion(t) is not None:
            t["crown_height"] = t["ht"] - t["th"]
        elif t["ht"] is not None and fill is not None:
            t["crown_height"] = t["ht"] * fill
            t["imputed"].append(IMPUTED["crown_height"])


def _fill_wood_density(trees, wood):
    """Global Wood Density Database (species, genus, family), then the census median."""
    census = _overall(trees, lambda t: t["wd"])
    for t in trees:
        if t["wd"] is not None:
            continue
        value, level = wood.lookup(t["genus"], t.get("species_name"), t["family"])
        if value is None and census is not None:
            value, level = census, "overall"
        if value is not None:
            t["wd"] = value
            t["imputed"].append(IMPUTED[f"wd_{level}"])


def compute(trees, curves, wood=None):
    """Fill missing inputs and estimate carbon and interception of every tree.

    ``trees``: dicts with id, species, genus, family, lon, lat, status and the optional
    measurements dbh, ht, th, cd, wd (and ``species_name``, the epithet, for the wood
    density lookup; ``wood`` defaults to the shipped table). Returns one dict per tree (see EcosystemService).
    The order of the steps is the notebook's (the crown is checked against the measured
    height, before missing heights are filled).
    """
    for t in trees:
        t["imputed"] = []
        for k in ("dbh", "ht", "th", "cd", "wd"):
            t.setdefault(k, None)
    _fill_species_median(trees, "dbh", IMPUTED["dbh"])
    _fill_crown_diameter(trees)
    _fill_species_median(trees, "ht", IMPUTED["ht"])
    _fill_crown_height(trees)
    _fill_wood_density(trees, wood or WoodDensity())
    return [
        {
            "biodiversity_record_id": t["id"],
            "carbon_kg": _carbon(t),
            **_rain(t, curves),
            "imputed": ", ".join(t["imputed"]),
        }
        for t in trees
    ]


def _carbon(t):
    """kg C, or None when an input could not be measured nor estimated."""
    if t["family"] == PALM_FAMILY:
        return carbon_kg(agb_palm(t["ht"])) if t["ht"] is not None else None
    if t["family"] in NON_WOODY_FAMILIES:
        return 0.0
    if t["dbh"] is None or t["wd"] is None or t["dbh"] <= 0:
        return None
    return carbon_kg(agb_chave2005(t["dbh"], t["wd"]))


def _rain(t, curves):
    """Crown area, leaf area index and intercepted rain (None without a crown)."""
    if t["cd"] is None or t["crown_height"] is None:
        return {
            "crown_area_m2": None,
            "leaf_area_index": None,
            "rain_interception_m3": None,
        }
    crown_area = math.pi * t["cd"] ** 2 / 4
    lai = (
        0.0
        if t["status"] == DEAD
        else leaf_area_index(max(t["crown_height"], MIN_CROWN_HEIGHT), t["cd"])
    )
    mm = curves.interception_mm(
        curves.nearest(t["lon"], t["lat"]), LEAF_STORAGE_MM * lai
    )
    return {
        "crown_area_m2": crown_area,
        "leaf_area_index": lai,
        "rain_interception_m3": crown_area * mm / 1000,
    }


@transaction.atomic
def refresh():
    """Recompute and store the services of every active tree (about 100,000 rows)."""
    rows = compute(load_trees(), RainCurves())
    EcosystemService.objects.all().delete()
    EcosystemService.objects.bulk_create(
        [EcosystemService(**r) for r in rows], batch_size=5000
    )
    return rows
