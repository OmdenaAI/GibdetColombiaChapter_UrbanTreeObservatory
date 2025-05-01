import django_filters
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import filters, viewsets
from rest_framework.permissions import IsAuthenticatedOrReadOnly

from .models import Measurement, Observation
from .serializers import MeasurementSerializer, ObservationSerializer


class MeasurementFilter(django_filters.FilterSet):
    """Filter for the Measurement model."""

    # Date range filters
    date_from = django_filters.DateFilter(field_name="date", lookup_expr="gte")
    date_to = django_filters.DateFilter(field_name="date", lookup_expr="lte")

    # Value range filters
    value_min = django_filters.NumberFilter(field_name="value", lookup_expr="gte")
    value_max = django_filters.NumberFilter(field_name="value", lookup_expr="lte")

    class Meta:
        model = Measurement
        fields = {
            "biodiversity_record": ["exact"],
            "attribute": ["exact"],
            "unit": ["exact"],
            "method": ["exact"],
        }


class MeasurementViewSet(viewsets.ReadOnlyModelViewSet):
    """API endpoint for the Measurement model."""

    queryset = Measurement.objects.select_related("biodiversity_record")
    serializer_class = MeasurementSerializer
    permission_classes = [IsAuthenticatedOrReadOnly]
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_class = MeasurementFilter
    ordering_fields = [
        "biodiversity_record",
        "attribute",
        "value",
        "date",
        "created_at",
    ]
    ordering = ["-date"]

    def get_queryset(self):
        """Optimize queryset for large dataset."""
        queryset = super().get_queryset()

        # Limit to 1000 records by default unless explicitly paginated
        if not self.request.query_params.get("page"):
            # Get the IDs of the latest 1000 records
            # Using values_list with flat=True to get just the IDs
            latest_ids = list(
                queryset.order_by("-date").values_list("id", flat=True)[:1000]
            )

            # Create a new queryset with those IDs
            return queryset.filter(id__in=latest_ids)

        return queryset


class ObservationFilter(django_filters.FilterSet):
    """Filter for the Observation model."""

    # Date range filters
    date_from = django_filters.DateFilter(field_name="date", lookup_expr="gte")
    date_to = django_filters.DateFilter(field_name="date", lookup_expr="lte")

    # Text search
    search = django_filters.CharFilter(method="search_filter")

    class Meta:
        model = Observation
        fields = {
            "biodiversity_record": ["exact"],
            "reproductive_condition": ["exact"],
            "phytosanitary_status": ["exact"],
            "physical_condition": ["exact"],
            "foliage_density": ["exact"],
            "aesthetic_value": ["exact"],
            "growth_phase": ["exact"],
            "standing": ["exact"],
            "recorded_by": ["exact", "icontains"],
        }

    def search_filter(self, queryset, name, value):
        """Search in text fields."""
        from django.db.models import Q

        return queryset.filter(
            Q(field_notes__icontains=value)
            | Q(accompanying_collectors__icontains=value)
            | Q(recorded_by__icontains=value)
        )


class ObservationViewSet(viewsets.ReadOnlyModelViewSet):
    """API endpoint for the Observation model."""

    queryset = Observation.objects.select_related("biodiversity_record")
    serializer_class = ObservationSerializer
    permission_classes = [IsAuthenticatedOrReadOnly]
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_class = ObservationFilter
    ordering_fields = [
        "biodiversity_record",
        "reproductive_condition",
        "phytosanitary_status",
        "growth_phase",
        "date",
        "created_at",
    ]
    ordering = ["-date"]

    def get_queryset(self):
        """Optimize queryset for large dataset."""
        queryset = super().get_queryset()

        # Limit to 1000 records by default unless explicitly paginated
        if not self.request.query_params.get("page"):
            # Get the IDs of the latest 1000 records
            # Using values_list with flat=True to get just the IDs
            latest_ids = list(
                queryset.order_by("-date").values_list("id", flat=True)[:1000]
            )

            # Create a new queryset with those IDs
            return queryset.filter(id__in=latest_ids)

        return queryset
