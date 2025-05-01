from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import MeasurementViewSet, ObservationViewSet

app_name = "reports"

router = DefaultRouter()
router.register(r"measurements", MeasurementViewSet, basename="measurement")
router.register(r"observations", ObservationViewSet, basename="observation")

urlpatterns = [
    path("", include(router.urls)),
]
