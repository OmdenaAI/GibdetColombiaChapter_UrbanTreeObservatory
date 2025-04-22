from django.test import TestCase
from django.core.exceptions import ValidationError
from apps.taxonomy.models import Family, Genus, Species, FunctionalGroup, Trait, TraitValue
from django.db.utils import IntegrityError

class FamilyTestCase(TestCase):
    """Test case for the Family model."""

    def setUp(self):
        """Set up test data."""
        self.family = Family.objects.create(name="Fabaceae")

    def test_str_representation(self):
        """Test the string representation of a family."""
        self.assertEqual(str(self.family), "Fabaceae")

    def test_unique_name(self):
        """Test that family names must be unique."""
        with self.assertRaises(IntegrityError):
            Family.objects.create(name="Fabaceae").full_clean()

class GenusTestCase(TestCase):
    """Test case for the Genus model."""

    def setUp(self):
        """Set up test data."""
        self.family = Family.objects.create(name="Fabaceae")
        self.genus = Genus.objects.create(name="Caesalpinia", family=self.family)

    def test_str_representation(self):
        """Test the string representation of a genus."""
        self.assertEqual(str(self.genus), "Caesalpinia")

    def test_unique_name(self):
        """Test that genus names must be unique."""
        with self.assertRaises(IntegrityError):
            Genus.objects.create(name="Caesalpinia", family=self.family).full_clean()

class SpeciesTestCase(TestCase):
    """Test case for the Species model."""

    def setUp(self):
        """Set up test data."""
        self.family = Family.objects.create(name="Fabaceae")
        self.genus = Genus.objects.create(name="Caesalpinia", family=self.family)
        self.species = Species.objects.create(
            genus=self.genus,
            name="spinosa",
            accepted_scientific_name="Caesalpinia spinosa",
            origin=Species.Origin.NATIVE,
            iucn_status=Species.IUCNStatus.LEAST_CONCERN,
            life_form=Species.LifeForm.TREE,
            canopy_shape=Species.CanopyShape.BROAD,
            flower_color=Species.FlowerColor.YELLOW,
            gbif_id=5349236
        )

    def test_str_representation(self):
        """Test the string representation of a species."""
        self.assertEqual(str(self.species), "Caesalpinia spinosa")

    def test_scientific_name_property(self):
        """Test the scientific_name property."""
        self.assertEqual(self.species.scientific_name, "Caesalpinia spinosa")
    
    def test_gbif_url_property(self):
        """Test the gbif_url property."""
        expected_url = "https://www.gbif.org/species/5349236"
        self.assertEqual(self.species.gbif_url, expected_url)

    def test_gbif_url_none(self):
        """Test the gbif_url property when gbif_id is None."""
        self.species.gbif_id = None
        self.assertIsNone(self.species.gbif_url)

    def test_tropical_plants_url_property(self):
        """Test the tropical_plants_url property."""
        expected_url = "https://tropical.theferns.info/viewtropical.php?id=Caesalpinia+spinosa"
        self.assertEqual(self.species.tropical_plants_url, expected_url)


class TraitTestCase(TestCase):
    """Test case for the Trait model."""

    def setUp(self):
        """Set up test data."""
        self.trait = Trait.objects.create(type=Trait.TraitType.CARBON_SEQUESTRATION_IDX)

    def test_str_representation(self):
        """Test the string representation of a trait."""
        self.assertEqual(str(self.trait), "carbon sequestration index")

class FunctionalGroupTestCase(TestCase):
    """Test case for the FunctionalGroup model."""

    def setUp(self):
        """Set up test data."""
        self.group = FunctionalGroup.objects.create(
            group_id=1,
            description="Test functional group"
        )

    def test_str_representation(self):
        """Test the string representation of a functional group."""
        self.assertEqual(str(self.group), "Group 1")

    def test_unique_group_id(self):
        """Test that group_id must be unique."""
        with self.assertRaises(IntegrityError):
            FunctionalGroup.objects.create(group_id=1).full_clean()

class TraitValueTestCase(TestCase):
    """Test case for the TraitValue model."""

    def setUp(self):
        """Set up test data."""
        self.trait = Trait.objects.create(type=Trait.TraitType.TOTAL_HEIGHT_MAX)
        self.group = FunctionalGroup.objects.create(group_id=1)
        self.trait_value = TraitValue.objects.create(
            trait=self.trait,
            functional_group=self.group,
            min_value=10.0,
            max_value=20.0
        )

    def test_str_representation(self):
        """Test the string representation of a trait value."""
        self.assertEqual(str(self.trait_value), "maximum total height (m): 10.0-20.0")
    
    def test_min_value_less_than_max_value(self):
        """Test that min_value must be less than max_value."""
        with self.assertRaises(IntegrityError):
            TraitValue.objects.create(
                trait=self.trait,
                functional_group=self.group,
                min_value=20.0,
                max_value=10.0
            ).full_clean()

    def test_min_value_greater_than_zero(self):
        """Test that min_value must be greater than zero."""
        with self.assertRaises(IntegrityError):
            TraitValue.objects.create(
                trait=self.trait,
                functional_group=self.group,
                min_value=-1.0,
                max_value=10.0
            ).full_clean()

    def test_max_value_greater_than_zero(self):
        """Test that max_value must be greater than zero."""
        with self.assertRaises(IntegrityError):
            TraitValue.objects.create(
                trait=self.trait,
                functional_group=self.group,
                min_value=0.0,
                max_value=-1.0
            ).full_clean()

   