from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import filters, viewsets
from rest_framework.permissions import IsAuthenticatedOrReadOnly

from .models import Family, FunctionalGroup, Genus, Species, Trait
from .serializers import (
    FamilySerializer,
    FunctionalGroupSerializer,
    GenusSerializer,
    SpeciesSerializer,
    TraitSerializer,
)


class FamilyViewSet(viewsets.ReadOnlyModelViewSet):
    """API endpoint for Family model."""

    queryset = Family.objects.all()
    serializer_class = FamilySerializer
    permission_classes = [IsAuthenticatedOrReadOnly]
    filter_backends = [
        filters.SearchFilter,
        filters.OrderingFilter,
        DjangoFilterBackend,
    ]
    search_fields = ["name"]
    ordering_fields = ["name", "created_at"]
    ordering = ["name"]


class GenusViewSet(viewsets.ReadOnlyModelViewSet):
    """API endpoint for Genus model."""

    queryset = Genus.objects.all()
    serializer_class = GenusSerializer
    permission_classes = [IsAuthenticatedOrReadOnly]
    filter_backends = [
        filters.SearchFilter,
        filters.OrderingFilter,
        DjangoFilterBackend,
    ]
    search_fields = ["name"]
    filterset_fields = ["family"]
    ordering_fields = ["name", "family__name", "created_at"]
    ordering = ["name"]


class SpeciesViewSet(viewsets.ReadOnlyModelViewSet):
    """API endpoint for Species model."""

    queryset = Species.objects.all()
    serializer_class = SpeciesSerializer
    permission_classes = [IsAuthenticatedOrReadOnly]
    filter_backends = [
        filters.SearchFilter,
        filters.OrderingFilter,
        DjangoFilterBackend,
    ]
    search_fields = ["name", "accepted_scientific_name", "genus__name"]
    filterset_fields = {
        "genus": ["exact"],
        "genus__family": ["exact"],
        "life_form": ["exact"],
        "origin": ["exact"],
        "iucn_status": ["exact"],
        "canopy_shape": ["exact"],
        "flower_color": ["exact"],
        "functional_group": ["exact"],
    }
    ordering_fields = ["genus__name", "name", "life_form", "iucn_status", "created_at"]
    ordering = ["genus__name", "name"]


class FunctionalGroupViewSet(viewsets.ReadOnlyModelViewSet):
    """API endpoint for FunctionalGroup model."""

    queryset = FunctionalGroup.objects.all()
    serializer_class = FunctionalGroupSerializer
    permission_classes = [IsAuthenticatedOrReadOnly]
    filter_backends = [filters.OrderingFilter, DjangoFilterBackend]
    ordering_fields = ["group_id"]
    ordering = ["group_id"]


class TraitViewSet(viewsets.ReadOnlyModelViewSet):
    """API endpoint for Trait model."""

    queryset = Trait.objects.all()
    serializer_class = TraitSerializer
    permission_classes = [IsAuthenticatedOrReadOnly]
    filter_backends = [filters.OrderingFilter, DjangoFilterBackend]
    filterset_fields = ["type"]
    ordering_fields = ["type"]
    ordering = ["type"]
