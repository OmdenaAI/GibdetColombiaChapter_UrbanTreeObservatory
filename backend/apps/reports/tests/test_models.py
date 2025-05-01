import pytest


@pytest.mark.django_db
def test_measurement_str(measurement):
    """Test the string representation of the measurement."""
    date_str = f" on {measurement.date}" if measurement.date else ""
    expected = (
        f"{measurement.get_attribute_display()} measurement for "
        f"biodiversity record #{measurement.biodiversity_record.id}{date_str}"
    )
    assert str(measurement) == expected


@pytest.mark.django_db
def test_observation_str(observation):
    """Test the string representation of the observation."""
    date_str = f" on {observation.date}" if observation.date else ""
    expected = f"Observation for {observation.biodiversity_record}{date_str}"
    assert str(observation) == expected
