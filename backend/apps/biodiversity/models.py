from django.contrib.gis.db import models as gis_models
from django.db import models
from django.urls import reverse
from django.utils.translation import gettext_lazy as _

from apps.core.models import BaseModel
from apps.places.models import Site, Neighborhood
from apps.taxonomy.models import Species


class BiodiversityRecord(BaseModel):
    """Represents a record of biodiversity, including species, location,
    common name, and other attributes."""

    common_name = models.CharField(
        _("common name"), max_length=100, null=True, blank=True
    )
    species = models.ForeignKey(
        Species,
        on_delete=models.PROTECT,
        related_name="biodiversity_records",
        verbose_name=_("species"),
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
    )
    location = gis_models.PointField(_("location"), srid=4326, geography=True)
    elevation_m = models.FloatField(_("elevation (m)"), null=True, blank=True)
    recorded_by = models.CharField(
        _("recorded by"), max_length=50, default="Cortolima", blank=True
    )
    date = models.DateField(_("recorded date"), null=True, blank=True)

    class Meta:
        verbose_name = _("biodiversity record")
        verbose_name_plural = _("biodiversity records")
        ordering = ["species", "location"]

    def __str__(self):
        """Return a string representation of the biodiversity record.

        Example:
            "Ocobo (Tabebuia rosea) at Parque Centenario"
        """
        common_name = self.common_name if self.common_name else "Unknown"
        return f"{common_name} ({self.species.scientific_name}) at {self.site.name}"

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
