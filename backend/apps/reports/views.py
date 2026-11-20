import django_filters
from django.utils import timezone, translation
from django.utils.translation import gettext as _
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import filters, mixins, status, viewsets
from rest_framework.decorators import action
from rest_framework.parsers import JSONParser, MultiPartParser
from rest_framework.permissions import AllowAny, IsAdminUser, IsAuthenticatedOrReadOnly
from rest_framework.response import Response
from rest_framework.views import APIView

from . import upload
from .analytics import analytics_summary
from .dashboard import dashboard_summary
from .models import Measurement, Observation, Upload
from .serializers import MeasurementSerializer, ObservationSerializer, UploadSerializer


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


class DashboardView(APIView):
    """Aggregated figures for the frontend dashboard (read-only, public)."""

    permission_classes = [AllowAny]

    def get(self, request):
        return Response(dashboard_summary())


class AnalyticsView(APIView):
    """Urban forest indicators (species concentration, origin, size structure, density
    per comuna, health by species, threatened species). Cached for an hour."""

    permission_classes = [AllowAny]

    def get(self, request):
        return Response(analytics_summary())


def _language(request):
    lang = request.query_params.get("lang", "")
    return lang if lang in {"es", "en"} else "en"


class UploadViewSet(
    mixins.ListModelMixin, mixins.RetrieveModelMixin, viewsets.GenericViewSet
):
    """Files that update the tree database (Reports page); staff users only.

    ``POST uploads/`` (multipart ``file``) checks the file and answers what would change,
    without writing; ``POST uploads/{id}/apply/`` writes it. ``?lang=es`` translates the
    messages. See ``upload.py`` for the file's columns.
    """

    queryset = Upload.objects.select_related("user")
    serializer_class = UploadSerializer
    permission_classes = [IsAdminUser]
    parser_classes = [MultiPartParser, JSONParser]

    def create(self, request):
        file = request.FILES.get("file")
        with translation.override(_language(request)):
            if file is None:
                return _error(_("Choose a file."))
            fmt = upload.file_format(file.name)
            if fmt is None:
                return _error(
                    _(
                        "Use an Excel (.xlsx), CSV, zipped Shapefile (.zip) or GeoJSON file."
                    )
                )
            if file.size > upload.MAX_BYTES:
                return _error(_("The file is larger than 20 MB."))
            record = Upload.objects.create(
                file=file, name=file.name[:255], format=fmt, user=request.user
            )
            try:
                record.summary = self._check(record).summary()
            except upload.UploadError as e:
                record.file.delete(save=False)
                record.delete()
                return _error(str(e))
            record.save(update_fields=["summary", "updated_at"])
        return Response(self.get_serializer(record).data, status.HTTP_201_CREATED)

    @action(detail=True, methods=["post"])
    def apply(self, request, pk=None):
        record = self.get_object()
        with translation.override(_language(request)):
            if record.status == Upload.Status.APPLIED:
                return _error(_("This file was already applied."))
            # Checked again: the database may have changed since the preview.
            try:
                plan = self._check(record)
            except upload.UploadError as e:
                return _error(str(e))
            summary = plan.summary()
            if plan.errors:
                record.summary = summary
                record.save(update_fields=["summary", "updated_at"])
                return Response(
                    self.get_serializer(record).data, status.HTTP_400_BAD_REQUEST
                )
            upload.apply(plan)
            record.summary = summary
            record.status = Upload.Status.APPLIED
            record.applied_at = timezone.now()
            record.save()
        return Response(self.get_serializer(record).data)

    def _check(self, record):
        suffix = "." + record.name.rsplit(".", 1)[-1].lower()
        with upload.local_copy(record.file, suffix) as path:
            return upload.check(path, record.format, user=record.user)


def _error(message):
    return Response({"error": message}, status.HTTP_400_BAD_REQUEST)
