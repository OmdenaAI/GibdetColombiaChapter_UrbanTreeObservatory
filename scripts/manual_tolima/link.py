"""Link the extracted manual sheets to the catalog species.

Usage (API running on localhost:8000):
    python3 scripts/manual_tolima/link.py entries.json backend/apps/taxonomy/data/manual_tolima.json

Keeps only the sheets of species in the catalog, adding ``"species"`` (the catalog's
scientific name). Sheets are matched by the binomial of the manual's name; where the manual
uses a synonym or misspells the name, SYN maps it to the catalog's (each one checked by hand).
Citrus nobilis and Callistemon speciosus are left out on purpose: not clear synonyms of the
catalog's Citrus reticulata / Callistemon citrinus.
"""
import json, os, re, sys, unicodedata, urllib.request
def norm(s): return unicodedata.normalize("NFKD", s).encode("ascii","ignore").decode().lower()
def binom(s): return " ".join(re.sub(r"[^A-Za-z\s-]", " ", norm(s)).split()[:2])
cat=[]; url="http://localhost:8000/api/v1/taxonomy/species/?page_size=100"
while url:
    d=json.load(urllib.request.urlopen(url)); cat+=d["results"]; url=d.get("next")
# Manual name (binomial, normalized) -> catalog binomial, where the manual uses a synonym or misspells.
SYN = {
    "melicocca bijuga": "melicoccus bijugatus", "eugenia malaccensis": "syzygium malaccense",
    "cespedesia macrophylla": "cespedesia spathulata", "rapanea guianensis": "myrsine guianensis",
    "artocarpus communis": "artocarpus altilis", "tabernaemontana coronaria": "tabernaemontana divaricata",
    "crhysophyllum cainito": "chrysophyllum cainito", "eritrina fusca": "erythrina fusca",
    "eugenia jambos": "syzygium jambos", "yucca elephantipes": "yucca gigantea",
    "veitchia merrillii": "adonidia merrillii", "sabal mauritiiforme": "sabal mauritiiformis",
    "nageia rospigliosii": "retrophyllum rospigliosii",
}
by={}
for s in cat:
    sci=s["scientific_name"]
    for n in (sci, " ".join(sci.split()[-2:]), s.get("accepted_scientific_name") or ""):
        if n: by.setdefault(binom(n), sci)
out=[]; unmatched=[]
for e in json.load(open(sys.argv[1], encoding="utf-8")):
    b=binom(e["scientific_name"]); target=SYN.get(b,b); sp=by.get(target)
    if sp: out.append({"species": sp, **e}); print(f"{'≈' if b in SYN else '='} p.{e['pages'][0]:<4} {e['scientific_name'][:42]:42} -> {sp}")
    else: unmatched.append(f"p.{e['pages'][0]} {e['scientific_name']}")
dupes={o["species"] for o in out if sum(p["species"]==o["species"] for p in out)>1}
print(len(out),"linked;",len(unmatched),"not in catalog; duplicates:",dupes or "none")
print("not in catalog:", "; ".join(unmatched))
json.dump(out, open(sys.argv[2], "w", encoding="utf-8"), ensure_ascii=False, indent=1)
