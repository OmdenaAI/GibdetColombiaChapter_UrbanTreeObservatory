import json
import pytest
from django.urls import reverse
from django.contrib.gis.geos import Point
from rest_framework import status


@pytest.mark.django_db
class TestBiodiversityRecordAPI:
    """Test the BiodiversityRecord API endpoints."""

    def test_biodiversity_record_list(self, api_client, biodiversity_record):
        """Test retrieving the list of biodiversity records."""
        url = reverse("biodiversity:biodiversity-record-list")
        response = api_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        assert len(response.data["results"]) == 1
        assert (
            response.data["results"][0]["common_name"]
            == biodiversity_record.common_name
        )

        # Check that related objects are included
        assert "species" in response.data["results"][0]
        assert "site" in response.data["results"][0]
        assert "neighborhood" in response.data["results"][0]

        # Check that location-related fields are present
        assert "longitude" in response.data["results"][0]
        assert "latitude" in response.data["results"][0]

    def test_biodiversity_record_detail(self, api_client, biodiversity_record):
        """Test retrieving a specific biodiversity record."""
        url = reverse(
            "biodiversity:biodiversity-record-detail", args=[biodiversity_record.id]
        )
        response = api_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        assert response.data["common_name"] == biodiversity_record.common_name
        assert response.data["species"]["id"] == biodiversity_record.species.id
        assert response.data["site"]["id"] == biodiversity_record.site.id
        assert (
            response.data["neighborhood"]["id"] == biodiversity_record.neighborhood.id
        )

    def test_biodiversity_record_geojson(self, api_client, biodiversity_record):
        """Test retrieving biodiversity records in GeoJSON format."""
        url = reverse("biodiversity:biodiversity-record-list") + "?format=geojson"
        response = api_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        assert response.data["type"] == "FeatureCollection"
        assert len(response.data["features"]) == 1

        # Check properties
        properties = response.data["features"][0]["properties"]
        assert properties["common_name"] == biodiversity_record.common_name
        assert (
            properties["species_scientific_name"]
            == biodiversity_record.species.scientific_name
        )
        assert properties["neighborhood_name"] == biodiversity_record.neighborhood.name

        # Check geometry
        assert response.data["features"][0]["geometry"]["type"] == "Point"
        assert "coordinates" in response.data["features"][0]["geometry"]
        assert len(response.data["features"][0]["geometry"]["coordinates"]) == 2


@pytest.mark.django_db
class TestBiodiversityFilters:
    """Test filtering capabilities for biodiversity records."""

    def test_filter_by_species(self, api_client, biodiversity_record):
        """Test filtering biodiversity records by species."""
        url = (
            reverse("biodiversity:biodiversity-record-list")
            + f"?species={biodiversity_record.species.id}"
        )
        response = api_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        assert len(response.data["results"]) == 1
        assert (
            response.data["results"][0]["species"]["id"]
            == biodiversity_record.species.id
        )

    def test_filter_by_site(self, api_client, biodiversity_record):
        """Test filtering biodiversity records by site."""
        url = (
            reverse("biodiversity:biodiversity-record-list")
            + f"?site={biodiversity_record.site.id}"
        )
        response = api_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        assert len(response.data["results"]) == 1
        assert response.data["results"][0]["site"]["id"] == biodiversity_record.site.id

    def test_filter_by_neighborhood(self, api_client, biodiversity_record):
        """Test filtering biodiversity records by neighborhood."""
        url = (
            reverse("biodiversity:biodiversity-record-list")
            + f"?neighborhood={biodiversity_record.neighborhood.id}"
        )
        response = api_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        assert len(response.data["results"]) == 1
        assert (
            response.data["results"][0]["neighborhood"]["id"]
            == biodiversity_record.neighborhood.id
        )

    def test_filter_by_locality(self, api_client, biodiversity_record):
        """Test hierarchical filtering by locality."""
        locality_id = biodiversity_record.neighborhood.locality.id
        url = (
            reverse("biodiversity:biodiversity-record-list")
            + f"?neighborhood__locality={locality_id}"
        )
        response = api_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        assert len(response.data["results"]) == 1

    def test_search_by_common_name(self, api_client, biodiversity_record):
        """Test searching biodiversity records by common name."""
        term = biodiversity_record.common_name[:4]  # First few letters
        url = reverse("biodiversity:biodiversity-record-list") + f"?search={term}"
        response = api_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        assert len(response.data["results"]) == 1
        assert response.data["results"][0]["id"] == biodiversity_record.id

    def test_date_range_filter(self, api_client, biodiversity_record):
        """Test filtering biodiversity records by date range."""
        # Use a date range that includes the record's date
        start_date = (
            biodiversity_record.date.replace(day=1)
            if biodiversity_record.date
            else "2020-01-01"
        )
        end_date = (
            biodiversity_record.date.replace(day=28)
            if biodiversity_record.date
            else "2025-12-31"
        )

        url = (
            reverse("biodiversity:biodiversity-record-list")
            + f"?date_from={start_date}&date_to={end_date}"
        )
        response = api_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        assert len(response.data["results"]) == 1
        assert response.data["results"][0]["id"] == biodiversity_record.id


@pytest.mark.django_db
class TestSpatialEndpoints:
    """Test the spatial endpoints for biodiversity records."""

    @pytest.fixture
    def fixed_location_record(self, biodiversity_record):
        """Create a biodiversity record with a fixed location for testing."""
        # Update the record with a fixed location
        biodiversity_record.location = Point(-75.2, 4.3, srid=4326)
        biodiversity_record.save()
        return biodiversity_record

    def test_near_endpoint(self, api_client, fixed_location_record):
        """Test the near endpoint for proximity search."""
        # Use coordinates close to the fixed location
        url = (
            reverse("biodiversity:biodiversity-record-near")
            + "?lat=4.3&lon=-75.2&radius=100"
        )
        response = api_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        assert len(response.data) == 1
        assert response.data[0]["id"] == fixed_location_record.id

    def test_bbox_endpoint(self, api_client, fixed_location_record):
        """Test the bbox endpoint for bounding box search."""
        # Define a bounding box that includes the fixed location
        url = (
            reverse("biodiversity:biodiversity-record-bbox")
            + "?min_lon=-75.3&min_lat=4.2&max_lon=-75.1&max_lat=4.4"
        )
        response = api_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        assert len(response.data) == 1
        assert response.data[0]["id"] == fixed_location_record.id

    def test_by_neighborhood_endpoint(self, api_client, biodiversity_record):
        """Test the by_neighborhood endpoint."""
        url = (
            reverse("biodiversity:biodiversity-record-by-neighborhood")
            + f"?id={biodiversity_record.neighborhood.id}"
        )
        response = api_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        # Since this endpoint returns GeoJSON, check the features
        assert len(response.data["features"]) == 1

    def test_by_locality_endpoint(self, api_client, biodiversity_record):
        """Test the by_locality endpoint."""
        url = (
            reverse("biodiversity:biodiversity-record-by-locality")
            + f"?id={biodiversity_record.neighborhood.locality.id}"
        )
        response = api_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        # Since this endpoint returns GeoJSON, check the features
        assert len(response.data["features"]) == 1

    def test_by_polygon_endpoint(self, api_client, fixed_location_record):
        """Test the by_polygon endpoint."""
        # Create a polygon that contains the fixed location
        polygon = [[-75.3, 4.2], [-75.1, 4.2], [-75.1, 4.4], [-75.3, 4.4], [-75.3, 4.2]]

        url = reverse("biodiversity:biodiversity-record-by-polygon")
        response = api_client.post(
            url, data=json.dumps({"polygon": polygon}), content_type="application/json"
        )

        assert response.status_code == status.HTTP_200_OK
        assert len(response.data) == 1
