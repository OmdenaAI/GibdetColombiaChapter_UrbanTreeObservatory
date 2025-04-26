from django.contrib.gis.db import models as gis_models
from django.db import models
from django.utils.translation import gettext_lazy as _

from apps.core.models import BaseModel


class Country(models.Model):
    """Represents a country."""

    name = models.CharField(_("country"), max_length=50, unique=True)
    boundary = gis_models.MultiPolygonField(
        _("country boundary"),
        geography=True,
        null=True,
        blank=True,
    )

    class Meta:
        ordering = ["name"]
        verbose_name = _("country")
        verbose_name_plural = _("countries")

    def __str__(self):
        return self.name


class Department(models.Model):
    """Represents a department within a country."""

    name = models.CharField(_("department"), max_length=50, unique=True)
    country = models.ForeignKey(
        Country,
        on_delete=models.CASCADE,
        related_name="departments",
        verbose_name=_("country"),
    )
    boundary = gis_models.MultiPolygonField(
        _("department boundary"),
        geography=True,
        null=True,
        blank=True,
    )

    class Meta:
        ordering = ["name"]
        verbose_name = _("department")
        verbose_name_plural = _("departments")

    def __str__(self):
        return f"{self.name}, {self.country.name}"


class Municipality(models.Model):
    """Represents a municipality within a department."""

    name = models.CharField(_("municipality"), max_length=50, unique=True)
    department = models.ForeignKey(
        Department,
        on_delete=models.CASCADE,
        related_name="municipalities",
        verbose_name=_("department"),
    )
    boundary = gis_models.MultiPolygonField(
        _("municipality boundary"),
        geography=True,
        null=True,
        blank=True,
    )

    class Meta:
        ordering = ["name"]
        verbose_name = _("municipality")
        verbose_name_plural = _("municipalities")

    def __str__(self):
        return f"{self.name}, {self.department.name}"


class Locality(BaseModel):
    """Represents a locality within a municipality."""

    name = models.CharField(_("locality"), max_length=50, unique=True)
    municipality = models.ForeignKey(
        Municipality,
        on_delete=models.CASCADE,
        related_name="localities",
        verbose_name=_("municipality"),
    )
    boundary = gis_models.MultiPolygonField(
        _("locality boundary"),
        geography=True,
        null=True,
        blank=True,
    )
    calculated_area_m2 = models.FloatField(
        _("calculated area (m²)"),
        null=True,
        blank=True,
    )
    population_2019 = models.PositiveIntegerField(
        _("population 2019"),
        null=True,
        blank=True,
    )

    class Meta:
        ordering = ["name"]
        verbose_name = _("locality")
        verbose_name_plural = _("localities")

    def __str__(self):
        return f"{self.name}, {self.municipality.name}"


class Neighborhood(BaseModel):
    """Represents a neighborhood within a locality."""

    name = models.CharField(_("neighborhood"), max_length=50, unique=True)
    locality = models.ForeignKey(
        Locality,
        on_delete=models.CASCADE,
        related_name="neighborhoods",
        verbose_name=_("locality"),
    )
    boundary = gis_models.MultiPolygonField(
        _("neighborhood boundary"),
        geography=True,
        null=True,
        blank=True,
    )

    class Meta:
        ordering = ["name"]
        verbose_name = _("neighborhood")
        verbose_name_plural = _("neighborhoods")

    def __str__(self):
        return f"{self.name}, {self.locality.name}, {self.locality.municipality.name}"
