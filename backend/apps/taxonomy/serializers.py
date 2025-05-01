from rest_framework import serializers

from .models import Family, FunctionalGroup, Genus, Species, Trait, TraitValue


class FamilySerializer(serializers.ModelSerializer):
    """Serializer for the Family model."""

    class Meta:
        model = Family
        fields = ["id", "uuid", "name", "created_at", "updated_at"]


class GenusSerializer(serializers.ModelSerializer):
    """Serializer for the Genus model."""

    family = FamilySerializer(read_only=True)
    family_id = serializers.PrimaryKeyRelatedField(
        queryset=Family.objects.all(), source="family", write_only=True
    )

    class Meta:
        model = Genus
        fields = [
            "id",
            "uuid",
            "name",
            "family",
            "family_id",
            "created_at",
            "updated_at",
        ]


class TraitSerializer(serializers.ModelSerializer):
    """Serializer for the Trait model."""

    type_display = serializers.CharField(source="get_type_display", read_only=True)

    class Meta:
        model = Trait
        fields = ["id", "uuid", "type", "type_display", "created_at", "updated_at"]


class TraitValueSerializer(serializers.ModelSerializer):
    """Serializer for the TraitValue model."""

    trait = TraitSerializer(read_only=True)

    class Meta:
        model = TraitValue
        fields = [
            "id",
            "uuid",
            "trait",
            "min_value",
            "max_value",
            "created_at",
            "updated_at",
        ]


class FunctionalGroupSerializer(serializers.ModelSerializer):
    """Serializer for the FunctionalGroup model."""

    trait_values = TraitValueSerializer(many=True, read_only=True)

    class Meta:
        model = FunctionalGroup
        fields = ["id", "uuid", "group_id", "trait_values", "created_at", "updated_at"]


class SpeciesSerializer(serializers.ModelSerializer):
    """Serializer for the Species model."""

    genus = GenusSerializer(read_only=True)
    genus_id = serializers.PrimaryKeyRelatedField(
        queryset=Genus.objects.all(), source="genus", write_only=True
    )

    functional_group = FunctionalGroupSerializer(read_only=True)

    scientific_name = serializers.CharField(read_only=True)
    gbif_url = serializers.URLField(read_only=True)
    tropical_plants_url = serializers.URLField(read_only=True)

    origin_display = serializers.CharField(source="get_origin_display", read_only=True)
    iucn_status_display = serializers.CharField(
        source="get_iucn_status_display", read_only=True
    )
    life_form_display = serializers.CharField(
        source="get_life_form_display", read_only=True
    )
    canopy_shape_display = serializers.CharField(
        source="get_canopy_shape_display", read_only=True
    )
    flower_color_display = serializers.CharField(
        source="get_flower_color_display", read_only=True
    )

    class Meta:
        model = Species
        fields = [
            "id",
            "uuid",
            "genus",
            "genus_id",
            "name",
            "scientific_name",
            "accepted_scientific_name",
            "functional_group",
            "origin",
            "origin_display",
            "iucn_status",
            "iucn_status_display",
            "life_form",
            "life_form_display",
            "canopy_shape",
            "canopy_shape_display",
            "flower_color",
            "flower_color_display",
            "gbif_id",
            "gbif_url",
            "tropical_plants_url",
            "identified_by",
            "date",
            "created_at",
            "updated_at",
        ]


class SpeciesLightSerializer(serializers.ModelSerializer):
    """Lightweight serializer for the Species model used in nested relations."""

    scientific_name = serializers.CharField(read_only=True)

    class Meta:
        model = Species
        fields = ["id", "scientific_name", "life_form"]
