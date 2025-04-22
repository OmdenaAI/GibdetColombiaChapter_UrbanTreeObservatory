from django.test import TestCase
from django.contrib.gis.geos import Point
from apps.reports.models import Measurement, Observation
from apps.biodiversity.models import BiodiversityRecord
from apps.taxonomy.models import Family, Genus, Species
from apps.places.models import Country, Department, Municipality, Place

class MeasurementTestCase(TestCase):
    """Test case for the Measurement model."""

    def setUp(self):
        """Set up test data."""
        # Create necessary related objects
        # self.country = Country.objects.create(name="Colombia")
        # self.department = Department.objects.create(
        #     name="Tolima",
        #     country=self.country
        # )
        self.municipality = Municipality.objects.get(name="Ibagué")

        self.place = Place.objects.create(
            municipality=self.municipality,
            site="Parque Centenario",
            populated_center="Centro",
            zone=1,
            subzone=1
        )

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

        self.biodiversity_record = BiodiversityRecord.objects.create(
            species=self.species,
            place=self.place,
            location=Point(-75.2, 4.4)
        )

        self.measurement = Measurement.objects.create(
            biodiversity_record=self.biodiversity_record,
            attribute=Measurement.MeasuredAttribute.TOTAL_HEIGHT,
            value=15.5,
            unit=Measurement.MeasurementUnit.METERS,
            method=Measurement.MeasurementMethod.OPTICAL_ESTIMATION,
            date="2025-04-19"
        )

    def test_str_representation(self):
        """Test the string representation of a measurement."""
        expected = f"total height measurement for biodiversity record #{self.measurement.biodiversity_record.pk} on 2025-04-19"
        self.assertEqual(str(self.measurement), expected)

    def test_str_no_date(self):
        """Test string representation without date."""
        self.measurement.date = None
        expected = f"total height measurement for biodiversity record #{self.measurement.biodiversity_record.pk}"
        self.assertEqual(str(self.measurement), expected)

    def test_default_method(self):
        """Test default measurement method."""
        measurement = Measurement.objects.create(
            biodiversity_record=self.biodiversity_record,
            attribute=Measurement.MeasuredAttribute.TOTAL_HEIGHT,
            value=15.5
        )
        self.assertEqual(measurement.method, Measurement.MeasurementMethod.NOT_REPORTED)

    def test_default_unit(self):
        """Test default measurement unit."""
        measurement = Measurement.objects.create(
            biodiversity_record=self.biodiversity_record,
            attribute=Measurement.MeasuredAttribute.TOTAL_HEIGHT,
            value=15.5
        )
        self.assertEqual(measurement.unit, Measurement.MeasurementUnit.NOT_REPORTED)

class ObservationTestCase(TestCase):
    """Test case for the Observation model."""

    def setUp(self):
        """Set up test data."""
        # Create necessary related objects (reusing from MeasurementTestCase)
        # self.country = Country.objects.create(name="Colombia")
        # self.department = Department.objects.create(
        #     name="Tolima",
        #     country=self.country
        # )
        self.municipality = Municipality.objects.get(name="Ibagué")

        self.place = Place.objects.create(
            municipality=self.municipality,
            site="Parque Centenario",
            populated_center="Centro",
            zone=1,
            subzone=1
        )

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

        self.biodiversity_record = BiodiversityRecord.objects.create(
            species=self.species,
            place=self.place,
            location=Point(-75.2, 4.4)
        )

        self.observation = Observation.objects.create(
            biodiversity_record=self.biodiversity_record,
            reproductive_condition=Observation.ReproductiveCondition.FLOWERING,
            phytosanitary_status=Observation.PhytosanitaryStatus.HEALTHY,
            physical_condition=Observation.PhysicalCondition.GOOD,
            foliage_density=Observation.FoliageDensity.DENSE,
            aesthetic_value=Observation.AestheticValue.ESSENTIAL,
            growth_phase=Observation.GrowthPhase.ADULT,
            is_standing=True,
            field_notes="Test observation",
            recorded_by="Test User",
            date="2025-04-19"
        )

    def test_str_representation(self):
        """Test the string representation of an observation."""
        expected = "Observation for Caesalpinia spinosa at -75.2, 4.4 on 2025-04-19"
        self.assertEqual(str(self.observation), expected)

    def test_str_no_date(self):
        """Test string representation without date."""
        self.observation.date = None
        expected = "Observation for Caesalpinia spinosa at -75.2, 4.4"
        self.assertEqual(str(self.observation), expected)

    def test_default_reproductive_condition(self):
        """Test default reproductive condition."""
        observation = Observation.objects.create(
            biodiversity_record=self.biodiversity_record
        )
        self.assertEqual(
            observation.reproductive_condition,
            Observation.ReproductiveCondition.NOT_REPORTED
        )

    def test_default_phytosanitary_status(self):
        """Test default phytosanitary status."""
        observation = Observation.objects.create(
            biodiversity_record=self.biodiversity_record
        )
        self.assertEqual(
            observation.phytosanitary_status,
            Observation.PhytosanitaryStatus.NOT_REPORTED
        )

    def test_damage_percent_defaults(self):
        """Test default damage percentages."""
        observation = Observation.objects.create(
            biodiversity_record=self.biodiversity_record
        )
        self.assertEqual(observation.rd, Observation.DamagePercent.ZERO)
        self.assertEqual(observation.dm, Observation.DamagePercent.ZERO)
        self.assertEqual(observation.bbs, Observation.DamagePercent.ZERO)
        self.assertEqual(observation.ab, Observation.DamagePercent.ZERO)
        self.assertEqual(observation.pi, Observation.DamagePercent.ZERO)
        self.assertEqual(observation.ph, Observation.DamagePercent.ZERO)
        self.assertEqual(observation.pa, Observation.DamagePercent.ZERO)
        self.assertEqual(observation.pd, Observation.DamagePercent.ZERO)
        self.assertEqual(observation.pe, Observation.DamagePercent.ZERO)
        self.assertEqual(observation.pp, Observation.DamagePercent.ZERO)
        self.assertEqual(observation.po, Observation.DamagePercent.ZERO)
        self.assertEqual(observation.r_vol, Observation.DamagePercent.ZERO)
        self.assertEqual(observation.r_cr, Observation.DamagePercent.ZERO)
        self.assertEqual(observation.r_ce, Observation.DamagePercent.ZERO)