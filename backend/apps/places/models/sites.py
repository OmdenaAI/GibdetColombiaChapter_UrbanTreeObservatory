from django.db import models
from django.utils.translation import gettext_lazy as _

from apps.core.models import BaseModel
from .spatial import Locality


class Place(BaseModel):
    """Represents a general location of biodiversity records."""

    name = models.CharField(_("site name"), max_length=50)
    locality = models.ForeignKey(
        Locality,
        on_delete=models.CASCADE,
        related_name="places",
        verbose_name=_("locality"),
    )
    populated_center = models.CharField(_("populated center"), max_length=50)
    zone = models.PositiveSmallIntegerField(_("zone"), null=True, blank=True)
    subzone = models.PositiveSmallIntegerField(_("subzone"), null=True, blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["locality", "name"],
                name="unique_place",
            )
        ]
        ordering = ["name"]

    def __str__(self):
        """Returns a string representation of the place, including the site,
        municipality, department, and country.

        Example: "Parque Centenario, Ibagué, Tolima, Colombia"
        """
        municipality = self.locality.municipality
        department = municipality.department
        country = department.country
        components = [self.name, municipality.name, department.name, country.name]
        return ", ".join(filter(None, components))
