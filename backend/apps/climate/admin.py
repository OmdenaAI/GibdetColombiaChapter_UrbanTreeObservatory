from django.contrib import admin
from django.contrib.gis.admin import GISModelAdmin

from .models import Station, Climate


@admin.register(Station)
class StationAdmin(GISModelAdmin):
    list_display = ("code", "name")
    search_fields = ("name", "code")
    raw_id_fields = ("municipality",)
    readonly_fields = ("id",)


@admin.register(Climate)
class ClimateAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "station",
        "station_municipality",
        "date",
        "sensor_display",
        "measurement",
    )
    list_filter = ("station", "station__municipality", "sensor", "measure_unit", "date")
    search_fields = ("station__name", "station__code")
    raw_id_fields = ("station",)
    readonly_fields = ("created_at", "updated_at")
    date_hierarchy = "date"
    list_per_page = 25

    @admin.display(description="Municipality")
    def station_municipality(self, obj):
        return obj.station.municipality

    @admin.display(description="Sensor")
    def sensor_display(self, obj):
        return obj.get_sensor_display()

    @admin.display(description="Value")
    def measurement(self, obj):
        return f"{obj.value} {obj.measure_unit}"
