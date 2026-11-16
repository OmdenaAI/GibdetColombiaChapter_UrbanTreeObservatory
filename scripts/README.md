# Data Exploration Script

The `explore_csv_data.py` script analyzes CSV files to identify unique values for fields that map to TextChoices in Django models, helping you understand your data before importing it.

```bash
python scripts/explore_csv_data.py --data-dir=/path/to/csv/files [--output-dir=./reports]
```

**Output:**

- `csv_exploration_report.txt`: A plain text report with unique values.
- `csv_exploration_report.html`: An HTML report with more detailed information, including data types and value frequencies.
- `mapping_template.json`: A JSON template that can be edited to define mappings for TextChoices.

# Tolima arborization manual (species sheets)

The species detail shows, verbatim, the species' sheet from *Manual de arborización para el
departamento del Tolima* (Cortolima – Jardín Botánico San Jorge, 2017; sheets on pp. 148-255).
The reviewed data lives in `backend/apps/taxonomy/data/manual_tolima.json` and is loaded with
`python manage.py load_manual_tolima`. To regenerate it from the PDF (needs poppler):

```bash
python3 scripts/manual_tolima/extract.py MANUAL.pdf > entries.json      # 108 sheets
python3 scripts/manual_tolima/extract.py MANUAL.pdf --report            # bold prefixes it did not classify
python3 scripts/manual_tolima/link.py entries.json backend/apps/taxonomy/data/manual_tolima.json
```

The text is kept as written in the manual, typos included; only line breaks from the layout
are joined. Check any change against the PDF pages before committing the JSON.
