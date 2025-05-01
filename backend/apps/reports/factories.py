import factory

from apps.biodiversity.factories import BiodiversityRecordFactory
from apps.core.factories import BaseFactory
from apps.reports.models import Measurement, Observation


class MeasurementFactory(BaseFactory):
    class Meta:
        model = Measurement

    biodiversity_record = factory.SubFactory(BiodiversityRecordFactory)
    attribute = factory.Iterator(
        [choice[0] for choice in Measurement.MeasuredAttribute.choices]
    )
    value = factory.Faker("pyfloat", min_value=0, max_value=100)
    unit = factory.Iterator(
        [choice[0] for choice in Measurement.MeasurementUnit.choices]
    )
    method = factory.Iterator(
        [choice[0] for choice in Measurement.MeasurementMethod.choices]
    )
    date = factory.Faker("date_this_decade")


class ObservationFactory(BaseFactory):
    class Meta:
        model = Observation

    biodiversity_record = factory.SubFactory(BiodiversityRecordFactory)
    reproductive_condition = factory.Iterator(
        [choice[0] for choice in Observation.ReproductiveCondition.choices]
    )
    phytosanitary_status = factory.Iterator(
        [choice[0] for choice in Observation.PhytosanitaryStatus.choices]
    )
    physical_condition = factory.Iterator(
        [choice[0] for choice in Observation.PhysicalCondition.choices]
    )
    foliage_density = factory.Iterator(
        [choice[0] for choice in Observation.FoliageDensity.choices]
    )
    aesthetic_value = factory.Iterator(
        [choice[0] for choice in Observation.AestheticValue.choices]
    )
    growth_phase = factory.Iterator(
        [choice[0] for choice in Observation.GrowthPhase.choices]
    )

    # General status fields
    ed = factory.Iterator(
        [choice[0] for choice in Observation.PhysicalCondition.choices]
    )
    hc = factory.Iterator([choice[0] for choice in Observation.HealthCondition.choices])
    hcf = factory.Iterator(
        [choice[0] for choice in Observation.HealthCondition.choices]
    )
    standing = factory.Iterator(
        [choice[0] for choice in Observation.YesNoReported.choices]
    )

    # Yes/No fields
    cre = factory.Iterator([choice[0] for choice in Observation.YesNoReported.choices])
    crh = factory.Iterator([choice[0] for choice in Observation.YesNoReported.choices])
    cra = factory.Iterator([choice[0] for choice in Observation.YesNoReported.choices])
    coa = factory.Iterator([choice[0] for choice in Observation.YesNoReported.choices])
    ce = factory.Iterator([choice[0] for choice in Observation.YesNoReported.choices])
    civ = factory.Iterator([choice[0] for choice in Observation.YesNoReported.choices])
    crt = factory.Iterator([choice[0] for choice in Observation.YesNoReported.choices])
    crg = factory.Iterator([choice[0] for choice in Observation.YesNoReported.choices])
    cap = factory.Iterator([choice[0] for choice in Observation.YesNoReported.choices])

    # Percentage damage fields
    rd = factory.Iterator([choice[0] for choice in Observation.DamagePercent.choices])
    dm = factory.Iterator([choice[0] for choice in Observation.DamagePercent.choices])
    bbs = factory.Iterator([choice[0] for choice in Observation.DamagePercent.choices])
    ab = factory.Iterator([choice[0] for choice in Observation.DamagePercent.choices])
    pi = factory.Iterator([choice[0] for choice in Observation.DamagePercent.choices])
    ph = factory.Iterator([choice[0] for choice in Observation.DamagePercent.choices])
    pa = factory.Iterator([choice[0] for choice in Observation.DamagePercent.choices])
    pd = factory.Iterator([choice[0] for choice in Observation.DamagePercent.choices])
    pe = factory.Iterator([choice[0] for choice in Observation.DamagePercent.choices])
    pp = factory.Iterator([choice[0] for choice in Observation.DamagePercent.choices])
    po = factory.Iterator([choice[0] for choice in Observation.DamagePercent.choices])
    r_vol = factory.Iterator(
        [choice[0] for choice in Observation.DamagePercent.choices]
    )
    r_cr = factory.Iterator([choice[0] for choice in Observation.DamagePercent.choices])
    r_ce = factory.Iterator([choice[0] for choice in Observation.DamagePercent.choices])

    # Other fields
    photo_url = factory.Faker("image_url")
    field_notes = factory.Faker("paragraph")
    recorded_by = factory.Faker("name")
    accompanying_collectors = factory.Faker("name")
    date = factory.Faker("date_this_decade")
