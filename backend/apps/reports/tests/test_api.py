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


@pytest.mark.django_db
class TestDashboardAPI:
    """GET /api/v1/reports/dashboard/ aggregates census, taxonomy and climate data."""

    def test_dashboard_summary(self, api_client, neighborhood, species):
        import datetime

        from apps.biodiversity.factories import BiodiversityRecordFactory
        from apps.climate.factories import ClimateFactory
        from apps.reports.factories import MeasurementFactory, ObservationFactory

        neighborhood.locality.population_2019 = 100
        neighborhood.locality.save()
        for i, (height, status_code) in enumerate([(3.0, "HE"), (12.0, "HE"), (30.0, "SI")]):
            record = BiodiversityRecordFactory(
                neighborhood=neighborhood,
                species=species,
                date=datetime.date(2017, 1, 1 + i),
            )
            MeasurementFactory(biodiversity_record=record, attribute="HT", value=height, unit="m")
            ObservationFactory(biodiversity_record=record, phytosanitary_status=status_code)
        BiodiversityRecordFactory(neighborhood=neighborhood, species=species, date=datetime.date(1899, 1, 1))
        ClimateFactory(date=datetime.date(2025, 4, 1), value=20.0)

        response = api_client.get(reverse("reports:dashboard"))

        assert response.status_code == status.HTTP_200_OK
        data = response.data
        assert data["overall"]["total_trees"] == 4
        assert data["trees_per_capita"] == {"population": 100, "value": 0.04}
        assert data["phytosanitary_status"] == {"HE": 2, "SI": 1}
        assert data["top_species"][0]["count"] == 4
        assert data["records_by_year"] == {"years": [{"year": 2017, "count": 3}], "invalid_dates": 1}
        bins = {b["from_m"]: b["count"] for b in data["height_distribution"]}
        assert (bins[0], bins[10], bins[25]) == (1, 1, 1)
        temperature = data["monthly_temperature"]
        assert temperature["months"] == ["2025-04"]
        assert [s["values"] for s in temperature["stations"]] == [[20.0]]
        assert data["recent_records"][0]["height_m"] == 30.0
        assert data["recent_records"][0]["phytosanitary_status"] == "SI"


@pytest.mark.django_db
class TestAnalyticsAPI:
    """GET /api/v1/reports/analytics/: urban forest indicators."""

    def test_analytics_summary(self, api_client, neighborhood, genus):
        import datetime

        from django.core.cache import cache

        from apps.biodiversity.factories import BiodiversityRecordFactory
        from apps.reports.factories import MeasurementFactory, ObservationFactory
        from apps.taxonomy.factories import SpeciesFactory

        cache.clear()
        neighborhood.locality.population_2019 = 1000
        neighborhood.locality.save()
        native = SpeciesFactory(genus=genus, name="nativa", origin="NT", life_form="TR", iucn_status="VU")
        exotic = SpeciesFactory(genus=genus, name="exotica", origin="CU", life_form="TR", iucn_status="LC")
        # 3 native trees (one sick), 1 introduced; DBH 5, 15, 25, 90 cm.
        for species, dbh, health in [
            (native, 5.0, "HE"),
            (native, 15.0, "SI"),
            (native, 25.0, "HE"),
            (exotic, 90.0, "HE"),
        ]:
            record = BiodiversityRecordFactory(
                neighborhood=neighborhood, species=species, date=datetime.date(2017, 1, 1)
            )
            MeasurementFactory(biodiversity_record=record, attribute="DBH", value=dbh, unit="cm")
            ObservationFactory(biodiversity_record=record, phytosanitary_status=health)

        response = api_client.get(reverse("reports:analytics"))

        assert response.status_code == status.HTTP_200_OK
        data = response.data
        assert data["total_trees"] == 4
        assert data["trees_per_1000_inhabitants"] == 4
        assert data["native_percent"] == 75.0
        assert data["issues_percent"] == 25.0
        rule = {r["level"]: r for r in data["concentration"]["rule"]}
        assert rule["species"]["percent"] == 75.0
        assert rule["species"]["limit"] == 10
        assert rule["genus"]["percent"] == 100.0
        classes = {c["from_cm"]: c["count"] for c in data["dbh_classes"]["classes"]}
        assert (classes[0], classes[10], classes[20], classes[80]) == (1, 1, 1, 1)
        # The factory boundaries contain the factory points: every tree is placed.
        comunas = data["comunas"]
        assert sum(c["trees"] for c in comunas["results"]) == 4
        assert comunas["outside_comunas"] == 0
        health = {s["name"]: s for s in data["species_health"]}
        assert health[native.scientific_name]["sick_percent"] == 33.3
        threatened = data["threatened"]
        assert {s["status"]: s["count"] for s in threatened["by_status"]}["VU"] == 3
        cache.clear()
