"""
Import initial data from CSV files into the database.

This Django management command imports data for an Urban Tree Observatory including:
- Taxonomy (families, genera, species)
- Sites, geographical locations, and spatial data
- Functional groups and traits
- Biodiversity records
- Measurements and observations

Prerequisites:
1. Required migrations must be completed
2. Target tables must be empty (except for country, department, municipality)
3. Municipality of Ibagué (Tolima, Colombia) must exist in the database

Assumptions:
- All records are for the municipality of Ibagué, Tolima, Colombia.
- The CSV files are structured correctly and contain all necessary data.
- The JSON files contain valid GeoJSON data.

Usage:
    python manage.py import_initial_data [options]

Options:
    --local-dir PATH        Path to directory containing the CSV and JSON files
                              in subdirectories csv/ and json/

    --taxonomy-url URL      URL for the taxonomy details CSV file
    --sites-url URL         URL for the sites CSV file
    --biodiversity-url URL  URL for the biodiversity records CSV file
    --measurements-url URL  URL for the measurements CSV file
    --observations-url URL  URL for the observations details CSV file
    --traits-url URL        URL for the functional groups traits CSV file
    --climate-url URL       URL for the climate data CSV file
    --localities-url URL    URL for the localities JSON file
    --hoods-url URL         URL for the neighborhoods JSON file

Settings:
    IMPORT_MEASUREMENTS_CHUNK_SIZE
        Number of rows to process at a time when importing measurements.
        Default: 50000. Adjust based on available memory.

    IMPORT_CLIMATE_CHUNK_SIZE
        Number of rows to process at a time when importing climate data.
        Default: 50000. Adjust based on available memory.

    These can be set as environment variables, e.g.:
        export IMPORT_MEASUREMENTS_CHUNK_SIZE=25000
        export IMPORT_CLIMATE_CHUNK_SIZE=10000

By default, the command fetches data from Hugging Face URLs.

Example:
    python manage.py import_initial_data  # Uses default Hugging Face URLs
    python manage.py import_initial_data --local-dir /path/to/data  # Uses local files
"""

import json
from pathlib import Path

from tqdm import tqdm
import pandas as pd

from django.conf import settings
from django.contrib.gis.geos import GEOSGeometry, MultiPolygon, Point
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction, connection

from apps.taxonomy.models import (
    Family,
    Genus,
    Species,
    FunctionalGroup,
    Trait,
    TraitValue,
)
from apps.places.models import Locality, Municipality, Neighborhood, Site
from apps.biodiversity.models import BiodiversityRecord
from apps.reports.models import Measurement, Observation
from apps.climate.models import Station, Climate


class Command(BaseCommand):
    help = "Import CSV and JSON data into the database"

    def add_arguments(self, parser):
        """Add command line arguments for the management command."""

        parser.add_argument(
            "--taxonomy-url",
            default="https://huggingface.co/datasets/juanpac96/urban_tree_census_data/taxonomy.csv",
            help="URL for the taxonomy details CSV file",
        )
        parser.add_argument(
            "--sites-url",
            default="https://huggingface.co/datasets/juanpac96/urban_tree_census_data/sites.csv",
            help="URL for the sites CSV file",
        )
        parser.add_argument(
            "--biodiversity-url",
            default="https://huggingface.co/datasets/juanpac96/urban_tree_census_data/biodiversity.csv",
            help="URL for the biodiversity records CSV file",
        )
        parser.add_argument(
            "--measurements-url",
            default="https://huggingface.co/datasets/juanpac96/urban_tree_census_data/measurements.csv",
            help="URL for the measurements CSV file",
        )
        parser.add_argument(
            "--observations-url",
            default="https://huggingface.co/datasets/juanpac96/urban_tree_census_data/observations.csv",
            help="URL for the observations details CSV file",
        )
        parser.add_argument(
            "--traits-url",
            default="https://huggingface.co/datasets/juanpac96/urban_tree_census_data/traits.csv",
            help="URL for the functional groups traits CSV file",
        )
        parser.add_argument(
            "--climate-url",
            default="https://huggingface.co/datasets/juanpac96/urban_tree_census_data/climate.csv",
            help="URL for the climate data CSV file",
        )
        parser.add_argument(
            "--localities-url",
            default="https://huggingface.co/datasets/juanpac96/urban_tree_census_data/localities.json",
            help="URL for the localities JSON file",
        )
        parser.add_argument(
            "--hoods-url",
            default="https://huggingface.co/datasets/juanpac96/urban_tree_census_data/hoods.json",
            help="URL for the neighborhoods JSON file",
        )
        parser.add_argument(
            "--local-dir",
            help="Local directory containing CSV and JSON files with the same names as Hugging Face URLs",
        )

    def parse_date(self, date_string):
        """Convert a date-time string to a date object for Django DateField.

        Args:
            date_string: String in format 'YYYY-MM-DD HH:MM:SS' or None/NaN

        Returns:
            date object or None if input is empty/NaN
        """
        if pd.isna(date_string) or not date_string:
            return None

        try:
            # Parse the datetime string and extract just the date part
            return pd.to_datetime(date_string).date()
        except ValueError:
            return None

    def handle(self, *args, **options):
        # Store the URLs or paths for later use
        self.use_local = options.get("local_dir") is not None

        if self.use_local:
            self.data_dir = Path(options["local_dir"])
            self.stdout.write(
                self.style.SUCCESS(
                    f"Starting import from local directory: {self.data_dir}"
                )
            )
        else:
            self.taxonomy_url = options["taxonomy_url"]
            self.sites_url = options["sites_url"]
            self.biodiversity_url = options["biodiversity_url"]
            self.measurements_url = options["measurements_url"]
            self.observations_url = options["observations_url"]
            self.traits_url = options["traits_url"]
            self.climate_url = options["climate_url"]
            self.localities_url = options["localities_url"]
            self.hoods_url = options["hoods_url"]
            self.stdout.write(self.style.SUCCESS("Starting import from URLs"))

        # Check that required migrations have run
        self.check_required_data()

        # Validate that all required files exist
        self.validate_files()

        # Check that tables to be populated are empty
        self.check_empty_tables()

        try:
            with transaction.atomic():
                # Call import methods in order of dependencies
                self.import_localities()
                self.import_neighborhoods()
                self.import_sites()
                self.import_taxonomy()
                self.import_functional_groups()
                self.import_biodiversity_records()
                self.import_measurements()
                self.import_observations()
                self.import_climate_data()

            self.stdout.write(self.style.SUCCESS("Import completed successfully"))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Import failed: {str(e)}"))
            raise

        # Check that all foreign keys map to valid primary keys
        self.check_foreign_key_integrity()

        # Reset sequences for all tables to avoid ID conflicts
        self.reset_sequences()

    def check_required_data(self):
        """Check that required initial data exists (from migrations)."""
        try:
            # Check that Ibagué exists (if so, Colombia and Tolima are assumed present)
            ibague = Municipality.objects.get(name="Ibagué")
            self.stdout.write(
                self.style.SUCCESS("Required initial location data confirmed")
            )

            # Store for later use
            self.ibague = ibague
        except Municipality.DoesNotExist:
            raise CommandError(
                "Municipality 'Ibagué' not found. Please ensure initial migrations have run."
            )

    def validate_files(self):
        """Validate that all required data files exist and can be accessed."""
        self.stdout.write("Validating data files...")

        missing_files = []

        if self.use_local:
            # Check if all required files exist in the local directory
            required_csv_files = [
                "taxonomy.csv",
                "sites.csv",
                "biodiversity.csv",
                "measurements.csv",
                "observations.csv",
                "traits.csv",
                "climate.csv",
            ]
            required_json_files = ["localities.json", "hoods.json"]

            self._check_required_files("csv", required_csv_files, missing_files)
            self._check_required_files("json", required_json_files, missing_files)

        else:
            # Check if all remote URLs are accessible
            urls = [
                ("taxonomy", self.taxonomy_url),
                ("sites", self.sites_url),
                ("biodiversity", self.biodiversity_url),
                ("measurements", self.measurements_url),
                ("observations", self.observations_url),
                ("traits", self.traits_url),
                ("climate", self.climate_url),
                ("localities", self.localities_url),
                ("hoods", self.hoods_url),
            ]

            # For remote URLs, we'll just check if pandas can open them
            # This is a lightweight check to avoid downloading entire files
            for name, url in urls:
                try:
                    # Just try to read the header
                    pd.read_csv(url, nrows=1)
                except Exception as e:
                    missing_files.append(f"{name} ({url}): {str(e)}")

        if missing_files:
            message = (
                f"The following files could not be accessed: {', '.join(missing_files)}. "
                "Please ensure all required data files are available before running the import."
            )
            raise CommandError(message)

        self.stdout.write(self.style.SUCCESS("All required data files are accessible"))

    def _check_required_files(self, subdir, filenames, missing_files):
        for filename in filenames:
            file_path = self.data_dir / subdir / filename
            if not file_path.exists():
                missing_files.append(str(file_path))

    def check_empty_tables(self):
        """Check that all tables to be populated are empty before import."""
        tables_to_check = [
            (Family, "Family"),
            (Genus, "Genus"),
            (Species, "Species"),
            (Site, "Site"),
            (FunctionalGroup, "FunctionalGroup"),
            (Trait, "Trait"),
            (TraitValue, "TraitValue"),
            (BiodiversityRecord, "BiodiversityRecord"),
            (Measurement, "Measurement"),
            (Observation, "Observation"),
            (Station, "Station"),
            (Climate, "Climate"),
            (Locality, "Locality"),
            (Neighborhood, "Neighborhood"),
        ]

        non_empty_tables = []

        for model, name in tables_to_check:
            if model.objects.exists():
                non_empty_tables.append(name)

        if non_empty_tables:
            message = (
                f"The following tables are not empty: {', '.join(non_empty_tables)}. "
                "Please empty these tables before running the import to avoid ID conflicts."
            )
            raise CommandError(message)

        self.stdout.write(
            self.style.SUCCESS("All required tables are empty - ready to import")
        )

    def import_localities(self):
        self.stdout.write("Importing locality data...")

        # Read localities.json
        if self.use_local:
            json_path = self.data_dir / "json" / "localities.json"
        else:
            json_path = self.localities_url

        with open(json_path, "r") as f:
            data = json.load(f)

        # Validate top-level structure
        if not isinstance(data, dict) or "localities" not in data:
            raise CommandError(
                "localities.json must be a JSON object with a 'localities' key."
            )

        localities_list = data["localities"]
        if not isinstance(localities_list, list):
            raise CommandError("'localities' key must contain a list.")

        # Validate required keys (for non-nullable model fields) in each locality
        required_keys = {"id", "name"}
        for idx, loc in enumerate(localities_list):
            missing = required_keys - set(loc)
            if missing:
                raise CommandError(
                    f"Missing required keys in localities.json at index {idx}: {missing}"
                )

        # Convert to DataFrame for further processing
        localities_data = pd.DataFrame(localities_list)

        # Create localities using municipality_id
        localities_batch = []
        for idx, row in enumerate(
            tqdm(localities_data.itertuples(index=False), desc="Preparing localities")
        ):
            # Get the boundary GeoJSON dict from the original list (not DataFrame, to avoid dtype issues)
            boundary_geojson = localities_list[idx].get("boundary")
            boundary_geom = None
            if boundary_geojson:
                try:
                    # Convert dict to string for GEOSGeometry
                    boundary_geom = self._parse_geometry(boundary_geojson)
                except Exception as e:
                    raise CommandError(
                        f"Invalid boundary geometry for locality id={row.id}: {e}"
                    )

            locality = Locality(
                id=row.id,  # Primary key
                name=row.name,
                municipality=self.ibague,  # Using the stored reference
                calculated_area_m2=row.calculated_area_m2
                if pd.notna(row.calculated_area_m2)
                else None,
                population_2019=row.population_2019
                if pd.notna(row.population_2019)
                else None,
                boundary=boundary_geom,
            )
            localities_batch.append(locality)

        # Bulk create localities
        created_localities = Locality.objects.bulk_create(localities_batch)

        # Create mapping for use in neighborhoods
        self.localities_by_id = {loc.id: loc for loc in created_localities}

        # Create the unknown locality if needed
        self._create_unknown_locality()

        self.stdout.write(
            self.style.SUCCESS(f"Imported {len(localities_batch)} localities")
        )

    def _create_unknown_locality(self):
        """Create the unknown locality with id=14 if it does not exist."""
        unknown_id = 14
        if Locality.objects.filter(id=unknown_id).exists():
            raise CommandError(
                "A locality with id=14 already exists. Cannot create the unknown locality."
            )
        unknown_locality = Locality.objects.create(
            id=unknown_id,
            name="Desconocida",
            municipality=self.ibague,
            boundary=None,
            calculated_area_m2=None,
            population_2019=None,
        )
        self.localities_by_id[unknown_id] = unknown_locality

    def import_neighborhoods(self):
        self.stdout.write("Importing neighborhood data...")

        # Read hoods.json
        if self.use_local:
            json_path = self.data_dir / "json" / "hoods.json"
        else:
            json_path = self.hoods_url

        with open(json_path, "r") as f:
            data = json.load(f)

        # Validate top-level structure
        if not isinstance(data, dict) or "hoods" not in data:
            raise CommandError("hoods.json must be a JSON object with a 'hoods' key.")

        neighborhoods_list = data["hoods"]
        if not isinstance(neighborhoods_list, list):
            raise CommandError("'hoods' key must contain a list.")

        # Validate required keys (for non-nullable model fields) in each neighborhood
        required_keys = {"id", "name", "locality_id"}
        for idx, hood in enumerate(neighborhoods_list):
            missing = required_keys - set(hood)
            if missing:
                raise CommandError(
                    f"Missing required keys in hoods.json at index {idx}: {missing}"
                )

        # Convert to DataFrame for further processing
        neighborhoods_data = pd.DataFrame(neighborhoods_list)

        # Create neighborhoods using locality_id
        neighborhoods_batch = []
        for idx, row in enumerate(
            tqdm(
                neighborhoods_data.itertuples(index=False),
                desc="Preparing neighborhoods",
            )
        ):
            # Get the boundary GeoJSON dict from the original list (not DataFrame, to avoid dtype issues)
            boundary_geojson = neighborhoods_list[idx].get("boundary")
            boundary_geom = None
            if boundary_geojson:
                try:
                    # Convert dict to string for GEOSGeometry
                    boundary_geom = self._parse_geometry(boundary_geojson)
                except Exception as e:
                    raise CommandError(
                        f"Invalid boundary geometry for neighborhood id={row.id}: {e}"
                    )

            neighborhood = Neighborhood(
                id=row.id,  # Primary key
                name=row.name,
                locality=self.localities_by_id[
                    row.locality_id
                ],  # Using the mapping from localities
                calculated_area_m2=row.calculated_area_m2
                if pd.notna(row.calculated_area_m2)
                else None,
                boundary=boundary_geom,
            )
            neighborhoods_batch.append(neighborhood)

        # Bulk create neighborhoods
        created_hoods = Neighborhood.objects.bulk_create(
            neighborhoods_batch, batch_size=100
        )

        # Create mapping for use in biodiversity records
        self.neighborhoods_by_id = {hood.id: hood for hood in created_hoods}

        # Create the unknown neighborhood if needed
        self._create_unknown_neighborhood()

        self.stdout.write(
            self.style.SUCCESS(f"Imported {len(neighborhoods_batch)} neighborhoods")
        )

    def _create_unknown_neighborhood(self):
        """Create the unknown neighborhood with id=688 if it does not exist."""
        unknown_id = 688
        if Neighborhood.objects.filter(id=unknown_id).exists():
            raise CommandError(
                "A neighborhood with id=688 already exists. Cannot create the unknown neighborhood."
            )
        unknown_neighborhood = Neighborhood.objects.create(
            id=unknown_id,
            name="Desconocido",
            locality=self.localities_by_id[14],  # Use the unknown locality
            calculated_area_m2=None,
            boundary=None,
        )
        self.neighborhoods_by_id[unknown_id] = unknown_neighborhood

    def _parse_geometry(self, geojson):
        """Parses GeoJSON dict into a GEOSGeometry MultiPolygon"""
        geom = GEOSGeometry(json.dumps(geojson), srid=4326)
        if geom.geom_type == "Polygon":
            geom = MultiPolygon(geom)
        elif geom.geom_type != "MultiPolygon":
            raise CommandError(f"Unsupported geometry type: {geom.geom_type}")
        return geom

    def import_sites(self):
        self.stdout.write("Importing site data...")

        # Read sites.csv
        if self.use_local:
            csv_path = self.data_dir / "csv" / "sites.csv"
        else:
            csv_path = self.sites_url

        df = pd.read_csv(csv_path)

        # Validate headers
        required_columns = {"id", "name", "zone", "subzone"}
        if not required_columns.issubset(df.columns):
            missing = required_columns - set(df.columns)
            raise CommandError(f"Missing required columns in sites.csv: {missing}")

        # Create sites
        sites_batch = []
        for row in tqdm(
            df.itertuples(index=False), desc="Preparing sites", total=len(df)
        ):
            site = Site(
                id=row.id,  # Primary key
                name=row.name,
                zone=row.zone if pd.notna(row.zone) else None,
                subzone=row.subzone if pd.notna(row.subzone) else None,
            )
            sites_batch.append(site)

        # Bulk create sites
        created_sites = Site.objects.bulk_create(sites_batch, batch_size=100)

        # Create mapping for use in biodiversity records
        self.sites_by_id = {site.id: site for site in created_sites}

        self.stdout.write(
            self.style.SUCCESS(
                f"Imported {len(sites_batch)} sites in Ibagué, Tolima, Colombia"
            )
        )

    def import_taxonomy(self):
        self.stdout.write("Importing taxonomy data...")

        # Read taxonomy.csv
        if self.use_local:
            csv_path = self.data_dir / "csv" / "taxonomy.csv"
        else:
            csv_path = self.taxonomy_url

        df = pd.read_csv(csv_path)

        # Validate headers
        required_columns = {
            "taxonomy_id",
            "family",
            "genus",
            "specie",
            "accept_scientific_name",
            "origin",
            "iucn_category",
            "lifeForm",
            "canopy_shape_code",
            "flower_color_code",
            "gbif_id",
            "identified_by",
            "date_of_identification",
        }
        if not required_columns.issubset(df.columns):
            missing = required_columns - set(df.columns)
            raise CommandError(f"Missing required columns in taxonomy.csv: {missing}")

        # Create families (track created ones to avoid duplicates)
        families = {}
        for family_name in tqdm(df["family"].unique(), desc="Importing families"):
            family, _ = Family.objects.get_or_create(name=family_name)
            families[family_name] = family

        # Create genera
        genera = {}
        for row in tqdm(
            df[["family", "genus"]].drop_duplicates().itertuples(index=False),
            desc="Importing genera",
        ):
            genus, _ = Genus.objects.get_or_create(
                name=row.genus, family=families[row.family]
            )
            genera[row.genus] = genus

        # Create species (all rows, as each represents a unique species)
        species_batch = []

        for row in tqdm(
            df.itertuples(index=False), desc="Preparing species", total=len(df)
        ):
            # Map the origin, iucn_status, etc from CSV to model choices
            # Note: We assume the CSV values match the model choices' values
            species = Species(
                id=row.taxonomy_id,  # Primary key
                genus=genera[row.genus],
                name=row.specie.replace(
                    row.genus + " ", ""
                ),  # Remove genus prefix if present
                accepted_scientific_name=row.accept_scientific_name,
                origin=row.origin,
                iucn_status=row.iucn_category,
                life_form=row.lifeForm,
                canopy_shape=row.canopy_shape_code,
                flower_color=row.flower_color_code,
                gbif_id=row.gbif_id if pd.notna(row.gbif_id) else None,
                identified_by=row.identified_by,
                date=self.parse_date(row.date_of_identification)
                if pd.notna(row.date_of_identification)
                else None,
                # functional_group will be set later
            )
            species_batch.append(species)

        # Bulk create species
        created_species = Species.objects.bulk_create(species_batch, batch_size=100)

        # Create mapping for use in biodiversity records
        self.species_by_id = {sp.id: sp for sp in created_species}

        self.stdout.write(
            self.style.SUCCESS(
                f"Imported {len(families)} families, {len(genera)} genera, {len(created_species)} species"
            )
        )

    def import_functional_groups(self):
        self.stdout.write("Importing functional groups and traits...")

        # Read traits.csv
        if self.use_local:
            csv_path = self.data_dir / "csv" / "traits.csv"
        else:
            csv_path = self.traits_url

        df = pd.read_csv(csv_path)

        # Validate headers
        required_columns = {
            "pft_id",
            "taxonomy_id",
            "carbon_sequestration_min",
            "carbon_sequestration_max",
            "shade_index_min",
            "shade_index_max",
            "canopy_diameter_min",
            "canopy_diameter_max",
            "height_max_min",
            "height_max_max",
        }
        if not required_columns.issubset(df.columns):
            missing = required_columns - set(df.columns)
            raise CommandError(f"Missing required columns in traits.csv: {missing}")

        # Create the four traits (if they don't exist already)
        traits = {
            "carbon": Trait.objects.get_or_create(
                type=Trait.TraitType.CARBON_SEQUESTRATION
            )[0],
            "shade": Trait.objects.get_or_create(type=Trait.TraitType.SHADE_IDX)[0],
            "canopy": Trait.objects.get_or_create(type=Trait.TraitType.CANOPY_DIAMETER)[
                0
            ],
            "height": Trait.objects.get_or_create(type=Trait.TraitType.HEIGHT_MAX)[0],
        }

        # Deduplicate by pft_id: keep only the first row for each group
        fg_rows = df.drop_duplicates(subset=["pft_id"]).copy()

        # Create functional groups
        fg_batch = []
        for row in tqdm(
            fg_rows.itertuples(index=False), desc="Creating functional groups"
        ):
            fg = FunctionalGroup(group_id=row.pft_id)
            fg_batch.append(fg)
        functional_groups = FunctionalGroup.objects.bulk_create(fg_batch)

        # Create mapping of pft_id to FunctionalGroup objects
        fg_map = {fg.group_id: fg for fg in functional_groups}

        # Create trait values (one set per group)
        trait_values = []
        for row in tqdm(fg_rows.itertuples(index=False), desc="Creating trait values"):
            # Carbon sequestration trait values
            trait_values.append(
                TraitValue(
                    trait=traits["carbon"],
                    functional_group=fg_map[row.pft_id],
                    min_value=row.carbon_sequestration_min
                    if pd.notna(row.carbon_sequestration_min)
                    else None,
                    max_value=row.carbon_sequestration_max
                    if pd.notna(row.carbon_sequestration_max)
                    else None,
                )
            )

            # Shade index trait values
            trait_values.append(
                TraitValue(
                    trait=traits["shade"],
                    functional_group=fg_map[row.pft_id],
                    min_value=row.shade_index_min
                    if pd.notna(row.shade_index_min)
                    else None,
                    max_value=row.shade_index_max
                    if pd.notna(row.shade_index_max)
                    else None,
                )
            )

            # Canopy diameter trait values
            trait_values.append(
                TraitValue(
                    trait=traits["canopy"],
                    functional_group=fg_map[row.pft_id],
                    min_value=row.canopy_diameter_min
                    if pd.notna(row.canopy_diameter_min)
                    else None,
                    max_value=row.canopy_diameter_max
                    if pd.notna(row.canopy_diameter_max)
                    else None,
                )
            )

            # Height max trait values
            trait_values.append(
                TraitValue(
                    trait=traits["height"],
                    functional_group=fg_map[row.pft_id],
                    min_value=row.height_max_min
                    if pd.notna(row.height_max_min)
                    else None,
                    max_value=row.height_max_max
                    if pd.notna(row.height_max_max)
                    else None,
                )
            )

        # Bulk create all trait values
        TraitValue.objects.bulk_create(trait_values, batch_size=500)

        # Update species with functional group references (all rows, not deduplicated)
        taxonomy_to_fg = {}
        for row in df.itertuples(index=False):
            taxonomy_to_fg[row.taxonomy_id] = fg_map[row.pft_id]

        # Batch update species with functional groups
        species_updates = []
        for taxonomy_id, fg in taxonomy_to_fg.items():
            if taxonomy_id in self.species_by_id:
                species = self.species_by_id[taxonomy_id]
                species.functional_group = fg
                species_updates.append(species)

        # Batch update species
        Species.objects.bulk_update(
            species_updates, ["functional_group"], batch_size=100
        )

        self.stdout.write(
            self.style.SUCCESS(
                f"Imported {len(functional_groups)} functional groups, {len(trait_values)} trait values"
            )
        )

    def import_biodiversity_records(self):
        self.stdout.write("Importing biodiversity records...")

        # Read biodiversity.csv
        if self.use_local:
            csv_path = self.data_dir / "csv" / "biodiversity.csv"
        else:
            csv_path = self.biodiversity_url

        df = pd.read_csv(csv_path)

        # Validate headers
        required_columns = {
            "code_record",
            "common_name",
            "longitude",
            "latitude",
            "elevation_m",
            "registered_by",
            "date_event",
            "site_id",
            "species_id",
            "hood_id",
        }
        if not required_columns.issubset(df.columns):
            missing = required_columns - set(df.columns)
            raise CommandError(
                f"Missing required columns in biodiversity.csv: {missing}"
            )

        # Create biodiversity records in batches to manage memory
        batch_size = 1000
        total_batches = (len(df) // batch_size) + (1 if len(df) % batch_size > 0 else 0)

        records_created = 0
        self.bio_records_by_id = {}  # To store mapping for later use with measurements/observations

        for batch_idx in tqdm(
            range(total_batches), desc="Importing biodiversity records"
        ):
            start_idx = batch_idx * batch_size
            end_idx = min((batch_idx + 1) * batch_size, len(df))
            batch_df = df.iloc[start_idx:end_idx]

            batch_records = []
            for row in batch_df.itertuples(index=False):
                bio_record = BiodiversityRecord(
                    id=row.code_record,  # Primary key
                    common_name=row.common_name,
                    species=self.species_by_id[row.species_id],
                    site=self.sites_by_id[row.site_id],
                    neighborhood=self.neighborhoods_by_id[row.hood_id],
                    location=Point(row.longitude, row.latitude, srid=4326),
                    elevation_m=row.elevation_m if pd.notna(row.elevation_m) else None,
                    recorded_by=row.registered_by,
                    date=self.parse_date(row.date_event)
                    if pd.notna(row.date_event)
                    else None,
                )
                batch_records.append(bio_record)

            # Bulk create the batch
            created_records = BiodiversityRecord.objects.bulk_create(batch_records)
            records_created += len(created_records)

            # Update mapping
            for record in created_records:
                self.bio_records_by_id[record.id] = record

        self.stdout.write(
            self.style.SUCCESS(f"Imported {records_created} biodiversity records")
        )

    def import_measurements(self):
        self.stdout.write("Importing measurements...")

        # Read measurements.csv
        # We'll process this in chunks due to the large number of rows
        chunksize = settings.IMPORT_MEASUREMENTS_CHUNK_SIZE

        if self.use_local:
            csv_path = self.data_dir / "csv" / "measurements.csv"
        else:
            csv_path = self.measurements_url

        # Count total rows for tqdm
        total_rows = sum(1 for _ in open(csv_path)) - 1  # subtract header

        reader = pd.read_csv(csv_path, chunksize=chunksize)

        total_measurements = 0

        with tqdm(total=total_rows, desc="Importing measurements") as pbar:
            for chunk in reader:
                # Validate headers in the first chunk
                required_columns = {
                    "record_code",
                    "measurement_name",
                    "measurement_value",
                    "measurement_unit",
                    "measurement_method",
                    "measurement_date_event",
                }
                if not required_columns.issubset(chunk.columns):
                    missing = required_columns - set(chunk.columns)
                    raise CommandError(
                        f"Missing required columns in measurements.csv: {missing}"
                    )

                batch_measurements = []

                for row in chunk.itertuples(index=False):
                    measurement = Measurement(
                        biodiversity_record_id=row.record_code,  # Foreign key
                        attribute=row.measurement_name,
                        value=row.measurement_value
                        if pd.notna(row.measurement_value)
                        else None,
                        unit=row.measurement_unit,
                        method=row.measurement_method,
                        date=self.parse_date(row.measurement_date_event)
                        if pd.notna(row.measurement_date_event)
                        else None,
                    )
                    batch_measurements.append(measurement)

                # Bulk create the measurements in this chunk
                created = Measurement.objects.bulk_create(
                    batch_measurements, batch_size=5000
                )
                total_measurements += len(created)
                pbar.update(len(chunk))

        self.stdout.write(
            self.style.SUCCESS(f"Imported {total_measurements} measurements")
        )

    def import_observations(self):
        self.stdout.write("Importing observations...")

        # Read observations.csv with specified data types to handle mixed types warning
        if self.use_local:
            csv_path = self.data_dir / "csv" / "observations.csv"
        else:
            csv_path = self.observations_url

        # Specify dtype for columns that may have mixed types
        dtype = {
            "rd": str,
            "dm": str,
            "bbs": str,
            "ab": str,
            "pi": str,
        }

        df = pd.read_csv(csv_path, dtype=dtype)

        # Validate headers
        required_columns = {
            "record_code",
            "reproductive_condition",
            "phytosanitary_status",
            "physical_condition",
            "foliage_density",
            "aesthetic_value",
            "growth_phase",
            "field_notes",
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
            "photo_url",
            "accompanying_collectors",
        }
        if not required_columns.issubset(df.columns):
            missing = required_columns - set(df.columns)
            raise CommandError(
                f"Missing required columns in observations.csv: {missing}"
            )

        # Process in batches
        batch_size = 1000
        total_batches = (len(df) // batch_size) + (1 if len(df) % batch_size > 0 else 0)

        observations_created = 0

        for batch_idx in tqdm(range(total_batches), desc="Importing observations"):
            start_idx = batch_idx * batch_size
            end_idx = min((batch_idx + 1) * batch_size, len(df))
            batch_df = df.iloc[start_idx:end_idx]

            batch_observations = []
            for row in batch_df.itertuples(index=False):
                observation = Observation(
                    biodiversity_record_id=row.record_code,  # Foreign key
                    reproductive_condition=row.reproductive_condition,
                    phytosanitary_status=row.phytosanitary_status,
                    physical_condition=row.physical_condition,
                    foliage_density=row.foliage_density,
                    aesthetic_value=row.aesthetic_value,
                    growth_phase=row.growth_phase,
                    field_notes=row.field_notes if pd.notna(row.field_notes) else "",
                    standing=row.standing,
                    rd=row.rd,
                    dm=row.dm,
                    bbs=row.bbs,
                    ab=row.ab,
                    ed=row.ed,
                    pi=row.pi,
                    ph=row.ph,
                    pa=row.pa,
                    hc=row.hc,
                    hcf=row.hcf,
                    pd=row.pd,
                    pe=row.pe,
                    pp=row.pp,
                    po=row.po,
                    cre=row.cre,
                    crh=row.crh,
                    cra=row.cra,
                    coa=row.coa,
                    ce=row.ce,
                    civ=row.civ,
                    crt=row.crt,
                    crg=row.crg,
                    cap=row.cap,
                    r_vol=row.r_vol,
                    r_cr=row.r_cr,
                    r_ce=row.r_ce,
                    recorded_by="Cortolima",  # Default from model
                    photo_url=row.photo_url if pd.notna(row.photo_url) else "",
                    accompanying_collectors=row.accompanying_collectors
                    if pd.notna(row.accompanying_collectors)
                    else "",
                )
                batch_observations.append(observation)

            # Bulk create the observations in this batch
            created = Observation.objects.bulk_create(
                batch_observations, batch_size=1000
            )
            observations_created += len(created)

        self.stdout.write(
            self.style.SUCCESS(f"Imported {observations_created} observations")
        )

    def import_climate_data(self):
        self.stdout.write("Importing climate data...")

        # Read climate.csv
        # We'll process this in chunks due to the large number of rows
        chunksize = settings.IMPORT_CLIMATE_CHUNK_SIZE

        if self.use_local:
            csv_path = self.data_dir / "csv" / "climate.csv"
        else:
            csv_path = self.climate_url

        # Read header to validate columns
        df_header = pd.read_csv(csv_path, nrows=1)

        # Validate headers
        required_columns = {
            "stationcode",
            "stationname",
            "datetime",
            "latitude",
            "longitude",
            "sensordescription",
            "measureunit",
            "value",
        }

        file_columns = set(df_header.columns)
        if not required_columns.issubset(file_columns):
            missing = required_columns - file_columns
            raise CommandError(f"Missing required columns in climate.csv: {missing}")

        # Import stations first (only a few unique stations)
        station_df = pd.read_csv(
            csv_path,
            usecols=["stationcode", "stationname", "latitude", "longitude"],
        )
        unique_stations = station_df.drop_duplicates(subset=["stationcode"]).copy()

        # Create stations
        stations_batch = []
        station_map = {}  # To map station codes to Station objects

        for row in tqdm(
            unique_stations.itertuples(index=False),
            desc="Creating climate stations",
            total=len(unique_stations),
        ):
            # Create a Point geometry for the location
            location = f"POINT({row.longitude} {row.latitude})"

            station = Station(
                code=row.stationcode,
                name=row.stationname,
                location=location,
                municipality=self.ibague,
            )
            stations_batch.append(station)

        # Bulk create the stations
        created_stations = Station.objects.bulk_create(stations_batch)
        for station in created_stations:
            station_map[station.code] = station

        self.stdout.write(
            self.style.SUCCESS(f"Imported {len(created_stations)} weather stations")
        )

        # Now import climate data in chunks
        # Count total rows for tqdm
        total_rows = sum(1 for _ in open(csv_path)) - 1  # subtract header

        reader = pd.read_csv(csv_path, chunksize=chunksize)

        total_records = 0

        with tqdm(total=total_rows, desc="Importing climate data") as pbar:
            for chunk in reader:
                batch_climate = []

                for row in chunk.itertuples(index=False):
                    station = station_map.get(row.stationcode)

                    climate_record = Climate(
                        station=station,
                        date=self.parse_date(row.datetime),
                        sensor=row.sensordescription,
                        value=row.value,
                        measure_unit=row.measureunit,
                    )
                    batch_climate.append(climate_record)

                # Bulk create the climate records in this chunk
                created = Climate.objects.bulk_create(batch_climate, batch_size=5000)
                total_records += len(created)
                pbar.update(len(chunk))

        self.stdout.write(
            self.style.SUCCESS(f"Imported {total_records} climate data records")
        )

    def check_foreign_key_integrity(self):
        """Check that all foreign keys map to valid primary keys."""

        self.stdout.write("Checking foreign key integrity...")

        # Check Neighborhood.locality_id
        hood_ids = set(
            Neighborhood.objects.values_list("locality_id", flat=True).distinct()
        )
        valid_locality_ids = set(Locality.objects.values_list("id", flat=True))
        invalid_locality_ids = hood_ids - valid_locality_ids
        self.stdout.write(
            f"Found {len(invalid_locality_ids)} invalid locality_id(s) in Neighborhood."
        )

        # Check BiodiversityRecord.site_id
        bio_site_ids = set(
            BiodiversityRecord.objects.values_list("site_id", flat=True).distinct()
        )
        valid_site_ids = set(Site.objects.values_list("id", flat=True))
        invalid_site_ids = bio_site_ids - valid_site_ids
        self.stdout.write(
            f"Found {len(invalid_site_ids)} invalid site_id(s) in BiodiversityRecord."
        )

        # Check BiodiversityRecord.species_id
        bio_species_ids = set(
            BiodiversityRecord.objects.values_list("species_id", flat=True).distinct()
        )
        valid_species_ids = set(Species.objects.values_list("id", flat=True))
        invalid_species_ids = bio_species_ids - valid_species_ids
        self.stdout.write(
            f"Found {len(invalid_species_ids)} invalid species_id(s) in BiodiversityRecord."
        )

        # Check BiodiversityRecord.neighborhood_id
        bio_hood_ids = set(
            BiodiversityRecord.objects.values_list(
                "neighborhood_id", flat=True
            ).distinct()
        )
        valid_hood_ids = set(Neighborhood.objects.values_list("id", flat=True))
        invalid_hood_ids = bio_hood_ids - valid_hood_ids
        self.stdout.write(
            f"Found {len(invalid_hood_ids)} invalid neighborhood_id(s) in BiodiversityRecord."
        )

        # Check Observation.biodiversity_record_id
        observation_ids = set(
            Observation.objects.values_list(
                "biodiversity_record_id", flat=True
            ).distinct()
        )
        valid_bio_ids = set(BiodiversityRecord.objects.values_list("id", flat=True))
        invalid_obs_ids = observation_ids - valid_bio_ids
        self.stdout.write(
            f"Found {len(invalid_obs_ids)} invalid biodiversity_record_id(s) in Observation."
        )

        # Check Measurement.biodiversity_record_id
        measurement_ids = set(
            Measurement.objects.values_list(
                "biodiversity_record_id", flat=True
            ).distinct()
        )
        invalid_meas_ids = measurement_ids - valid_bio_ids
        self.stdout.write(
            f"Found {len(invalid_meas_ids)} invalid biodiversity_record_id(s) in Measurement."
        )

    def reset_sequences(self):
        """Reset ID sequences after import for PostgreSQL."""

        models = [
            Family,
            Genus,
            Species,
            Site,
            FunctionalGroup,
            Trait,
            TraitValue,
            BiodiversityRecord,
            Measurement,
            Observation,
            Station,
            Climate,
            Locality,
            Neighborhood,
        ]
        with connection.cursor() as cursor:
            for model in models:
                table = model._meta.db_table
                cursor.execute(
                    f"SELECT setval(pg_get_serial_sequence('{table}', 'id'), "
                    f"COALESCE((SELECT MAX(id) FROM {table}), 0) + 1, false)"
                )
        self.stdout.write(self.style.SUCCESS("Sequence IDs reset successfully"))
