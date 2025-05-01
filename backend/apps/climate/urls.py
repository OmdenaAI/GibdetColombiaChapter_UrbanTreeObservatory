from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import ClimateViewSet, StationViewSet

app_name = "climate"

router = DefaultRouter()
router.register(r"stations", StationViewSet, basename="station")
router.register(r"data", ClimateViewSet, basename="climate")

urlpatterns = [
    path("", include(router.urls)),
]
