import random

import factory
from django.contrib.gis.geos import Point

from apps.biodiversity.models import BiodiversityRecord
from apps.core.factories import BaseFactory
from apps.places.factories import NeighborhoodFactory, SiteFactory
from apps.taxonomy.factories import SpeciesFactory


class BiodiversityRecordFactory(BaseFactory):
    class Meta:
        model = BiodiversityRecord

    common_name = factory.Faker("word")
    species = factory.SubFactory(SpeciesFactory)
    site = factory.SubFactory(SiteFactory)
    neighborhood = factory.SubFactory(NeighborhoodFactory)

    # Generate a random point in Colombia (roughly)
    # Colombia bounds: ~(66°W to 79°W) and (~-4°S to 13°N)
    # We use longitude, latitude order for Point
    location = factory.LazyFunction(
        lambda: Point(
            random.uniform(-79.0, -66.0),  # longitude
            random.uniform(-4.0, 13.0),  # latitude
            srid=4326,
        )
    )

    # Default values
    elevation_m = factory.Faker("pyfloat", min_value=0, max_value=4000)
    recorded_by = factory.Faker("name")
    date = factory.Faker("date_this_decade")
