from django.contrib.gis.db import models as gis_models
from django.db import models
from django.urls import reverse
from django.utils.translation import gettext_lazy as _
from django.utils.translation import pgettext_lazy

from apps.core.models import BaseModel
from apps.places.models import Neighborhood, Site
from apps.taxonomy.models import Species


class ActiveRecordManager(models.Manager):
    """Only the trees that still exist (``status`` active)."""

    def get_queryset(self):
        return super().get_queryset().filter(status=BiodiversityRecord.Status.ACTIVE)


class BiodiversityRecord(BaseModel):
    """Represents a record of biodiversity, including species, location,
    common name, and other attributes.

    A tree that no longer exists (felled, fallen...) is kept with ``status`` removed and
    the date, reason and a note of the removal: the census data stays in the database,
    but the platform does not show it. ``objects`` (the default manager, also used by
    related managers such as ``species.biodiversity_records``) returns active trees only;
    ``all_objects`` returns every record (admin, data maintenance).
    """

    class Status(models.TextChoices):
        ACTIVE = "AC", _("active")
        REMOVED = "RE", _("removed")

    class PlantingSite(models.TextChoices):
        """Where the tree grows, as the census form records it (``emplazamiento``)."""

        PARK = "PA", _("park")
        SIDEWALK = "SW", _("sidewalk")
        MEDIAN = "ME", _("road median")
        GREEN_STRIP = "GS", _("green strip")
        TREE_PIT = "TP", _("tree pit")
        FRONT_GARDEN = "FG", _("front garden")
        ROUNDABOUT = "RB", _("roundabout")

    class RemovalReason(models.TextChoices):
        FELLED = "FE", _("felled")
        FALLEN = "FA", _("fallen")
        DEAD_STANDING = "DS", _("dead standing")
        TRANSPLANTED = "TR", _("transplanted")
        OTHER = "OT", _("other")

    common_name = models.CharField(
        _("common name"), max_length=100, null=True, blank=True
    )
    species = models.ForeignKey(
        Species,
        on_delete=models.PROTECT,
        related_name="biodiversity_records",
        verbose_name=pgettext_lazy("plural", "species"),
    )
    neighborhood = models.ForeignKey(
        Neighborhood,
        on_delete=models.PROTECT,
        related_name="biodiversity_records",
        verbose_name=_("neighborhood"),
    )
    site = models.ForeignKey(
        Site,
        on_delete=models.PROTECT,
        related_name="biodiversity_records",
        verbose_name=_("site"),
        null=True,
        blank=True,
    )
    location = gis_models.PointField(_("location"), srid=4326, geography=True)
    elevation_m = models.FloatField(_("elevation (m)"), null=True, blank=True)
    recorded_by = models.CharField(
        _("recorded by"), max_length=50, default="Cortolima", blank=True
    )
    date = models.DateField(_("recorded date"), null=True, blank=True)
    planting_site = models.CharField(
        _("planting site"),
        max_length=2,
        choices=PlantingSite,
        blank=True,
        db_index=True,
        help_text=_("Park, sidewalk, road median... Empty when unknown."),
    )
    system_comment = models.TextField(
        _("system comment"), null=True, blank=True, editable=False
    )
    status = models.CharField(
        _("status"),
        max_length=2,
        choices=Status,
        default=Status.ACTIVE,
        db_index=True,
    )
    removed_on = models.DateField(_("removal date"), null=True, blank=True)
    removal_reason = models.CharField(
        _("removal reason"), max_length=2, choices=RemovalReason, blank=True
    )
    removal_note = models.TextField(_("removal note"), blank=True)

    objects = ActiveRecordManager()
    all_objects = models.Manager()

    class Meta:
        verbose_name = _("biodiversity record")
        verbose_name_plural = _("biodiversity records")
        ordering = ["species", "location"]

    def __str__(self):
        """Return a string representation of the biodiversity record.

        Example:
            "Ocobo (Tabebuia rosea) at Alto De La Cruz"
        """
        common_name = self.common_name if self.common_name else "Unknown"
        return f"{common_name} ({self.species.scientific_name}) at {self.neighborhood.name}"

    def get_admin_url(self):
        return reverse(
            f"admin:{self._meta.app_label}_{self._meta.model_name}_change",
            args=[self.pk],
        )

    @property
    def longitude(self):
        """Get the longitude of the biodiversity record's location"""
        return self.location.x if self.location else None

    @property
    def latitude(self):
        """Get the latitude of the biodiversity record's location"""
        return self.location.y if self.location else None
