import json

import pytest
from django.core.management import call_command
from django.urls import reverse
from rest_framework import status

from apps.taxonomy.factories import SpeciesFactory
from apps.taxonomy.models import ManualEntry

SECTIONS = [
    {"title": "Descripción", "text": "Árbol de 5 a 15 m."},
    {"title": "Localización recomendada", "text": "Parques. **Evaluar el espacio.**"},
]


def entry_for(species, **extra):
    return {
        "species": species.scientific_name,
        "title": "FICUS BENJAMINA",
        "scientific_name": f"{species.scientific_name} L.",
        "family": "Moraceae",
        "common_names": "ficus",
        "origin": "India",
        "pages": [184, 185],
        "sections": SECTIONS,
        **extra,
    }


@pytest.mark.django_db
class TestManualEntryAPI:
    def test_manual_returns_the_sheet_in_order(self, authenticated_client):
        species = SpeciesFactory()
        ManualEntry.objects.create(
            species=species,
            title="X",
            scientific_name="X L.",
            sections=SECTIONS,
            page_start=184,
            page_end=185,
        )
        url = reverse("taxonomy:species-manual", args=[species.id])
        response = authenticated_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        assert [s["title"] for s in response.data["sections"]] == [
            "Descripción",
            "Localización recomendada",
        ]
        assert response.data["page_start"] == 184
        assert "Manual de arborización" in response.data["source"]

    def test_manual_is_404_without_a_sheet(self, authenticated_client):
        species = SpeciesFactory()
        url = reverse("taxonomy:species-manual", args=[species.id])

        assert authenticated_client.get(url).status_code == status.HTTP_404_NOT_FOUND

    def test_species_flags_has_manual_entry(self, authenticated_client):
        with_sheet, without = SpeciesFactory(), SpeciesFactory()
        ManualEntry.objects.create(
            species=with_sheet, title="X", scientific_name="X", page_start=1, page_end=1
        )
        flag = {
            s.id: authenticated_client.get(
                reverse("taxonomy:species-detail", args=[s.id])
            ).data["has_manual_entry"]
            for s in (with_sheet, without)
        }

        assert flag == {with_sheet.id: True, without.id: False}


@pytest.mark.django_db
class TestLoadManualTolima:
    def test_load_is_idempotent_and_reports_missing(self, tmp_path, capsys):
        species = SpeciesFactory()
        data = tmp_path / "manual.json"
        data.write_text(
            json.dumps(
                [
                    entry_for(species),
                    {**entry_for(species), "species": "Nonexistent sp"},
                ]
            ),
            encoding="utf-8",
        )

        call_command("load_manual_tolima", file=str(data))
        call_command("load_manual_tolima", file=str(data))
        out = capsys.readouterr().out

        entry = ManualEntry.objects.get(species=species)
        assert ManualEntry.objects.count() == 1
        assert entry.sections == SECTIONS
        assert (entry.page_start, entry.page_end) == (184, 185)
        assert "1 created" in out and "1 updated" in out
        assert "Nonexistent sp" in out

    def test_shipped_data_file_is_well_formed(self):
        from apps.taxonomy.management.commands.load_manual_tolima import DEFAULT_FILE

        entries = json.loads(DEFAULT_FILE.read_text(encoding="utf-8"))
        assert entries
        for e in entries:
            assert e["species"] and e["scientific_name"] and e["sections"]
            assert 142 <= e["pages"][0] <= e["pages"][1] <= 255
            assert all(s["title"] and s["text"] for s in e["sections"])
            assert all(s["text"].count("**") % 2 == 0 for s in e["sections"])
