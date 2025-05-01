import pytest


@pytest.mark.django_db
def test_family_str(family):
    """Test the string representation of the family."""
    assert str(family) == family.name


@pytest.mark.django_db
def test_genus_str(genus):
    """Test the string representation of the genus."""
    assert str(genus) == genus.name


@pytest.mark.django_db
def test_species_str(species):
    """Test the string representation of the species."""
    assert str(species) == species.scientific_name


@pytest.mark.django_db
def test_functional_group_str(functional_group):
    """Test the string representation of the functional group."""
    assert str(functional_group) == f"Group {str(functional_group.group_id)}"


@pytest.mark.django_db
def test_trait_str(trait):
    """Test the string representation of the trait (traits)."""
    assert str(trait) == trait.get_type_display()
