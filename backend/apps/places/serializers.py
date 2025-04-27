from rest_framework import serializers
from .models import Country, Department, Municipality, Site


class CountrySerializer(serializers.ModelSerializer):
    """Serializer for the Country model."""

    class Meta:
        model = Country
        fields = ["id", "name"]


class DepartmentSerializer(serializers.ModelSerializer):
    """Serializer for the Department model."""

    country = CountrySerializer(read_only=True)
    country_id = serializers.PrimaryKeyRelatedField(
        queryset=Country.objects.all(), source="country", write_only=True
    )

    class Meta:
        model = Department
        fields = ["id", "name", "country", "country_id"]


class MunicipalitySerializer(serializers.ModelSerializer):
    """Serializer for the Municipality model."""

    department = DepartmentSerializer(read_only=True)
    department_id = serializers.PrimaryKeyRelatedField(
        queryset=Department.objects.all(), source="department", write_only=True
    )

    class Meta:
        model = Municipality
        fields = ["id", "name", "department", "department_id"]


class SiteSerializer(serializers.ModelSerializer):
    """Serializer for the Site model."""

    class Meta:
        model = Site
        fields = [
            "id",
            "uuid",
            "name",
            "locality",
            "zone",
            "subzone",
            "created_at",
            "updated_at",
        ]


class SiteLightSerializer(serializers.ModelSerializer):
    """Lightweight serializer for the Site model for nested usage."""

    class Meta:
        model = Site
        fields = [
            "id",
            "uuid",
            "name",
        ]
