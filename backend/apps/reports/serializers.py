from rest_framework import serializers

from apps.biodiversity.models import BiodiversityRecord
from apps.biodiversity.serializers import BiodiversityRecordLightSerializer

from .models import Measurement, Observation


class MeasurementSerializer(serializers.ModelSerializer):
    """Serializer for the Measurement model."""

    # Use SerializerMethodField instead of direct relation to control output format
    biodiversity_record = serializers.SerializerMethodField()

    biodiversity_record_id = serializers.PrimaryKeyRelatedField(
        write_only=True,
        source="biodiversity_record",
        queryset=BiodiversityRecord.objects.all(),
    )

    attribute_display = serializers.CharField(
        source="get_attribute_display", read_only=True
    )
    unit_display = serializers.CharField(source="get_unit_display", read_only=True)
    method_display = serializers.CharField(source="get_method_display", read_only=True)

    def get_biodiversity_record(self, obj):
        """Return the biodiversity_record ID or full object based on context."""
        # For list views, just return the ID
        if self.context.get("view") and self.context["view"].action == "list":
            return obj.biodiversity_record.id
        # For detail views, return the full serialization
        return BiodiversityRecordLightSerializer(obj.biodiversity_record).data

    class Meta:
        model = Measurement
        fields = [
            "id",
            "uuid",
            "biodiversity_record",
            "biodiversity_record_id",
            "attribute",
            "attribute_display",
            "value",
            "unit",
            "unit_display",
            "method",
            "method_display",
            "date",
            "created_at",
            "updated_at",
        ]


class ObservationSerializer(serializers.ModelSerializer):
    """Serializer for the Observation model."""

    # Use SerializerMethodField instead of direct relation to control output format
    biodiversity_record = serializers.SerializerMethodField()

    biodiversity_record_id = serializers.PrimaryKeyRelatedField(
        write_only=True,
        source="biodiversity_record",
        queryset=BiodiversityRecord.objects.all(),
    )

    # Display fields for choice fields
    reproductive_condition_display = serializers.CharField(
        source="get_reproductive_condition_display", read_only=True
    )
    phytosanitary_status_display = serializers.CharField(
        source="get_phytosanitary_status_display", read_only=True
    )
    physical_condition_display = serializers.CharField(
        source="get_physical_condition_display", read_only=True
    )
    foliage_density_display = serializers.CharField(
        source="get_foliage_density_display", read_only=True
    )
    aesthetic_value_display = serializers.CharField(
        source="get_aesthetic_value_display", read_only=True
    )
    growth_phase_display = serializers.CharField(
        source="get_growth_phase_display", read_only=True
    )
    standing_display = serializers.CharField(
        source="get_standing_display", read_only=True
    )

    def get_biodiversity_record(self, obj):
        """Return the biodiversity_record ID or full object based on context."""
        # For list views, just return the ID
        if self.context.get("view") and self.context["view"].action == "list":
            return obj.biodiversity_record.id
        # For detail views, return the full serialization
        return BiodiversityRecordLightSerializer(obj.biodiversity_record).data

    class Meta:
        model = Observation
        fields = [
            "id",
            "uuid",
            "biodiversity_record",
            "biodiversity_record_id",
            "reproductive_condition",
            "reproductive_condition_display",
            "phytosanitary_status",
            "phytosanitary_status_display",
            "physical_condition",
            "physical_condition_display",
            "foliage_density",
            "foliage_density_display",
            "aesthetic_value",
            "aesthetic_value_display",
            "growth_phase",
            "growth_phase_display",
            "standing",
            "standing_display",
            "field_notes",
            "photo_url",
            "recorded_by",
            "accompanying_collectors",
            "date",
            "created_at",
            "updated_at",
            # Including the coded fields
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
        ]
