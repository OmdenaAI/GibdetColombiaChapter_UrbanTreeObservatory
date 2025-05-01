from rest_framework import serializers
from rest_framework_gis.serializers import GeoFeatureModelSerializer

from apps.places.serializers import NeighborhoodLightSerializer, SiteLightSerializer
from apps.taxonomy.serializers import SpeciesLightSerializer

from .models import BiodiversityRecord


class BiodiversityRecordSerializer(serializers.ModelSerializer):
    """Standard serializer for BiodiversityRecord model."""

    species = SpeciesLightSerializer(read_only=True)
    site = SiteLightSerializer(read_only=True)
    neighborhood = NeighborhoodLightSerializer(read_only=True)
    longitude = serializers.FloatField(read_only=True)
    latitude = serializers.FloatField(read_only=True)

    class Meta:
        model = BiodiversityRecord
        fields = [
            "id",
            "uuid",
            "common_name",
            "species",
            "site",
            "neighborhood",
            "location",
            "longitude",
            "latitude",
            "elevation_m",
            "recorded_by",
            "date",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["longitude", "latitude"]


class BiodiversityRecordGeoSerializer(GeoFeatureModelSerializer):
    """GeoJSON serializer for BiodiversityRecord model."""

    species = SpeciesLightSerializer(read_only=True)
    site = SiteLightSerializer(read_only=True)
    neighborhood = NeighborhoodLightSerializer(read_only=True)
    longitude = serializers.FloatField(read_only=True)
    latitude = serializers.FloatField(read_only=True)

    # Add additional fields that may be useful for map tooltips
    species_scientific_name = serializers.CharField(
        source="species.scientific_name", read_only=True
    )
    neighborhood_name = serializers.CharField(
        source="neighborhood.name", read_only=True
    )
    locality_name = serializers.CharField(
        source="neighborhood.locality.name", read_only=True
    )
    municipality_name = serializers.CharField(
        source="neighborhood.locality.municipality.name", read_only=True
    )

    class Meta:
        model = BiodiversityRecord
        geo_field = "location"
        fields = [
            "id",
            "uuid",
            "common_name",
            "species",
            "species_scientific_name",
            "site",
            "neighborhood",
            "neighborhood_name",
            "locality_name",
            "municipality_name",
            "longitude",
            "latitude",
            "elevation_m",
            "recorded_by",
            "date",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["longitude", "latitude"]


class BiodiversityRecordLightSerializer(serializers.ModelSerializer):
    """Lightweight serializer for BiodiversityRecord model for nested usage."""

    species_name = serializers.CharField(
        source="species.scientific_name", read_only=True
    )
    site_name = serializers.CharField(source="site.name", read_only=True)
    neighborhood_name = serializers.CharField(
        source="neighborhood.name", read_only=True
    )

    class Meta:
        model = BiodiversityRecord
        fields = [
            "id",
            "uuid",
            "common_name",
            "species_name",
            "site_name",
            "neighborhood_name",
            "date",
        ]
