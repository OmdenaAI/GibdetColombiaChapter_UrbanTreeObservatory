from django.contrib import admin

from .models import Country, Department, Municipality, Place


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


@admin.register(Place)
class PlaceAdmin(admin.ModelAdmin):
    list_display = ("name", "populated_center", "zone", "subzone", "locality")
    list_filter = ("locality", "zone", "subzone")
    search_fields = ("site", "populated_center", "locality__name")
    readonly_fields = ("id", "created_at", "updated_at")
    list_per_page = 25
