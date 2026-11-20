from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import (
    AnalyticsView,
    DashboardView,
    MeasurementViewSet,
    ObservationViewSet,
    UploadViewSet,
)

app_name = "reports"

router = DefaultRouter()
router.register(r"measurements", MeasurementViewSet, basename="measurement")
router.register(r"observations", ObservationViewSet, basename="observation")
router.register(r"uploads", UploadViewSet, basename="upload")

urlpatterns = [
    path("dashboard/", DashboardView.as_view(), name="dashboard"),
    path("analytics/", AnalyticsView.as_view(), name="analytics"),
    path("", include(router.urls)),
]
