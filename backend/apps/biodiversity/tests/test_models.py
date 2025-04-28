import pytest
from django.contrib.gis.geos import Point


@pytest.mark.django_db
def test_biodiversity_record_str(biodiversity_record):
    """Test the string representation of the biodiversity record."""
    expected = f"{biodiversity_record.common_name} ({biodiversity_record.species.scientific_name}) at {biodiversity_record.neighborhood.name}"
    assert str(biodiversity_record) == expected


@pytest.mark.django_db
def test_biodiversity_record_properties(biodiversity_record):
    """Test the longitude and latitude properties of the biodiversity record."""
    # Set a specific location for testing
    test_point = Point(-75.2, 4.3, srid=4326)
    biodiversity_record.location = test_point
    biodiversity_record.save()

    # Check longitude and latitude properties
    assert biodiversity_record.longitude == -75.2
    assert biodiversity_record.latitude == 4.3

    # Test the properties when we access them directly without using a real location
    # This simulates the behavior without having to save a null value
    original_location = biodiversity_record.location
    try:
        biodiversity_record.location = None
        assert biodiversity_record.longitude is None
        assert biodiversity_record.latitude is None
    finally:
        # Restore the original location
        biodiversity_record.location = original_location
