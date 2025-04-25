"""
Key database constraints and model design notes:

- Each FunctionalGroup can have at most one TraitValue per Trait
  (enforced by a unique constraint on (trait, functional_group)).
- Each Trait is unique by its type (Trait.type is unique), so a
  FunctionalGroup can have at most one TraitValue for each TraitType.
- A FunctionalGroup may have zero to n TraitValue relations,
  corresponding to the available n TraitType choices (four initially).
- TraitValue allows partial values: min_value and max_value can be
  null independently.
- These constraints ensure that trait values are not duplicated
  for any functional group and trait combination, and that the
  schema is extensible if new TraitTypes are added.
"""

from django.db import models
from django.urls import reverse
from django.utils.translation import gettext_lazy as _
from django.core.validators import MinValueValidator

from apps.core.models import BaseModel


class Family(BaseModel):
    """Represents a family of species."""

    name = models.CharField(_("family name"), max_length=50, unique=True)

    class Meta:
        verbose_name = _("family")
        verbose_name_plural = _("families")
        ordering = ["name"]

    def __str__(self):
        return self.name


class Genus(BaseModel):
    """Represents a genus of species."""

    name = models.CharField(_("genus name"), max_length=50, unique=True)
    family = models.ForeignKey(
        Family,
        on_delete=models.CASCADE,
        related_name="genera",
        verbose_name=_("family"),
    )

    class Meta:
        verbose_name = _("genus")
        verbose_name_plural = _("genera")
        ordering = ["name"]

    def __str__(self):
        return self.name


class Trait(BaseModel):
    """Represents a trait that can be measured for a species group."""

    class TraitType(models.TextChoices):
        CARBON_SEQUESTRATION = "CS", _("carbon sequestration (%)")
        SHADE_IDX = "SH", _("shade index")
        CANOPY_DIAMETER = "CY", _("canopy diameter (m)")
        HEIGHT_MAX = "HX", _("maximum height (m)")

    type = models.CharField(
        _("trait type"),
        max_length=2,
        choices=TraitType,
        unique=True,
    )

    class Meta:
        ordering = ["type"]

    def __str__(self):
        return self.get_type_display()


class TraitValue(BaseModel):
    """Represents a specific trait value range for a functional group."""

    trait = models.ForeignKey(
        Trait,
        on_delete=models.CASCADE,
        related_name="trait_values",
        verbose_name=_("trait"),
    )
    functional_group = models.ForeignKey(
        "FunctionalGroup",
        on_delete=models.CASCADE,
        related_name="trait_values",
        verbose_name=_("functional group"),
    )
    min_value = models.FloatField(
        _("minimum value"),
        null=True,
        blank=True,
        validators=[MinValueValidator(0.0)],
        help_text=_("Minimum value for this trait in the functional group"),
    )
    max_value = models.FloatField(
        _("maximum value"),
        null=True,
        blank=True,
        validators=[MinValueValidator(0.0)],
        help_text=_("Maximum value for this trait in the functional group"),
    )

    class Meta:
        verbose_name = _("trait value")
        verbose_name_plural = _("trait values")
        constraints = [
            models.UniqueConstraint(
                fields=["trait", "functional_group"],
                name="unique_trait_per_functional_group",
            ),
            models.CheckConstraint(
                condition=models.Q(min_value__isnull=True) | models.Q(min_value__gte=0),
                name="min_value_greater_than_zero",
            ),
            models.CheckConstraint(
                condition=models.Q(max_value__isnull=True) | models.Q(max_value__gte=0),
                name="max_value_greater_than_zero",
            ),
        ]

    def __str__(self):
        return f"{self.trait}: {self.min_value}-{self.max_value}"


class FunctionalGroup(BaseModel):
    """Represents a functional group of species."""

    group_id = models.PositiveSmallIntegerField(
        _("group id"),
        help_text=_("Unique identifier for the functional group"),
        unique=True,
    )
    traits = models.ManyToManyField(
        Trait,
        through="TraitValue",
        related_name="functional_groups",
        verbose_name=_("traits"),
    )

    class Meta:
        verbose_name = _("functional group")
        verbose_name_plural = _("functional groups")
        ordering = ["group_id"]

    def __str__(self):
        return f"Group {str(self.group_id)}"


class Species(BaseModel):
    """Represents a species, including its genus and family."""

    class Origin(models.TextChoices):
        NATIVE = "NT", _("native")
        CULTIVATED = "CU", _("cultivated")
        NATIVE_CULTIVATED = "NC", _("native | cultivated")
        NATURALIZED = "NU", _("naturalized")
        NATURALIZED_CULTIVATED = "NL", _("naturalized | cultivated")
        ENDEMIC = "EN", _("endemic")
        NOT_IDENTIFIED = "NI", _("not identified")

    class IUCNStatus(models.TextChoices):
        DATA_DEFICIENT = "DD", _("data deficient")
        LEAST_CONCERN = "LC", _("least concern")
        CONSERVATION_DEPENDENT = "CD", _("lower risk / conservation dependent")
        NEAR_THREATENED = "NT", _("near threatened")
        VULNERABLE = "VU", _("vulnerable")
        ENDANGERED = "EN", _("endangered")
        CRITICALLY_ENDANGERED = "CR", _("critically endangered")
        EXTINCT_IN_WILD = "EW", _("extinct in the wild")
        EXTINCT = "EX", _("extinct")
        NOT_EVALUATED = "NE", _("not evaluated")

    class LifeForm(models.TextChoices):
        TREE = "TR", _("tree")
        PALM_TREE = "PT", _("palm tree")
        SHRUB = "SH", _("shrub")
        OTHER = "OT", _("other")

    class CanopyShape(models.TextChoices):
        BROAD = "BD", _("broad")
        CAULIROSULA_FAN = "CF", _("caulirosula - fan")
        CAULIROSULA_FEATHER = "CR", _("caulirosula - feather")
        CAULIROSULA_SESPITOSO = "CS", _("caulirosula sespitoso")
        COLUMNAR = "CO", _("columnar")
        GLOBOSE = "GL", _("globose")
        IRREGULAR = "IR", _("irregular")
        OVAL = "OV", _("oval")
        PYRAMIDAL = "PY", _("pyramidal")
        SEMIGLOBOSE = "SG", _("semiglobose")
        SPREADING = "SP", _("spreading")
        OTHER = "OT", _("other")
        NOT_IDENTIFIED = "NI", _("not identified")

    class FlowerColor(models.TextChoices):
        BROWN = "BR", _("brown")
        FUCHSIA = "FU", _("fuchsia")
        GREEN = "GR", _("green")
        ORANGE = "OR", _("orange")
        PINK = "PI", _("pink")
        RED = "RE", _("red")
        VIOLET = "VI", _("violet")
        WHITE = "WH", _("white")
        YELLOW = "YE", _("yellow")
        OTHER = "OT", _("other")
        NOT_IDENTIFIED = "NI", _("not identified")

    genus = models.ForeignKey(
        Genus,
        on_delete=models.CASCADE,
        related_name="species",
        verbose_name=_("genus"),
    )
    name = models.CharField(
        _("species name"), max_length=50, help_text=_("Species name without the genus")
    )
    functional_group = models.ForeignKey(
        FunctionalGroup,
        on_delete=models.SET_NULL,
        related_name="species",
        verbose_name=_("functional group"),
        null=True,
    )
    accepted_scientific_name = models.CharField(
        _("accepted scientific name"),
        max_length=150,
        help_text=_(
            "Scientific genus and species name with optional reference to whom named it"
        ),
        default="No identificado",
    )
    origin = models.CharField(
        _("origin"),
        max_length=2,
        choices=Origin,
        default=Origin.NOT_IDENTIFIED,
    )
    iucn_status = models.CharField(
        _("IUCN status"),
        max_length=2,
        choices=IUCNStatus,
        default=IUCNStatus.NOT_EVALUATED,
    )
    life_form = models.CharField(
        _("life form"),
        max_length=2,
        choices=LifeForm,
        default=LifeForm.TREE,
    )
    canopy_shape = models.CharField(
        _("canopy shape"),
        max_length=50,
        choices=CanopyShape,
        default=CanopyShape.NOT_IDENTIFIED,
    )
    flower_color = models.CharField(
        _("flower color"),
        max_length=50,
        choices=FlowerColor,
        default=FlowerColor.NOT_IDENTIFIED,
    )
    gbif_id = models.PositiveIntegerField(
        _("GBIF ID"), null=True, blank=True, help_text=_("GBIF species identifier")
    )
    identified_by = models.CharField(
        _("identified by"), max_length=255, default="Cortolima"
    )
    date = models.DateField(_("identified date"), null=True, blank=True)

    class Meta:
        verbose_name = _("species")
        verbose_name_plural = _("species")
        ordering = ["genus", "name"]
        constraints = [
            models.UniqueConstraint(
                fields=["genus", "name"],
                name="unique_genus_species",
            ),
        ]

    def __str__(self):
        return self.scientific_name

    def get_admin_url(self):
        return reverse(
            f"admin:{self._meta.app_label}_{self._meta.model_name}_change",
            args=[self.pk],
        )

    @property
    def gbif_url(self):
        """Return the GBIF URL for the species if gbif_id exists."""
        if self.gbif_id is not None:
            return f"https://www.gbif.org/species/{self.gbif_id}"
        return None

    @property
    def scientific_name(self):
        """Return the scientific name of the species."""
        return f"{self.genus.name} {self.name}"

    @property
    def tropical_plants_url(self):
        """Return the URL for the species on the Useful Tropical Plants Database."""
        return f"https://tropical.theferns.info/viewtropical.php?id={self.genus.name}+{self.name}"
