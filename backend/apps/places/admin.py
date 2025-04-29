from django.contrib import admin

from .models import Country, Department, Municipality, Locality, Neighborhood, Site


@admin.register(Country)
class CountryAdmin(admin.ModelAdmin):
    list_display = ("name",)
    search_fields = ("name",)
    readonly_fields = ("id",)


@admin.register(Department)
class DepartmentAdmin(admin.ModelAdmin):
    list_display = ("name", "country")
    list_filter = ("country",)
    search_fields = ("name",)
    readonly_fields = ("id",)


@admin.register(Municipality)
class MunicipalityAdmin(admin.ModelAdmin):
    list_display = ("name", "department")
    list_filter = ("department__country", "department")
    search_fields = ("name", "department__name")
    readonly_fields = ("id",)


@admin.register(Locality)
class LocalityAdmin(admin.ModelAdmin):
    list_display = ("name", "municipality")
    list_filter = (
        "municipality__department__country",
        "municipality__department",
        "municipality",
    )
    search_fields = ("name", "municipality__name")
    readonly_fields = ("id", "created_at", "updated_at", "uuid")
    list_per_page = 25


@admin.register(Neighborhood)
class NeighborhoodAdmin(admin.ModelAdmin):
    list_display = ("name", "locality")
    list_filter = (
        "locality__municipality__department__country",
        "locality__municipality__department",
        "locality__municipality",
    )
    search_fields = ("name", "locality__name")
    readonly_fields = ("id", "created_at", "updated_at", "uuid")
    list_per_page = 25


@admin.register(Site)
class SiteAdmin(admin.ModelAdmin):
    list_display = ("name", "zone", "subzone")
    list_filter = ("zone", "subzone")
    search_fields = ("name",)
    readonly_fields = ("id", "created_at", "updated_at")
    list_per_page = 25
