import datetime

import pytest
from django.contrib.gis.geos import Point
from django.core.management import call_command

from apps.biodiversity.factories import BiodiversityRecordFactory
from apps.biodiversity.management.commands.fix_census_dates import EXCEL_EPOCH
from apps.reports.factories import MeasurementFactory

MAY, JUNE = datetime.date(2014, 5, 8), datetime.date(2014, 6, 1)


def tree(lon, date, **dbh):
    record = BiodiversityRecordFactory(location=Point(lon, 4.44), date=date)
    MeasurementFactory(biodiversity_record=record, attribute="DBH", date=date, **dbh)
    return record


@pytest.mark.django_db
def test_takes_the_most_frequent_date_of_the_neighbours():
    undated = tree(-75.2000, EXCEL_EPOCH)
    tree(-75.2005, MAY)  # ~55 m
    tree(-75.2008, MAY)
    tree(-75.2010, JUNE)
    tree(-75.2100, JUNE)  # ~1.1 km: outside the radius
    tree(-75.2101, JUNE)

    call_command("fix_census_dates")

    undated.refresh_from_db()
    assert undated.date == MAY
    assert {m.date for m in undated.measurements.all()} == {MAY}
    call_command("fix_census_dates")  # nothing left to fix
    undated.refresh_from_db()
    assert undated.date == MAY


@pytest.mark.django_db
def test_dry_run_and_isolated_trees_keep_their_date():
    undated = tree(-75.2000, EXCEL_EPOCH)
    tree(-75.2005, MAY)
    alone = tree(-74.0, EXCEL_EPOCH)

    call_command("fix_census_dates", dry_run=True)
    undated.refresh_from_db()
    assert undated.date == EXCEL_EPOCH

    call_command("fix_census_dates")
    alone.refresh_from_db()
    assert alone.date == EXCEL_EPOCH
