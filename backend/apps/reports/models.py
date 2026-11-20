from django.conf import settings
from django.db import connection, models
from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver
from django.utils.translation import gettext_lazy as _

from apps.biodiversity.models import BiodiversityRecord
from apps.core.models import BaseModel


class OfActiveTreeManager(models.Manager):
    """Measurements / observations of trees that still exist (see
    ``BiodiversityRecord.Status``); ``all_objects`` keeps every row."""

    def get_queryset(self):
        return (
            super()
            .get_queryset()
            .filter(biodiversity_record__status=BiodiversityRecord.Status.ACTIVE)
        )


# Newest first: dated rows before undated ones (the census observations have no date).
LATEST_ORDER = "date DESC NULLS LAST, created_at DESC, id DESC"


def refresh_latest(record_ids=None):
    """Recompute ``is_latest`` of measurements (per tree and attribute) and observations
    (per tree), for the given trees or for all of them.

    Measurements and observations keep their history: a new height does not replace the
    previous one. Statistics use only the newest row, flagged ``is_latest``, so that a tree
    is counted once. ``save`` / ``delete`` refresh it through signals; bulk writers (the
    initial import, file uploads) call this function themselves.
    """
    where = "" if record_ids is None else "WHERE biodiversity_record_id = ANY(%s)"
    params = [] if record_ids is None else [list(record_ids)]
    with connection.cursor() as cursor:
        for table, keys in (
            (Measurement._meta.db_table, "biodiversity_record_id, attribute"),
            (Observation._meta.db_table, "biodiversity_record_id"),
        ):
            join = " AND ".join(f"t.{k} = l.{k}" for k in keys.split(", "))
            cursor.execute(
                f"""
                UPDATE {table} t SET is_latest = (t.id = l.id)
                FROM (
                    SELECT DISTINCT ON ({keys}) id, {keys} FROM {table} {where}
                    ORDER BY {keys}, {LATEST_ORDER}
                ) l
                WHERE {join} AND t.is_latest IS DISTINCT FROM (t.id = l.id)
                """,
                params,
            )


class Study(BaseModel):
    """A research work whose data was loaded into the census (thesis, report, survey).

    Measurements and assessments taken from it point here, so every value can be traced
    to its source and cited.
    """

    slug = models.SlugField(_("identifier"), max_length=80, unique=True)
    title = models.CharField(_("title"), max_length=500)
    authors = models.CharField(_("authors"), max_length=500)
    institution = models.CharField(_("institution"), max_length=255, blank=True)
    year = models.PositiveSmallIntegerField(_("year"))
    date = models.DateField(
        _("date"), help_text=_("Date given to the study's measurements.")
    )
    citation = models.TextField(_("citation"))
    short_citation = models.CharField(
        _("short citation"),
        max_length=100,
        blank=True,
        help_text=_(
            "APA in-text citation shown next to its values, e.g. Torres (2025)."
        ),
    )
    methods = models.TextField(_("methods"), blank=True)
    notes = models.TextField(_("notes"), blank=True)

    class Meta:
        verbose_name = _("study")
        verbose_name_plural = _("studies")
        ordering = ["-date"]

    def __str__(self):
        return self.short_citation or f"{self.authors} ({self.year})"


class Measurement(BaseModel):
    """Records quantifiable attributes like trunk height or total height for trees.

    Stores numeric data collected through defined methodologies with
    tracking of measurement dates and techniques."""

    class MeasuredAttribute(models.TextChoices):
        TRUNK_HEIGHT = "TH", _("trunk height")
        TOTAL_HEIGHT = "HT", _("total height")
        CROWN_DIAMETER = "CD", _("crown diameter")
        DIAMETER_BH = "DBH", _("diameter at breast height")
        VOLUME = "VO", _("volume")
        WOOD_DENSITY = "WD", _("wood density")
        CROWN_DIAMETER_NS = "CDN", _("crown diameter north-south")
        CROWN_DIAMETER_EW = "CDE", _("crown diameter east-west")
        INTERNAL_DAMAGE = "ID", _("internal damage")
        ACOUSTIC_VELOCITY = "AV", _("transverse acoustic velocity")
        GREEN_DENSITY = "GD", _("green wood density")
        DYNAMIC_MOE = "MOE", _("dynamic modulus of elasticity")
        NOT_REPORTED = "NR", _("not reported")

    class MeasurementUnit(models.TextChoices):
        METERS = "m", _("meters (m)")
        CUBIC_METERS = "m3", _("cubic meters (m3)")
        CENTIMETERS = "cm", _("centimeters (cm)")
        GRAMS_PER_CUBIC_CM = "g/cm3", _("grams per cubic centimeter (g/cm3)")
        PERCENT = "%", _("percent (%)")
        METERS_PER_SECOND = "m/s", _("meters per second (m/s)")
        MEGAPASCALS = "MPa", _("megapascals (MPa)")
        NOT_REPORTED = "NR", _("not reported")

    class MeasurementMethod(models.TextChoices):
        OPTICAL_ESTIMATION = "OE", _("optical estimation")
        VOLUME_EQUATION = "VE", _("volume equation")
        DIAMETER_TAPE = "DT", _("diameter tape")
        WOOD_DENSITY_DB = "WD", _("wood density database")
        MEASURING_TAPE = "MT", _("measuring tape")
        LASER_HYPSOMETER = "LH", _("laser hypsometer")
        ACOUSTIC_TOMOGRAPHY = "AT", _("acoustic tomography")
        STRESS_WAVE = "SW", _("stress wave timer")
        INCREMENT_BORER = "IB", _("increment borer core")
        NOT_REPORTED = "NR", _("not reported")

    biodiversity_record = models.ForeignKey(
        BiodiversityRecord,
        on_delete=models.CASCADE,
        related_name="measurements",
        verbose_name=_("biodiversity record"),
    )
    attribute = models.CharField(
        _("measured attribute"),
        max_length=3,
        choices=MeasuredAttribute,
        default=MeasuredAttribute.NOT_REPORTED,
    )
    value = models.FloatField(_("measurement value"))
    unit = models.CharField(
        _("measurement unit"),
        max_length=5,
        choices=MeasurementUnit,
        default=MeasurementUnit.NOT_REPORTED,
    )
    method = models.CharField(
        _("measurement method"),
        max_length=2,
        choices=MeasurementMethod,
        default=MeasurementMethod.NOT_REPORTED,
    )
    date = models.DateField(_("measurement date"), null=True, blank=True)
    study = models.ForeignKey(
        Study,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="measurements",
        verbose_name=_("study"),
    )

    is_latest = models.BooleanField(
        _("latest"),
        default=False,
        editable=False,
        help_text=_("Newest row of this tree (see refresh_latest)."),
    )

    objects = OfActiveTreeManager()
    all_objects = models.Manager()

    class Meta:
        verbose_name = _("measurement")
        verbose_name_plural = _("measurements")
        ordering = ["-created_at"]

    def __str__(self):
        """Returns a string representation of the measurement, including the
        measured attribute, biodiversity record, and measurement date if available.
        Example: "trunk height measurement for biodiversity record #1 on 2025-10-01"
        """
        date_str = f" on {self.date}" if self.date else ""
        return (
            f"{self.get_attribute_display()} measurement for "
            f"biodiversity record #{self.biodiversity_record.id}{date_str}"
        )


class Observation(BaseModel):
    """Captures qualitative assessments of tree conditions and characteristics.

    Documents subjective evaluations including aesthetic value, health status,
    and reproductive phases that complement objective measurements."""

    class ReproductiveCondition(models.TextChoices):
        FLOWERING = "FL", _("flowering")
        FRUITING = "FR", _("fruiting")
        STERILE = "ST", _("sterile")
        NOT_REPORTED = "NR", _("not reported")

    class PhytosanitaryStatus(models.TextChoices):
        HEALTHY = "HE", _("healthy")
        SICK = "SI", _("sick")
        CRITICAL = "CR", _("critical")
        DEAD = "DE", _("dead")
        NOT_REPORTED = "NR", _("not reported")

    class PhysicalCondition(models.TextChoices):
        GOOD = "GO", _("good")
        FAIR = "FA", _("fair")
        POOR = "PO", _("poor")
        NOT_REPORTED = "NR", _("not reported")

    class FoliageDensity(models.TextChoices):
        DENSE = "DE", _("dense")
        MEDIUM = "ME", _("medium")
        SPARSE = "SP", _("sparse")
        NOT_REPORTED = "NR", _("not reported")

    class AestheticValue(models.TextChoices):
        ESSENTIAL = "ES", _("essential")
        EMBLEMATIC = "EM", _("emblematic")
        DESIRABLE = "DE", _("desirable")
        INDIFFERENT = "IN", _("indifferent")
        UNACCEPTABLE = "UN", _("unacceptable")
        NOT_REPORTED = "NR", _("not reported")

    class GrowthPhase(models.IntegerChoices):
        SEEDLING = 1, _("seedling")
        JUVENILE = 2, _("juvenile")
        ADULT = 3, _("adult")

    class YesNoReported(models.TextChoices):
        YES = "Y", _("yes")
        NO = "N", _("no")
        NOT_REPORTED = "NR", _("not reported")

    class HealthCondition(models.TextChoices):
        NATURAL_STATE = "NS", _("natural state")
        NUTRIENT_DEFICIENCY = "ND", _("nutrient deficiency")
        NOT_REPORTED = "NR", _("not reported")

    class DamagePercent(models.TextChoices):
        ZERO = "0", _("0%")
        TWENTY = "20", _("20%")
        FORTY = "40", _("40%")
        SIXTY = "60", _("60%")
        EIGHTY = "80", _("80%")
        HUNDRED = "100", _("100%")
        NOT_REPORTED = "NR", _("not reported")

    biodiversity_record = models.ForeignKey(
        BiodiversityRecord,
        on_delete=models.CASCADE,
        related_name="observations",
        verbose_name=_("biodiversity record"),
    )
    reproductive_condition = models.CharField(
        _("reproductive condition"),
        max_length=2,
        choices=ReproductiveCondition,
        default=ReproductiveCondition.NOT_REPORTED,
    )
    phytosanitary_status = models.CharField(
        _("phytosanitary status"),
        max_length=2,
        choices=PhytosanitaryStatus,
        default=PhytosanitaryStatus.NOT_REPORTED,
    )
    physical_condition = models.CharField(
        _("physical condition"),
        max_length=2,
        choices=PhysicalCondition,
        default=PhysicalCondition.NOT_REPORTED,
    )
    foliage_density = models.CharField(
        _("foliage density"),
        max_length=2,
        choices=FoliageDensity,
        default=FoliageDensity.NOT_REPORTED,
    )
    aesthetic_value = models.CharField(
        _("aesthetic value"),
        max_length=2,
        choices=AestheticValue,
        default=AestheticValue.NOT_REPORTED,
    )
    growth_phase = models.IntegerField(
        _("growth phase"),
        choices=GrowthPhase,
        default=GrowthPhase.SEEDLING,
    )

    # General status fields without explicit name in the original data
    ed = models.CharField(
        _("ed"),
        max_length=2,
        choices=PhysicalCondition,
        default=PhysicalCondition.NOT_REPORTED,
    )
    hc = models.CharField(
        _("hc"),
        max_length=2,
        choices=HealthCondition,
        default=HealthCondition.NOT_REPORTED,
    )
    hcf = models.CharField(
        _("hcf"),
        max_length=2,
        choices=HealthCondition,
        default=HealthCondition.NOT_REPORTED,
    )

    standing = models.CharField(
        _("standing"),
        max_length=2,
        choices=YesNoReported,
        default=YesNoReported.NOT_REPORTED,
    )

    # Yes/No/Not reported fields without explicit names in the original data
    cre = models.CharField(
        _("cre"),
        max_length=2,
        choices=YesNoReported,
        default=YesNoReported.NOT_REPORTED,
    )
    crh = models.CharField(
        _("crh"),
        max_length=2,
        choices=YesNoReported,
        default=YesNoReported.NOT_REPORTED,
    )
    cra = models.CharField(
        _("cra"),
        max_length=2,
        choices=YesNoReported,
        default=YesNoReported.NOT_REPORTED,
    )
    coa = models.CharField(
        _("coa"),
        max_length=2,
        choices=YesNoReported,
        default=YesNoReported.NOT_REPORTED,
    )
    ce = models.CharField(
        _("ce"),
        max_length=2,
        choices=YesNoReported,
        default=YesNoReported.NOT_REPORTED,
    )
    civ = models.CharField(
        _("civ"),
        max_length=2,
        choices=YesNoReported,
        default=YesNoReported.NOT_REPORTED,
    )
    crt = models.CharField(
        _("crt"),
        max_length=2,
        choices=YesNoReported,
        default=YesNoReported.NOT_REPORTED,
    )
    crg = models.CharField(
        _("crg"),
        max_length=2,
        choices=YesNoReported,
        default=YesNoReported.NOT_REPORTED,
    )
    cap = models.CharField(
        _("cap"),
        max_length=2,
        choices=YesNoReported,
        default=YesNoReported.NOT_REPORTED,
    )

    # Percentage damage fields without explicit names in the original data
    rd = models.CharField(
        _("rd"),
        max_length=3,
        choices=DamagePercent,
        default=DamagePercent.ZERO,
    )
    dm = models.CharField(
        _("dm"),
        max_length=3,
        choices=DamagePercent,
        default=DamagePercent.ZERO,
    )
    bbs = models.CharField(
        _("bbs"),
        max_length=3,
        choices=DamagePercent,
        default=DamagePercent.ZERO,
    )
    ab = models.CharField(
        _("ab"),
        max_length=3,
        choices=DamagePercent,
        default=DamagePercent.ZERO,
    )
    pi = models.CharField(
        _("pi"),
        max_length=3,
        choices=DamagePercent,
        default=DamagePercent.ZERO,
    )
    ph = models.CharField(
        _("ph"),
        max_length=3,
        choices=DamagePercent,
        default=DamagePercent.ZERO,
    )
    pa = models.CharField(
        _("pa"),
        max_length=3,
        choices=DamagePercent,
        default=DamagePercent.ZERO,
    )
    pd = models.CharField(
        _("pd"),
        max_length=3,
        choices=DamagePercent,
        default=DamagePercent.ZERO,
    )
    pe = models.CharField(
        _("pe"),
        max_length=3,
        choices=DamagePercent,
        default=DamagePercent.ZERO,
    )
    pp = models.CharField(
        _("pp"),
        max_length=3,
        choices=DamagePercent,
        default=DamagePercent.ZERO,
    )
    po = models.CharField(
        _("po"),
        max_length=3,
        choices=DamagePercent,
        default=DamagePercent.ZERO,
    )
    r_vol = models.CharField(
        _("r_vol"),
        max_length=3,
        choices=DamagePercent,
        default=DamagePercent.ZERO,
    )
    r_cr = models.CharField(
        _("r_cr"),
        max_length=3,
        choices=DamagePercent,
        default=DamagePercent.ZERO,
    )
    r_ce = models.CharField(
        _("r_ce"),
        max_length=3,
        choices=DamagePercent,
        default=DamagePercent.ZERO,
    )

    photo_url = models.URLField(
        _("photo URL"),
        max_length=255,
        null=True,
        blank=True,
        help_text=_("URL of the photo associated with the observation"),
    )
    field_notes = models.TextField(_("field notes"), blank=True)
    recorded_by = models.CharField(_("recorded by"), max_length=50, default="Cortolima")
    accompanying_collectors = models.CharField(
        _("accompanying collectors"), max_length=255, blank=True
    )
    date = models.DateField(_("observation date"), null=True, blank=True)
    study = models.ForeignKey(
        Study,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="observations",
        verbose_name=_("study"),
    )

    is_latest = models.BooleanField(
        _("latest"),
        default=False,
        editable=False,
        help_text=_("Newest row of this tree (see refresh_latest)."),
    )

    objects = OfActiveTreeManager()
    all_objects = models.Manager()

    class Meta:
        verbose_name = _("observation")
        verbose_name_plural = _("observations")
        ordering = ["-created_at"]

    def __str__(self):
        date_str = f" on {self.date}" if self.date else ""
        return f"Observation for {self.biodiversity_record}{date_str}"


@receiver(post_save, sender=Measurement)
@receiver(post_save, sender=Observation)
@receiver(post_delete, sender=Measurement)
@receiver(post_delete, sender=Observation)
def _refresh_latest_of_tree(sender, instance, **kwargs):
    refresh_latest([instance.biodiversity_record_id])


class Assessment(BaseModel):
    """A tree's structural and risk assessment in a study: visual (EVA, ISA form),
    acoustic tomography and biomechanics (ArborSonic 3D), plus the site and crown
    descriptors recorded with it. The numeric results (internal damage, velocity,
    densities, stiffness) are measurements of the same study."""

    class Risk(models.TextChoices):
        LOW = "LO", _("low")
        MODERATE = "MO", _("moderate")
        HIGH = "HI", _("high")
        EXTREME = "EX", _("extreme")

    class DamageLevel(models.TextChoices):
        NONE = "NO", _("no damage")
        LOW = "LO", _("low")
        MEDIUM = "ME", _("medium")
        HIGH = "HI", _("high")
        VERY_HIGH = "VH", _("very high")

    class AgeClass(models.TextChoices):
        YOUNG = "YO", _("young")
        ADULT = "AD", _("adult")
        MATURE = "MA", _("mature")
        OVERMATURE = "OV", _("overmature")

    PlantingSite = BiodiversityRecord.PlantingSite

    biodiversity_record = models.ForeignKey(
        BiodiversityRecord,
        on_delete=models.CASCADE,
        related_name="assessments",
        verbose_name=_("biodiversity record"),
    )
    study = models.ForeignKey(
        Study,
        on_delete=models.PROTECT,
        related_name="assessments",
        verbose_name=_("study"),
    )
    date = models.DateField(_("assessment date"))
    study_code = models.CharField(
        _("code in the study"),
        max_length=30,
        blank=True,
        help_text=_("The tree's number or code in the source, when it differs."),
    )
    visual_risk = models.CharField(
        _("visual risk (EVA)"), max_length=2, choices=Risk, blank=True
    )
    visual_risk_part = models.CharField(
        _("part of the tree at risk"), max_length=60, blank=True
    )
    biomechanical_risk = models.CharField(
        _("biomechanical risk"), max_length=2, choices=Risk, blank=True
    )
    tomography_level = models.CharField(
        _("internal damage level"), max_length=2, choices=DamageLevel, blank=True
    )
    damage_section_diameter_cm = models.FloatField(
        _("diameter of the most damaged section (cm)"), null=True, blank=True
    )
    damage_section_height_cm = models.FloatField(
        _("height of the most damaged section (cm)"), null=True, blank=True
    )
    tomography_sections = models.PositiveSmallIntegerField(
        _("sections scanned"), null=True, blank=True
    )
    age_class = models.CharField(
        _("age class"), max_length=2, choices=AgeClass, blank=True
    )
    planting_site = models.CharField(
        _("planting site"), max_length=2, choices=PlantingSite, blank=True
    )
    crown_exposure_class = models.PositiveSmallIntegerField(
        _("crown light exposure (1-5)"), null=True, blank=True
    )
    crown_exposure_percent = models.PositiveSmallIntegerField(
        _("crown light exposure (%)"), null=True, blank=True
    )
    notes = models.TextField(_("notes"), blank=True)

    class Meta:
        verbose_name = _("assessment")
        verbose_name_plural = _("assessments")
        ordering = ["-date"]
        constraints = [
            models.UniqueConstraint(
                fields=["biodiversity_record", "study"],
                name="unique_assessment_per_study",
            )
        ]

    def __str__(self):
        return f"{self.study} - #{self.biodiversity_record_id}"


class Upload(BaseModel):
    """A file sent from the Reports page to update the tree database.

    It is first checked (``preview``: what would change, row errors) and written only when
    the user confirms (``applied``). The file is kept, so every change to the database can
    be traced to the file and the user that made it.
    """

    class Status(models.TextChoices):
        PREVIEW = "PR", _("preview")
        APPLIED = "AP", _("applied")

    file = models.FileField(_("file"), upload_to="uploads/%Y/%m/")
    name = models.CharField(_("file name"), max_length=255)
    format = models.CharField(_("format"), max_length=10)
    status = models.CharField(
        _("status"), max_length=2, choices=Status, default=Status.PREVIEW
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="uploads",
        verbose_name=_("user"),
    )
    summary = models.JSONField(_("summary"), default=dict)
    applied_at = models.DateTimeField(_("applied at"), null=True, blank=True)

    class Meta:
        verbose_name = _("upload")
        verbose_name_plural = _("uploads")
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.name} ({self.get_status_display()})"
