"""Per-tree indicators derived from a tree's latest measurements and assessment.

Formula symbols: D = DBH (m; cm in the biomass equation), H = total height,
Hc = crown base (trunk) height, Dc / Dns / Deo = crown diameter (mean / N-S / E-W),
a = damaged fraction of the cross-section, ρ = basic wood density (g/cm³).

Nothing here is stored: each indicator is computed on request from the values it
depends on, so it always follows the data and its formula is shown with it. They are
estimates: each one says which formula and assumptions it uses.

References
- Crown and stem form: ISA (2017) Tree Risk Assessment; i-Tree Eco crown variables.
- Residual wall t/R and the 0.32 limit: Mattheck & Breloer (1994), The Body Language
  of Trees. Assumes the damaged area is a centred, circular hollow.
- Strength loss of a hollow stem, (d/D)^3: Wagener (1963); Coder (1989).
- Above-ground biomass: Chave et al. (2014), Glob. Change Biol. 20: 3177, eq. 4,
  fitted on forest trees; carbon fraction 0.47 (IPCC 2006).
- Intervention criteria: Torres Payares (2025), recommendations - internal damage
  > 50 %, MOEd at least 20 % below the species mean, high biomechanical risk, visible
  damage in the visual assessment, green density more than 20 % from the species mean.
"""

import math

from django.db.models import Avg
from django.utils.translation import gettext as _

from .models import Assessment, Measurement

A = Measurement.MeasuredAttribute

RESIDUAL_WALL_LIMIT = 0.32
DAMAGE_LIMIT = 50  # %
DEVIATION_LIMIT = 20  # % from the species mean
CARBON_FRACTION = 0.47
CO2_PER_C = 44 / 12


def species_means(species_id):
    """Mean of the latest dynamic MOE and green density of the species' trees."""
    rows = (
        Measurement.objects.filter(
            biodiversity_record__species_id=species_id,
            attribute__in=[A.DYNAMIC_MOE, A.GREEN_DENSITY],
            is_latest=True,
        )
        .values("attribute")
        .annotate(mean=Avg("value"))
    )
    return {r["attribute"]: r["mean"] for r in rows}


def _metric(key, label, value, unit, formula, digits=2, flag=None, note=None):
    return {
        "key": key,
        "label": label,
        "value": round(value, digits),
        "unit": unit,
        "formula": formula,
        "flag": flag,  # True: beyond the reference limit; None: no limit
        "note": note,
    }


def _crown(v):
    out = []
    ht, th, cd = v.get(A.TOTAL_HEIGHT), v.get(A.TRUNK_HEIGHT), v.get(A.CROWN_DIAMETER)
    ns, ew = v.get(A.CROWN_DIAMETER_NS), v.get(A.CROWN_DIAMETER_EW)
    if ns and ew:
        out.append(
            _metric(
                "crown_area",
                _("crown projection area"),
                math.pi / 4 * ns * ew,
                "m²",
                "π/4 · Dns · Deo",
                1,
            )
        )
        out.append(
            _metric(
                "crown_asymmetry",
                _("crown asymmetry"),
                100 * abs(ns - ew) / max(ns, ew),
                "%",
                "|Dns − Deo| / max(Dns, Deo)",
                0,
            )
        )
    elif cd:
        out.append(
            _metric(
                "crown_area",
                _("crown projection area"),
                math.pi / 4 * cd**2,
                "m²",
                "π/4 · Dc²",
                1,
            )
        )
    if ht and th is not None and 0 <= th < ht:
        out.append(
            _metric(
                "live_crown_ratio",
                _("live crown ratio"),
                100 * (ht - th) / ht,
                "%",
                "(H − Hc) / H",
                0,
            )
        )
        if cd:
            out.append(
                _metric(
                    "sail_area",
                    _("wind-exposed crown area"),
                    math.pi / 4 * (ht - th) * cd,
                    "m²",
                    "π/4 · (H − Hc) · Dc",
                    1,
                    note=_("Elliptical crown profile; wind load grows with it."),
                )
            )
    return out


def _stem(v):
    out = []
    dbh, ht = v.get(A.DIAMETER_BH), v.get(A.TOTAL_HEIGHT)
    if dbh:
        out.append(
            _metric(
                "basal_area",
                _("basal area"),
                math.pi / 4 * (dbh / 100) ** 2,
                "m²",
                "π/4 · D²",
                3,
            )
        )
    if dbh and ht:
        out.append(
            _metric("slenderness", _("slenderness"), ht / (dbh / 100), "", "H / D", 0)
        )
    damage = v.get(A.INTERNAL_DAMAGE)
    if damage is not None:
        wall = 1 - math.sqrt(min(damage, 100) / 100)
        out.append(
            _metric(
                "residual_wall",
                _("residual sound wall t/R"),
                wall,
                "",
                "1 − √a",
                2,
                flag=wall < RESIDUAL_WALL_LIMIT,
                note=_("Limit 0.32 (Mattheck); assumes a centred hollow."),
            )
        )
        out.append(
            _metric(
                "strength_loss",
                _("estimated loss of bending strength"),
                100 * (min(damage, 100) / 100) ** 1.5,
                "%",
                "(d/D)³ = a^1.5",
                0,
                note=_("Centred hollow (Wagener)."),
            )
        )
    return out


def _wood(v, wd_method, means):
    out = []
    for key, attribute, label in (
        ("moe_vs_species", A.DYNAMIC_MOE, _("dynamic MOE vs species mean")),
        (
            "green_density_vs_species",
            A.GREEN_DENSITY,
            _("green density vs species mean"),
        ),
    ):
        value, mean = v.get(attribute), means.get(attribute)
        if value is None or not mean:
            continue
        dev = 100 * (value / mean - 1)
        flag = (
            (dev <= -DEVIATION_LIMIT)
            if attribute == A.DYNAMIC_MOE
            else (abs(dev) > DEVIATION_LIMIT)
        )
        out.append(_metric(key, label, dev, "%", "x / x̄ − 1", 0, flag=flag))
    dbh, ht, wd = v.get(A.DIAMETER_BH), v.get(A.TOTAL_HEIGHT), v.get(A.WOOD_DENSITY)
    if dbh and ht and wd:
        agb = 0.0673 * (wd * dbh**2 * ht) ** 0.976
        source = (
            _("wood density measured on this tree")
            if wd_method == Measurement.MeasurementMethod.INCREMENT_BORER
            else _("wood density of the species (database)")
        )
        out.append(
            _metric(
                "biomass",
                _("above-ground biomass"),
                agb,
                "kg",
                "0.0673 · (ρ · D² · H)^0.976",
                0,
                note=_("Chave et al. 2014, fitted on forest trees; %(source)s.")
                % {"source": source},
            )
        )
        out.append(
            _metric(
                "co2",
                _("stored CO₂ equivalent"),
                agb * CARBON_FRACTION * CO2_PER_C,
                "kg",
                "AGB · 0.47 · 44/12",
                0,
            )
        )
    return out


def _priority(v, assessment, metrics):
    """Torres Payares (2025): how many intervention criteria the tree meets."""
    by_key = {m["key"]: m for m in metrics}
    checks = []
    if (damage := v.get(A.INTERNAL_DAMAGE)) is not None:
        checks.append(damage > DAMAGE_LIMIT)
    for key in ("moe_vs_species", "green_density_vs_species"):
        if key in by_key:
            checks.append(by_key[key]["flag"])
    if assessment and assessment.biomechanical_risk:
        checks.append(
            assessment.biomechanical_risk
            in (Assessment.Risk.HIGH, Assessment.Risk.EXTREME)
        )
    if assessment and assessment.visual_risk:
        checks.append(assessment.visual_risk != Assessment.Risk.LOW)
    if not checks:
        return None
    met = sum(checks)
    return _metric(
        "priority",
        _("intervention criteria met"),
        met,
        f"/ {len(checks)}",
        _(
            "damage > 50 %, MOEd ≤ −20 %, biomechanical risk high, visual risk "
            "≥ moderate, green density ±20 %"
        ),
        0,
        flag=met >= 3,
    )


def tree_metrics(record, measurements, assessment):
    """Indicators of a tree, from its measurements (the latest of each is used) and its
    latest assessment."""
    latest = {m.attribute: m for m in measurements if m.is_latest}
    v = {attribute: m.value for attribute, m in latest.items()}
    wd = latest.get(A.WOOD_DENSITY)
    means = (
        species_means(record.species_id)
        if A.DYNAMIC_MOE in v or A.GREEN_DENSITY in v
        else {}
    )
    metrics = _crown(v) + _stem(v) + _wood(v, wd and wd.method, means)
    priority = _priority(v, assessment, metrics)
    return metrics + ([priority] if priority else [])
