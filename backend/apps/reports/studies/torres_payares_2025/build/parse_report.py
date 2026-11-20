"""Turn the report text and the spreadsheet dump into one JSON per tree (no DB access).

Usage: python3 -I parse_report.py informe.txt muestreo.json anexo_a.json anexo_c.json out.json
"""

import json
import re
import sys

informe, muestreo, anexo_a, anexo_c, out = sys.argv[1:6]
text = open(informe, encoding="utf-8").read()
excel = json.load(open(muestreo, encoding="utf-8"))
coords = {r["code"]: r for r in json.load(open(anexo_a))}
lab = {r["code"]: r for r in json.load(open(anexo_c))}

SPECIES = ["Caracoli", "Ceiba", "Saman", "Ocobo"]  # column order of Tables 3 and 10
SCIENTIFIC = {
    "Caracoli": "Anacardium excelsum",
    "Ceiba": "Ceiba pentandra",
    "Saman": "Samanea saman",
    "Ocobo": "Tabebuia rosea",
}


def num(s):
    s = (s or "").strip().rstrip("-").rstrip(".,")
    if s in ("", "-"):
        return None
    return float(s.replace(",", "."))  # the report mixes decimal comma and point


# --- Tables 6-9: acoustic tomography (body copies, after the table of contents) -----
BODY = text.index("4.2.1 Anacardium excelsum (Bertero & Balb.) Skeels. De")
TOMO_TABLES = {
    "Caracoli": ("Tabla 6.", "Tabla 7."),
    "Ocobo": ("Tabla 7.", "Tabla 8."),
    "Saman": ("Tabla 8.", "Tabla 9."),
    "Ceiba": ("Tabla 9.", "Tabla 10."),
}
LEVELS = "Sin afectación|Muy alto|Medio|Bajo|Alto"
ROW = re.compile(
    rf"^\s*(\d{{1,2}})([a-cA-C]?)\s+(\S+)\s+([\d.,]+)\s+({LEVELS})\s+(\d+)\s+(\S+)\s+(\S+)\s*$",
    re.M,
)
tomo = {}
for sp, (a, b) in TOMO_TABLES.items():
    start = text.index(a, BODY)
    seg = text[start : text.index(b, start)]
    for m in ROW.finditer(seg):
        no = int(m[1])
        tomo.setdefault((sp, no), []).append(
            {
                "section": m[2].lower(),
                "dap": num(m[3]) if m[3] != "81.," else 81.1,
                "vt": num(m[4]),
                "level": m[5],
                "damage": float(m[6]),
                "dst": num(m[7]),
                "hst": num(m[8]),
            }
        )
for sp in SPECIES:
    missing = [n for n in range(1, 26) if (sp, n) not in tomo]
    assert not missing, (sp, missing)

# --- Table 3: visual assessment (EVA), transcribed: the PDF wraps its cells -----
F, R, C, FR, FC, CR, CF, RF = (
    "Fuste",
    "Ramas",
    "Copa",
    "Fuste y ramas",
    "Fuste y copa",
    "Copa y ramas",
    "Copa y fuste",
    "Ramas y fuste",
)
B, M, A = "Bajo", "Moderado", "Alto"
EVA = {  # No.: (Caracoli, Ceiba, Saman, Ocobo) as (risk, part)
    1: ((B, F), (B, FR), (B, FC), (B, R)),
    2: ((B, F), (B, FR), (B, C), (B, FR)),
    3: ((B, F), (B, R), (B, F), (B, FR)),
    4: ((B, R), (B, RF), (B, F), (B, FR)),
    5: ((B, F), (B, C), (M, F), (B, F)),
    6: ((B, FC), (B, R), (B, F), (B, FR)),
    7: ((B, FC), (B, FC), (B, C), (B, R)),
    8: ((B, CR), (M, CF), (B, R), (M, F)),
    9: ((B, F), (B, FR), (B, R), (B, FC)),
    10: ((M, C), (B, FC), (B, R), (B, FR)),
    11: ((B, F), (M, CR), (B, RF), (M, R)),
    12: ((B, R), (B, FC), (B, R), (B, R)),
    13: ((B, R), (M, R), (B, FR), (B, FR)),
    14: ((B, F), (B, FR), (B, R), (B, FR)),
    15: ((B, FC), (B, FR), (B, R), (B, F)),
    16: ((B, CR), (A, CR), (B, CR), (M, F)),
    17: ((B, CR), (M, CR), (B, CR), (M, F)),
    18: ((M, CR), (B, CR), (M, CR), (M, "Copa y raíz")),
    19: ((B, CR), (B, CR), (M, CR), (B, CR)),
    20: ((B, CR), (B, CR), (A, CR), (B, CF)),
    21: ((B, CR), (B, CR), (M, CR), (B, CR)),
    22: ((B, CR), (B, CR), (M, CR), (A, F)),
    23: ((B, CR), (B, CR), (B, CR), (B, CR)),
    24: ((M, CR), (M, CR), (B, CR), (B, CF)),
    25: ((B, CR), (A, CR), (B, CR), (M, CR)),
}

# --- Table 10: biomechanical risk (ArborSonic 3D) -----------------------------------
start = text.index("Tabla 10.", BODY)
seg = text[start : text.index("Esta tensión", start)]
BIO = {}
for m in re.finditer(r"^\s*(\d{1,2})\s+(\w+)\s+(\w+)\s+(\w+)\s+(\w+)\s*$", seg, re.M):
    BIO[int(m[1])] = m.groups()[1:]
assert len(BIO) == 25

# --- Spreadsheet: per-species order gives the report number (1-15 then 16-25) -------
by_sp = {}
for r in excel:
    sp = "Caracoli" if r["species"].startswith("Caracol") else r["species"]
    by_sp.setdefault(sp, []).append(r)
trees = []
for sp, rows in by_sp.items():
    seq = [r for r in rows if r["n"] <= 60] + [r for r in rows if r["n"] > 60]
    assert len(seq) == 25, sp
    col = SPECIES.index(sp)
    for no, r in enumerate(seq, start=1):
        code = int(r["code"])
        sections = tomo[(sp, no)]
        main = sections[0]
        worst = max(sections, key=lambda s: (s["damage"], s is main))
        eva_risk, eva_part = EVA[no][col]
        trees.append(
            {
                "excel_no": int(r["n"]),
                "species_no": no,
                "species": SCIENTIFIC[sp],
                "code": code,
                "excel": r,
                "report_dap": main["dap"],
                "tomography": worst,
                "tomography_sections": len(sections),
                "eva_risk": eva_risk,
                "eva_part": eva_part,
                "biomechanical_risk": BIO[no][col],
                "lab": lab.get(code),
                "coords": coords.get(code),
            }
        )
json.dump(trees, open(out, "w"), ensure_ascii=False, indent=1)
print(len(trees), "trees")
