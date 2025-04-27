import pytest


@pytest.mark.django_db
def test_country_str(country):
    """Test the string representation of the country."""
    assert str(country) == country.name


@pytest.mark.django_db
def test_department_str(department):
    """Test the string representation of the department."""
    assert str(department) == f"{department.name}, {department.country.name}"


@pytest.mark.django_db
def test_municipality_str(municipality):
    """Test the string representation of the municipality."""
    assert (
        str(municipality)
        == f"{municipality.name}, {municipality.department.name}, {municipality.department.country.name}"
    )


@pytest.mark.django_db
def test_locality_str(locality):
    """Test the string representation of the locality."""
    expected = (
        f"{locality.name}, {locality.municipality.name}, "
        f"{locality.municipality.department.name}, "
        f"{locality.municipality.department.country.name}"
    )
    assert str(locality) == expected


@pytest.mark.django_db
def test_neighborhood_str(neighborhood):
    """Test the string representation of the neighborhood."""
    expected = (
        f"{neighborhood.name}, {neighborhood.locality.municipality.name}, "
        f"{neighborhood.locality.municipality.department.name}, "
        f"{neighborhood.locality.municipality.department.country.name}"
    )
    assert str(neighborhood) == expected


@pytest.mark.django_db
def test_site_str(site):
    """Test the string representation of the site."""
    expected = (
        f"{site.name}, {site.locality.municipality.name}, "
        f"{site.locality.municipality.department.name}, "
        f"{site.locality.municipality.department.country.name}"
    )
    assert str(site) == expected
