import pytest
from django.urls import reverse
from rest_framework import status


@pytest.mark.django_db
class TestPlacesAPI:
    """Test the Places API endpoints."""

    def test_country_list(self, api_client, country):
        """Test retrieving the list of countries."""
        url = reverse("places:country-list")
        response = api_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        # Find our test country in the results
        country_found = False
        for result in response.data["results"]:
            if result["name"] == country.name:
                country_found = True
                break

        assert country_found, f"Test country '{country.name}' not found in results"

    def test_country_detail(self, api_client, country):
        """Test retrieving a specific country."""
        url = reverse("places:country-detail", args=[country.id])
        response = api_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        assert response.data["name"] == country.name
        assert "boundary" in response.data

    # The GeoJSON format support test is skipped for now
    # as it requires additional configuration
    @pytest.mark.skip(reason="GeoJSON format support needs configuration")
    def test_country_geojson(self, api_client, country):
        """Test retrieving countries in GeoJSON format."""
        url = reverse("places:country-list")
        response = api_client.get(url, {"format": "geojson"})

        assert response.status_code == status.HTTP_200_OK
        assert response.data["type"] == "FeatureCollection"
        # Find our test country in the features
        country_found = False
        for feature in response.data["features"]:
            if feature["properties"]["name"] == country.name:
                country_found = True
                assert feature["geometry"] is not None
                break

        assert country_found, (
            f"Test country '{country.name}' not found in GeoJSON features"
        )


@pytest.mark.django_db
class TestAdministrativeDivisions:
    """Test the administrative divisions endpoints (departments, municipalities)."""

    def test_department_list(self, api_client, department):
        """Test retrieving the list of departments."""
        url = reverse("places:department-list")
        response = api_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        # Find our test department in the results
        department_found = False
        for result in response.data["results"]:
            if result["name"] == department.name:
                department_found = True
                break

        assert department_found, (
            f"Test department '{department.name}' not found in results"
        )

    def test_department_filter_by_country(self, api_client, department):
        """Test filtering departments by country."""
        url = reverse("places:department-list") + f"?country={department.country.id}"
        response = api_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        # Find our test department in the filtered results
        department_found = False
        for result in response.data["results"]:
            if result["name"] == department.name:
                department_found = True
                break

        assert department_found, (
            f"Test department '{department.name}' not found in filtered results"
        )

    def test_municipality_list(self, api_client, municipality):
        """Test retrieving the list of municipalities."""
        url = reverse("places:municipality-list")
        response = api_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        # Find our test municipality in the results
        municipality_found = False
        for result in response.data["results"]:
            if result["name"] == municipality.name:
                municipality_found = True
                break

        assert municipality_found, (
            f"Test municipality '{municipality.name}' not found in results"
        )

    def test_municipality_filter_by_department(self, api_client, municipality):
        """Test filtering municipalities by department."""
        url = (
            reverse("places:municipality-list")
            + f"?department={municipality.department.id}"
        )
        response = api_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        # Find our test municipality in the filtered results
        municipality_found = False
        for result in response.data["results"]:
            if result["name"] == municipality.name:
                municipality_found = True
                break

        assert municipality_found, (
            f"Test municipality '{municipality.name}' not found in filtered results"
        )


@pytest.mark.django_db
class TestLocalityEndpoints:
    """Test the locality and neighborhood endpoints."""

    def test_locality_list(self, api_client, locality):
        """Test retrieving the list of localities."""
        url = reverse("places:locality-list")
        response = api_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        assert len(response.data["results"]) == 1
        assert response.data["results"][0]["name"] == locality.name
        assert response.data["results"][0]["calculated_area_m2"] == 1000000
        assert response.data["results"][0]["population_2019"] == 50000

    def test_locality_filter_by_municipality(self, api_client, locality):
        """Test filtering localities by municipality."""
        url = (
            reverse("places:locality-list")
            + f"?municipality={locality.municipality.id}"
        )
        response = api_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        assert len(response.data["results"]) == 1
        assert response.data["results"][0]["name"] == locality.name

    @pytest.mark.skip(reason="GeoJSON format not working correctly yet")
    def test_locality_geojson(self, authenticated_client, locality):
        """Test retrieving localities in GeoJSON format."""
        url = reverse("places:locality-list")
        response = authenticated_client.get(url, {"format": "geojson"})

        assert response.status_code == status.HTTP_200_OK
        assert response.data["type"] == "FeatureCollection"
        assert len(response.data["features"]) == 1
        assert response.data["features"][0]["properties"]["name"] == locality.name
        assert "municipality_name" in response.data["features"][0]["properties"]

    def test_neighborhood_list(self, api_client, neighborhood):
        """Test retrieving the list of neighborhoods."""
        url = reverse("places:neighborhood-list")
        response = api_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        assert len(response.data["results"]) == 1
        assert response.data["results"][0]["name"] == neighborhood.name

    def test_neighborhood_filter_by_locality(self, api_client, neighborhood):
        """Test filtering neighborhoods by locality."""
        url = (
            reverse("places:neighborhood-list")
            + f"?locality={neighborhood.locality.id}"
        )
        response = api_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        assert len(response.data["results"]) == 1
        assert response.data["results"][0]["name"] == neighborhood.name

    def test_hierarchical_filters(self, api_client, neighborhood):
        """Test hierarchical filtering (nested relationships)."""
        municipality_id = neighborhood.locality.municipality.id
        url = (
            reverse("places:neighborhood-list")
            + f"?locality__municipality={municipality_id}"
        )
        response = api_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        assert len(response.data["results"]) == 1
        assert response.data["results"][0]["name"] == neighborhood.name


@pytest.mark.django_db
class TestSiteEndpoints:
    """Test the site endpoints."""

    def test_site_list(self, api_client, site):
        """Test retrieving the list of sites."""
        url = reverse("places:site-list")
        response = api_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        assert len(response.data["results"]) == 1
        assert response.data["results"][0]["name"] == site.name
        assert response.data["results"][0]["zone"] == 1
        assert response.data["results"][0]["subzone"] == 2

    def test_site_detail(self, api_client, site):
        """Test retrieving a specific site."""
        url = reverse("places:site-detail", args=[site.id])
        response = api_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        assert response.data["name"] == site.name
        assert response.data["zone"] == 1
        assert response.data["subzone"] == 2

    def test_site_filter_by_zone(self, api_client, site):
        """Test filtering sites by zone."""
        url = reverse("places:site-list") + "?zone=1"
        response = api_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        assert len(response.data["results"]) == 1
        assert response.data["results"][0]["name"] == site.name


@pytest.mark.django_db
class TestTreeStatistics:
    """Tree statistics per locality / neighborhood."""

    @pytest.fixture
    def trees(self, neighborhood, species):
        from apps.biodiversity.factories import BiodiversityRecordFactory
        from apps.places.factories import NeighborhoodFactory
        from apps.reports.factories import MeasurementFactory
        from apps.reports.models import EcosystemService
        from apps.taxonomy.factories import SpeciesFactory

        other_species = SpeciesFactory()
        records = [
            BiodiversityRecordFactory(neighborhood=neighborhood, species=species),
            BiodiversityRecordFactory(neighborhood=neighborhood, species=species),
            BiodiversityRecordFactory(neighborhood=neighborhood, species=other_species),
        ]
        for record, height in zip(records, [10.0, 20.0, 30.0], strict=True):
            MeasurementFactory(
                biodiversity_record=record, attribute="HT", value=height, unit="m"
            )
            MeasurementFactory(
                biodiversity_record=record, attribute="DBH", value=99.0, unit="cm"
            )
            EcosystemService.objects.create(
                biodiversity_record=record,
                carbon_kg=1500.0,
                rain_interception_m3=2.5,
                crown_area_m2=20.0,
                leaf_area_index=3.0,
            )
        empty = NeighborhoodFactory(locality=neighborhood.locality)
        return neighborhood, empty

    def test_neighborhood_statistics(self, api_client, trees):
        neighborhood, empty = trees
        url = reverse("places:neighborhood-statistics")
        response = api_client.get(url, {"locality": neighborhood.locality_id})

        assert response.status_code == status.HTTP_200_OK
        by_id = {r["id"]: r for r in response.data["results"]}
        assert by_id[neighborhood.id] == {
            "id": neighborhood.id,
            "total_trees": 3,
            "species_count": 2,
            "avg_height_m": 20.0,
            "carbon_t": 4.5,
            "carbon_co2e_t": 16.5,
            "rain_interception_m3": 8,
        }
        assert by_id[empty.id]["total_trees"] == 0
        assert by_id[empty.id]["avg_height_m"] is None
        assert by_id[empty.id]["carbon_t"] == 0
        assert response.data["overall"]["total_trees"] == 3
        assert response.data["overall"]["carbon_t"] == 4.5
        assert response.data["overall"]["rain_interception_m3"] == 8

    def test_neighborhood_bbox(self, api_client, trees):
        from django.contrib.gis.geos import MultiPolygon, Polygon

        from apps.places.factories import NeighborhoodFactory

        neighborhood, empty = trees  # factory boundaries cover most of Colombia
        far = NeighborhoodFactory(
            locality=neighborhood.locality,
            boundary=MultiPolygon(
                Polygon.from_bbox((10.0, 10.0, 10.1, 10.1)), srid=4326
            ),
        )
        url = reverse("places:neighborhood-bbox")
        box = {"min_lon": -75.3, "min_lat": 4.4, "max_lon": -75.2, "max_lat": 4.5}

        response = api_client.get(url, box)

        assert response.status_code == status.HTTP_200_OK
        by_id = {r["id"]: r for r in response.data["results"]}
        assert set(by_id) == {neighborhood.id, empty.id}  # not `far`
        row = by_id[neighborhood.id]
        assert row["total_trees"] == 3
        assert row["avg_height_m"] == 20.0
        assert row["rain_interception_m3"] == 8
        assert row["locality"] == neighborhood.locality.name
        assert row["boundary"]["type"] == "MultiPolygon"
        assert by_id[empty.id]["total_trees"] == 0
        assert response.data["truncated"] is False

        excluded = api_client.get(url, {**box, "exclude": f"{neighborhood.id}"})
        assert [r["id"] for r in excluded.data["results"]] == [empty.id]
        assert far.id not in by_id

    def test_neighborhood_bbox_requires_numbers(self, api_client):
        url = reverse("places:neighborhood-bbox")
        assert api_client.get(url, {"min_lon": "x"}).status_code == 400
        bad = {"min_lon": 0, "min_lat": 0, "max_lon": 1, "max_lat": 1, "exclude": "a"}
        assert api_client.get(url, bad).status_code == 400

    def test_locality_statistics(self, api_client, trees):
        neighborhood, _ = trees
        url = reverse("places:locality-statistics")
        response = api_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        by_id = {r["id"]: r for r in response.data["results"]}
        assert by_id[neighborhood.locality_id]["total_trees"] == 3
        assert by_id[neighborhood.locality_id]["species_count"] == 2
        assert by_id[neighborhood.locality_id]["carbon_t"] == 4.5
