from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import BiodiversityRecordViewSet

app_name = "biodiversity"

router = DefaultRouter()
router.register(r"records", BiodiversityRecordViewSet, basename="biodiversity-record")

urlpatterns = [
    path("", include(router.urls)),
]
