"""Trees that no longer exist (status removed) stay in the database but no endpoint shows
or counts them."""

import csv
import datetime
import io

import pytest
from django.core.cache import cache
from django.core.management import CommandError, call_command
from django.urls import reverse
from rest_framework import status

from apps.biodiversity.models import BiodiversityRecord
from apps.reports.models import Measurement, Observation

Status = BiodiversityRecord.Status


@pytest.fixture
def trees(neighborhood, species):
    """Two trees with a height and an observation; the second one is removed."""
    from apps.biodiversity.factories import BiodiversityRecordFactory
    from apps.reports.factories import MeasurementFactory, ObservationFactory

    out = []
    for name in ("Vigente", "Talado"):
        record = BiodiversityRecordFactory(
            neighborhood=neighborhood,
            species=species,
            common_name=name,
            date=datetime.date(2017, 1, 1),
        )
        MeasurementFactory(biodiversity_record=record, attribute="HT", value=5.0)
        ObservationFactory(biodiversity_record=record, phytosanitary_status="HE")
        out.append(record)
    BiodiversityRecord.all_objects.filter(pk=out[1].pk).update(
        status=Status.REMOVED,
        removed_on=datetime.date(2026, 11, 16),
        removal_reason=BiodiversityRecord.RemovalReason.FELLED,
    )
    cache.clear()
    yield out
    cache.clear()


@pytest.mark.django_db
class TestRemovedTreesAreHidden:
    def test_kept_in_database(self, trees):
        assert BiodiversityRecord.all_objects.count() == 2
        assert BiodiversityRecord.objects.count() == 1
        assert Measurement.all_objects.count() == 2
        assert Measurement.objects.count() == 1
        assert Observation.objects.count() == 1
        assert trees[0].species.biodiversity_records.count() == 1

    def test_inventory(self, api_client, trees):
        active, removed = trees
        data = api_client.get(reverse("biodiversity:inventory-list")).data
        assert [r["id"] for r in data["results"]] == [active.id]
        detail = reverse("biodiversity:inventory-detail", args=[removed.id])
        assert api_client.get(detail).status_code == status.HTTP_404_NOT_FOUND

        export = api_client.post(
            reverse("biodiversity:inventory-export"),
            {"ids": [active.id, removed.id]},
            format="json",
        )
        text = b"".join(export.streaming_content).decode("utf-8-sig")
        assert [r["id"] for r in csv.DictReader(io.StringIO(text))] == [str(active.id)]

    def test_map_query(self, api_client, trees):
        url = reverse("biodiversity:inventory-query")
        assert api_client.post(url, {}, format="json").data["count"] == 1
        by_code = api_client.post(url, {"id": trees[1].id}, format="json")
        assert by_code.data["count"] == 0

    def test_records_and_map_points(self, authenticated_client, trees):
        data = authenticated_client.get(
            reverse("biodiversity:biodiversity-record-list")
        ).data
        assert data["count"] == 1
        bbox = authenticated_client.get(
            reverse("biodiversity:biodiversity-record-bbox"),
            {"min_lon": -180, "min_lat": -90, "max_lon": 180, "max_lat": 90},
        )
        assert [r["id"] for r in bbox.data] == [trees[0].id]

    def test_statistics(self, api_client, trees):
        for kind in ("locality", "neighborhood"):
            data = api_client.get(reverse(f"places:{kind}-statistics")).data
            assert data["overall"]["total_trees"] == 1

    def test_dashboard_and_analytics(self, api_client, trees):
        dashboard = api_client.get(reverse("reports:dashboard")).data
        assert dashboard["overall"]["total_trees"] == 1
        assert sum(dashboard["phytosanitary_status"].values()) == 1
        analytics = api_client.get(reverse("reports:analytics")).data
        assert analytics["total_trees"] == 1
        assert sum(c["trees"] for c in analytics["comunas"]["results"]) == 1


@pytest.mark.django_db
class TestLoadRemovedTrees:
    def write(self, tmp_path, rows):
        path = tmp_path / "removed.csv"
        with open(path, "w", encoding="utf-8", newline="") as f:
            w = csv.writer(f)
            w.writerow(["id", "removed_on", "reason", "note"])
            w.writerows(rows)
        return path

    def test_marks_and_is_idempotent(self, tmp_path, biodiversity_record):
        path = self.write(
            tmp_path,
            [[biodiversity_record.id, "2026-11-16", "felled", "Verificado en campo"]],
        )
        out = io.StringIO()
        call_command("load_removed_trees", file=path, stdout=out)
        assert "Marked 1 trees" in out.getvalue()
        record = BiodiversityRecord.all_objects.get(pk=biodiversity_record.pk)
        assert record.status == Status.REMOVED
        assert record.removed_on == datetime.date(2026, 11, 16)
        assert record.removal_reason == BiodiversityRecord.RemovalReason.FELLED
        assert record.removal_note == "Verificado en campo"

        out = io.StringIO()
        call_command("load_removed_trees", file=path, stdout=out)
        assert "Marked 0 trees" in out.getvalue()

    def test_dry_run_writes_nothing(self, tmp_path, biodiversity_record):
        path = self.write(
            tmp_path, [[biodiversity_record.id, "2026-11-16", "felled", ""]]
        )
        call_command(
            "load_removed_trees", file=path, dry_run=True, stdout=io.StringIO()
        )
        assert BiodiversityRecord.objects.filter(pk=biodiversity_record.pk).exists()

    def test_bad_rows_change_nothing(self, tmp_path, biodiversity_record):
        path = self.write(
            tmp_path,
            [
                [biodiversity_record.id, "2026-11-16", "felled", ""],
                [999999, "2026-11-16", "felled", ""],
                [biodiversity_record.id + 1, "16/11/2026", "felled", ""],
                [biodiversity_record.id + 2, "2026-11-16", "burnt", ""],
            ],
        )
        with pytest.raises(CommandError) as exc:
            call_command("load_removed_trees", file=path, stdout=io.StringIO())
        message = str(exc.value)
        assert "id 999999 does not exist" in message
        assert "bad date" in message
        assert "'burnt'" in message
        assert BiodiversityRecord.objects.filter(pk=biodiversity_record.pk).exists()

    def test_repository_file_is_valid(self):
        from apps.biodiversity.management.commands.load_removed_trees import (
            DEFAULT_FILE,
        )

        with open(DEFAULT_FILE, encoding="utf-8") as f:
            rows = list(csv.DictReader(f))
        assert rows and all(r["reason"] == "felled" for r in rows)
