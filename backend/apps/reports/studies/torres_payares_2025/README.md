# Torres Payares (2025): instrumental assessment of 100 urban trees

Source: Lewys Eduardo Torres Payares, *Evaluación instrumental del arbolado urbano a
través de ensayos no destructivos…*, final report of the social-service project
(Ingeniería Forestal, Universidad del Tolima, 2025), and its field spreadsheet
*Base de datos Muestreo arbóreo.xlsx*. The data is loaded with the author's
authorization; cite it with the reference in `study.json`.

100 trees, 25 per species: *Anacardium excelsum* (caracolí), *Ceiba pentandra* (ceiba),
*Samanea saman* (samán) and *Tabebuia rosea* (ocobo). In the report each species is
numbered 1–25: numbers 1–15 were visually assessed by Giraldo (2023) and 16–25 in this
study, which also cored them for density and measured their stiffness.

## Files

| File | Content |
|---|---|
| `study.json` | Metadata of the `Study` row: citation, methods, date |
| `trees.csv` | One row per census tree, values already reconciled (see below) |
| `build/parse_report.py` | Reads the report's text (Tables 3, 6–10, Annexes A and C) and the spreadsheet |
| `build/build_rows.py` | Matches the trees to the census and writes `trees.csv` |

Load (idempotent: replaces this study's rows, keeps the rest of each tree's history):

```bash
docker compose exec backend python manage.py import_study apps/reports/studies/torres_payares_2025
```

## What is stored

| Variable | Where | Method | Trees |
|---|---|---|---|
| DBH (from circumference, CAP/π) | Measurement `DBH` | tape | 100 |
| Total height, crown base (trunk) height | `HT`, `TH` | laser hypsometer (Nikon Forestry Pro) | 91, 90 |
| Crown diameter N-S, E-W and their mean | `CDN`, `CDE`, `CD` | tape | 97 |
| Internal damage, max. % of the section | `ID` | acoustic tomography (ArborSonic 3D) | 100 |
| Transverse acoustic velocity | `AV` | acoustic tomography | 100 |
| Green density | `GD` | Pressler increment borer | 40 |
| Basic density (dry mass / green volume) | `WD` | increment borer | 40 |
| Dynamic modulus of elasticity, MOEd = V²·Dv | `MOE` | stress wave timer (TreeSonic) | 40 |
| Visual risk (EVA, ISA form) and part at risk | `Assessment` | Table 3 | 100 |
| Biomechanical risk | `Assessment` | ArborSonic 3D, Table 10 | 100 |
| Damage level, diameter and height of the worst section | `Assessment` | Tables 6–9 | 100 |
| Age class, planting site, crown light exposure, notes | `Assessment` | spreadsheet | 100 |
| Phytosanitary status, physical condition | `Observation` | derived (below) | 100 |

Each tree also gets a new **observation** dated with the study, which keeps the
census fields of the previous one (the census observation stays as history):

- **Phytosanitary status** from the decay found by the tomography, since rot is a
  sanitary problem: *critical* when it reaches 50 % of the section (the report's
  intervention threshold), *sick* from 10 % or when the field notes describe rot, fungi,
  chlorosis or dead wood, *healthy* otherwise. Result: 51 healthy, 39 sick, 10 critical
  (the census had 95 healthy and 5 sick).
- **Physical condition** from the risk, a structural matter that does not by itself make
  a tree sick: *poor* when the visual or the biomechanical risk is high or extreme,
  *fair* when either is moderate, *good* otherwise. Result: 69 good, 21 fair, 10 poor.

Basic density is the quantity of the global wood density database (one value per
species), so for the 40 cored trees it becomes the tree's latest `WD`; every other tree
keeps its species value. Green density depends on the wood's moisture and is not used
for biomass.

All values are dated **2025-07-22**, the date of the final report: the sources give no
measurement dates.

## Reconciliation rules

1. **The report wins** over the spreadsheet; the spreadsheet fills what the report
   lacks (heights, crown, site, age, notes).
2. **Values copied from the census are not new measurements.** Seven report DBHs equal
   the 2015 census to the decimal while the spreadsheet has a field value; those use the
   spreadsheet. Tree 34979 is the exception: the spreadsheet's 50.9 cm is a typing
   error and both the report and the census say 111 cm. In 9 trees two or more of total
   height, trunk height and crown diameter equal the census exactly (column
   `copied_from_census`); they are left out and the census values stay.
3. **Typos**: report DBHs 11.5 and 1558 (ten times off) use the spreadsheet (110.5,
   155.8).
4. **Tomography**: trees scanned at several heights or stems (rows 2a, 2b… in Tables
   8–9) keep the section with the highest damage. The damage percentages of Annex C
   contradict Tables 6–9 (for *A. excelsum* that column holds the section diameter);
   the tables are used.
5. **The spreadsheet's crown length (HLT C)** is not HT − HC in 68 of 99 trees, and in
   11 it exceeds the total height; it is not loaded. The crown length is computed as
   HT − HC.
6. **Crown light exposure (ELC)** uses two scales: classes 1–5 for numbers 1–15 and
   percentages for 16–25. They are stored in separate fields.

## Matching to the census

The 60 trees numbered 1–15 match by code (same species). Of the 40 assessed in this
study, 18 match by code. For the other 22 the code does not exist in the census (20) or
belongs to another species several km away (39132, 40163). Each one takes the best census
tree of the same species within 25 m of the coordinates in Annex A, by distance and
DBH growth since 2015, with no tree used twice (column `match`):

- `census_dbh` (4): the report's DBH is that tree's census DBH, so the match is certain.
- `nearest` (18): the best candidate. The study's coordinates lie 5–12 m from the
  census points throughout, which looks like an offset between the two surveys. The
  weakest match is 32475 → 115026 (22.6 m; 44 cm in 2015, 91 cm in the report).

The census location of each tree is kept. The assessment's notes record how a tree was
matched and when its DBH came from the spreadsheet.

## Known gaps

- No raw ArborSonic or TreeSonic files: the safety factor is known only for ceiba No. 18
  (21 %).
- The report's list of trees to intervene (ceiba 16, samán 7, ocobo 6, 7 and 19) does
  not follow its own five criteria literally. On the tree page, the indicator
  *intervention criteria met* applies them as written. With every criterion that can be
  checked, ceibas 16 and 17 meet three or more.
