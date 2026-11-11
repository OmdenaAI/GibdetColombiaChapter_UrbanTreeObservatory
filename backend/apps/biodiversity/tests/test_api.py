import json

import pytest
from django.contrib.gis.geos import Point
from django.urls import reverse
from rest_framework import status


@pytest.mark.django_db
class TestBiodiversityRecordAPI:
    """Test the BiodiversityRecord API endpoints."""

    def test_biodiversity_record_list(self, authenticated_client, biodiversity_record):
        """Test retrieving the list of biodiversity records."""
        url = reverse("biodiversity:biodiversity-record-list")
        response = authenticated_client.get(url)

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

    def test_biodiversity_record_detail(
        self, authenticated_client, biodiversity_record
    ):
        """Test retrieving a specific biodiversity record."""
        url = reverse(
            "biodiversity:biodiversity-record-detail", args=[biodiversity_record.id]
        )
        response = authenticated_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        assert response.data["common_name"] == biodiversity_record.common_name
        assert response.data["species"]["id"] == biodiversity_record.species.id
        assert response.data["site"]["id"] == biodiversity_record.site.id
        assert (
            response.data["neighborhood"]["id"] == biodiversity_record.neighborhood.id
        )

    @pytest.mark.skip(reason="GeoJSON format not working correctly yet")
    def test_biodiversity_record_geojson(
        self, authenticated_client, biodiversity_record
    ):
        """Test retrieving biodiversity records in GeoJSON format."""
        url = reverse("biodiversity:biodiversity-record-list")
        response = authenticated_client.get(url, {"format": "geojson"})

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

    def test_filter_by_species(self, authenticated_client, biodiversity_record):
        """Test filtering biodiversity records by species."""
        url = (
            reverse("biodiversity:biodiversity-record-list")
            + f"?species={biodiversity_record.species.id}"
        )
        response = authenticated_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        assert len(response.data["results"]) == 1
        assert (
            response.data["results"][0]["species"]["id"]
            == biodiversity_record.species.id
        )

    def test_filter_by_site(self, authenticated_client, biodiversity_record):
        """Test filtering biodiversity records by site."""
        url = (
            reverse("biodiversity:biodiversity-record-list")
            + f"?site={biodiversity_record.site.id}"
        )
        response = authenticated_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        assert len(response.data["results"]) == 1
        assert response.data["results"][0]["site"]["id"] == biodiversity_record.site.id

    def test_filter_by_neighborhood(self, authenticated_client, biodiversity_record):
        """Test filtering biodiversity records by neighborhood."""
        url = (
            reverse("biodiversity:biodiversity-record-list")
            + f"?neighborhood={biodiversity_record.neighborhood.id}"
        )
        response = authenticated_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        assert len(response.data["results"]) == 1
        assert (
            response.data["results"][0]["neighborhood"]["id"]
            == biodiversity_record.neighborhood.id
        )

    def test_filter_by_locality(self, authenticated_client, biodiversity_record):
        """Test hierarchical filtering by locality."""
        locality_id = biodiversity_record.neighborhood.locality.id
        url = (
            reverse("biodiversity:biodiversity-record-list")
            + f"?neighborhood__locality={locality_id}"
        )
        response = authenticated_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        assert len(response.data["results"]) == 1

    def test_search_by_common_name(self, authenticated_client, biodiversity_record):
        """Test searching biodiversity records by common name."""
        term = biodiversity_record.common_name[:4]  # First few letters
        url = reverse("biodiversity:biodiversity-record-list") + f"?search={term}"
        response = authenticated_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        assert len(response.data["results"]) == 1
        assert response.data["results"][0]["id"] == biodiversity_record.id

    @pytest.mark.skip(reason="Test fails erratically; needs to be fixed.")
    def test_date_range_filter(self, authenticated_client, biodiversity_record):
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
        response = authenticated_client.get(url)

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

    def test_near_endpoint(self, authenticated_client, fixed_location_record):
        """Test the near endpoint for proximity search."""
        # Use coordinates close to the fixed location
        url = (
            reverse("biodiversity:biodiversity-record-list")
            + "near/?lat=4.3&lon=-75.2&radius=100"
        )
        response = authenticated_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        assert len(response.data) == 1
        assert response.data[0]["id"] == fixed_location_record.id

    def test_bbox_endpoint(self, authenticated_client, fixed_location_record):
        """Test the bbox endpoint for bounding box search."""
        # Define a bounding box that includes the fixed location
        url = (
            reverse("biodiversity:biodiversity-record-list")
            + "bbox/?min_lon=-75.3&min_lat=4.2&max_lon=-75.1&max_lat=4.4"
        )
        response = authenticated_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        assert len(response.data) == 1
        assert response.data[0]["id"] == fixed_location_record.id

    def test_by_neighborhood_endpoint(self, authenticated_client, biodiversity_record):
        """Test the by_neighborhood endpoint."""
        url = (
            reverse("biodiversity:biodiversity-record-list")
            + f"by_neighborhood/?id={biodiversity_record.neighborhood.id}"
        )
        response = authenticated_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        # Since this endpoint returns GeoJSON, check the features
        assert len(response.data["features"]) == 1

    def test_by_locality_endpoint(self, authenticated_client, biodiversity_record):
        """Test the by_locality endpoint."""
        url = (
            reverse("biodiversity:biodiversity-record-list")
            + f"by_locality/?id={biodiversity_record.neighborhood.locality.id}"
        )
        response = authenticated_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        # Since this endpoint returns GeoJSON, check the features
        assert len(response.data["features"]) == 1

    def test_by_polygon_endpoint(self, authenticated_client, fixed_location_record):
        """Test the by_polygon endpoint."""
        # Create a polygon that contains the fixed location
        polygon = [[-75.3, 4.2], [-75.1, 4.2], [-75.1, 4.4], [-75.3, 4.4], [-75.3, 4.2]]

        url = reverse("biodiversity:biodiversity-record-list") + "by_polygon/"
        response = authenticated_client.post(
            url, data=json.dumps({"polygon": polygon}), content_type="application/json"
        )

        assert response.status_code == status.HTTP_200_OK
        assert len(response.data) == 1


@pytest.mark.django_db
class TestInventoryAPI:
    """/api/v1/biodiversity/inventory/: read-only tree inventory with CSV export."""

    @pytest.fixture
    def trees(self, neighborhood, species):
        import datetime

        from apps.biodiversity.factories import BiodiversityRecordFactory
        from apps.reports.factories import MeasurementFactory, ObservationFactory

        out = []
        for i, (height, health) in enumerate([(3.0, "HE"), (12.0, "SI")]):
            record = BiodiversityRecordFactory(
                neighborhood=neighborhood,
                species=species,
                common_name=f"Tree {i}",
                date=datetime.date(2017, 1, 1),
            )
            # An older and a newer total height: the newer one is reported.
            MeasurementFactory(
                biodiversity_record=record, attribute="HT", value=1.0, unit="m",
                date=datetime.date(2014, 1, 1),
            )
            MeasurementFactory(
                biodiversity_record=record, attribute="HT", value=height, unit="m",
                date=datetime.date(2017, 1, 1),
            )
            MeasurementFactory(
                biodiversity_record=record, attribute="DBH", value=20.0, unit="cm",
                date=datetime.date(2017, 1, 1),
            )
            ObservationFactory(biodiversity_record=record, phytosanitary_status=health)
            out.append(record)
        return out

    def test_list_reports_latest_values(self, api_client, trees):
        response = api_client.get(reverse("biodiversity:inventory-list"))

        assert response.status_code == status.HTTP_200_OK
        assert response.data["count"] == 2
        row = response.data["results"][1]
        assert row["id"] == trees[1].id
        assert row["height_m"] == 12.0
        assert row["dbh_cm"] == 20.0
        assert row["phytosanitary_status"] == "SI"
        assert row["family"] == trees[1].species.genus.family.name

    def test_filters(self, api_client, trees, species):
        url = reverse("biodiversity:inventory-list")
        genus = species.genus.name
        family = species.genus.family.name
        hood = trees[0].neighborhood.name

        def ids(**params):
            return [r["id"] for r in api_client.get(url, params).data["results"]]

        assert ids(id=trees[0].id) == [trees[0].id]
        assert ids(species=f"{genus} {species.name}".upper()) == [t.id for t in trees]
        assert ids(species="tree 1") == [trees[1].id]
        assert ids(family=family[:4].lower()) == [t.id for t in trees]
        assert ids(neighborhood=hood[:3]) == [t.id for t in trees]
        assert ids(health="SI") == [trees[1].id]
        assert ids(species="no such tree") == []

    def test_detail_has_every_measurement_and_observation(self, api_client, trees):
        response = api_client.get(reverse("biodiversity:inventory-detail", args=[trees[0].id]))

        assert response.status_code == status.HTTP_200_OK
        data = response.data
        heights = [m for m in data["measurements"] if m["attribute"] == "HT"]
        assert [h["value"] for h in heights] == [3.0, 1.0]  # newest first
        assert heights[0]["label"] == "total height"
        fields = {f["field"]: f for f in data["observations"][0]["fields"]}
        assert fields["phytosanitary_status"]["display"] == "healthy"

    def test_detail_language(self, api_client, trees):
        url = reverse("biodiversity:inventory-detail", args=[trees[0].id])

        def labels(params):
            data = api_client.get(url, params).data
            height = next(m for m in data["measurements"] if m["attribute"] == "HT")
            fields = {f["field"]: f for f in data["observations"][0]["fields"]}
            return height["label"], fields["phytosanitary_status"]["display"]

        assert labels({"lang": "es"}) == ("altura total", "saludable")
        assert labels({"lang": "en"}) == ("total height", "healthy")
        # Unsupported or missing: English.
        assert labels({"lang": "fr"}) == ("total height", "healthy")

    def test_detail_not_found(self, api_client):
        response = api_client.get(reverse("biodiversity:inventory-detail", args=[999999]))
        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_export_filtered_and_selected(self, api_client, trees):
        import csv
        import io

        url = reverse("biodiversity:inventory-export")

        def rows(response):
            assert response.status_code == status.HTTP_200_OK
            assert "attachment" in response["Content-Disposition"]
            text = b"".join(response.streaming_content).decode("utf-8-sig")
            return list(csv.DictReader(io.StringIO(text)))

        all_rows = rows(api_client.get(url))
        assert [int(r["id"]) for r in all_rows] == [t.id for t in trees]
        assert all_rows[1]["total_height_m"] == "12.0"
        assert all_rows[1]["phytosanitary_status"] == "sick"

        assert [r["id"] for r in rows(api_client.get(url, {"health": "HE"}))] == [str(trees[0].id)]

        selected = rows(api_client.post(url, {"ids": [trees[1].id]}, format="json"))
        assert [r["id"] for r in selected] == [str(trees[1].id)]

    def test_export_language(self, api_client, trees):
        import csv
        import io

        url = reverse("biodiversity:inventory-export")

        def statuses(response):
            text = b"".join(response.streaming_content).decode("utf-8-sig")
            reader = csv.DictReader(io.StringIO(text))
            # The header stays in English in every language.
            assert "phytosanitary_status" in reader.fieldnames
            return [r["phytosanitary_status"] for r in reader]

        assert statuses(api_client.get(url, {"lang": "es"})) == ["saludable", "enfermo"]
        assert statuses(api_client.get(url, {"lang": "en"})) == ["healthy", "sick"]
        selected = api_client.post(
            f"{url}?lang=es", {"ids": [trees[1].id]}, format="json"
        )
        assert statuses(selected) == ["enfermo"]

    def test_export_rejects_bad_ids(self, api_client):
        url = reverse("biodiversity:inventory-export")
        for body in ({}, {"ids": []}, {"ids": ["1"]}):
            assert api_client.post(url, body, format="json").status_code == 400

    def test_read_only(self, api_client, trees):
        url = reverse("biodiversity:inventory-detail", args=[trees[0].id])
        assert api_client.delete(url).status_code == status.HTTP_405_METHOD_NOT_ALLOWED
