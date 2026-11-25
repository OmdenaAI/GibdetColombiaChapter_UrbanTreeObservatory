"""Read-only tree inventory for the frontend's "Trees" page.

``/api/v1/biodiversity/inventory/``:

- list: one row per tree with its latest total height, DBH and phytosanitary status;
  filters ``id``, ``species`` (scientific or common name), ``family``, ``neighborhood``
  and ``health`` (status code); 25 rows per page (``page_size`` up to 100).
- retrieve: the tree with every measurement and observation (all census fields).
- ``export/``: CSV. ``GET`` with the list filters exports every matching tree; ``POST``
  ``{"ids": [...]}`` exports the selected ones.
- ``query/`` (POST) and ``options/``: the map's queries by filters and area of interest,
  with CSV, Excel and GeoJSON downloads (see ``query.py``).

``?lang=es|en`` sets the language of the labels in the detail and of the category values
in the CSV (default: English). The CSV header is always in English.

Editing and deleting is left to the Django admin.
"""

import csv

import django_filters
from django.db.models import CharField, F, OuterRef, Q, Subquery, Value
from django.db.models.functions import Concat
from django.http import StreamingHttpResponse
from django.utils import timezone, translation
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import filters, serializers, status, viewsets
from rest_framework.decorators import action
from rest_framework.pagination import PageNumberPagination
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from apps.reports.metrics import tree_metrics
from apps.reports.models import Assessment, Measurement, Observation

from . import query
from .models import BiodiversityRecord

# Measured attributes in CSV order: the census variables, which the Reports upload
# also reads back.
CSV_ATTRIBUTES = [
    Measurement.MeasuredAttribute.TOTAL_HEIGHT,
    Measurement.MeasuredAttribute.DIAMETER_BH,
    Measurement.MeasuredAttribute.TRUNK_HEIGHT,
    Measurement.MeasuredAttribute.CROWN_DIAMETER,
    Measurement.MeasuredAttribute.VOLUME,
    Measurement.MeasuredAttribute.WOOD_DENSITY,
]

# Display order on the tree page: the census variables, then the study ones.
ATTRIBUTES = [
    *CSV_ATTRIBUTES,
    Measurement.MeasuredAttribute.CROWN_DIAMETER_NS,
    Measurement.MeasuredAttribute.CROWN_DIAMETER_EW,
    Measurement.MeasuredAttribute.INTERNAL_DAMAGE,
    Measurement.MeasuredAttribute.ACOUSTIC_VELOCITY,
    Measurement.MeasuredAttribute.GREEN_DENSITY,
    Measurement.MeasuredAttribute.DYNAMIC_MOE,
]

# Assessment fields shown on the tree page, in order.
ASSESSMENT_FIELDS = [
    "visual_risk",
    "visual_risk_part",
    "biomechanical_risk",
    "tomography_level",
    "damage_section_diameter_cm",
    "damage_section_height_cm",
    "tomography_sections",
    "age_class",
    "planting_site",
    "crown_exposure_class",
    "crown_exposure_percent",
    "study_code",
    "notes",
]

# Observation fields that are bookkeeping, not census data.
OBSERVATION_SKIP = {
    "id",
    "uuid",
    "created_at",
    "updated_at",
    "biodiversity_record",
    "is_latest",
}

EXPORT_CHUNK = 2000
MAX_SELECTED = 10000

LANGUAGES = {"es", "en"}
DEFAULT_LANGUAGE = "en"


def request_language(request):
    """``?lang=`` if it is a supported language, else English."""
    lang = request.query_params.get("lang", "").lower()
    return lang if lang in LANGUAGES else DEFAULT_LANGUAGE


def _latest_measurement(attribute):
    return Subquery(
        Measurement.objects.filter(
            biodiversity_record=OuterRef("pk"), attribute=attribute, is_latest=True
        ).values("value")[:1]
    )


def inventory_queryset():
    return (
        BiodiversityRecord.objects.select_related(
            "species__genus__family", "neighborhood__locality", "site"
        )
        .annotate(
            scientific_name=Concat(
                F("species__genus__name"),
                Value(" "),
                F("species__name"),
                output_field=CharField(),
            ),
            height_m=_latest_measurement(Measurement.MeasuredAttribute.TOTAL_HEIGHT),
            dbh_cm=_latest_measurement(Measurement.MeasuredAttribute.DIAMETER_BH),
            phytosanitary_status=Subquery(
                Observation.objects.filter(
                    biodiversity_record=OuterRef("pk"), is_latest=True
                ).values("phytosanitary_status")[:1]
            ),
        )
        .order_by("id")
    )


class InventoryFilter(django_filters.FilterSet):
    id = django_filters.NumberFilter(field_name="id")
    species = django_filters.CharFilter(method="filter_species")
    family = django_filters.CharFilter(
        field_name="species__genus__family__name", lookup_expr="icontains"
    )
    neighborhood = django_filters.CharFilter(
        field_name="neighborhood__name", lookup_expr="icontains"
    )
    health = django_filters.ChoiceFilter(
        field_name="phytosanitary_status",
        choices=Observation.PhytosanitaryStatus.choices,
    )

    class Meta:
        model = BiodiversityRecord
        fields = []

    def filter_species(self, queryset, name, value):
        value = value.strip()
        return queryset.filter(
            Q(scientific_name__icontains=value) | Q(common_name__icontains=value)
        )


class InventoryPagination(PageNumberPagination):
    page_size = 25
    page_size_query_param = "page_size"
    max_page_size = 100


class InventoryRowSerializer(serializers.ModelSerializer):
    scientific_name = serializers.CharField()
    family = serializers.CharField(source="species.genus.family.name")
    neighborhood = serializers.CharField(source="neighborhood.name")
    locality = serializers.CharField(source="neighborhood.locality.name")
    height_m = serializers.FloatField()
    dbh_cm = serializers.FloatField()
    phytosanitary_status = serializers.CharField()

    class Meta:
        model = BiodiversityRecord
        fields = [
            "id",
            "common_name",
            "scientific_name",
            "family",
            "neighborhood",
            "locality",
            "height_m",
            "dbh_cm",
            "phytosanitary_status",
            "date",
        ]


def _choice_field(obj, field):
    value = getattr(obj, field.attname)
    entry = {"field": field.name, "label": str(field.verbose_name), "value": value}
    if field.choices:
        entry["display"] = str(dict(field.flatchoices).get(value, value))
    return entry


def tree_detail(record):
    measurements = sorted(
        record.measurements.all(),
        key=lambda m: (
            ATTRIBUTES.index(m.attribute)
            if m.attribute in ATTRIBUTES
            else len(ATTRIBUTES),
            -(m.date.toordinal() if m.date else 0),
        ),
    )
    observations = sorted(
        record.observations.all(),
        key=lambda o: (o.date or record.date or timezone.now().date(), o.created_at),
        reverse=True,
    )
    obs_fields = [
        f for f in Observation._meta.concrete_fields if f.name not in OBSERVATION_SKIP
    ]
    assessments = sorted(record.assessments.all(), key=lambda a: a.date, reverse=True)
    assessment_fields = [Assessment._meta.get_field(n) for n in ASSESSMENT_FIELDS]
    species = record.species
    return {
        "id": record.id,
        "uuid": str(record.uuid),
        "common_name": record.common_name,
        "species": {
            "id": species.id,
            "scientific_name": species.scientific_name,
            "accepted_scientific_name": species.accepted_scientific_name,
            "family": species.genus.family.name,
            "genus": species.genus.name,
            "life_form": species.get_life_form_display(),
            "origin": species.get_origin_display(),
            "iucn_status": species.iucn_status,
        },
        "neighborhood": record.neighborhood.name,
        "locality": record.neighborhood.locality.name,
        "site": record.site.name if record.site else None,
        "planting_site": str(record.get_planting_site_display()) or None,
        "latitude": record.latitude,
        "longitude": record.longitude,
        "elevation_m": record.elevation_m,
        "recorded_by": record.recorded_by,
        "date": record.date,
        "measurements": [
            {
                "attribute": m.attribute,
                "label": m.get_attribute_display(),
                "value": m.value,
                "unit": m.unit,
                "method": m.get_method_display(),
                "date": m.date,
                "source": str(m.study) if m.study else None,
            }
            for m in measurements
        ],
        "assessments": [
            {
                "date": a.date,
                "study": str(a.study),
                "citation": a.study.citation,
                "fields": [
                    _choice_field(a, f)
                    for f in assessment_fields
                    if getattr(a, f.attname) not in ("", None)
                ],
            }
            for a in assessments
        ],
        "metrics": tree_metrics(
            record, measurements, assessments[0] if assessments else None
        ),
        "observations": [
            {
                "date": o.date,
                "fields": [_choice_field(o, f) for f in obs_fields],
            }
            for o in observations
        ],
    }


# --- CSV -------------------------------------------------------------------------------

CSV_HEADER = [
    "id",
    "common_name",
    "scientific_name",
    "family",
    "neighborhood",
    "comuna",
    "site",
    "latitude",
    "longitude",
    "record_date",
    *(
        f"{label}_{unit}"
        for label, unit in [
            ("total_height", "m"),
            ("dbh", "cm"),
            ("trunk_height", "m"),
            ("crown_diameter", "m"),
            ("volume", "m3"),
            ("wood_density", "g_cm3"),
        ]
    ),
    "last_measurement_date",
    "phytosanitary_status",
    "physical_condition",
    "foliage_density",
    "growth_phase",
    "photo_url",
]


class _Echo:
    def write(self, value):
        return value


OBS_COLUMNS = [
    "phytosanitary_status",
    "physical_condition",
    "foliage_density",
    "growth_phase",
]


def _display(model, field_name):
    """code -> label for a choices field (in the active language)."""
    field = model._meta.get_field(field_name)
    return {code: str(label) for code, label in field.flatchoices}


def _csv_rows(queryset, lang):
    # A generator: the override must be active while the rows are produced.
    with translation.override(lang):
        yield from _csv_rows_in_language(queryset)


def _csv_rows_in_language(queryset):
    """``queryset`` only selects the trees. Their data is read in chunks with plain
    ``values_list`` queries: building model instances made a full export take minutes."""
    ids = list(queryset.order_by("id").values_list("id", flat=True))
    labels = {f: _display(Observation, f) for f in OBS_COLUMNS}
    yield CSV_HEADER
    for start in range(0, len(ids), EXPORT_CHUNK):
        chunk = ids[start : start + EXPORT_CHUNK]
        records = (
            BiodiversityRecord.objects.filter(id__in=chunk)
            .order_by("id")
            .values_list(
                "id",
                "common_name",
                "species__genus__name",
                "species__name",
                "species__genus__family__name",
                "neighborhood__name",
                "neighborhood__locality__name",
                "site__name",
                "location",
                "date",
            )
        )
        measures = {}
        for rid, attribute, value, date in Measurement.objects.filter(
            biodiversity_record_id__in=chunk, is_latest=True
        ).values_list("biodiversity_record_id", "attribute", "value", "date"):
            measures.setdefault(rid, {})[attribute] = (value, date)
        observations = {
            row[0]: row[1:]
            for row in Observation.objects.filter(
                biodiversity_record_id__in=chunk, is_latest=True
            ).values_list("biodiversity_record_id", *OBS_COLUMNS, "photo_url")
        }
        for (
            rid,
            common,
            genus,
            epithet,
            family,
            hood,
            comuna,
            site,
            loc,
            date,
        ) in records:
            m = measures.get(rid, {})
            o = observations.get(rid)
            dates = [d for _, d in m.values() if d]
            yield [
                rid,
                common or "",
                f"{genus} {epithet}",
                family,
                hood,
                comuna,
                site or "",
                loc.y if loc else "",
                loc.x if loc else "",
                date or "",
                *(m[a][0] if a in m else "" for a in CSV_ATTRIBUTES),
                max(dates) if dates else "",
                *(
                    (
                        labels[f].get(v, v)
                        for f, v in zip(OBS_COLUMNS, o[:-1], strict=True)
                    )
                    if o
                    else [""] * len(OBS_COLUMNS)
                ),
                (o[-1] or "") if o else "",
            ]


def csv_response(queryset, name, lang=DEFAULT_LANGUAGE):
    writer = csv.writer(_Echo())
    stream = (writer.writerow(row) for row in _csv_rows(queryset, lang))
    response = StreamingHttpResponse(
        _with_bom(stream), content_type="text/csv; charset=utf-8"
    )
    stamp = timezone.now().strftime("%Y-%m-%d")
    response["Content-Disposition"] = f'attachment; filename="{name}-{stamp}.csv"'
    return response


def _with_bom(stream):
    """BOM first, so that Excel opens the file as UTF-8."""
    yield "﻿"
    yield from stream


class InventoryViewSet(viewsets.ReadOnlyModelViewSet):
    """Tree inventory: list with filters, full detail and CSV export."""

    permission_classes = [AllowAny]
    serializer_class = InventoryRowSerializer
    pagination_class = InventoryPagination
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_class = InventoryFilter
    ordering_fields = ["id", "scientific_name", "height_m", "dbh_cm", "date"]
    ordering = ["id"]

    def get_queryset(self):
        return inventory_queryset()

    def retrieve(self, request, *args, **kwargs):
        record = (
            BiodiversityRecord.objects.select_related(
                "species__genus__family", "neighborhood__locality", "site"
            )
            .prefetch_related(
                "measurements__study", "observations", "assessments__study"
            )
            .filter(pk=kwargs["pk"])
            .first()
        )
        if record is None:
            return Response(status=status.HTTP_404_NOT_FOUND)
        # Labels come from the models' translations.
        with translation.override(request_language(request)):
            return Response(tree_detail(record))

    @action(detail=False, methods=["get", "post"])
    def export(self, request):
        if request.method == "POST":
            ids = request.data.get("ids") if isinstance(request.data, dict) else None
            if (
                not isinstance(ids, list)
                or not ids
                or len(ids) > MAX_SELECTED
                or not all(isinstance(i, int) for i in ids)
            ):
                return Response(
                    {"error": f"'ids' must be a list of 1 to {MAX_SELECTED} integers."},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            queryset = BiodiversityRecord.objects.filter(id__in=ids)
            return csv_response(
                queryset, "tree-inventory-selected", request_language(request)
            )
        queryset = self.filter_queryset(self.get_queryset())
        return csv_response(queryset, "tree-inventory", request_language(request))

    @action(detail=False, methods=["post"], url_path="query")
    def query(self, request):
        """Trees matching the map's filters and area of interest: summary or download."""
        try:
            params = query.parse(request.data)
        except query.QueryError as exc:
            return Response({"error": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        queryset = query.filter_trees(inventory_queryset(), params)
        fmt = params["format"]
        if fmt == "json":
            return Response(query.summary(queryset))
        lang = query.language(request.data, request_language(request))
        name = "tree-query"
        if fmt == "csv":
            return csv_response(queryset, name, lang)
        rows = _csv_rows(queryset, lang)
        if fmt == "xlsx":
            return query.xlsx_response(rows, name)
        return query.geojson_response(rows, name)

    @action(detail=False, methods=["get"])
    def options(self, request):
        """Comunas and barrios with trees (id, name), for the map's filter lists."""
        return Response(query.options())
