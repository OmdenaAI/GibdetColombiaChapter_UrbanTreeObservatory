import pytest
from rest_framework.test import APIClient

from apps.places.factories import (
    CountryFactory,
    DepartmentFactory,
    MunicipalityFactory,
    LocalityFactory,
    NeighborhoodFactory,
    SiteFactory,
)
from apps.taxonomy.factories import (
    FamilyFactory,
    GenusFactory,
    SpeciesFactory,
    FunctionalGroupFactory,
)
from apps.biodiversity.factories import BiodiversityRecordFactory
from apps.reports.factories import MeasurementFactory, ObservationFactory
from apps.climate.factories import StationFactory, ClimateFactory
from apps.users.factories import UserFactory, StaffUserFactory, SuperUserFactory


@pytest.fixture
def api_client():
    """Return an API client for testing API views."""
    return APIClient()


@pytest.fixture
def user():
    """Return a regular user."""
    return UserFactory()


@pytest.fixture
def staff_user():
    """Return a staff user."""
    return StaffUserFactory()


@pytest.fixture
def admin_user():
    """Return a superuser/admin."""
    return SuperUserFactory()


@pytest.fixture
def authenticated_client(user):
    """Return an authenticated API client."""
    client = APIClient()
    client.force_authenticate(user=user)
    return client


@pytest.fixture
def staff_client(staff_user):
    """Return an authenticated API client with staff privileges."""
    client = APIClient()
    client.force_authenticate(user=staff_user)
    return client


@pytest.fixture
def admin_client(admin_user):
    """Return an authenticated API client with admin privileges."""
    client = APIClient()
    client.force_authenticate(user=admin_user)
    return client


@pytest.fixture
def country():
    """Create a country for testing."""
    return CountryFactory(name="Test Country")


@pytest.fixture
def department(country):
    """Create a department for testing."""
    return DepartmentFactory(name="Test Department", country=country)


@pytest.fixture
def municipality(department):
    """Create a municipality for testing."""
    return MunicipalityFactory(name="Test Municipality", department=department)


@pytest.fixture
def locality(municipality):
    """Create a locality for testing."""
    return LocalityFactory(
        name="Test Locality",
        municipality=municipality,
        calculated_area_m2=1000000,
        population_2019=50000,
    )


@pytest.fixture
def neighborhood(locality):
    """Create a neighborhood for testing."""
    return NeighborhoodFactory(name="Test Neighborhood", locality=locality)


@pytest.fixture
def site(locality):
    """Create a site for testing."""
    return SiteFactory(
        name="Test Site",
        locality=locality,
        zone=1,
        subzone=2,
    )


@pytest.fixture
def family():
    """Create a family for testing."""
    return FamilyFactory(name="Test Family")


@pytest.fixture
def genus(family):
    """Create a genus for testing."""
    return GenusFactory(name="Test Genus", family=family)


@pytest.fixture
def traits():
    """Create all four trait types."""
    from apps.taxonomy.models import Trait

    traits = []
    for trait_type in [
        "CS",  # Carbon sequestration
        "SH",  # Shade index
        "CY",  # Canopy diameter
        "HX",  # Max height
    ]:
        trait, _ = Trait.objects.get_or_create(type=trait_type)
        traits.append(trait)
    return traits


@pytest.fixture
def functional_group(traits):
    """Create a functional group with traits."""
    return FunctionalGroupFactory(traits=traits)


@pytest.fixture
def species(genus, functional_group):
    """Create a species for testing."""
    return SpeciesFactory(
        genus=genus,
        name="testspecies",
        functional_group=functional_group,
        life_form="TR",  # Tree
    )


@pytest.fixture
def biodiversity_record(species, site, neighborhood):
    """Create a biodiversity record for testing."""
    return BiodiversityRecordFactory(
        common_name="Test Tree", species=species, site=site, neighborhood=neighborhood
    )


@pytest.fixture
def measurement(biodiversity_record):
    """Create a measurement for testing."""
    return MeasurementFactory(
        biodiversity_record=biodiversity_record,
        attribute="TH",  # Trunk height
        value=10.5,
        unit="m",  # meters
    )


@pytest.fixture
def observation(biodiversity_record):
    """Create an observation for testing."""
    return ObservationFactory(
        biodiversity_record=biodiversity_record,
        phytosanitary_status="HE",  # Healthy
        physical_condition="GO",  # Good
    )


@pytest.fixture
def station(municipality):
    """Create a weather station for testing."""
    return StationFactory(code=1001, name="Test Station", municipality=municipality)


@pytest.fixture
def climate_record(station):
    """Create a climate record for testing."""
    return ClimateFactory(
        station=station,
        sensor="t2m",  # Air temperature at 2m
        value=25.5,
        measure_unit="°C",  # Celsius
    )
