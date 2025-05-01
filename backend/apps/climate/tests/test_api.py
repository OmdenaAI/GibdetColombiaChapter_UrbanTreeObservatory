from datetime import timedelta

import pytest
from django.urls import reverse
from rest_framework import status


@pytest.mark.django_db
class TestStationAPI:
    """Test the Station API endpoints."""

    def test_station_list(self, authenticated_client, station):
        """Test retrieving the list of stations."""
        url = reverse("climate:station-list")
        response = authenticated_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        # Find our test station in the results
        station_found = False
        for result in response.data["results"]:
            if result["code"] == station.code and result["name"] == station.name:
                station_found = True
                break

        assert station_found, f"Test station '{station.name}' not found in results"

    def test_station_detail(self, authenticated_client, station):
        """Test retrieving a specific station."""
        url = reverse("climate:station-detail", args=[station.id])
        response = authenticated_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        assert response.data["code"] == station.code
        assert response.data["name"] == station.name
        assert "municipality" in response.data
        assert response.data["municipality"]["id"] == station.municipality.id

        # Check that location data is included
        assert "longitude" in response.data
        assert "latitude" in response.data

    def test_station_filter_by_municipality(self, authenticated_client, station):
        """Test filtering stations by municipality."""
        url = (
            reverse("climate:station-list") + f"?municipality={station.municipality.id}"
        )
        response = authenticated_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        # Verify our test station is in the filtered results
        station_found = False
        for result in response.data["results"]:
            if result["code"] == station.code:
                station_found = True
                break

        assert station_found, (
            f"Test station '{station.name}' not found in filtered results"
        )

    def test_station_search_by_name(self, authenticated_client, station):
        """Test searching for stations by name."""
        # Use first few letters of the station name
        search_term = station.name[:3]
        url = reverse("climate:station-list") + f"?search={search_term}"
        response = authenticated_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        # Verify our test station is in the search results
        station_found = False
        for result in response.data["results"]:
            if result["code"] == station.code:
                station_found = True
                break

        assert station_found, (
            f"Test station '{station.name}' not found in search results"
        )

    def test_station_search_by_code(self, authenticated_client, station):
        """Test searching for stations by code."""
        search_term = str(station.code)
        url = reverse("climate:station-list") + f"?search={search_term}"
        response = authenticated_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        # Verify our test station is in the search results
        station_found = False
        for result in response.data["results"]:
            if result["code"] == station.code:
                station_found = True
                break

        assert station_found, (
            f"Test station with code '{station.code}' not found in search results"
        )

    @pytest.mark.skip(reason="GeoJSON format not fully configured yet")
    def test_station_geojson(self, authenticated_client, station):
        """Test retrieving stations in GeoJSON format."""
        url = reverse("climate:station-list") + "?format=geojson"
        response = authenticated_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        assert response.data["type"] == "FeatureCollection"

        # Find our test station in the GeoJSON features
        station_found = False
        for feature in response.data["features"]:
            if feature["properties"]["code"] == station.code:
                station_found = True
                assert feature["geometry"]["type"] == "Point"
                assert len(feature["geometry"]["coordinates"]) == 2
                break

        assert station_found, (
            f"Test station '{station.name}' not found in GeoJSON features"
        )

    def test_near_endpoint(self, authenticated_client, station):
        """Test the near endpoint for proximity search."""
        # Use the station's coordinates for the search center
        lat = station.latitude
        lon = station.longitude
        url = (
            reverse("climate:station-list") + f"near/?lat={lat}&lon={lon}&radius=10000"
        )
        response = authenticated_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        assert len(response.data) >= 1

        # Verify our test station is in the results
        station_found = False
        for result in response.data:
            if result["code"] == station.code:
                station_found = True
                break

        assert station_found, f"Test station '{station.name}' not found in near results"

    def test_near_endpoint_validation(self, authenticated_client):
        """Test validation for the near endpoint."""
        # Missing lat parameter
        url = reverse("climate:station-list") + "near/?lon=75.0&radius=1000"
        response = authenticated_client.get(url)
        assert response.status_code == status.HTTP_400_BAD_REQUEST

        # Invalid lat parameter
        url = reverse("climate:station-list") + "near/?lat=invalid&lon=75.0&radius=1000"
        response = authenticated_client.get(url)
        assert response.status_code == status.HTTP_400_BAD_REQUEST


@pytest.mark.django_db
class TestClimateAPI:
    """Test the Climate API endpoints."""

    def test_climate_list(self, api_client, climate_record):
        """Test retrieving the list of climate records."""
        # Add required filter parameters since the API limits results
        url = reverse("climate:climate-list") + f"?station={climate_record.station.id}"
        response = api_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        assert len(response.data["results"]) >= 1

        # Verify our test climate record is in the results
        record_found = False
        for result in response.data["results"]:
            if (
                result["station"] == climate_record.station.id
                and result["value"] == climate_record.value
                and result["sensor"] == climate_record.sensor
            ):
                record_found = True
                break

        assert record_found, "Test climate record not found in results"

    def test_climate_detail(self, authenticated_client, climate_record):
        """Test retrieving a specific climate record."""
        url = reverse("climate:climate-detail", args=[climate_record.id])
        response = authenticated_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        # In detail view, station is an object (not an ID)
        assert response.data["station"]["id"] == climate_record.station.id
        assert response.data["value"] == climate_record.value
        assert response.data["sensor"] == climate_record.sensor
        assert response.data["measure_unit"] == climate_record.measure_unit

    def test_climate_filter_by_station(self, authenticated_client, climate_record):
        """Test filtering climate records by station."""
        url = reverse("climate:climate-list") + f"?station={climate_record.station.id}"
        response = authenticated_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        assert len(response.data["results"]) >= 1

        # Verify all results are for the specified station
        for result in response.data["results"]:
            assert result["station"] == climate_record.station.id

    def test_climate_filter_by_municipality(self, authenticated_client, climate_record):
        """Test filtering climate records by station municipality."""
        municipality_id = climate_record.station.municipality.id
        url = (
            reverse("climate:climate-list")
            + f"?station__municipality={municipality_id}"
        )
        response = authenticated_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        assert len(response.data["results"]) >= 1

        # Since we're using the station municipality filter, verify our record is found
        record_found = False
        for result in response.data["results"]:
            if (
                result["station"] == climate_record.station.id
                and result["value"] == climate_record.value
            ):
                record_found = True
                break

        assert record_found, (
            "Test climate record not found in municipality-filtered results"
        )

    def test_climate_filter_by_sensor(self, authenticated_client, climate_record):
        """Test filtering climate records by sensor type."""
        url = (
            reverse("climate:climate-list")
            + f"?sensor={climate_record.sensor}&station={climate_record.station.id}"
        )
        response = authenticated_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        assert len(response.data["results"]) >= 1

        # Verify all results have the filtered sensor type
        for result in response.data["results"]:
            assert result["sensor"] == climate_record.sensor

    def test_climate_filter_by_value_range(self, authenticated_client, climate_record):
        """Test filtering climate records by value range."""
        min_value = climate_record.value - 1
        max_value = climate_record.value + 1
        url = (
            reverse("climate:climate-list")
            + f"?value_min={min_value}&value_max={max_value}&station={climate_record.station.id}"
        )
        response = authenticated_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        assert len(response.data["results"]) >= 1

        # Verify all results are within the specified value range
        for result in response.data["results"]:
            assert result["value"] >= min_value
            assert result["value"] <= max_value

    def test_climate_filter_by_date_range(self, authenticated_client, climate_record):
        """Test filtering climate records by date range."""
        # Create a date range that includes the climate record date
        date_from = (climate_record.date - timedelta(days=1)).isoformat()
        date_to = (climate_record.date + timedelta(days=1)).isoformat()

        url = (
            reverse("climate:climate-list")
            + f"?date_from={date_from}&date_to={date_to}&station={climate_record.station.id}"
        )
        response = authenticated_client.get(url)

        assert response.status_code == status.HTTP_200_OK

        # Verify our test climate record is in the date-filtered results
        record_found = False
        for result in response.data["results"]:
            if (
                result["station"] == climate_record.station.id
                and result["value"] == climate_record.value
                and result["sensor"] == climate_record.sensor
            ):
                record_found = True
                break

        assert record_found, "Test climate record not found in date-filtered results"

    def test_default_limit_without_filters(self, authenticated_client):
        """Test that the default limit is applied when no filters are provided."""
        url = reverse("climate:climate-list")
        response = authenticated_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        assert len(response.data["results"]) <= 1000  # Default limit defined in view
