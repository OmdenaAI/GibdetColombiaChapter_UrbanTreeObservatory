import pytest
from django.contrib.gis.geos import Point
from django.core.management import CommandError, call_command

from apps.biodiversity.factories import BiodiversityRecordFactory
from apps.biodiversity.management.commands.load_planting_sites import metres

# Census points in EPSG:3116 and the same points in WGS84 (as the platform stores them).
A = ("8828670887", "9772914385", -75.13274701359529, 4.390097052172941)
B = ("8828588243", "9773067245", -75.13282165241242, 4.390235156993443)


def census(tmp_path, *rows):
    path = tmp_path / "sites.csv"
    lines = ["num_arbol,X,Y,emplazamiento", *(",".join(r) for r in rows)]
    path.write_text("\n".join(lines), encoding="utf-8")
    return path


def tree(point):
    return BiodiversityRecordFactory(location=Point(point[2], point[3]))


def test_coordinates_without_decimal_point():
    assert metres("8828670887") == pytest.approx(882867.0887)
    assert metres("882867") == 882867.0
    assert metres("882867.5") == 882867.5


@pytest.mark.django_db
def test_sets_the_site_by_position(tmp_path):
    a, b, new = tree(A), tree(B), BiodiversityRecordFactory()
    path = census(tmp_path, ("1", A[0], A[1], "Anden"), ("2", B[0], B[1], "Parque"))

    call_command("load_planting_sites", file=path)

    for record in (a, b, new):
        record.refresh_from_db()
    assert (a.planting_site, b.planting_site, new.planting_site) == ("SW", "PA", "")


@pytest.mark.django_db
def test_shared_point_with_different_sites_stays_empty(tmp_path):
    a = tree(A)
    path = census(tmp_path, ("1", A[0], A[1], "Anden"), ("1_a", A[0], A[1], "Parque"))
    call_command("load_planting_sites", file=path)
    a.refresh_from_db()
    assert a.planting_site == ""


@pytest.mark.django_db
def test_dry_run_and_unknown_site(tmp_path):
    a = tree(A)
    call_command(
        "load_planting_sites",
        file=census(tmp_path, ("1", A[0], A[1], "Anden")),
        dry_run=True,
    )
    a.refresh_from_db()
    assert a.planting_site == ""
    with pytest.raises(CommandError, match="Terraza"):
        call_command(
            "load_planting_sites", file=census(tmp_path, ("1", A[0], A[1], "Terraza"))
        )
