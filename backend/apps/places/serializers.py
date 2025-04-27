from rest_framework import serializers
from rest_framework_gis.serializers import GeoFeatureModelSerializer
from .models import Country, Department, Municipality, Locality, Neighborhood, Site


class CountrySerializer(serializers.ModelSerializer):
    """Serializer for the Country model."""

    class Meta:
        model = Country
        fields = ["id", "name", "boundary"]


class CountryGeoSerializer(GeoFeatureModelSerializer):
    """GeoJSON serializer for the Country model."""

    class Meta:
        model = Country
        geo_field = "boundary"
        fields = ["id", "name"]


class DepartmentSerializer(serializers.ModelSerializer):
    """Serializer for the Department model."""

    country = CountrySerializer(read_only=True)
    country_id = serializers.PrimaryKeyRelatedField(
        queryset=Country.objects.all(), source="country", write_only=True
    )

    class Meta:
        model = Department
        fields = ["id", "name", "country", "country_id", "boundary"]


class DepartmentGeoSerializer(GeoFeatureModelSerializer):
    """GeoJSON serializer for the Department model."""

    country_name = serializers.CharField(source="country.name", read_only=True)

    class Meta:
        model = Department
        geo_field = "boundary"
        fields = ["id", "name", "country_id", "country_name"]


class MunicipalitySerializer(serializers.ModelSerializer):
    """Serializer for the Municipality model."""

    department = DepartmentSerializer(read_only=True)
    department_id = serializers.PrimaryKeyRelatedField(
        queryset=Department.objects.all(), source="department", write_only=True
    )

    class Meta:
        model = Municipality
        fields = ["id", "name", "department", "department_id", "boundary"]


class MunicipalityGeoSerializer(GeoFeatureModelSerializer):
    """GeoJSON serializer for the Municipality model."""

    department_name = serializers.CharField(source="department.name", read_only=True)
    country_name = serializers.CharField(
        source="department.country.name", read_only=True
    )

    class Meta:
        model = Municipality
        geo_field = "boundary"
        fields = ["id", "name", "department_id", "department_name", "country_name"]


class LocalitySerializer(serializers.ModelSerializer):
    """Serializer for the Locality model."""

    municipality = MunicipalitySerializer(read_only=True)
    municipality_id = serializers.PrimaryKeyRelatedField(
        queryset=Municipality.objects.all(), source="municipality", write_only=True
    )

    class Meta:
        model = Locality
        fields = [
            "id",
            "uuid",
            "name",
            "municipality",
            "municipality_id",
            "boundary",
            "calculated_area_m2",
            "population_2019",
            "created_at",
            "updated_at",
        ]


class LocalityGeoSerializer(GeoFeatureModelSerializer):
    """GeoJSON serializer for the Locality model."""

    municipality_name = serializers.CharField(
        source="municipality.name", read_only=True
    )
    department_name = serializers.CharField(
        source="municipality.department.name", read_only=True
    )

    class Meta:
        model = Locality
        geo_field = "boundary"
        fields = [
            "id",
            "uuid",
            "name",
            "municipality_id",
            "municipality_name",
            "department_name",
            "calculated_area_m2",
            "population_2019",
        ]


class LocalityLightSerializer(serializers.ModelSerializer):
    """Lightweight serializer for the Locality model."""

    class Meta:
        model = Locality
        fields = ["id", "uuid", "name"]


class NeighborhoodSerializer(serializers.ModelSerializer):
    """Serializer for the Neighborhood model."""

    locality = LocalitySerializer(read_only=True)
    locality_id = serializers.PrimaryKeyRelatedField(
        queryset=Locality.objects.all(), source="locality", write_only=True
    )

    class Meta:
        model = Neighborhood
        fields = [
            "id",
            "uuid",
            "name",
            "locality",
            "locality_id",
            "boundary",
            "created_at",
            "updated_at",
        ]


class NeighborhoodGeoSerializer(GeoFeatureModelSerializer):
    """GeoJSON serializer for the Neighborhood model."""

    locality_name = serializers.CharField(source="locality.name", read_only=True)
    municipality_name = serializers.CharField(
        source="locality.municipality.name", read_only=True
    )

    class Meta:
        model = Neighborhood
        geo_field = "boundary"
        fields = [
            "id",
            "uuid",
            "name",
            "locality_id",
            "locality_name",
            "municipality_name",
        ]


class NeighborhoodLightSerializer(serializers.ModelSerializer):
    """Lightweight serializer for the Neighborhood model."""

    class Meta:
        model = Neighborhood
        fields = ["id", "uuid", "name"]


class SiteSerializer(serializers.ModelSerializer):
    """Serializer for the Site model."""

    locality = LocalityLightSerializer(read_only=True)
    locality_id = serializers.PrimaryKeyRelatedField(
        queryset=Locality.objects.all(), source="locality", write_only=True
    )

    class Meta:
        model = Site
        fields = [
            "id",
            "uuid",
            "name",
            "locality",
            "locality_id",
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
