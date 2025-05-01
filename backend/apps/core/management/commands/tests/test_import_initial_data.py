"""
Tests for the import_initial_data management command.

These tests verify the critical functionality of the data import command to prevent regression
failures. The command imports data from CSV and JSON files into the database for the Urban Tree
Observatory.
"""

import json
import tempfile
from io import StringIO
from pathlib import Path
from unittest import mock

import pandas as pd
import pytest
from django.core.management import call_command
from django.core.management.base import CommandError

from apps.biodiversity.models import BiodiversityRecord
from apps.climate.models import Climate, Station
from apps.core.management.commands.import_initial_data import Command
from apps.places.models import (
    Locality,
    Municipality,
    Neighborhood,
    Site,
)
from apps.reports.models import Measurement, Observation
from apps.taxonomy.models import (
    Family,
    FunctionalGroup,
    Genus,
    Species,
    Trait,
    TraitValue,
)


class TestImportInitialDataCommand:
    """Tests for the import_initial_data management command."""

    @pytest.fixture
    def ibague(self, department):
        """Create Ibagué municipality as required by the command."""
        return Municipality.objects.create(name="Ibagué", department=department)

    @pytest.fixture
    def setup_empty_tables(self):
        """Ensure all tables to be populated are empty."""
        Family.objects.all().delete()
        Genus.objects.all().delete()
        Species.objects.all().delete()
        Site.objects.all().delete()
        FunctionalGroup.objects.all().delete()
        Trait.objects.all().delete()
        TraitValue.objects.all().delete()
        BiodiversityRecord.objects.all().delete()
        Measurement.objects.all().delete()
        Observation.objects.all().delete()
        Station.objects.all().delete()
        Climate.objects.all().delete()
        Locality.objects.all().delete()
        Neighborhood.objects.all().delete()

    @pytest.fixture
    def mock_data_dir(self):
        """Create a temporary directory with mock CSV and JSON files."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create directory structure
            csv_dir = Path(temp_dir) / "csv"
            json_dir = Path(temp_dir) / "json"
            csv_dir.mkdir()
            json_dir.mkdir()

            # Create mock localities data
            localities_data = {
                "localities": [
                    {
                        "id": 1,
                        "name": "Test Locality",
                        "calculated_area_m2": 100000,
                        "population_2019": 10000,
                        "boundary": {
                            "type": "MultiPolygon",
                            "coordinates": [[[[0, 0], [0, 1], [1, 1], [1, 0], [0, 0]]]],
                        },
                    }
                ]
            }
            with open(json_dir / "localities.json", "w") as f:
                json.dump(localities_data, f)

            # Create mock neighborhoods data
            neighborhoods_data = {
                "hoods": [
                    {
                        "id": 1,
                        "name": "Test Neighborhood",
                        "locality_id": 1,
                        "calculated_area_m2": 10000,
                        "boundary": {
                            "type": "MultiPolygon",
                            "coordinates": [
                                [[[0, 0], [0, 0.5], [0.5, 0.5], [0.5, 0], [0, 0]]]
                            ],
                        },
                    }
                ]
            }
            with open(json_dir / "hoods.json", "w") as f:
                json.dump(neighborhoods_data, f)

            # Create mock sites CSV
            sites_df = pd.DataFrame(
                {"id": [1], "name": ["Test Site"], "zone": [1], "subzone": [2]}
            )
            sites_df.to_csv(csv_dir / "sites.csv", index=False)

            # Create mock taxonomy CSV
            taxonomy_df = pd.DataFrame(
                {
                    "taxonomy_id": [1],
                    "family": ["Test Family"],
                    "genus": ["Test Genus"],
                    "specie": ["Test Genus species"],
                    "accept_scientific_name": ["Test Genus species"],
                    "origin": ["NT"],  # Native (2-char code)
                    "iucn_category": ["LC"],  # Least Concern (2-char code)
                    "lifeForm": ["TR"],  # Tree (2-char code)
                    "canopy_shape_code": ["SP"],  # Spreading (2-char code)
                    "flower_color_code": ["WH"],  # White (2-char code)
                    "gbif_id": [123456789],
                    "identified_by": ["Test Botanist"],
                    "date_of_identification": ["2023-01-01 00:00:00"],
                }
            )
            taxonomy_df.to_csv(csv_dir / "taxonomy.csv", index=False)

            # Create mock traits CSV
            traits_df = pd.DataFrame(
                {
                    "pft_id": [1],
                    "taxonomy_id": [1],
                    "carbon_sequestration_min": [10.0],
                    "carbon_sequestration_max": [20.0],
                    "shade_index_min": [0.5],
                    "shade_index_max": [0.8],
                    "canopy_diameter_min": [2.0],
                    "canopy_diameter_max": [5.0],
                    "height_max_min": [10.0],
                    "height_max_max": [15.0],
                }
            )
            traits_df.to_csv(csv_dir / "traits.csv", index=False)

            # Create mock biodiversity records CSV
            biodiversity_df = pd.DataFrame(
                {
                    "code_record": [1],
                    "common_name": ["Test Common Name"],
                    "longitude": [-75.2],
                    "latitude": [4.4],
                    "elevation_m": [1000],
                    "registered_by": ["Test Collector"],
                    "date_event": ["2023-01-02 00:00:00"],
                    "site_id": [1],
                    "species_id": [1],
                    "hood_id": [1],
                }
            )
            biodiversity_df.to_csv(csv_dir / "biodiversity.csv", index=False)

            # Create mock measurements CSV
            measurements_df = pd.DataFrame(
                {
                    "record_code": [1],
                    "measurement_name": ["TH"],  # Trunk height
                    "measurement_value": [12.5],
                    "measurement_unit": ["m"],  # Valid measurement unit
                    "measurement_method": ["OE"],  # Optical Estimation
                    "measurement_date_event": ["2023-01-03 00:00:00"],
                }
            )
            measurements_df.to_csv(csv_dir / "measurements.csv", index=False)

            # Create mock observations CSV
            observations_df = pd.DataFrame(
                {
                    "record_code": [1],
                    "reproductive_condition": ["FL"],  # Flowering
                    "phytosanitary_status": ["HE"],  # Healthy
                    "physical_condition": ["GO"],  # Good
                    "foliage_density": ["DE"],  # Dense
                    "aesthetic_value": ["HI"],  # High
                    "growth_phase": [3],  # Adult
                    "field_notes": ["Test notes"],
                    "standing": ["Y"],  # Yes
                    "rd": ["0"],  # 0% damage
                    "dm": ["0"],
                    "bbs": ["0"],
                    "ab": ["0"],
                    "ed": ["GO"],  # Good condition
                    "pi": ["0"],
                    "ph": ["0"],
                    "pa": ["0"],
                    "hc": ["NS"],  # Natural State
                    "hcf": ["NS"],
                    "pd": ["0"],
                    "pe": ["0"],
                    "pp": ["0"],
                    "po": ["0"],
                    "cre": ["Y"],  # Yes
                    "crh": ["Y"],
                    "cra": ["Y"],
                    "coa": ["Y"],
                    "ce": ["Y"],
                    "civ": ["Y"],
                    "crt": ["Y"],
                    "crg": ["Y"],
                    "cap": ["Y"],
                    "r_vol": ["0"],
                    "r_cr": ["0"],
                    "r_ce": ["0"],
                    "photo_url": ["https://example.com/photo.jpg"],
                    "accompanying_collectors": ["Test helpers"],
                }
            )
            observations_df.to_csv(csv_dir / "observations.csv", index=False)

            # Create mock climate CSV
            climate_df = pd.DataFrame(
                {
                    "stationcode": [101],
                    "stationname": ["Test Station"],
                    "datetime": ["2023-01-01 12:00:00"],
                    "latitude": [4.4],
                    "longitude": [-75.2],
                    "sensordescription": ["t2m"],  # Temperature at 2m
                    "measureunit": ["°C"],
                    "value": [25.5],
                }
            )
            climate_df.to_csv(csv_dir / "climate.csv", index=False)

            yield temp_dir

    @pytest.mark.django_db
    def test_command_requires_ibague_municipality(
        self, setup_empty_tables, country, department, mock_data_dir
    ):
        """Test that the command requires Ibagué municipality to exist."""
        with mock.patch(
            "apps.core.management.commands.import_initial_data.Municipality.objects.get"
        ) as mock_get:
            mock_get.side_effect = Municipality.DoesNotExist(
                "Municipality 'Ibagué' not found."
            )

            out = StringIO()

            with pytest.raises(CommandError) as excinfo:
                call_command("import_initial_data", local_dir=mock_data_dir, stdout=out)

            assert "Municipality 'Ibagué' not found" in str(excinfo.value)

    @pytest.mark.django_db
    def test_command_requires_empty_tables(
        self, ibague, setup_empty_tables, mock_data_dir
    ):
        """Test that the command checks for empty tables before importing."""
        # Create a family to make tables non-empty
        Family.objects.create(name="Existing Family")

        with mock.patch(
            "apps.core.management.commands.import_initial_data.Municipality.objects.get"
        ) as mock_get:
            # Configure mock to return the test ibague municipality
            mock_get.return_value = ibague

            out = StringIO()

            with pytest.raises(CommandError) as excinfo:
                call_command("import_initial_data", local_dir=mock_data_dir, stdout=out)

            assert "not empty" in str(excinfo.value)
            assert "Family" in str(excinfo.value)

    @pytest.mark.django_db
    def test_command_with_local_data_dir(
        self, ibague, setup_empty_tables, mock_data_dir
    ):
        """Test the command with a local data directory."""
        with mock.patch(
            "apps.core.management.commands.import_initial_data.Municipality.objects.get"
        ) as mock_get:
            # Configure mock to return the test ibague municipality
            mock_get.return_value = ibague

            out = StringIO()

            # Call the command with the mock data directory
            call_command("import_initial_data", local_dir=mock_data_dir, stdout=out)

            # Verify output indicates success
            output = out.getvalue()
            assert "Import completed successfully" in output

            # Verify data was imported
            assert Family.objects.count() == 1
            assert Genus.objects.count() == 1
            assert Species.objects.count() == 1
            assert Site.objects.count() == 1
            assert FunctionalGroup.objects.count() == 1
            assert Trait.objects.count() == 4  # Four trait types
            assert TraitValue.objects.count() == 4  # One value for each trait type
            assert BiodiversityRecord.objects.count() == 1
            assert Measurement.objects.count() == 1
            assert Observation.objects.count() == 1
            assert Station.objects.count() == 1
            assert Climate.objects.count() == 1
            assert Locality.objects.count() == 2  # Regular + unknown
            assert Neighborhood.objects.count() == 2  # Regular + unknown

    @pytest.mark.django_db
    def test_command_checks_missing_files(
        self, ibague, setup_empty_tables, mock_data_dir
    ):
        """Test that the command validates all required files exist."""
        # Delete a required file
        (Path(mock_data_dir) / "csv" / "taxonomy.csv").unlink()

        with mock.patch(
            "apps.core.management.commands.import_initial_data.Municipality.objects.get"
        ) as mock_get:
            # Configure mock to return the test ibague municipality
            mock_get.return_value = ibague

            out = StringIO()

            with pytest.raises(CommandError) as excinfo:
                call_command("import_initial_data", local_dir=mock_data_dir, stdout=out)

            assert "files could not be accessed" in str(excinfo.value)
            assert str(Path(mock_data_dir) / "csv" / "taxonomy.csv") in str(
                excinfo.value
            )

    @pytest.mark.django_db
    def test_command_handles_malformed_json(
        self, ibague, setup_empty_tables, mock_data_dir
    ):
        """Test that the command validates JSON structure."""
        # Write malformed localities.json
        with open(Path(mock_data_dir) / "json" / "localities.json", "w") as f:
            f.write('{"invalid_key": []}')

        with mock.patch(
            "apps.core.management.commands.import_initial_data.Municipality.objects.get"
        ) as mock_get:
            # Configure mock to return the test ibague municipality
            mock_get.return_value = ibague

            out = StringIO()

            with pytest.raises(CommandError) as excinfo:
                call_command("import_initial_data", local_dir=mock_data_dir, stdout=out)

            assert "must be a JSON object with a 'localities' key" in str(excinfo.value)

    @pytest.mark.django_db
    def test_command_validates_csv_headers(
        self, ibague, setup_empty_tables, mock_data_dir
    ):
        """Test that the command validates CSV headers."""
        # Write biodiversity.csv with missing required column
        df = pd.DataFrame(
            {"code_record": [1], "common_name": ["Test"]}
        )  # Missing many required columns
        df.to_csv(Path(mock_data_dir) / "csv" / "biodiversity.csv", index=False)

        with mock.patch(
            "apps.core.management.commands.import_initial_data.Municipality.objects.get"
        ) as mock_get:
            # Configure mock to return the test ibague municipality
            mock_get.return_value = ibague

            out = StringIO()

            with pytest.raises(CommandError) as excinfo:
                call_command("import_initial_data", local_dir=mock_data_dir, stdout=out)

            assert "Missing required columns in biodiversity.csv" in str(excinfo.value)

    @pytest.mark.django_db
    @mock.patch("apps.core.management.commands.import_initial_data.pd.read_csv")
    def test_command_with_remote_urls(self, mock_read_csv, ibague, setup_empty_tables):
        """Test the command fetching from URLs."""

        # Mock pandas read_csv to return appropriate DataFrames for each URL
        def mock_read_csv_implementation(url, *args, **kwargs):
            if "taxonomy" in str(url):
                return pd.DataFrame(
                    {
                        "taxonomy_id": [1],
                        "family": ["Test Family"],
                        "genus": ["Test Genus"],
                        "specie": ["Test Genus species"],
                        "accept_scientific_name": ["Test Genus species"],
                        "origin": ["NT"],
                        "iucn_category": ["LC"],
                        "lifeForm": ["TR"],
                        "canopy_shape_code": ["SP"],
                        "flower_color_code": ["WH"],
                        "gbif_id": [123456789],
                        "identified_by": ["Test Botanist"],
                        "date_of_identification": ["2023-01-01 00:00:00"],
                    }
                )
            # For URL validation
            elif "nrows=1" in kwargs:
                return pd.DataFrame({"header": [1]})
            return pd.DataFrame()

        mock_read_csv.side_effect = mock_read_csv_implementation

        # Mock the Ibague query
        with mock.patch(
            "apps.core.management.commands.import_initial_data.Municipality.objects.get"
        ) as mock_get:
            # Configure mock to return the test ibague municipality
            mock_get.return_value = ibague

            # Mock open to handle JSON files
            with mock.patch(
                "builtins.open",
                mock.mock_open(read_data='{"localities":[], "hoods":[]}'),
            ):
                # Mock JSON loading
                with mock.patch("json.load") as mock_json_load:
                    mock_json_load.return_value = {"localities": [], "hoods": []}

                    out = StringIO()

                    # Will fail due to incomplete mocking, but should get past URL validation
                    with pytest.raises(Exception):
                        call_command("import_initial_data", stdout=out)

                    # Verify URL validation was attempted
                    output = out.getvalue()
                    assert "All required data files are accessible" in output

    @pytest.mark.django_db
    def test_foreign_key_integrity(self, ibague, setup_empty_tables, mock_data_dir):
        """Test that the command verifies foreign key integrity after import."""
        with mock.patch(
            "apps.core.management.commands.import_initial_data.Municipality.objects.get"
        ) as mock_get:
            # Configure mock to return the test ibague municipality
            mock_get.return_value = ibague

            out = StringIO()

            # Call the command with the mock data directory
            call_command("import_initial_data", local_dir=mock_data_dir, stdout=out)

            # Verify output indicates foreign key check
            output = out.getvalue()
            assert "Checking foreign key integrity" in output

            # Verify each check was performed
            assert "Found 0 invalid locality_id(s) in Neighborhood" in output
            assert "Found 0 invalid site_id(s) in BiodiversityRecord" in output
            assert "Found 0 invalid species_id(s) in BiodiversityRecord" in output
            assert "Found 0 invalid neighborhood_id(s) in BiodiversityRecord" in output
            assert "Found 0 invalid biodiversity_record_id(s) in Observation" in output
            assert "Found 0 invalid biodiversity_record_id(s) in Measurement" in output

    @pytest.mark.django_db
    def test_unknown_locality_and_neighborhood_creation(
        self, ibague, setup_empty_tables, mock_data_dir
    ):
        """Test that the command creates unknown locality and neighborhood if needed."""
        with mock.patch(
            "apps.core.management.commands.import_initial_data.Municipality.objects.get"
        ) as mock_get:
            # Configure mock to return the test ibague municipality
            mock_get.return_value = ibague

            out = StringIO()

            # Call the command with the mock data directory
            call_command("import_initial_data", local_dir=mock_data_dir, stdout=out)

            # Verify unknown locality (id=14) was created
            unknown_locality = Locality.objects.get(id=14)
            assert unknown_locality.name == "Desconocida"

            # Verify unknown neighborhood (id=688) was created
            unknown_neighborhood = Neighborhood.objects.get(id=688)
            assert unknown_neighborhood.name == "Desconocido"
            assert unknown_neighborhood.locality_id == 14

    def test_command_has_chunksize_parameter(self):
        """Test that the command accepts a chunksize parameter with correct default."""
        # Create a parser
        parser = mock.MagicMock()
        parser.add_argument = mock.MagicMock()

        # Create command and call add_arguments
        command = Command()
        command.add_arguments(parser)

        # Check that chunksize parameter was added with correct attributes
        call_args_list = parser.add_argument.call_args_list

        # Find the call that adds the chunksize parameter
        chunksize_call = None
        for call in call_args_list:
            args, kwargs = call
            if args and args[0] == "--chunksize":
                chunksize_call = call
                break

        assert chunksize_call is not None, (
            "No --chunksize parameter found in add_arguments"
        )

        # Check the attributes
        args, kwargs = chunksize_call
        assert kwargs.get("type") is int, "chunksize parameter should be type int"
        assert kwargs.get("default") == 25000, (
            "chunksize parameter should default to 25000"
        )
        assert "help" in kwargs, "chunksize parameter should have help text"

        # Verify the help text mentions measurements and climate data
        help_text = kwargs.get("help").lower()
        assert "measurement" in help_text or "climate" in help_text, (
            "Help text should mention what the chunksize affects"
        )

    def test_methods_use_chunksize_for_pandas_read_csv(self):
        """Test that the methods pass the chunksize parameter to pd.read_csv."""
        # This test verifies that the chunksize parameter is used in the relevant methods

        # Mock pd.read_csv to avoid actual file operations
        with mock.patch(
            "apps.core.management.commands.import_initial_data.pd.read_csv"
        ) as mock_read_csv:
            # Create expected return values
            mock_read_csv.return_value = pd.DataFrame(
                {
                    "record_code": [1],
                    "measurement_name": ["TH"],
                    "measurement_value": [10.0],
                    "measurement_unit": ["m"],
                    "measurement_method": ["OE"],
                    "measurement_date_event": ["2023-01-01"],
                }
            )

            # Use source code inspection to verify the implementation details
            import inspect

            # Get the source code of the import_measurements method
            measurements_source = inspect.getsource(Command.import_measurements)

            # Check that it assigns self.chunksize to a local variable
            assert "chunksize = self.chunksize" in measurements_source, (
                "import_measurements does not use self.chunksize"
            )

            # Check that it contains the read_csv with chunksize parameter
            assert (
                "pd.read_csv(csv_path, chunksize=chunksize)" in measurements_source
            ), "import_measurements does not use chunksize in pd.read_csv"

            # Get the source code of the import_climate_data method
            climate_source = inspect.getsource(Command.import_climate_data)

            # Check that it assigns self.chunksize to a local variable
            assert "chunksize = self.chunksize" in climate_source, (
                "import_climate_data does not use self.chunksize"
            )

            # Check that it contains the read_csv with chunksize parameter
            assert "pd.read_csv(csv_path, chunksize=chunksize)" in climate_source, (
                "import_climate_data does not use chunksize in pd.read_csv"
            )
