import django_filters
from django.contrib.gis.geos import Point, Polygon
from django.contrib.gis.measure import D
from django.db.models import Q
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import filters, status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticatedOrReadOnly
from rest_framework.response import Response

from .models import BiodiversityRecord
from .serializers import (
    BiodiversityRecordGeoSerializer,
    BiodiversityRecordSerializer,
)


class BiodiversityRecordFilter(django_filters.FilterSet):
    """Filter for BiodiversityRecord."""

    # Date range filters
    date_from = django_filters.DateFilter(field_name="date", lookup_expr="gte")
    date_to = django_filters.DateFilter(field_name="date", lookup_expr="lte")

    # Text search
    search = django_filters.CharFilter(method="search_filter")

    # Taxonomy filters
    family = django_filters.NumberFilter(field_name="species__genus__family")
    genus = django_filters.NumberFilter(field_name="species__genus")
    life_form = django_filters.CharFilter(field_name="species__life_form")

    # Location filters for spatial queries are implemented directly in the viewset

    class Meta:
        model = BiodiversityRecord
        fields = {
            "species": ["exact"],
            "site": ["exact"],
            "neighborhood": ["exact"],
            "neighborhood__locality": ["exact"],
            "neighborhood__locality__municipality": ["exact"],
            "neighborhood__locality__municipality__department": ["exact"],
            "neighborhood__locality__municipality__department__country": ["exact"],
            "recorded_by": ["exact", "icontains"],
        }

    def search_filter(self, queryset, name, value):
        """Custom search filter across multiple fields."""
        return queryset.filter(
            Q(common_name__icontains=value)
            | Q(species__name__icontains=value)
            | Q(species__genus__name__icontains=value)
            | Q(site__name__icontains=value)
            | Q(neighborhood__name__icontains=value)
        )


class BiodiversityRecordViewSet(viewsets.ReadOnlyModelViewSet):
    """API endpoint for BiodiversityRecord model."""

    queryset = BiodiversityRecord.objects.select_related(
        "species",
        "species__genus",
        "species__genus__family",
        "site",
        "neighborhood",
        "neighborhood__locality",
        "neighborhood__locality__municipality",
    )
    serializer_class = BiodiversityRecordSerializer
    permission_classes = [IsAuthenticatedOrReadOnly]
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_class = BiodiversityRecordFilter
    ordering_fields = [
        "species__genus__name",
        "species__name",
        "site__name",
        "neighborhood__name",
        "date",
        "created_at",
    ]
    ordering = ["-date"]

    def get_serializer_class(self):
        """Return appropriate serializer class."""
        format_param = self.request.query_params.get("format")
        if format_param == "geojson":
            return BiodiversityRecordGeoSerializer
        return BiodiversityRecordSerializer

    @action(detail=False, methods=["get"])
    def near(self, request):
        """Filter records by proximity to a point.

        Query parameters:
        - lat: latitude (required)
        - lon: longitude (required)
        - radius: radius in meters (default: 1000)
        - limit: maximum number of results (default: 50)
        """
        try:
            lat = float(request.query_params.get("lat"))
            lon = float(request.query_params.get("lon"))
            radius = float(request.query_params.get("radius", 1000))
            limit = int(request.query_params.get("limit", 50))
        except (TypeError, ValueError):
            return Response(
                {
                    "error": "Invalid parameters. lat, lon, radius, and limit must be numeric."
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Limit radius to 10km to prevent performance issues
        radius = min(radius, 10000)

        # Get records within the radius
        records = BiodiversityRecord.objects.filter(
            location__dwithin=(Point(lon, lat), D(m=radius))
        ).order_by("location")[:limit]

        serializer = self.get_serializer(records, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=["get"])
    def bbox(self, request):
        """Filter records within a bounding box.

        Query parameters:
        - min_lon: minimum longitude (required)
        - min_lat: minimum latitude (required)
        - max_lon: maximum longitude (required)
        - max_lat: maximum latitude (required)
        - limit: maximum number of results (default: 500)
        """
        try:
            min_lon = float(request.query_params.get("min_lon"))
            min_lat = float(request.query_params.get("min_lat"))
            max_lon = float(request.query_params.get("max_lon"))
            max_lat = float(request.query_params.get("max_lat"))
            limit = int(request.query_params.get("limit", 500))
        except (TypeError, ValueError):
            return Response(
                {
                    "error": "Invalid parameters. min_lon, min_lat, max_lon, max_lat, and limit must be numeric."
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Limit to 500 records to prevent performance issues
        limit = min(limit, 500)

        # Create bounding box
        bbox = Polygon.from_bbox((min_lon, min_lat, max_lon, max_lat))

        # Get records within the bounding box
        records = BiodiversityRecord.objects.filter(location__contained=bbox).order_by(
            "location"
        )[:limit]

        serializer = self.get_serializer(records, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=["get"])
    def by_neighborhood(self, request):
        """Get records for a specific neighborhood with optimized GeoJSON response.

        Query parameters:
        - id: neighborhood ID (required)
        - limit: maximum number of results (default: 1000)
        """
        try:
            neighborhood_id = int(request.query_params.get("id"))
            limit = int(request.query_params.get("limit", 1000))
        except (TypeError, ValueError):
            return Response(
                {"error": "Invalid parameters. id and limit must be numeric."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Limit to 1000 records to prevent performance issues
        limit = min(limit, 1000)

        # Get records for the neighborhood
        records = BiodiversityRecord.objects.filter(
            neighborhood_id=neighborhood_id
        ).order_by("location")[:limit]

        serializer = BiodiversityRecordGeoSerializer(records, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=["get"])
    def by_locality(self, request):
        """Get records for a specific locality with optimized GeoJSON response.

        Query parameters:
        - id: locality ID (required)
        - limit: maximum number of results (default: 2000)
        """
        try:
            locality_id = int(request.query_params.get("id"))
            limit = int(request.query_params.get("limit", 2000))
        except (TypeError, ValueError):
            return Response(
                {"error": "Invalid parameters. id and limit must be numeric."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Limit to 2000 records to prevent performance issues
        limit = min(limit, 2000)

        # Get records for the locality
        records = BiodiversityRecord.objects.filter(
            neighborhood__locality_id=locality_id
        ).order_by("location")[:limit]

        serializer = BiodiversityRecordGeoSerializer(records, many=True)
        return Response(serializer.data)

    @action(
        detail=False, methods=["post"], permission_classes=[IsAuthenticatedOrReadOnly]
    )
    def by_polygon(self, request):
        """Filter records within a custom polygon.

        POST JSON data should include:
        {
            "polygon": [
                [lon1, lat1],
                [lon2, lat2],
                ...
                [lonN, latN],
                [lon1, lat1]  # close the polygon
            ],
            "limit": 1000  # optional, default: 1000
        }
        """
        try:
            data = request.data
            polygon_coords = data.get("polygon")
            limit = int(data.get("limit", 1000))

            if not polygon_coords or len(polygon_coords) < 4:
                return Response(
                    {
                        "error": "Invalid polygon. Must have at least 3 points, plus the closing point."
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )

            # Make sure polygon is closed
            if polygon_coords[0] != polygon_coords[-1]:
                polygon_coords.append(polygon_coords[0])

            # Create polygon
            polygon = Polygon(polygon_coords)

            # Limit to 1000 records to prevent performance issues
            limit = min(limit, 1000)

            # Get records within the polygon
            records = BiodiversityRecord.objects.filter(
                location__contained=polygon
            ).order_by("location")[:limit]

            serializer = self.get_serializer(records, many=True)
            return Response(serializer.data)

        except (TypeError, ValueError, KeyError) as e:
            return Response(
                {"error": f"Invalid parameters: {str(e)}"},
                status=status.HTTP_400_BAD_REQUEST,
            )
