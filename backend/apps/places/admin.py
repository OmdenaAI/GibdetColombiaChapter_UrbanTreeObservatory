from django.contrib import admin
from leaflet.admin import LeafletGeoAdmin

from .models import Country, Department, Locality, Municipality, Neighborhood, Site


# Use the standard LeafletGeoAdmin class for spatial models
@admin.register(Country)
class CountryAdmin(LeafletGeoAdmin):
    list_display = ("name",)
    search_fields = ("name",)
    readonly_fields = ("id",)
    settings_overrides = {
        "DEFAULT_CENTER": (4.4378, -75.2012),
        "DEFAULT_ZOOM": 5,
        "TILES": [
            (
                "OpenStreetMap",
                "https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png",
                {
                    "attribution": '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors',
                },
            )
        ],
    }


@admin.register(Department)
class DepartmentAdmin(LeafletGeoAdmin):
    list_display = ("name", "country")
    list_filter = ("country",)
    search_fields = ("name",)
    readonly_fields = ("id",)
    settings_overrides = {
        "DEFAULT_CENTER": (4.4378, -75.2012),
        "DEFAULT_ZOOM": 6,
        "TILES": [
            (
                "OpenStreetMap",
                "https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png",
                {
                    "attribution": '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors',
                },
            )
        ],
    }


@admin.register(Municipality)
class MunicipalityAdmin(LeafletGeoAdmin):
    list_display = ("name", "department")
    list_filter = ("department__country", "department")
    search_fields = ("name", "department__name")
    readonly_fields = ("id",)
    settings_overrides = {
        "DEFAULT_CENTER": (4.4378, -75.2012),
        "DEFAULT_ZOOM": 8,
        "TILES": [
            (
                "OpenStreetMap",
                "https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png",
                {
                    "attribution": '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors',
                },
            )
        ],
    }


@admin.register(Locality)
class LocalityAdmin(LeafletGeoAdmin):
    list_display = ("name", "municipality")
    list_filter = (
        "municipality__department__country",
        "municipality__department",
        "municipality",
    )
    search_fields = ("name", "municipality__name")
    readonly_fields = ("id", "created_at", "updated_at", "uuid")
    list_per_page = 25
    settings_overrides = {
        "DEFAULT_CENTER": (4.4378, -75.2012),
        "DEFAULT_ZOOM": 10,
        "TILES": [
            (
                "OpenStreetMap",
                "https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png",
                {
                    "attribution": '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors',
                },
            )
        ],
        "SCALE": "both",
        "RESET_VIEW": False,
    }


@admin.register(Neighborhood)
class NeighborhoodAdmin(LeafletGeoAdmin):
    list_display = ("name", "locality")
    list_filter = (
        "locality__municipality__department__country",
        "locality__municipality__department",
        "locality__municipality",
    )
    search_fields = ("name", "locality__name")
    readonly_fields = ("id", "created_at", "updated_at", "uuid")
    list_per_page = 25
    settings_overrides = {
        "DEFAULT_CENTER": (4.4378, -75.2012),
        "DEFAULT_ZOOM": 13,
        "TILES": [
            (
                "OpenStreetMap",
                "https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png",
                {
                    "attribution": '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors',
                },
            )
        ],
        "SCALE": "both",
        "RESET_VIEW": False,
    }


@admin.register(Site)
class SiteAdmin(admin.ModelAdmin):
    list_display = ("name", "zone", "subzone")
    list_filter = ("zone", "subzone")
    search_fields = ("name",)
    readonly_fields = ("id", "created_at", "updated_at")
    list_per_page = 25
