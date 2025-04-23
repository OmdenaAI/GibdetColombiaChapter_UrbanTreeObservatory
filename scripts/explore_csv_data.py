#!/usr/bin/env python3
"""
Enhanced data exploration script for Urban Tree Observatory CSV files.

This script analyzes CSV files from the Urban Tree Observatory dataset
and extracts key information needed for model updates and mapping strategies.

Usage:
    python scripts/explore_csv_data.py --data-dir=/path/to/csv/files

Output:
    - csv_exploration_report.txt: Plain text report with unique values
    - csv_exploration_report.html: HTML report with more detailed information
    - mapping_template.json: Template for value mappings
"""

import os
import csv
import argparse
import json
from collections import Counter
import datetime
import re


# Fields that map to TextChoices in Django models
TEXT_CHOICE_FIELDS = {
    "taxonomy.csv": [
        "origin",
        "iucn_category",
        "lifeForm",
        "canopy_shape_code",
        "flower_color_code",
    ],
    "biodiversity.csv": [],
    "measurements.csv": ["measurement_name", "measurement_unit", "measurement_method"],
    "observations.csv": [
        "reproductive_condition",
        "phytosanitary_status",
        "physical_condition",
        "foliage_density",
        "aesthetic_value",
        "growth_phase",
        "standing",
        "rd",
        "dm",
        "bbs",
        "ab",
        "ed",
        "pi",
        "ph",
        "pa",
        "hc",
        "hcf",
        "pd",
        "pe",
        "pp",
        "po",
        "cre",
        "crh",
        "cra",
        "coa",
        "ce",
        "civ",
        "crt",
        "crg",
        "cap",
        "r_vol",
        "r_cr",
        "r_ce",
    ],
    "places.csv": [],
    "traits.csv": [],
    "climate.csv": ["sensordescription", "measureunit"],
}

# Other interesting fields to analyze (not TextChoices)
ADDITIONAL_FIELDS = {
    "taxonomy.csv": [
        "family",
        "genus",
        "specie",
        "accept_scientific_name",
        "identified_by",
        "gbif_id",
    ],
    "biodiversity.csv": [
        "common_name",
        "registered_by",
    ],
    "measurements.csv": [],
    "observations.csv": ["accompanying_collectors"],
    "places.csv": [
        "country",
        "department",
        "municipality",
        "populated_center",
        "zone",
        "subzone",
        "site",
    ],
    "traits.csv": [],
    "climate.csv": [
        "stationcode",
        "stationname",
        "longitude",
        "latitude",
        "sensordescription",
        "measureunit",
    ],
}

# Fields to sample (show sample values rather than all unique values)
SAMPLE_FIELDS = {
    "biodiversity.csv": ["code_record", "place_id", "taxonomy_id"],
    "measurements.csv": ["record_code"],
    "observations.csv": ["record_code"],
    "taxonomy.csv": ["gbif_id"],
}

# Fields to analyze for special patterns
PATTERN_FIELDS = {
    "biodiversity.csv": ["code_record"],
    "measurements.csv": ["record_code"],
    "observations.csv": ["record_code"],
    "taxonomy.csv": ["specie", "accept_scientific_name", "gbif_id"],
}

# Fields to analyze for relationship mapping
RELATIONSHIP_FIELDS = {
    "biodiversity.csv": [("code_record", "taxonomy_id", "place_id")],
    "measurements.csv": [("record_code",)],
    "observations.csv": [("record_code",)],
}


def read_csv(file_path):
    """Read a CSV file and return its contents as a list of dictionaries."""
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            return list(reader)
    except FileNotFoundError:
        print(f"File not found: {file_path}")
        return []
    except Exception as e:
        print(f"Error reading {file_path}: {e}")
        return []


def extract_unique_values(data, fields):
    """Extract unique values for specified fields in the data."""
    result = {}
    for field in fields:
        values = [row.get(field, "").strip() for row in data if row.get(field)]
        # Remove empty values
        values = [v for v in values if v]
        # Count occurrences of each value
        value_counts = Counter(values)
        # Sort by frequency (most common first)
        sorted_values = sorted(value_counts.items(), key=lambda x: (-x[1], x[0]))
        result[field] = sorted_values
    return result


def sample_values(data, fields, sample_size=5):
    """Extract sample values for specified fields."""
    result = {}
    for field in fields:
        values = [row.get(field, "").strip() for row in data if row.get(field)]
        # Remove empty values
        values = [v for v in values if v]
        # Get unique values
        unique_values = list(set(values))

        # If more than twice our sample size, show first few and last few
        if len(unique_values) > sample_size * 2:
            first_samples = unique_values[:sample_size]
            last_samples = unique_values[-sample_size:]
            result[field] = {
                "total_unique": len(unique_values),
                "first_samples": first_samples,
                "last_samples": last_samples,
                "total_values": len(values),
            }
        else:
            result[field] = {
                "total_unique": len(unique_values),
                "all_samples": unique_values[: sample_size * 2],
                "total_values": len(values),
            }
    return result


def analyze_patterns(data, fields):
    """Analyze fields for common patterns."""
    result = {}
    for field in fields:
        values = [row.get(field, "").strip() for row in data if row.get(field)]
        values = [v for v in values if v]

        if not values:
            result[field] = {"pattern": "No values found"}
            continue

        # Sample a subset for pattern analysis
        sample = values[:100]

        # Common patterns to check
        patterns = {
            "numeric_only": all(v.isdigit() for v in sample),
            "contains_digits": any(re.search(r"\d", v) for v in sample),
            "contains_dash": any("-" in v for v in sample),
            "contains_slash": any("/" in v for v in sample),
            "contains_space": any(" " in v for v in sample),
            "contains_punctuation": any(re.search(r"[^\w\s]", v) for v in sample),
            "starts_with_number": any(re.match(r"^\d", v) for v in sample),
            "starts_with_letter": any(re.match(r"^[a-zA-Z]", v) for v in sample),
        }

        # Add field-specific patterns
        if field == "specie" or field == "accept_scientific_name":
            patterns["contains_genus"] = any(
                re.search(r"^[A-Z][a-z]+ [a-z]+", v) for v in sample
            )

        if field == "gbif_id":
            patterns["contains_url"] = any(re.search(r"http", v) for v in sample)

        if field == "code_record" or field == "record_code":
            patterns["format_like_xx_yyyyy"] = any(
                re.search(r"^\d+_\d+$", v) for v in sample
            )
            patterns["format_like_yyyyy_xx"] = any(
                re.search(r"^\d+_\d+$", v) for v in sample
            )
            patterns["contains_f3"] = any("F3" in v.upper() for v in sample)

        # Check pattern consistency
        for pattern_name, pattern_exists in patterns.items():
            if pattern_exists:
                # Check if ALL values follow the pattern
                all_match = True
                for v in sample:
                    if pattern_name == "numeric_only" and not v.isdigit():
                        all_match = False
                        break
                    elif pattern_name == "contains_digits" and not re.search(r"\d", v):
                        all_match = False
                        break
                    elif pattern_name == "contains_dash" and "-" not in v:
                        all_match = False
                        break
                    elif pattern_name == "contains_slash" and "/" not in v:
                        all_match = False
                        break
                    elif pattern_name == "contains_space" and " " not in v:
                        all_match = False
                        break
                    elif pattern_name == "contains_punctuation" and not re.search(
                        r"[^\w\s]", v
                    ):
                        all_match = False
                        break
                    elif pattern_name == "starts_with_number" and not re.match(
                        r"^\d", v
                    ):
                        all_match = False
                        break
                    elif pattern_name == "starts_with_letter" and not re.match(
                        r"^[a-zA-Z]", v
                    ):
                        all_match = False
                        break
                    elif pattern_name == "contains_genus" and not re.search(
                        r"^[A-Z][a-z]+ [a-z]+", v
                    ):
                        all_match = False
                        break
                    elif pattern_name == "contains_url" and not re.search(r"http", v):
                        all_match = False
                        break
                    elif pattern_name == "format_like_xx_yyyyy" and not re.search(
                        r"^\d+_\d+$", v
                    ):
                        all_match = False
                        break
                    elif pattern_name == "format_like_yyyyy_xx" and not re.search(
                        r"^\d+_\d+$", v
                    ):
                        all_match = False
                        break
                    elif pattern_name == "contains_f3" and "F3" not in v.upper():
                        all_match = False
                        break

                patterns[pattern_name] = "all" if all_match else "some"

        # Extract minimum and maximum lengths
        lengths = [len(v) for v in sample]
        min_length = min(lengths) if lengths else 0
        max_length = max(lengths) if lengths else 0

        result[field] = {
            "patterns": patterns,
            "min_length": min_length,
            "max_length": max_length,
            "example_values": sample[:5],
        }
    return result


def analyze_relationships(biodiversity_data, measurements_data, observations_data):
    """Analyze relationships between code_record and record_code fields."""
    result = {}

    # Extract code_record values from biodiversity records
    bio_codes = set(
        [
            row.get("code_record", "").strip()
            for row in biodiversity_data
            if row.get("code_record")
        ]
    )

    # Extract record_code values from measurements
    meas_codes = set(
        [
            row.get("record_code", "").strip()
            for row in measurements_data
            if row.get("record_code")
        ]
    )

    # Extract record_code values from observations
    obs_codes = set(
        [
            row.get("record_code", "").strip()
            for row in observations_data
            if row.get("record_code")
        ]
    )

    # Check overlap
    bio_meas_overlap = len(bio_codes.intersection(meas_codes))
    bio_obs_overlap = len(bio_codes.intersection(obs_codes))
    meas_obs_overlap = len(meas_codes.intersection(obs_codes))

    # Look for patterns in relationships
    meas_bio_examples = []
    obs_bio_examples = []

    for meas_code in list(meas_codes)[:5]:
        matches = [code for code in bio_codes if code in meas_code or meas_code in code]
        if matches:
            meas_bio_examples.append((meas_code, matches[0]))

    for obs_code in list(obs_codes)[:5]:
        matches = [code for code in bio_codes if code in obs_code or obs_code in code]
        if matches:
            obs_bio_examples.append((obs_code, matches[0]))

    result["biodiversity_measurements_relationship"] = {
        "biodiversity_records_count": len(bio_codes),
        "measurements_records_count": len(meas_codes),
        "overlap_count": bio_meas_overlap,
        "overlap_percentage": round(
            bio_meas_overlap / len(bio_codes) * 100 if bio_codes else 0, 2
        ),
        "examples": meas_bio_examples,
    }

    result["biodiversity_observations_relationship"] = {
        "biodiversity_records_count": len(bio_codes),
        "observations_records_count": len(obs_codes),
        "overlap_count": bio_obs_overlap,
        "overlap_percentage": round(
            bio_obs_overlap / len(bio_codes) * 100 if bio_codes else 0, 2
        ),
        "examples": obs_bio_examples,
    }

    result["measurements_observations_relationship"] = {
        "measurements_records_count": len(meas_codes),
        "observations_records_count": len(obs_codes),
        "overlap_count": meas_obs_overlap,
        "overlap_percentage": round(
            meas_obs_overlap / len(meas_codes) * 100 if meas_codes else 0, 2
        ),
    }

    return result


def analyze_species_names(data):
    """Analyze species names to check for genus inclusion."""
    result = {}
    species_data = []

    for row in data:
        species_name = row.get("specie", "").strip()
        genus = row.get("genus", "").strip()

        if species_name and genus:
            # Check if species name starts with genus
            starts_with_genus = species_name.startswith(genus)

            # If it doesn't start with genus, check if it contains genus followed by space
            contains_genus = (
                genus + " " in species_name if not starts_with_genus else False
            )

            species_data.append(
                {
                    "species_name": species_name,
                    "genus": genus,
                    "starts_with_genus": starts_with_genus,
                    "contains_genus": contains_genus,
                }
            )

    # Summarize findings
    total = len(species_data)
    starts_with_genus_count = sum(
        1 for item in species_data if item["starts_with_genus"]
    )
    contains_genus_count = sum(1 for item in species_data if item["contains_genus"])

    result["total_species"] = total
    result["species_starting_with_genus"] = starts_with_genus_count
    result["species_starting_with_genus_percentage"] = round(
        starts_with_genus_count / total * 100 if total else 0, 2
    )
    result["species_containing_genus"] = contains_genus_count
    result["species_containing_genus_percentage"] = round(
        contains_genus_count / total * 100 if total else 0, 2
    )

    # Examples where species doesn't include genus
    no_genus_examples = [
        item
        for item in species_data
        if not item["starts_with_genus"] and not item["contains_genus"]
    ]
    result["species_without_genus_examples"] = no_genus_examples[:5]

    return result


def analyze_measurement_units(data):
    """Analyze measurement names to infer units."""
    result = {}

    measurement_types = {}

    for row in data:
        name = row.get("measurement_name", "").strip()
        method = row.get("measurement_method", "").strip()

        if name:
            if name not in measurement_types:
                measurement_types[name] = {"methods": Counter(), "count": 0}

            measurement_types[name]["count"] += 1
            if method:
                measurement_types[name]["methods"][method] += 1

    # Analyze each measurement type
    for name, info in measurement_types.items():
        unit = "unknown"

        # Infer units based on measurement name
        if "volume" in name.lower() and "m3" in name.lower():
            unit = "m3"
        elif "diameter" in name.lower() and "cm" in name.lower():
            unit = "cm"
        elif "density" in name.lower() and "g/cm3" in name.lower():
            unit = "g/cm3"
        elif (
            "height" in name.lower()
            or "crown" in name.lower()
            or "canopy" in name.lower()
        ):
            unit = "m"

        # Find most common method
        most_common_method = (
            info["methods"].most_common(1)[0][0] if info["methods"] else "unknown"
        )

        result[name] = {
            "count": info["count"],
            "inferred_unit": unit,
            "most_common_method": most_common_method,
            "methods": [
                {"method": method, "count": count}
                for method, count in info["methods"].most_common()
            ],
        }

    return result


def analyze_data_types(data, fields):
    """Analyze potential data types of fields."""
    result = {}
    for field in fields:
        values = [row.get(field, "").strip() for row in data if row.get(field)]
        # Remove empty values
        values = [v for v in values if v]

        # Sample up to 100 values
        sample = values[:100]

        # Check if values look like numbers
        numeric = all(
            v.replace(".", "", 1).isdigit() for v in sample if v and v.count(".") <= 1
        )

        # Check if values look like dates (simple check)
        date_formats = ["%Y-%m-%d", "%d/%m/%Y", "%m/%d/%Y", "%d-%m-%Y"]
        dates = False
        for date_format in date_formats:
            try:
                if sample and all(
                    datetime.datetime.strptime(v, date_format) for v in sample if v
                ):
                    dates = True
                    break
            except ValueError:
                continue

        # Determine likely type
        if numeric:
            data_type = "numeric"
        elif dates:
            data_type = "date"
        else:
            data_type = "text"

        result[field] = data_type
    return result


def generate_text_report(
    analysis_results,
    sample_results,
    pattern_results,
    species_analysis,
    measurement_analysis,
    relationship_analysis,
    column_lists,
    output_file,
):
    """Generate a plain text report from the analysis results."""
    with open(output_file, "w", encoding="utf-8") as f:
        f.write("Urban Tree Observatory Data Exploration Report\n")
        f.write("=" * 50 + "\n\n")

        # First, list all files and their columns
        f.write("CSV Files and Their Columns\n")
        f.write("=" * 30 + "\n\n")

        for csv_file, columns in column_lists.items():
            f.write(f"File: {csv_file}\n")
            f.write("-" * 30 + "\n")
            f.write(f"  Total columns: {len(columns)}\n")
            f.write("  Column list:\n")
            for col in columns:
                f.write(f"    - {col}\n")
            f.write("\n")

        f.write("\n" + "=" * 50 + "\n\n")

        # Write relationship analysis
        f.write("Relationship Analysis\n")
        f.write("=" * 30 + "\n\n")

        for rel_name, rel_info in relationship_analysis.items():
            f.write(f"  {rel_name}:\n")
            for key, value in rel_info.items():
                if key == "examples":
                    f.write(f"    {key}:\n")
                    for ex in value:
                        f.write(f"      - {ex[0]} -> {ex[1]}\n")
                else:
                    f.write(f"    {key}: {value}\n")
            f.write("\n")

        # Write species name analysis
        f.write("Species Name Analysis\n")
        f.write("=" * 30 + "\n\n")

        for key, value in species_analysis.items():
            if key == "species_without_genus_examples":
                f.write(f"  {key}:\n")
                for ex in value:
                    f.write(
                        f"    - Species: {ex['species_name']}, Genus: {ex['genus']}\n"
                    )
            else:
                f.write(f"  {key}: {value}\n")
        f.write("\n")

        # Write measurement analysis
        f.write("Measurement Analysis\n")
        f.write("=" * 30 + "\n\n")

        for name, info in measurement_analysis.items():
            f.write(f"  {name}:\n")
            f.write(f"    count: {info['count']}\n")
            f.write(f"    inferred_unit: {info['inferred_unit']}\n")
            f.write(f"    most_common_method: {info['most_common_method']}\n")
            f.write("    methods:\n")
            for method_info in info["methods"]:
                f.write(f"      - {method_info['method']}: {method_info['count']}\n")
            f.write("\n")

        # Write sampled values
        f.write("Sampled Values Analysis\n")
        f.write("=" * 30 + "\n\n")

        for csv_file, field_samples in sample_results.items():
            f.write(f"File: {csv_file}\n")
            f.write("-" * 30 + "\n\n")

            for field, sample_info in field_samples.items():
                f.write(f"  Field: {field}\n")
                f.write(f"    Total unique values: {sample_info['total_unique']}\n")
                f.write(f"    Total values: {sample_info['total_values']}\n")

                if "all_samples" in sample_info:
                    f.write("    All samples:\n")
                    for sample in sample_info["all_samples"]:
                        f.write(f"      - '{sample}'\n")
                else:
                    f.write("    First samples:\n")
                    for sample in sample_info["first_samples"]:
                        f.write(f"      - '{sample}'\n")
                    f.write("    Last samples:\n")
                    for sample in sample_info["last_samples"]:
                        f.write(f"      - '{sample}'\n")
                f.write("\n")

        # Write pattern analysis
        f.write("Pattern Analysis\n")
        f.write("=" * 30 + "\n\n")

        for csv_file, field_patterns in pattern_results.items():
            f.write(f"File: {csv_file}\n")
            f.write("-" * 30 + "\n\n")

            for field, pattern_info in field_patterns.items():
                f.write(f"  Field: {field}\n")
                if isinstance(pattern_info, dict) and "patterns" in pattern_info:
                    f.write(f"    Min length: {pattern_info['min_length']}\n")
                    f.write(f"    Max length: {pattern_info['max_length']}\n")
                    f.write("    Example values:\n")
                    for ex in pattern_info["example_values"]:
                        f.write(f"      - '{ex}'\n")
                    f.write("    Patterns:\n")
                    for pattern, status in pattern_info["patterns"].items():
                        f.write(f"      - {pattern}: {status}\n")
                else:
                    f.write(f"    {pattern_info}\n")
                f.write("\n")

        # Then, the unique values analysis
        f.write("Field Value Analysis\n")
        f.write("=" * 30 + "\n\n")

        for csv_file, field_values in analysis_results.items():
            f.write(f"File: {csv_file}\n")
            f.write("-" * 30 + "\n\n")

            for field, values in field_values.items():
                f.write(f"  Field: {field}\n")
                for value, count in values:
                    f.write(f"    - '{value}' ({count} occurrences)\n")
                f.write("\n")

            f.write("\n")


def generate_html_report(
    analysis_results,
    sample_results,
    pattern_results,
    species_analysis,
    measurement_analysis,
    relationship_analysis,
    data_types_results,
    row_counts,
    column_lists,
    output_file,
):
    """Generate an HTML report from the analysis results."""
    html = """
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Urban Tree Observatory Data Exploration Report</title>
        <style>
            body {
                font-family: Arial, sans-serif;
                line-height: 1.6;
                margin: 0;
                padding: 20px;
                color: #333;
            }
            h1 {
                color: #2c3e50;
                border-bottom: 2px solid #3498db;
                padding-bottom: 10px;
            }
            h2 {
                color: #2980b9;
                margin-top: 30px;
            }
            h3 {
                color: #16a085;
            }
            .file-section {
                margin-bottom: 40px;
                padding: 20px;
                background-color: #f9f9f9;
                border-radius: 5px;
                box-shadow: 0 2px 5px rgba(0,0,0,0.1);
            }
            .field-section {
                margin-bottom: 20px;
                padding: 15px;
                background-color: #fff;
                border-radius: 5px;
                box-shadow: 0 1px 3px rgba(0,0,0,0.1);
            }
            table {
                width: 100%;
                border-collapse: collapse;
                margin: 10px 0;
            }
            th, td {
                padding: 8px;
                text-align: left;
                border-bottom: 1px solid #ddd;
            }
            th {
                background-color: #f2f2f2;
            }
            tr:hover {
                background-color: #f5f5f5;
            }
            .value-count {
                color: #7f8c8d;
                font-size: 0.9em;
            }
            .data-type {
                display: inline-block;
                padding: 2px 8px;
                border-radius: 3px;
                font-size: 0.8em;
                margin-left: 10px;
            }
            .type-text {
                background-color: #e74c3c;
                color: white;
            }
            .type-numeric {
                background-color: #3498db;
                color: white;
            }
            .type-date {
                background-color: #2ecc71;
                color: white;
            }
            .summary {
                margin-bottom: 30px;
                padding: 15px;
                background-color: #e8f4f8;
                border-radius: 5px;
            }
            .columns-section {
                margin-bottom: 20px;
            }
            .columns-table {
                max-width: 800px;
            }
            .tag {
                display: inline-block;
                padding: 2px 6px;
                margin: 2px;
                border-radius: 3px;
                background-color: #f39c12;
                color: white;
                font-size: 0.8em;
            }
            .nav-tabs {
                display: flex;
                margin-bottom: 20px;
                border-bottom: 1px solid #ddd;
                padding-left: 0;
                list-style: none;
            }
            .nav-tabs li {
                margin-bottom: -1px;
            }
            .nav-tabs a {
                display: block;
                padding: 10px 15px;
                margin-right: 2px;
                text-decoration: none;
                color: #555;
                border: 1px solid transparent;
                border-radius: 4px 4px 0 0;
            }
            .nav-tabs a:hover {
                border-color: #eee #eee #ddd;
                background-color: #f5f5f5;
            }
            .nav-tabs .active a {
                color: #555;
                background-color: #fff;
                border: 1px solid #ddd;
                border-bottom-color: transparent;
            }
            pre {
                background-color: #f8f9fa;
                border: 1px solid #eaecef;
                border-radius: 3px;
                padding: 10px;
                overflow: auto;
                font-family: monospace;
            }
            .pattern-all {
                color: #27ae60;
            }
            .pattern-some {
                color: #e67e22;
            }
            .pattern-none {
                color: #7f8c8d;
            }
        </style>
        <script>
            function showTab(tabId) {
                // Hide all tabs
                const tabs = document.querySelectorAll('.tab-content');
                tabs.forEach(tab => tab.style.display = 'none');

                // Remove active class from all tab links
                const tabLinks = document.querySelectorAll('.nav-tabs a');
                tabLinks.forEach(link => link.parentElement.classList.remove('active'));

                // Show the selected tab
                document.getElementById(tabId).style.display = 'block';

                // Add active class to selected tab link
                document.querySelector(`[href="#${tabId}"]`).parentElement.classList.add('active');

                // Save active tab to localStorage
                localStorage.setItem('activeTab', tabId);

                return false;
            }

            window.onload = function() {
                // Restore active tab from localStorage or default to first tab
                const activeTab = localStorage.getItem('activeTab') || 'summary-tab';
                showTab(activeTab);
            }
        </script>
    </head>
    <body>
        <h1>Urban Tree Observatory Data Exploration Report</h1>

        <ul class="nav-tabs">
            <li><a href="#summary-tab" onclick="return showTab('summary-tab')">Summary</a></li>
            <li><a href="#relationships-tab" onclick="return showTab('relationships-tab')">Relationships</a></li>
            <li><a href="#species-tab" onclick="return showTab('species-tab')">Species Analysis</a></li>
            <li><a href="#measurements-tab" onclick="return showTab('measurements-tab')">Measurements</a></li>
            <li><a href="#columns-tab" onclick="return showTab('columns-tab')">Columns</a></li>
            <li><a href="#patterns-tab" onclick="return showTab('patterns-tab')">Patterns</a></li>
            <li><a href="#samples-tab" onclick="return showTab('samples-tab')">Samples</a></li>
            <li><a href="#values-tab" onclick="return showTab('values-tab')">Field Values</a></li>
        </ul>

        <div id="summary-tab" class="tab-content summary">
            <h2>Dataset Summary</h2>
            <table>
                <tr><th>CSV File</th><th>Row Count</th><th>Column Count</th></tr>
"""

    # Add summary information
    for csv_file, count in row_counts.items():
        column_count = len(column_lists.get(csv_file, []))
        html += f"<tr><td>{csv_file}</td><td>{count}</td><td>{column_count}</td></tr>"

    html += """
            </table>

            <h3>Key Findings</h3>
            <ul>
                <li>Species data in taxonomy CSV appears to include genus in the 'specie' field</li>
                <li>Relationship codes between tables need mapping</li>
                <li>Measurement units need to be inferred from field names</li>
                <li>Various Spanish-language values need mapping to English TextChoices</li>
            </ul>
        </div>

        <div id="relationships-tab" class="tab-content">
            <h2>Relationship Analysis</h2>
    """

    # Add relationship analysis
    for rel_name, rel_info in relationship_analysis.items():
        html += f'<div class="file-section"><h3>{rel_name}</h3>'
        html += "<table>"

        for key, value in rel_info.items():
            if key == "examples":
                html += '<tr><td colspan="2"><h4>Mapping Examples:</h4></td></tr>'
                for ex in value:
                    html += f"<tr><td>{ex[0]}</td><td>{ex[1]}</td></tr>"
            else:
                html += f"<tr><td>{key}</td><td>{value}</td></tr>"

        html += "</table></div>"

    html += """
        </div>

        <div id="species-tab" class="tab-content">
            <h2>Species Name Analysis</h2>
            <div class="file-section">
    """

    # Add species analysis
    html += "<table>"
    for key, value in species_analysis.items():
        if key == "species_without_genus_examples":
            html += (
                '<tr><td colspan="2"><h3>Species without genus examples:</h3></td></tr>'
            )
            for ex in value:
                html += f"<tr><td>Species: {ex['species_name']}</td><td>Genus: {ex['genus']}</td></tr>"
        else:
            html += f"<tr><td>{key}</td><td>{value}</td></tr>"
    html += "</table>"

    html += """
            </div>
        </div>

        <div id="measurements-tab" class="tab-content">
            <h2>Measurement Analysis</h2>
    """

    # Add measurement analysis
    for name, info in measurement_analysis.items():
        html += f'<div class="field-section"><h3>{name}</h3>'
        html += "<table>"
        html += f"<tr><td>Count</td><td>{info['count']}</td></tr>"
        html += f"<tr><td>Inferred Unit</td><td>{info['inferred_unit']}</td></tr>"
        html += (
            f"<tr><td>Most Common Method</td><td>{info['most_common_method']}</td></tr>"
        )
        html += "</table>"

        html += "<h4>Methods:</h4><table>"
        html += "<tr><th>Method</th><th>Count</th></tr>"
        for method_info in info["methods"]:
            html += f"<tr><td>{method_info['method']}</td><td>{method_info['count']}</td></tr>"
        html += "</table></div>"

    html += """
        </div>

        <div id="columns-tab" class="tab-content columns-section">
            <h2>CSV File Columns</h2>
    """

    # Add columns section
    for csv_file, columns in column_lists.items():
        html += '<div class="file-section">'
        html += f"<h3>File: {csv_file} ({len(columns)} columns)</h3>"

        html += '<table class="columns-table">'
        html += "<tr><th>#</th><th>Column Name</th><th>Data Type</th><th>Field Type</th></tr>"

        for i, column in enumerate(columns):
            # Determine data type
            data_type = data_types_results.get(csv_file, {}).get(column, "unknown")
            type_class = f"type-{data_type}"

            # Determine field type
            field_type = "Regular Field"
            if column in TEXT_CHOICE_FIELDS.get(csv_file, []):
                field_type = '<span class="tag">TextChoice</span>'
            elif column in ADDITIONAL_FIELDS.get(csv_file, []):
                field_type = '<span class="tag">Analyzed</span>'
            elif column in SAMPLE_FIELDS.get(csv_file, []):
                field_type = '<span class="tag">Sampled</span>'
            elif column in PATTERN_FIELDS.get(csv_file, []):
                field_type = '<span class="tag">Pattern</span>'

            html += f'<tr><td>{i + 1}</td><td>{column}</td><td><span class="data-type {type_class}">{data_type}</span></td><td>{field_type}</td></tr>'

        html += "</table>"
        html += "</div>"

    html += """
        </div>

        <div id="patterns-tab" class="tab-content">
            <h2>Pattern Analysis</h2>
    """

    # Add pattern analysis
    for csv_file, field_patterns in pattern_results.items():
        html += '<div class="file-section">'
        html += f"<h3>File: {csv_file}</h3>"

        for field, pattern_info in field_patterns.items():
            html += '<div class="field-section">'
            html += f"<h4>Field: {field}</h4>"

            if isinstance(pattern_info, dict) and "patterns" in pattern_info:
                html += f"<p>Min length: {pattern_info['min_length']} | Max length: {pattern_info['max_length']}</p>"

                html += "<h5>Example values:</h5>"
                html += "<ul>"
                for ex in pattern_info["example_values"]:
                    html += f"<li><code>{ex}</code></li>"
                html += "</ul>"

                html += "<h5>Detected Patterns:</h5>"
                html += "<table>"
                html += "<tr><th>Pattern</th><th>Status</th></tr>"
                for pattern, status in pattern_info["patterns"].items():
                    status_class = (
                        f"pattern-{status}" if status in ["all", "some"] else ""
                    )
                    html += f'<tr><td>{pattern}</td><td class="{status_class}">{status}</td></tr>'
                html += "</table>"
            else:
                html += f"<p>{pattern_info}</p>"

            html += "</div>"

        html += "</div>"

    html += """
        </div>

        <div id="samples-tab" class="tab-content">
            <h2>Sample Values</h2>
    """

    # Add sample values
    for csv_file, field_samples in sample_results.items():
        html += '<div class="file-section">'
        html += f"<h3>File: {csv_file}</h3>"

        for field, sample_info in field_samples.items():
            html += '<div class="field-section">'
            html += f"<h4>Field: {field}</h4>"
            html += f"<p>Total unique values: {sample_info['total_unique']} | Total values: {sample_info['total_values']}</p>"

            if "all_samples" in sample_info:
                html += "<h5>All Samples:</h5>"
                html += "<ul>"
                for sample in sample_info["all_samples"]:
                    html += f"<li><code>{sample}</code></li>"
                html += "</ul>"
            else:
                html += '<div style="display: flex; gap: 20px;">'

                html += '<div style="flex: 1;">'
                html += "<h5>First Samples:</h5>"
                html += "<ul>"
                for sample in sample_info["first_samples"]:
                    html += f"<li><code>{sample}</code></li>"
                html += "</ul>"
                html += "</div>"

                html += '<div style="flex: 1;">'
                html += "<h5>Last Samples:</h5>"
                html += "<ul>"
                for sample in sample_info["last_samples"]:
                    html += f"<li><code>{sample}</code></li>"
                html += "</ul>"
                html += "</div>"

                html += "</div>"

            html += "</div>"

        html += "</div>"

    html += """
        </div>

        <div id="values-tab" class="tab-content">
            <h2>Field Value Analysis</h2>
    """

    # Add values section
    for csv_file, field_values in analysis_results.items():
        html += '<div class="file-section">'
        html += f"<h3>File: {csv_file}</h3>"

        for field, values in field_values.items():
            data_type = data_types_results.get(csv_file, {}).get(field, "unknown")
            type_class = f"type-{data_type}"

            # Determine field type
            field_type = ""
            if field in TEXT_CHOICE_FIELDS.get(csv_file, []):
                field_type = ' <span class="tag">TextChoice</span>'

            html += '<div class="field-section">'
            html += f'<h4>Field: {field} <span class="data-type {type_class}">{data_type}</span>{field_type}</h4>'

            html += "<table>"
            html += "<tr><th>Value</th><th>Occurrences</th></tr>"

            for value, count in values:
                html += f"<tr><td>{value}</td><td>{count}</td></tr>"

            html += "</table>"
            html += "</div>"

        html += "</div>"

    html += """
        </div>
    </body>
    </html>
    """

    with open(output_file, "w", encoding="utf-8") as f:
        f.write(html)


def get_csv_columns(file_path):
    """Get the column names from a CSV file."""
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            reader = csv.reader(f)
            header = next(reader)
            return header
    except FileNotFoundError:
        print(f"File not found: {file_path}")
        return []
    except Exception as e:
        print(f"Error reading header from {file_path}: {e}")
        return []


def main():
    parser = argparse.ArgumentParser(
        description="Explore CSV data for the Urban Tree Observatory project."
    )
    parser.add_argument(
        "--data-dir", required=True, help="Directory containing CSV files"
    )
    parser.add_argument(
        "--output-dir", default="data", help="Directory for output reports"
    )
    args = parser.parse_args()

    # Ensure output directory exists
    os.makedirs(args.output_dir, exist_ok=True)

    analysis_results = {}
    sample_results = {}
    pattern_results = {}
    data_types_results = {}
    row_counts = {}
    column_lists = {}

    # Data to store for relationship analysis
    biodiversity_data = []
    measurements_data = []
    observations_data = []
    taxonomy_data = []

    # Process each CSV file
    for csv_file in TEXT_CHOICE_FIELDS.keys():
        file_path = os.path.join(args.data_dir, csv_file)
        print(f"Processing {file_path}...")

        # Get column names
        columns = get_csv_columns(file_path)
        column_lists[csv_file] = columns

        data = read_csv(file_path)
        row_counts[csv_file] = len(data)

        # Store data for relationship analysis
        if csv_file == "biodiversity.csv":
            biodiversity_data = data
        elif csv_file == "measurements.csv":
            measurements_data = data
        elif csv_file == "observations.csv":
            observations_data = data
        elif csv_file == "taxonomy.csv":
            taxonomy_data = data

        if data:
            # Get field data types for ALL columns
            all_columns_data_types = analyze_data_types(data, columns)
            data_types_results[csv_file] = all_columns_data_types

            # Analyze fields that map to TextChoices and additional fields
            choice_fields = TEXT_CHOICE_FIELDS[csv_file]
            additional_fields = ADDITIONAL_FIELDS[csv_file]
            all_analyzed_fields = choice_fields + additional_fields

            unique_values = extract_unique_values(data, all_analyzed_fields)
            analysis_results[csv_file] = unique_values

            # Sample fields
            if csv_file in SAMPLE_FIELDS:
                sample_fields = SAMPLE_FIELDS[csv_file]
                samples = sample_values(data, sample_fields)
                sample_results[csv_file] = samples

            # Pattern analysis
            if csv_file in PATTERN_FIELDS:
                pattern_fields = PATTERN_FIELDS[csv_file]
                patterns = analyze_patterns(data, pattern_fields)
                pattern_results[csv_file] = patterns

    # Perform relationship analysis
    relationship_analysis = analyze_relationships(
        biodiversity_data, measurements_data, observations_data
    )

    # Perform species analysis (if taxonomy data exists)
    species_analysis = analyze_species_names(taxonomy_data) if taxonomy_data else {}

    # Perform measurement analysis
    measurement_analysis = (
        analyze_measurement_units(measurements_data) if measurements_data else {}
    )

    # Generate reports
    text_report_path = os.path.join(
        args.output_dir, "reports", "csv_exploration_report.txt"
    )
    html_report_path = os.path.join(
        args.output_dir, "reports", "csv_exploration_report.html"
    )

    # Ensure report directory exists
    os.makedirs(os.path.dirname(text_report_path), exist_ok=True)

    generate_text_report(
        analysis_results,
        sample_results,
        pattern_results,
        species_analysis,
        measurement_analysis,
        relationship_analysis,
        column_lists,
        text_report_path,
    )

    generate_html_report(
        analysis_results,
        sample_results,
        pattern_results,
        species_analysis,
        measurement_analysis,
        relationship_analysis,
        data_types_results,
        row_counts,
        column_lists,
        html_report_path,
    )

    print("Reports generated at:")
    print(f"  - {text_report_path}")
    print(f"  - {html_report_path}")

    # Also create a JSON mapping template that can be used to update the mappings
    mapping_template = {}
    for csv_file, fields in TEXT_CHOICE_FIELDS.items():
        for field in fields:
            if csv_file in analysis_results and field in analysis_results[csv_file]:
                values = [value for value, _ in analysis_results[csv_file][field]]
                if values:
                    field_name = f"{csv_file.split('.')[0]}_{field}".upper()
                    mapping_template[field_name] = {value: "" for value in values}

    mapping_template_path = os.path.join(
        args.output_dir, "reports", "mapping_template.json"
    )
    with open(mapping_template_path, "w", encoding="utf-8") as f:
        json.dump(mapping_template, f, ensure_ascii=False, indent=2)

    print(f"  - {mapping_template_path}")


if __name__ == "__main__":
    main()
