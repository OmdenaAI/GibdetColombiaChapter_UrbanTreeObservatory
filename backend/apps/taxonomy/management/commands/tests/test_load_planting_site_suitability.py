import pytest
from django.core.management import CommandError, call_command

from apps.taxonomy.factories import GenusFactory, SpeciesFactory

HEADER = "species,PA,RB,ME,GS,SW,TP,FG"


def matrix(tmp_path, *rows, header=HEADER):
    path = tmp_path / "matrix.csv"
    path.write_text("\n".join([header, *rows]), encoding="utf-8")
    return path


def species(genus, name):
    return SpeciesFactory(genus=GenusFactory(name=genus), name=name)


@pytest.mark.django_db
def test_apt_and_conditional_sites_are_recommended(tmp_path):
    ficus, other = species("Ficus", "benjamina"), species("Tabebuia", "rosea")
    path = matrix(tmp_path, "Ficus benjamina,A,?,N,C,N,N,N")

    call_command("load_planting_site_suitability", file=path)

    ficus.refresh_from_db()
    other.refresh_from_db()
    assert ficus.recommended_planting_sites == ["PA", "GS"]
    assert other.recommended_planting_sites == []


@pytest.mark.django_db
def test_is_idempotent_and_dry_run_writes_nothing(tmp_path, capsys):
    ficus = species("Ficus", "benjamina")
    path = matrix(
        tmp_path, "Ficus benjamina,A,A,?,?,?,?,?", "Ceiba pentandra,A,?,N,?,N,N,N"
    )

    call_command("load_planting_site_suitability", file=path, dry_run=True)
    ficus.refresh_from_db()
    assert ficus.recommended_planting_sites == []
    assert "would update 1" in capsys.readouterr().out

    call_command("load_planting_site_suitability", file=path)
    call_command("load_planting_site_suitability", file=path)
    out = capsys.readouterr().out
    assert "updated 0" in out and "Not in the platform: Ceiba pentandra" in out
    ficus.refresh_from_db()
    assert ficus.recommended_planting_sites == ["PA", "RB"]


@pytest.mark.django_db
@pytest.mark.parametrize(
    "header,row,message",
    [
        (HEADER, "Ficus benjamina,A,?,N,C,N,N,X", "unknown code X"),
        ("species,PA,RB", "Ficus benjamina,A,?", "missing columns"),
    ],
)
def test_rejects_bad_files(tmp_path, header, row, message):
    with pytest.raises(CommandError, match=message):
        call_command(
            "load_planting_site_suitability", file=matrix(tmp_path, row, header=header)
        )


def test_versioned_matrix_is_valid():
    from apps.taxonomy.management.commands.load_planting_site_suitability import (
        DEFAULT_FILE,
        read_matrix,
    )

    assert len(read_matrix(DEFAULT_FILE)) == 85
