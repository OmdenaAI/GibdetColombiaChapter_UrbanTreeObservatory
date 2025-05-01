from rest_framework import serializers
from rest_framework_gis.serializers import GeoFeatureModelSerializer

from apps.places.serializers import MunicipalitySerializer

from .models import Climate, Station


class StationSerializer(serializers.ModelSerializer):
    """Serializer for the Station model."""

    longitude = serializers.FloatField(read_only=True)
    latitude = serializers.FloatField(read_only=True)
    municipality = MunicipalitySerializer(read_only=True)

    class Meta:
        model = Station
        fields = [
            "id",
            "code",
            "name",
            "location",
            "longitude",
            "latitude",
            "municipality",
        ]


class StationGeoSerializer(GeoFeatureModelSerializer):
    """GeoJSON serializer for the Station model."""

    class Meta:
        model = Station
        geo_field = "location"
        fields = ["id", "code", "name"]


class ClimateSerializer(serializers.ModelSerializer):
    """Serializer for the Climate model."""

    # For write operations and list views, just use the station ID
    station_id = serializers.PrimaryKeyRelatedField(
        source="station",
        queryset=Station.objects.all(),
        write_only=True,
        required=False,
    )

    # For read operations in detail views, provide the full station data
    station = serializers.SerializerMethodField()

    municipality = MunicipalitySerializer(source="station.municipality", read_only=True)
    sensor_display = serializers.CharField(source="get_sensor_display", read_only=True)
    measure_unit_display = serializers.CharField(
        source="get_measure_unit_display", read_only=True
    )

    def get_station(self, obj):
        """Return the station ID or full station object based on context."""
        # For list views, just return the ID
        if self.context.get("view") and self.context["view"].action == "list":
            return obj.station.id
        # For detail views, return the full station serialization
        return StationSerializer(obj.station).data

    class Meta:
        model = Climate
        fields = [
            "id",
            "uuid",
            "station",
            "station_id",
            "municipality",
            "date",
            "sensor",
            "sensor_display",
            "value",
            "measure_unit",
            "measure_unit_display",
            "created_at",
            "updated_at",
        ]
