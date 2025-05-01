from django.urls import include, path

urlpatterns = [
    path("taxonomy/", include("apps.taxonomy.urls")),
    path("places/", include("apps.places.urls")),
    path("biodiversity/", include("apps.biodiversity.urls")),
    path("reports/", include("apps.reports.urls")),
    path("climate/", include("apps.climate.urls")),
]
