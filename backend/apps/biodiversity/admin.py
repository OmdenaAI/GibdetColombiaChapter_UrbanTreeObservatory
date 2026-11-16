from django.contrib import admin
from django.contrib.gis.admin import GISModelAdmin
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from .models import BiodiversityRecord


@admin.register(BiodiversityRecord)
class BiodiversityRecordAdmin(GISModelAdmin):
    list_display = (
        "id",
        "common_name",
        "species_name",
        "site_name",
        "neighborhood_name",
        "date",
        "status",
    )
    list_filter = (
        "status",
        "removal_reason",
        "date",
        "species__life_form",
        "neighborhood__locality",
    )
    search_fields = (
        "id",
        "common_name",
        "species__name",
        "species__genus__name",
        "site__name",
        "neighborhood__name",
        "neighborhood__locality__name",
        "system_comment",
    )
    raw_id_fields = ("species", "site", "neighborhood")
    readonly_fields = ("id", "created_at", "updated_at", "uuid", "system_comment")
    date_hierarchy = "date"
    list_per_page = 25
    actions = ["mark_removed", "mark_active"]

    def get_queryset(self, request):
        # Every record, also the removed ones (the default manager hides them).
        return BiodiversityRecord.all_objects.select_related(
            "species__genus", "site", "neighborhood"
        )

    @admin.action(description=_("Mark selected trees as removed (felled, today)"))
    def mark_removed(self, request, queryset):
        n = queryset.update(
            status=BiodiversityRecord.Status.REMOVED,
            removed_on=timezone.localdate(),
            removal_reason=BiodiversityRecord.RemovalReason.FELLED,
            updated_at=timezone.now(),
        )
        self.message_user(
            request,
            _(
                "%(n)d trees marked as removed. Edit them to adjust the date, reason "
                "or note."
            )
            % {"n": n},
        )

    @admin.action(description=_("Mark selected trees as active again"))
    def mark_active(self, request, queryset):
        n = queryset.update(
            status=BiodiversityRecord.Status.ACTIVE,
            removed_on=None,
            removal_reason="",
            removal_note="",
            updated_at=timezone.now(),
        )
        self.message_user(request, _("%(n)d trees marked as active.") % {"n": n})

    @admin.display(description="Species")
    def species_name(self, obj):
        return f"{obj.species.genus.name} {obj.species.name}"

    @admin.display(description="Site")
    def site_name(self, obj):
        return obj.site.name

    @admin.display(description="Neighborhood")
    def neighborhood_name(self, obj):
        return obj.neighborhood.name
