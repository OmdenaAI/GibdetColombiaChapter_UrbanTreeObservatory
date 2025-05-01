import django_filters
from django.contrib.gis.geos import Point
from django.contrib.gis.measure import D
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import filters, status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticatedOrReadOnly
from rest_framework.response import Response

from .models import Climate, Station
from .serializers import ClimateSerializer, StationGeoSerializer, StationSerializer


class StationFilter(django_filters.FilterSet):
    """Filter for Station model."""

    class Meta:
        model = Station
        fields = {
            "code": ["exact"],
            "name": ["exact", "icontains"],
            "municipality": ["exact"],
        }


class StationViewSet(viewsets.ReadOnlyModelViewSet):
    """API endpoint for Station model."""

    queryset = Station.objects.select_related("municipality")
    serializer_class = StationSerializer
    permission_classes = [IsAuthenticatedOrReadOnly]
    filter_backends = [
        DjangoFilterBackend,
        filters.SearchFilter,
        filters.OrderingFilter,
    ]
    filterset_class = StationFilter
    search_fields = ["name", "code"]
    ordering_fields = ["code", "name"]
    ordering = ["code"]

    def get_serializer_class(self):
        """Return appropriate serializer class."""
        format_param = self.request.query_params.get("format")
        if format_param == "geojson":
            return StationGeoSerializer
        return StationSerializer

    @action(detail=False, methods=["get"])
    def near(self, request):
        """Filter stations by proximity to a point.

        Query parameters:
        - lat: latitude (required)
        - lon: longitude (required)
        - radius: radius in meters (default: 10000)
        - limit: maximum number of results (default: 20)
        """
        try:
            lat = float(request.query_params.get("lat"))
            lon = float(request.query_params.get("lon"))
            radius = float(request.query_params.get("radius", 10000))
            limit = int(request.query_params.get("limit", 20))
        except (TypeError, ValueError):
            return Response(
                {
                    "error": "Invalid parameters. lat, lon, radius, and limit must be numeric."
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Limit radius to 50km to prevent performance issues
        radius = min(radius, 50000)

        # Get stations within the radius
        stations = Station.objects.filter(
            location__dwithin=(Point(lon, lat), D(m=radius))
        ).order_by("location")[:limit]

        serializer = self.get_serializer(stations, many=True)
        return Response(serializer.data)


class ClimateFilter(django_filters.FilterSet):
    """Filter for Climate model."""

    # Date range filters
    date_from = django_filters.DateFilter(field_name="date", lookup_expr="gte")
    date_to = django_filters.DateFilter(field_name="date", lookup_expr="lte")

    # Value range filters
    value_min = django_filters.NumberFilter(field_name="value", lookup_expr="gte")
    value_max = django_filters.NumberFilter(field_name="value", lookup_expr="lte")

    class Meta:
        model = Climate
        fields = {
            "station": ["exact"],
            "sensor": ["exact"],
            "measure_unit": ["exact"],
            "station__municipality": ["exact"],
        }


class ClimateViewSet(viewsets.ReadOnlyModelViewSet):
    """API endpoint for Climate model."""

    queryset = Climate.objects.select_related("station", "station__municipality")
    serializer_class = ClimateSerializer
    permission_classes = [IsAuthenticatedOrReadOnly]
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_class = ClimateFilter
    ordering_fields = [
        "station__code",
        "date",
        "sensor",
        "value",
        "created_at",
    ]
    ordering = ["-date"]

    def get_queryset(self):
        """Optimize queryset for large dataset (700,000+ records)."""
        queryset = super().get_queryset()

        # Ensure proper filtering before returning data
        # Instead of slicing the queryset (which causes issues with ordering and filtering),
        # we'll use the primary key values to create a new queryset
        if not any(
            param in self.request.query_params
            for param in [
                "station",
                "station__municipality",
                "date_from",
                "date_to",
                "sensor",
                "value_min",
                "value_max",
                "page",
            ]
        ):
            # Get the IDs of the latest 1000 records
            # Using values_list with flat=True to get just the IDs
            latest_ids = list(
                queryset.order_by("-date").values_list("id", flat=True)[:1000]
            )

            # Create a new queryset with those IDs
            return queryset.filter(id__in=latest_ids)

        return queryset
