from django.contrib import admin
from django.utils.html import format_html

from .models import Measurement, Observation


@admin.register(Measurement)
class MeasurementAdmin(admin.ModelAdmin):
    def get_queryset(self, request):
        # Also the rows of removed trees (the default manager hides them).
        return Measurement.all_objects.select_related("biodiversity_record")

    list_display = (
        "id",
        "biodiversity_record_display",
        "attribute_display",
        "measurement",
        "date",
    )
    list_filter = ("attribute", "unit", "method", "date")
    search_fields = ("biodiversity_record__id", "biodiversity_record__common_name")
    raw_id_fields = ("biodiversity_record",)
    readonly_fields = ("created_at", "updated_at")
    date_hierarchy = "date"
    list_per_page = 25

    @admin.display(description="Bio Record")
    def biodiversity_record_display(self, obj):
        url = obj.biodiversity_record.get_admin_url()
        return format_html(
            '<a href="{}">Record #{}</a>', url, obj.biodiversity_record_id
        )

    @admin.display(description="Attribute")
    def attribute_display(self, obj):
        return obj.get_attribute_display()

    @admin.display(description="Measurement")
    def measurement(self, obj):
        return f"{obj.value} {obj.unit}"


@admin.register(Observation)
class ObservationAdmin(admin.ModelAdmin):
    def get_queryset(self, request):
        # Also the rows of removed trees (the default manager hides them).
        return Observation.all_objects.select_related("biodiversity_record")

    list_display = (
        "id",
        "biodiversity_record_display",
        "phytosanitary_status_display",
        "growth_phase_display",
        "date",
    )
    list_filter = (
        "phytosanitary_status",
        "physical_condition",
        "foliage_density",
        "aesthetic_value",
        "growth_phase",
    )
    search_fields = (
        "biodiversity_record__id",
        "biodiversity_record__common_name",
        "field_notes",
    )
    raw_id_fields = ("biodiversity_record",)
    readonly_fields = ("created_at", "updated_at")
    date_hierarchy = "date"
    list_per_page = 25
    fieldsets = (
        (
            "Basic Information",
            {
                "fields": (
                    "biodiversity_record",
                    "date",
                    "recorded_by",
                    "accompanying_collectors",
                    "photo_url",
                )
            },
        ),
        (
            "Tree Condition",
            {
                "fields": (
                    "reproductive_condition",
                    "phytosanitary_status",
                    "physical_condition",
                    "foliage_density",
                    "aesthetic_value",
                    "growth_phase",
                    "standing",
                )
            },
        ),
        (
            "Technical Measurements",
            {
                "classes": ("collapse",),
                "fields": (
                    "ed",
                    "hc",
                    "hcf",
                    "cre",
                    "crh",
                    "cra",
                    "coa",
                    "ce",
                    "civ",
                    "crt",
                    "crg",
                    "cap",
                ),
            },
        ),
        (
            "Damage Assessment",
            {
                "classes": ("collapse",),
                "fields": (
                    "rd",
                    "dm",
                    "bbs",
                    "ab",
                    "pi",
                    "ph",
                    "pa",
                    "pd",
                    "pe",
                    "pp",
                    "po",
                    "r_vol",
                    "r_cr",
                    "r_ce",
                ),
            },
        ),
        ("Notes", {"fields": ("field_notes",)}),
    )

    @admin.display(description="Bio Record")
    def biodiversity_record_display(self, obj):
        url = obj.biodiversity_record.get_admin_url()
        return format_html(
            '<a href="{}">Record #{}</a>', url, obj.biodiversity_record_id
        )

    @admin.display(description="Health Status")
    def phytosanitary_status_display(self, obj):
        return obj.get_phytosanitary_status_display()

    @admin.display(description="Growth Phase")
    def growth_phase_display(self, obj):
        return obj.get_growth_phase_display()
