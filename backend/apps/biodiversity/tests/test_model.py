from django.test import TestCase
from django.contrib.gis.geos import Point
from apps.biodiversity.models import BiodiversityRecord
from apps.places.models import Place, Country, Department, Municipality
from apps.taxonomy.models import Species, Genus, Family


class BiodiversityRecordTestCase(TestCase):
    """Test case for the BiodiversityRecord model."""

    def setUp(self):
        """Set up test data."""
        # Create necessary related objects
        # self.country = Country.objects.create(name="Colombia")
        # self.department = Department.objects.create(
        #     name="Tolima", 
            # country=self.country
            # country=colombia
        # )
        # self.municipality = Municipality.objects.create(
        #     name="Ibagué",
        #     department=self.department
        # )
        municipality = Municipality.objects.get(name="Ibagué")
        self.place = Place.objects.create(
            municipality=municipality,
            site="Parque Centenario",
            populated_center="Centro",
            zone=1,
            subzone=1
        )

        # Create taxonomy objects
        self.family = Family.objects.create(name="Fabaceae")
        self.genus = Genus.objects.create(
            name="Caesalpinia",
            family=self.family
        )
        self.species = Species.objects.create(
            genus=self.genus,
            name="spinosa",
            accepted_scientific_name="Caesalpinia spinosa"
        )

        # Create the biodiversity record
        self.record = BiodiversityRecord.objects.create(
            common_name="Dividivi",
            species=self.species,
            place=self.place,
            location=Point(-75.2, 4.4),  # Example coordinates for Ibagué
            elevation_m=1285.0,
            recorded_by="Test User",
            date="2025-04-19"
        )

    def test_str_representation(self):
        """Test the string representation of a biodiversity record."""
        expected = "Caesalpinia spinosa at -75.2, 4.4"
        self.assertEqual(str(self.record), expected)

    