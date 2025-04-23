"""
Import initial data from CSV files into the database.

This Django management command imports data for an Urban Tree Observatory including:
- Taxonomy (families, genera, species)
- Places and locations
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

Usage:
    python manage.py import_initial_data [options]

Options:
    --local-dir PATH        Path to directory containing the CSV files
    --taxonomy-url URL      URL for the taxonomy details CSV file
    --places-url URL        URL for the places CSV file
    --biodiversity-url URL  URL for the biodiversity records CSV file
    --measurements-url URL  URL for the measurements CSV file
    --observations-url URL  URL for the observations details CSV file
    --traits-url URL        URL for the functional groups traits CSV file

By default, the command fetches data from Hugging Face URLs.

Example:
    python manage.py import_initial_data  # Uses default Hugging Face URLs
    python manage.py import_initial_data --local-dir /path/to/data  # Uses local files
"""

from pathlib import Path

from tqdm import tqdm
import pandas as pd

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
from apps.places.models import Municipality, Place
from apps.biodiversity.models import BiodiversityRecord
from apps.reports.models import Measurement, Observation
from apps.climate.models import Station, Climate


class Command(BaseCommand):
    help = "Import CSV data into the database"

    def add_arguments(self, parser):
        """Add command line arguments for the management command."""

        parser.add_argument(
            "--taxonomy-url",
            default="https://huggingface.co/datasets/juanpac96/urban_tree_census_data/taxonomy.csv",
            help="URL for the taxonomy details CSV file",
        )
        parser.add_argument(
            "--places-url",
            default="https://huggingface.co/datasets/juanpac96/urban_tree_census_data/places.csv",
            help="URL for the places CSV file",
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
            "--local-dir",
            help="Local directory containing CSV files with the same names as Hugging Face URLs",
        )

    def parse_date(self, date_string):
        """Convert a date-time string from CSV to a date object for Django DateField.

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
            self.places_url = options["places_url"]
            self.biodiversity_url = options["biodiversity_url"]
            self.measurements_url = options["measurements_url"]
            self.observations_url = options["observations_url"]
            self.traits_url = options["traits_url"]
            self.climate_url = options["climate_url"]
            self.stdout.write(
                self.style.SUCCESS("Starting import from Hugging Face URLs")
            )

        # Check that required migrations have run
        self.check_required_data()

        # Validate that all required files exist
        self.validate_files()

        # Check that tables to be populated are empty
        self.check_empty_tables()

        try:
            with transaction.atomic():
                # Call import methods in order of dependencies
                self.import_taxonomy()
                self.import_places()
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
            required_files = [
                "taxonomy.csv",
                "places.csv",
                "biodiversity.csv",
                "measurements.csv",
                "observations.csv",
                "traits.csv",
                "climate.csv",
            ]

            for filename in required_files:
                file_path = self.data_dir / filename
                if not file_path.exists():
                    missing_files.append(str(file_path))
        else:
            # Check if all remote URLs are accessible
            urls = [
                ("taxonomy", self.taxonomy_url),
                ("places", self.places_url),
                ("biodiversity", self.biodiversity_url),
                ("measurements", self.measurements_url),
                ("observations", self.observations_url),
                ("traits", self.traits_url),
                ("climate", self.climate_url),
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

    def check_empty_tables(self):
        """Check that all tables to be populated are empty before import."""
        tables_to_check = [
            (Family, "Family"),
            (Genus, "Genus"),
            (Species, "Species"),
            (Place, "Place"),
            (FunctionalGroup, "FunctionalGroup"),
            (Trait, "Trait"),
            (TraitValue, "TraitValue"),
            (BiodiversityRecord, "BiodiversityRecord"),
            (Measurement, "Measurement"),
            (Observation, "Observation"),
            (Station, "Station"),
            (Climate, "Climate"),
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

    def import_taxonomy(self):
        self.stdout.write("Importing taxonomy data...")

        # Read taxonomy.csv
        if self.use_local:
            csv_path = self.data_dir / "taxonomy.csv"
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

    def import_places(self):
        self.stdout.write("Importing place data...")

        # Read places.csv
        if self.use_local:
            csv_path = self.data_dir / "places.csv"
        else:
            csv_path = self.places_url

        df = pd.read_csv(csv_path)

        # Validate headers
        required_columns = {"id_place", "site", "populated_center", "zone", "subzone"}
        if not required_columns.issubset(df.columns):
            missing = required_columns - set(df.columns)
            raise CommandError(f"Missing required columns in places.csv: {missing}")

        # Create places using the ibague reference we stored earlier
        places_batch = []
        for row in tqdm(
            df.itertuples(index=False), desc="Preparing places", total=len(df)
        ):
            place = Place(
                id=row.id_place,  # Primary key
                municipality=self.ibague,  # Using the stored reference
                site=row.site,
                populated_center=row.populated_center,
                zone=row.zone if pd.notna(row.zone) else None,
                subzone=row.subzone if pd.notna(row.subzone) else None,
            )
            places_batch.append(place)

        # Bulk create places
        places = Place.objects.bulk_create(places_batch, batch_size=100)

        # Create mapping for use in biodiversity records
        self.places_by_id = {place.id: place for place in places}

        self.stdout.write(
            self.style.SUCCESS(
                f"Imported {len(places)} places in Ibagué, Tolima, Colombia"
            )
        )

    def import_functional_groups(self):
        self.stdout.write("Importing functional groups and traits...")

        # Read traits.csv
        if self.use_local:
            csv_path = self.data_dir / "traits.csv"
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

        # Create functional groups
        fg_batch = []
        for row in tqdm(
            df[["pft_id"]].drop_duplicates().itertuples(index=False),
            desc="Creating functional groups",
        ):
            fg = FunctionalGroup(group_id=row.pft_id)
            fg_batch.append(fg)

        functional_groups = FunctionalGroup.objects.bulk_create(fg_batch)

        # Create mapping of pft_id to FunctionalGroup objects
        fg_map = {fg.group_id: fg for fg in functional_groups}

        # Create trait values
        trait_values = []
        for row in tqdm(
            df.itertuples(index=False), desc="Creating trait values", total=len(df)
        ):
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

        # Update species with functional group references
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
            csv_path = self.data_dir / "biodiversity.csv"
        else:
            csv_path = self.biodiversity_url

        df = pd.read_csv(csv_path)

        # Validate headers
        required_columns = {
            "code_record",
            "common_name",
            "taxonomy_id",
            "place_id",
            "longitude",
            "latitude",
            "elevation_m",
            "registered_by",
            "date_event",
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
                # Create a Point geometry for the location
                location = f"POINT({row.longitude} {row.latitude})"

                bio_record = BiodiversityRecord(
                    id=row.code_record,  # Primary key
                    common_name=row.common_name,
                    species=self.species_by_id[row.taxonomy_id],
                    place=self.places_by_id[row.place_id],
                    location=location,
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
        chunksize = 50000  # Adjust based on available memory

        if self.use_local:
            csv_path = self.data_dir / "measurements.csv"
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
            csv_path = self.data_dir / "observations.csv"
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
        chunksize = 50000  # Adjust based on available memory

        if self.use_local:
            csv_path = self.data_dir / "climate.csv"
        else:
            csv_path = self.climate_url

        # Read header to validate columns
        df_header = pd.read_csv(csv_path, nrows=1)

        # Validate headers
        required_columns = {
            "municipality_id",
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
                        municipality=self.ibague,
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

        # Check BiodiversityRecord.place_id
        bio_place_ids = set(
            BiodiversityRecord.objects.values_list("place_id", flat=True).distinct()
        )
        valid_place_ids = set(Place.objects.values_list("id", flat=True))
        invalid_place_ids = bio_place_ids - valid_place_ids
        self.stdout.write(
            f"Found {len(invalid_place_ids)} invalid place_id(s) in BiodiversityRecord."
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

    def reset_sequences(self):
        """Reset ID sequences after import for PostgreSQL."""

        models = [
            Family,
            Genus,
            Species,
            Place,
            FunctionalGroup,
            Trait,
            TraitValue,
            BiodiversityRecord,
            Measurement,
            Observation,
            Station,
            Climate,
        ]
        with connection.cursor() as cursor:
            for model in models:
                table = model._meta.db_table
                cursor.execute(
                    f"SELECT setval(pg_get_serial_sequence('{table}', 'id'), "
                    f"COALESCE((SELECT MAX(id) FROM {table}), 0) + 1, false)"
                )
        self.stdout.write(self.style.SUCCESS("Sequence IDs reset successfully"))
