from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import (
    CountryViewSet,
    DepartmentViewSet,
    LocalityViewSet,
    MunicipalityViewSet,
    NeighborhoodViewSet,
    SiteViewSet,
)

app_name = "places"

router = DefaultRouter()
router.register(r"countries", CountryViewSet, basename="country")
router.register(r"departments", DepartmentViewSet, basename="department")
router.register(r"municipalities", MunicipalityViewSet, basename="municipality")
router.register(r"localities", LocalityViewSet, basename="locality")
router.register(r"neighborhoods", NeighborhoodViewSet, basename="neighborhood")
router.register(r"sites", SiteViewSet, basename="site")

urlpatterns = [
    path("", include(router.urls)),
]
