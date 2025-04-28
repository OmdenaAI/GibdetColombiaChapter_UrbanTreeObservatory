from django.db import models
from django.utils.translation import gettext_lazy as _

from apps.core.models import BaseModel


class Site(BaseModel):
    """Represents a general location of biodiversity records."""

    name = models.CharField(_("site name"), max_length=50)
    zone = models.PositiveSmallIntegerField(_("zone"), null=True, blank=True)
    subzone = models.PositiveSmallIntegerField(_("subzone"), null=True, blank=True)

    class Meta:
        verbose_name = _("site")
        verbose_name_plural = _("sites")
        ordering = ["name"]
        constraints = [
            models.UniqueConstraint(
                fields=["name", "zone", "subzone"],
                name="unique_site_per_zone_subzone",
            )
        ]

    def __str__(self):
        """Returns a string representation of the site."""
        components = [
            self.name,
            self.zone and self.subzone and f"Zone {self.zone}" or None,
            self.subzone and f"Subzone {self.subzone}" or None,
        ]
        return ", ".join(filter(None, components))
