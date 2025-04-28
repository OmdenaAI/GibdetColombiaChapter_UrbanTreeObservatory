import factory
from factory.django import DjangoModelFactory
from django.contrib.gis.geos import MultiPolygon, Polygon
from .models import Country, Department, Municipality, Locality, Neighborhood, Site
from apps.core.factories import BaseFactory


class CountryFactory(DjangoModelFactory):
    class Meta:
        model = Country
        django_get_or_create = ("name",)

    name = factory.Sequence(lambda n: f"Country {n}")

    # Generate a simple polygon for the country boundary
    # Colombia bounds: ~(66°W to 79°W) and (~-4°S to 13°N)
    # We use longitude, latitude order for MultiPolygon
    boundary = factory.LazyFunction(
        lambda: MultiPolygon(
            [
                Polygon(
                    (
                        (-79.0, -4.5),
                        (-66.0, -4.5),
                        (-66.0, 13.0),
                        (-79.0, 13.0),
                        (-79.0, -4.5),
                    )
                )
            ]
        )
    )


class DepartmentFactory(DjangoModelFactory):
    class Meta:
        model = Department
        django_get_or_create = ("name", "country")

    name = factory.Sequence(lambda n: f"Department {n}")
    country = factory.SubFactory(CountryFactory)

    # TODO: Add a realistic boundary for Tolima
    boundary = factory.LazyFunction(
        lambda: MultiPolygon(
            [
                Polygon(
                    (
                        (-79.0, -4.5),
                        (-66.0, -4.5),
                        (-66.0, 13.0),
                        (-79.0, 13.0),
                        (-79.0, -4.5),
                    )
                )
            ]
        )
    )


class MunicipalityFactory(DjangoModelFactory):
    class Meta:
        model = Municipality
        django_get_or_create = ("name", "department")

    name = factory.Sequence(lambda n: f"Municipality {n}")
    department = factory.SubFactory(DepartmentFactory)

    # TODO: Add a realistic boundary for Ibagué
    boundary = factory.LazyFunction(
        lambda: MultiPolygon(
            [
                Polygon(
                    (
                        (-79.0, -4.5),
                        (-66.0, -4.5),
                        (-66.0, 13.0),
                        (-79.0, 13.0),
                        (-79.0, -4.5),
                    )
                )
            ]
        )
    )


class LocalityFactory(DjangoModelFactory):
    class Meta:
        model = Locality
        django_get_or_create = ("name", "municipality")

    name = factory.Sequence(lambda n: f"Locality {n}")
    municipality = factory.SubFactory(MunicipalityFactory)

    # TODO: Add a realistic boundary for a locality in Ibagué
    boundary = factory.LazyFunction(
        lambda: MultiPolygon(
            [
                Polygon(
                    (
                        (-79.0, -4.5),
                        (-66.0, -4.5),
                        (-66.0, 13.0),
                        (-79.0, 13.0),
                        (-79.0, -4.5),
                    )
                )
            ]
        )
    )

    # Optional fields with default values
    calculated_area_m2 = factory.Faker("pyfloat", min_value=0, max_value=10000)
    population_2019 = factory.Faker("random_int", min=10000, max=100000)


class NeighborhoodFactory(DjangoModelFactory):
    class Meta:
        model = Neighborhood
        django_get_or_create = ("name", "locality")

    name = factory.Sequence(lambda n: f"Neighborhood {n}")
    locality = factory.SubFactory(LocalityFactory)

    # TODO: Add a realistic boundary for the neighborhood
    boundary = factory.LazyFunction(
        lambda: MultiPolygon(
            [
                Polygon(
                    (
                        (-79.0, -4.5),
                        (-66.0, -4.5),
                        (-66.0, 13.0),
                        (-79.0, 13.0),
                        (-79.0, -4.5),
                    )
                )
            ]
        )
    )


class SiteFactory(BaseFactory):
    class Meta:
        model = Site

    name = factory.Sequence(lambda n: f"Site {n}")
    zone = factory.Faker("random_int", min=1, max=10)
    subzone = factory.Faker("random_int", min=1, max=5)
