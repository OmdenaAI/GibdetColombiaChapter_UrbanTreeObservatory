"""Match the study's trees to the census and write the curated CSV.

Runs inside the backend container: python manage.py shell < build_rows.py
Reads /tmp/trees.json (parse_report.py) and writes /tmp/trees.csv.

Rules agreed with the project lead:
- The report wins over the spreadsheet; the spreadsheet fills what the report lacks.
- Except: a report DAP identical to the census DBH was copied from the 2015 census,
  and a report DAP ten times the spreadsheet's is a typo; both use the spreadsheet.
- Likewise heights and crown diameter: when two or more of them equal the census
  values exactly, they were copied from the census and are left out (the census rows
  stay); a single equal value can be a coincidence of rounded numbers.
- Codes that do not exist, or that point to another species, take the best census
  candidate of the same species near the report's coordinates (Annex A).
"""

import collections
import csv
import json
import math

from django.db import connection

from apps.biodiversity.models import BiodiversityRecord
from apps.reports.models import Measurement

RADIUS_M = 25
GROWTH_CM = 10  # expected DBH growth since the 2015 census
SITES = {"Separador vial": "Separador", "Anden": "Andén"}

trees = json.load(open("/tmp/trees.json", encoding="utf-8"))
codes = [t["code"] for t in trees]
species_of = {
    r.id: f"{r.species.genus.name} {r.species.name}"
    for r in BiodiversityRecord.objects.select_related("species__genus").filter(
        id__in=codes
    )
}


def census(ids, attribute="DBH"):
    """Newest census value (not from a study) per tree."""
    rows = (
        Measurement.objects.filter(
            biodiversity_record_id__in=ids, attribute=attribute, study__isnull=True
        )
        .order_by("biodiversity_record_id", "-date", "-id")
        .distinct("biodiversity_record_id")
        .values_list("biodiversity_record_id", "value")
    )
    return dict(rows)


census_dbh = census


def candidates(t):
    c = t["coords"]
    with connection.cursor() as cur:
        cur.execute(
            """
            SELECT r.id, ST_Distance(r.location, p)
            FROM biodiversity_biodiversityrecord r
            JOIN taxonomy_species s ON s.id = r.species_id
            JOIN taxonomy_genus g ON g.id = s.genus_id,
                 (SELECT ST_SetSRID(ST_MakePoint(%s, %s), 4326)::geography p) q
            WHERE g.name || ' ' || s.name = %s AND r.status = 'AC'
              AND ST_DWithin(r.location, p, %s)
            """,
            [c["lon"], c["lat"], t["species"], RADIUS_M],
        )
        return cur.fetchall()


# --- matching -------------------------------------------------------------------------
pairs = []  # (score, tree index, record id, distance)
for i, t in enumerate(trees):
    t["record_id"], t["match"], t["distance_m"] = None, None, None
    own_ok = species_of.get(t["code"]) == t["species"]
    if not t["coords"]:  # spreadsheet trees 1-60: by code
        assert own_ok, t["code"]
        t["record_id"], t["match"] = t["code"], "code"
        continue
    cands = candidates(t)
    dbh = census_dbh([r for r, _ in cands])
    dap = t["report_dap"]
    for rid, dist in cands:
        if rid == t["code"] and own_ok:
            pairs.append((-1, i, rid, dist))
            continue
        d = dbh.get(rid)
        if d is None or not (0.4 * dap <= d <= dap + 10):
            continue  # implausible size
        same = abs(d - dap) < 0.05  # the report copied this tree's census DBH
        score = 0 if same else dist + 0.5 * abs(dap - d - GROWTH_CM)
        pairs.append((score, i, rid, dist))

taken = set()
for score, i, rid, dist in sorted(pairs):
    t = trees[i]
    if t["record_id"] or rid in taken:
        continue
    t["record_id"], t["distance_m"] = rid, round(dist, 1)
    t["match"] = "code" if score == -1 else ("census_dbh" if score == 0 else "nearest")
    taken.add(rid)
for t in trees:
    if not t["record_id"]:
        t["match"] = "new"  # no plausible census tree: created with the study's code

# --- values ---------------------------------------------------------------------------
matched = [t["record_id"] for t in trees if t["record_id"]]
dbh = census_dbh(matched)
FORM = {"total_height_m": "HT", "trunk_height_m": "TH", "crown_diameter_m": "CD"}
form_census = {col: census(matched, attr) for col, attr in FORM.items()}


def r2(v):
    return None if v is None else round(v, 2)


rows = []
for t in trees:
    e, tomo, lab = t["excel"], t["tomography"], t["lab"] or {}
    excel_dap = round(e["cap_cm"] / math.pi, 2)
    dap, src = t["report_dap"], "report"
    census = dbh.get(t["record_id"])
    if census is not None and abs(dap - census) < 0.05 and t["code"] != 34979:
        dap, src = excel_dap, "spreadsheet (report copied the census)"
    elif dap > 5 * excel_dap or dap < excel_dap / 5:
        dap, src = excel_dap, "spreadsheet (typo in report)"
    ns, ew = e.get("dc_ns_m"), e.get("dc_ew_m")
    elc = e.get("elc")
    rows.append(
        {
            "record_id": t["record_id"] or t["code"],
            "match": t["match"],
            "match_distance_m": t["distance_m"],
            "study_code": t["code"],
            "spreadsheet_no": t["excel_no"],
            "report_no": t["species_no"],
            "species": t["species"],
            "latitude": round(t["coords"]["lat"], 7) if t["coords"] else None,
            "longitude": round(t["coords"]["lon"], 7) if t["coords"] else None,
            "dbh_cm": round(dap, 2),
            "dbh_source": src,
            "total_height_m": e["ht_m"],
            "trunk_height_m": e.get("hc_m"),
            "crown_diameter_ns_m": ns,
            "crown_diameter_ew_m": ew,
            "crown_diameter_m": r2((ns + ew) / 2) if ns and ew else None,
            "crown_exposure_class": int(elc) if elc and elc <= 5 else None,
            "crown_exposure_percent": int(elc) if elc and elc > 5 else None,
            "age_class": e["er"],
            "planting_site": SITES.get(e["site"], e["site"]),
            "notes": e.get("notes"),
            "tomography_level": tomo["level"],
            "internal_damage_percent": tomo["damage"],
            "transverse_velocity_m_s": tomo["vt"],
            "damage_section_diameter_cm": tomo["dst"],
            "damage_section_height_cm": tomo["hst"],
            "tomography_sections": t["tomography_sections"],
            "visual_risk": t["eva_risk"],
            "visual_risk_part": t["eva_part"],
            "biomechanical_risk": t["biomechanical_risk"],
            "green_density_g_cm3": lab.get("dv"),
            "basic_density_g_cm3": lab.get("db"),
            "dynamic_moe_mpa": lab.get("moed"),
        }
    )

for row in rows:
    same = [
        col
        for col in FORM
        if row[col] is not None
        and form_census[col].get(row["record_id"]) is not None
        and abs(row[col] - form_census[col][row["record_id"]]) < 0.005
    ]
    row["copied_from_census"] = " ".join(same) if len(same) >= 2 else ""
    for col in same if len(same) >= 2 else []:
        row[col] = None
    if "crown_diameter_m" in row["copied_from_census"].split():
        row["crown_diameter_ns_m"] = row["crown_diameter_ew_m"] = None

with open("/tmp/trees.csv", "w", newline="", encoding="utf-8") as f:
    w = csv.DictWriter(f, fieldnames=list(rows[0]))
    w.writeheader()
    w.writerows(rows)

for t in trees:
    if t["match"] != "code" or t["coords"] and t["record_id"] != t["code"]:
        print(
            t["code"],
            t["species"][:10],
            t["match"],
            t["record_id"],
            t["distance_m"],
            "dap",
            t["report_dap"],
            "census",
            dbh.get(t["record_id"]),
        )

print(
    "copied:",
    [
        (r["record_id"], r["copied_from_census"])
        for r in rows
        if r["copied_from_census"]
    ],
)
print(
    collections.Counter(r["match"] for r in rows),
    collections.Counter(r["dbh_source"] for r in rows),
)
