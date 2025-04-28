from django.contrib import admin

from .models import Country, Department, Municipality, Site


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


@admin.register(Site)
class SiteAdmin(admin.ModelAdmin):
    list_display = ("name", "zone", "subzone")
    list_filter = ("zone", "subzone")
    search_fields = ("name",)
    readonly_fields = ("id", "created_at", "updated_at")
    list_per_page = 25
