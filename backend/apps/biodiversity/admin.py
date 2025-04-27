from django.contrib import admin
from django.contrib.gis.admin import GISModelAdmin

from .models import BiodiversityRecord


@admin.register(BiodiversityRecord)
class BiodiversityRecordAdmin(GISModelAdmin):
    list_display = (
        "id",
        "common_name",
        "species_name",
        "site_name",
        "neighborhood_name",
        "date",
    )
    list_filter = ("date", "species__life_form", "neighborhood__locality")
    search_fields = (
        "common_name",
        "species__name",
        "species__genus__name",
        "site__name",
        "neighborhood__name",
        "neighborhood__locality__name",
    )
    raw_id_fields = ("species", "site", "neighborhood")
    readonly_fields = ("id", "created_at", "updated_at", "uuid")
    date_hierarchy = "date"
    list_per_page = 25

    @admin.display(description="Species")
    def species_name(self, obj):
        return f"{obj.species.genus.name} {obj.species.name}"

    @admin.display(description="Site")
    def site_name(self, obj):
        return obj.site.name

    @admin.display(description="Neighborhood")
    def neighborhood_name(self, obj):
        return obj.neighborhood.name
