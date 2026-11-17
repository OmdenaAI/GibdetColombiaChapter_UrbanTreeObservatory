from django.db.models import Count, Exists, OuterRef, Subquery
from django.views.generic import TemplateView
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import filters, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticatedOrReadOnly
from rest_framework.response import Response

from apps.biodiversity.models import BiodiversityRecord

from .models import Family, FunctionalGroup, Genus, ManualEntry, Species, Trait
from .serializers import (
    FamilySerializer,
    FunctionalGroupSerializer,
    GenusSerializer,
    ManualEntrySerializer,
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

    @action(detail=False, methods=["get"])
    def hierarchy(self, request):
        """Return taxonomy data in a hierarchical format for D3.js visualization."""
        hierarchy = {
            "name": "Tree of Life",
            "children": [],
        }
        families = self.get_queryset()
        for family in families:
            family_node = {
                "name": family.name,
                "id": family.id,
                "uuid": str(family.uuid),
                "type": "family",
                "children": [],
            }
            genera = family.genera.all()
            for genus in genera:
                genus_node = {
                    "name": genus.name,
                    "id": genus.id,
                    "uuid": str(genus.uuid),
                    "type": "genus",
                    "children": [],
                }
                species_list = genus.species.all()
                for species in species_list:
                    species_node = {
                        "name": species.name,
                        "id": species.id,
                        "uuid": str(species.uuid),
                        "scientific_name": species.scientific_name,
                        "type": "species",
                        "life_form": species.get_life_form_display(),
                        "origin": species.get_origin_display(),
                        "iucn_status": species.get_iucn_status_display(),
                    }
                    genus_node["children"].append(species_node)
                family_node["children"].append(genus_node)
            hierarchy["children"].append(family_node)

        return Response(hierarchy)


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
    """API endpoint for Species model.

    Each species carries ``common_name``: the most frequent non-empty common name among its
    biodiversity records (ties broken alphabetically), or ``null`` if it has none; and
    ``has_manual_entry``: whether ``manual/`` returns its sheet in the Tolima manual.
    """

    queryset = Species.objects.select_related(
        "genus__family", "functional_group"
    ).annotate(
        common_name=Subquery(
            BiodiversityRecord.objects.filter(species=OuterRef("pk"))
            .exclude(common_name__isnull=True)
            .exclude(common_name="")
            .values("common_name")
            .annotate(n=Count("id"))
            .order_by("-n", "common_name")
            .values("common_name")[:1]
        ),
        has_manual_entry=Exists(ManualEntry.objects.filter(species=OuterRef("pk"))),
    )
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

    @action(detail=True, methods=["get"])
    def manual(self, request, pk=None):
        """The species' sheet in the Tolima arborization manual; 404 when it has none."""
        entry = ManualEntry.objects.filter(species_id=pk).first()
        if entry is None:
            return Response(
                {"detail": "This species has no entry in the manual."}, status=404
            )
        return Response(ManualEntrySerializer(entry).data)


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


class TreeOfLifeView(TemplateView):
    template_name = "taxonomy/tree_of_life.html"
