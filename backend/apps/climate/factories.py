import random

import factory
from django.contrib.gis.geos import Point
from factory.django import DjangoModelFactory

from apps.climate.models import Climate, Station
from apps.core.factories import BaseFactory
from apps.places.factories import MunicipalityFactory


class StationFactory(DjangoModelFactory):
    class Meta:
        model = Station
        django_get_or_create = ("code",)

    code = factory.Sequence(lambda n: n + 1000)  # Start from 1000
    name = factory.Sequence(lambda n: f"Weather Station {n}")

    # Generate a random point in Colombia (roughly)
    # Colombia bounds: ~(66°W to 79°W) and (~-4°S to 13°N)
    location = factory.LazyFunction(
        lambda: Point(
            random.uniform(-79.0, -66.0),  # longitude
            random.uniform(-4.0, 13.0),  # latitude
            srid=4326,
        )
    )

    municipality = factory.SubFactory(MunicipalityFactory)

    @factory.post_generation
    def set_location_for_specific_municipalities(self, create, extracted, **kwargs):
        """Set location coordinates appropriate for the municipality if needed.

        This is a hook for tests to ensure geographic consistency when required.
        Called automatically by the set_municipality parameter or can be used in fixtures.
        """
        if not create:
            return

        # Municipality locations can be added when specific tests need them
        municipality_bounds = {
            "Ibagué": {
                "lon_min": -75.3,
                "lon_max": -75.1,
                "lat_min": 4.35,
                "lat_max": 4.5,
            }
            # Add other municipalities as needed for tests
        }

        if self.municipality.name in municipality_bounds:
            bounds = municipality_bounds[self.municipality.name]
            self.location = Point(
                random.uniform(bounds["lon_min"], bounds["lon_max"]),
                random.uniform(bounds["lat_min"], bounds["lat_max"]),
                srid=4326,
            )
            self.save()


class ClimateFactory(BaseFactory):
    class Meta:
        model = Climate

    station = factory.SubFactory(StationFactory)
    date = factory.Faker("date_this_decade")
    sensor = factory.Iterator(
        [choice[0] for choice in Climate.SensorDescription.choices]
    )
    value = factory.Faker(
        "pyfloat", min_value=-5.0, max_value=40.0
    )  # Temperature range
    measure_unit = factory.Iterator(
        [choice[0] for choice in Climate.MeasureUnit.choices]
    )
