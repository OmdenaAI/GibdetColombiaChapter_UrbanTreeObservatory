from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import (
    FamilyViewSet,
    FunctionalGroupViewSet,
    GenusViewSet,
    SpeciesViewSet,
    TraitViewSet,
)

app_name = "taxonomy"

router = DefaultRouter()
router.register(r"families", FamilyViewSet, basename="family")
router.register(r"genera", GenusViewSet, basename="genus")
router.register(r"species", SpeciesViewSet, basename="species")
router.register(
    r"functional-groups", FunctionalGroupViewSet, basename="functional-group"
)
router.register(r"traits", TraitViewSet, basename="trait")

urlpatterns = [
    path("", include(router.urls)),
]
