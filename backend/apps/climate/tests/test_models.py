import pytest


@pytest.mark.django_db
def test_station_str(station):
    """Test the string representation of the station."""
    assert str(station) == f"{station.name} ({station.code})"


@pytest.mark.django_db
def test_climate_str(climate_record):
    """Test the string representation of the climate record."""
    assert (
        str(climate_record)
        == f"{climate_record.station} - {climate_record.date} - {climate_record.value} {climate_record.measure_unit}"
    )
