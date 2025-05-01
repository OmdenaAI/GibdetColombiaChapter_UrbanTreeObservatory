from datetime import datetime, timedelta

import pytest
from django.urls import reverse
from rest_framework import status


@pytest.mark.django_db
class TestMeasurementAPI:
    """Test the Measurement API endpoints."""

    def test_measurement_list(self, authenticated_client, measurement):
        """Test retrieving the list of measurements."""
        url = reverse("reports:measurement-list")
        response = authenticated_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        assert len(response.data["results"]) >= 1

        # Verify our test measurement is in the results
        measurement_found = False
        for result in response.data["results"]:
            if (
                result["attribute"] == measurement.attribute
                and result["value"] == measurement.value
                and result["biodiversity_record"] == measurement.biodiversity_record.id
            ):
                measurement_found = True
                break

        assert measurement_found, "Test measurement not found in results"

    def test_measurement_detail(self, authenticated_client, measurement):
        """Test retrieving a specific measurement."""
        url = reverse("reports:measurement-detail", args=[measurement.id])
        response = authenticated_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        assert response.data["attribute"] == measurement.attribute
        assert response.data["value"] == measurement.value
        assert response.data["unit"] == measurement.unit
        # In detail view, biodiversity_record is an object (not an ID)
        assert (
            response.data["biodiversity_record"]["id"]
            == measurement.biodiversity_record.id
        )

    def test_measurement_filter_by_attribute(self, authenticated_client, measurement):
        """Test filtering measurements by attribute."""
        url = (
            reverse("reports:measurement-list") + f"?attribute={measurement.attribute}"
        )
        response = authenticated_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        assert len(response.data["results"]) >= 1

        # Verify all results have the filtered attribute
        for result in response.data["results"]:
            assert result["attribute"] == measurement.attribute

    def test_measurement_filter_by_biodiversity_record(
        self, authenticated_client, measurement
    ):
        """Test filtering measurements by biodiversity record."""
        url = (
            reverse("reports:measurement-list")
            + f"?biodiversity_record={measurement.biodiversity_record.id}"
        )
        response = authenticated_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        assert len(response.data["results"]) >= 1

        # Verify all results are for the specified biodiversity record
        for result in response.data["results"]:
            assert result["biodiversity_record"] == measurement.biodiversity_record.id

    def test_measurement_filter_by_value_range(self, authenticated_client, measurement):
        """Test filtering measurements by value range."""
        min_value = measurement.value - 1
        max_value = measurement.value + 1
        url = (
            reverse("reports:measurement-list")
            + f"?value_min={min_value}&value_max={max_value}"
        )
        response = authenticated_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        assert len(response.data["results"]) >= 1

        # Verify all results are within the specified value range
        for result in response.data["results"]:
            assert result["value"] >= min_value
            assert result["value"] <= max_value

    def test_measurement_filter_by_date_range(self, authenticated_client, measurement):
        """Test filtering measurements by date range."""
        # Create a date range that includes the measurement date
        if measurement.date:
            date_from = (measurement.date - timedelta(days=1)).isoformat()
            date_to = (measurement.date + timedelta(days=1)).isoformat()
        else:
            # If no date set, use a wide range that should include all records
            today = datetime.now().date()
            date_from = (today - timedelta(days=365)).isoformat()
            date_to = today.isoformat()

        url = (
            reverse("reports:measurement-list")
            + f"?date_from={date_from}&date_to={date_to}"
        )
        response = authenticated_client.get(url)

        assert response.status_code == status.HTTP_200_OK

        # If the measurement has a date, verify it's in the results
        if measurement.date:
            measurement_found = False
            for result in response.data["results"]:
                if (
                    result["attribute"] == measurement.attribute
                    and result["value"] == measurement.value
                    and result["biodiversity_record"]
                    == measurement.biodiversity_record.id
                ):
                    measurement_found = True
                    break

            assert measurement_found, (
                "Test measurement not found in date-filtered results"
            )


@pytest.mark.django_db
class TestObservationAPI:
    """Test the Observation API endpoints."""

    def test_observation_list(self, authenticated_client, observation):
        """Test retrieving the list of observations."""
        url = reverse("reports:observation-list")
        response = authenticated_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        assert len(response.data["results"]) >= 1

        # Verify our test observation is in the results
        observation_found = False
        for result in response.data["results"]:
            if (
                result["phytosanitary_status"] == observation.phytosanitary_status
                and result["physical_condition"] == observation.physical_condition
                and result["biodiversity_record"] == observation.biodiversity_record.id
            ):
                observation_found = True
                break

        assert observation_found, "Test observation not found in results"

    def test_observation_detail(self, authenticated_client, observation):
        """Test retrieving a specific observation."""
        url = reverse("reports:observation-detail", args=[observation.id])
        response = authenticated_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        assert response.data["phytosanitary_status"] == observation.phytosanitary_status
        assert response.data["physical_condition"] == observation.physical_condition
        # In detail view, biodiversity_record is an object (not an ID)
        assert (
            response.data["biodiversity_record"]["id"]
            == observation.biodiversity_record.id
        )

    def test_observation_filter_by_phytosanitary_status(
        self, authenticated_client, observation
    ):
        """Test filtering observations by phytosanitary status."""
        url = (
            reverse("reports:observation-list")
            + f"?phytosanitary_status={observation.phytosanitary_status}"
        )
        response = authenticated_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        assert len(response.data["results"]) >= 1

        # Verify all results have the filtered phytosanitary status
        for result in response.data["results"]:
            assert result["phytosanitary_status"] == observation.phytosanitary_status

    def test_observation_filter_by_physical_condition(
        self, authenticated_client, observation
    ):
        """Test filtering observations by physical condition."""
        url = (
            reverse("reports:observation-list")
            + f"?physical_condition={observation.physical_condition}"
        )
        response = authenticated_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        assert len(response.data["results"]) >= 1

        # Verify all results have the filtered physical condition
        for result in response.data["results"]:
            assert result["physical_condition"] == observation.physical_condition

    def test_observation_filter_by_biodiversity_record(
        self, authenticated_client, observation
    ):
        """Test filtering observations by biodiversity record."""
        url = (
            reverse("reports:observation-list")
            + f"?biodiversity_record={observation.biodiversity_record.id}"
        )
        response = authenticated_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        assert len(response.data["results"]) >= 1

        # Verify all results are for the specified biodiversity record
        for result in response.data["results"]:
            assert result["biodiversity_record"] == observation.biodiversity_record.id

    def test_observation_filter_by_date_range(self, authenticated_client, observation):
        """Test filtering observations by date range."""
        # Create a date range that includes the observation date
        if observation.date:
            date_from = (observation.date - timedelta(days=1)).isoformat()
            date_to = (observation.date + timedelta(days=1)).isoformat()
        else:
            # If no date set, use a wide range that should include all records
            today = datetime.now().date()
            date_from = (today - timedelta(days=365)).isoformat()
            date_to = today.isoformat()

        url = (
            reverse("reports:observation-list")
            + f"?date_from={date_from}&date_to={date_to}"
        )
        response = authenticated_client.get(url)

        assert response.status_code == status.HTTP_200_OK

        # If the observation has a date, verify it's in the results
        if observation.date:
            observation_found = False
            for result in response.data["results"]:
                if (
                    result["phytosanitary_status"] == observation.phytosanitary_status
                    and result["physical_condition"] == observation.physical_condition
                    and result["biodiversity_record"]
                    == observation.biodiversity_record.id
                ):
                    observation_found = True
                    break

            assert observation_found, (
                "Test observation not found in date-filtered results"
            )

    def test_observation_search(self, authenticated_client, observation):
        """Test searching observations by text fields."""
        # If observation has field notes or recorded_by with sufficient text to search
        if observation.field_notes:
            search_term = observation.field_notes[:5]  # Use first few characters
        elif observation.accompanying_collectors:
            search_term = observation.accompanying_collectors[:5]
        elif observation.recorded_by:
            search_term = observation.recorded_by[:5]
        else:
            search_term = "Cortolima"  # Default recorded_by value

        url = reverse("reports:observation-list") + f"?search={search_term}"
        response = authenticated_client.get(url)

        assert response.status_code == status.HTTP_200_OK
