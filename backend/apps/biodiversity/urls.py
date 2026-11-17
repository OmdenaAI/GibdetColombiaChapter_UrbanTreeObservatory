from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .inventory import InventoryViewSet
from .views import BiodiversityRecordViewSet

app_name = "biodiversity"

router = DefaultRouter()
router.register(r"records", BiodiversityRecordViewSet, basename="biodiversity-record")
router.register(r"inventory", InventoryViewSet, basename="inventory")

urlpatterns = [
    path("", include(router.urls)),
]
