import uuid

import factory
from django.utils.timezone import now as timezone_now


class BaseFactory(factory.django.DjangoModelFactory):
    """Base factory for models inheriting from BaseModel."""

    uuid = factory.LazyFunction(uuid.uuid4)
    created_at = factory.LazyFunction(timezone_now)
    updated_at = factory.LazyFunction(timezone_now)
