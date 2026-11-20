"""Files that update the tree database from the Reports page (``upload.py``)."""

import csv
import datetime
import io
import json
import struct
import zipfile

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse
from django.utils import translation
from rest_framework import status

from apps.biodiversity.models import BiodiversityRecord
from apps.biodiversity.xlsx import write_xlsx
from apps.reports import upload
from apps.reports.models import Measurement, Observation, Upload

HT = Measurement.MeasuredAttribute.TOTAL_HEIGHT
TODAY = datetime.date(2026, 11, 10)


@pytest.fixture
def tree(biodiversity_record):
    """A census tree with a total height and an undated observation."""
    from apps.reports.factories import MeasurementFactory, ObservationFactory

    MeasurementFactory(
        biodiversity_record=biodiversity_record,
        attribute=HT,
        value=10.0,
        unit="m",
        date=datetime.date(2017, 1, 1),
    )
    ObservationFactory(
        biodiversity_record=biodiversity_record, phytosanitary_status="HE", date=None
    )
    return biodiversity_record


def write(tmp_path, name, rows):
    """rows: header first. Written in the format given by the extension."""
    path = tmp_path / name
    header, *data = rows
    if name.endswith(".csv"):
        with open(path, "w", encoding="utf-8", newline="") as f:
            csv.writer(f).writerows(rows)
    elif name.endswith(".xlsx"):
        path.write_bytes(write_xlsx(rows).read())
    elif name.endswith(".geojson"):
        lat, lon = header.index("latitude"), header.index("longitude")
        features = [
            {
                "type": "Feature",
                "geometry": {"type": "Point", "coordinates": [r[lon], r[lat]]}
                if r[lat] != ""
                else None,
                "properties": dict(zip(header, r, strict=True)),
            }
            for r in data
        ]
        path.write_text(json.dumps({"type": "FeatureCollection", "features": features}))
    elif name.endswith(".zip"):
        path.write_bytes(shapefile_zip(header, data))
    return path


def shapefile_zip(header, data):
    """A zipped point Shapefile (fields cut at 10 characters, as GIS software does)."""
    lat, lon = header.index("latitude"), header.index("longitude")
    points = [(float(r[lon]), float(r[lat])) for r in data]
    xs, ys = [p[0] for p in points], [p[1] for p in points]

    def head(length_words):
        return (
            struct.pack(">7i", 9994, 0, 0, 0, 0, 0, length_words)
            + struct.pack("<2i", 1000, 1)
            + struct.pack("<8d", min(xs), min(ys), max(xs), max(ys), 0, 0, 0, 0)
        )

    shp, shx = b"", b""
    for n, (x, y) in enumerate(points, start=1):
        shx += struct.pack(">2i", 50 + len(shp) // 2, 10)
        shp += struct.pack(">2i", n, 10) + struct.pack("<i2d", 1, x, y)
    shp = head(50 + len(shp) // 2) + shp
    shx = head(50 + len(shx) // 2) + shx

    fields = [h[:10] for h in header]
    width = 60
    dbf = struct.pack(
        "<B3BIHH20x",
        3,
        126,
        11,
        18,
        len(data),
        32 + 32 * len(fields) + 1,
        1 + width * len(fields),
    )
    for name in fields:
        dbf += struct.pack("<11sc4xBB14x", name.encode(), b"C", width, 0)
    dbf += b"\r"
    for r in data:
        dbf += b" " + b"".join(str(v).encode()[:width].ljust(width) for v in r)
    dbf += b"\x1a"

    out = io.BytesIO()
    with zipfile.ZipFile(out, "w") as zf:
        zf.writestr("arboles/arboles.shp", shp)
        zf.writestr("arboles/arboles.shx", shx)
        zf.writestr("arboles/arboles.dbf", dbf)
    return out.getvalue()


def check(path):
    return upload.check(path, upload.file_format(path.name))


@pytest.mark.django_db
class TestCheck:
    @pytest.mark.parametrize("ext", ["csv", "xlsx", "geojson", "zip"])
    def test_update_in_every_format(self, tmp_path, tree, ext):
        """Same changes whatever the format (Shapefile with its cut field names)."""
        species = tree.species.scientific_name
        rows = [
            [
                "id",
                "common_name",
                "scientific_name",
                "total_height_m",
                "measurement_date",
                "phytosanitary_status",
                "latitude",
                "longitude",
            ],
            [
                tree.id,
                "Nuevo nombre",
                species,
                12.5,
                "2026-11-10",
                "enfermo",
                tree.latitude,
                tree.longitude,
            ],
        ]
        with translation.override("es"):
            plan = check(write(tmp_path, f"t.{ext}", rows))
            summary = plan.summary()
        assert plan.errors == []
        assert summary["counts"] == {
            "created": 0,
            "updated": 1,
            "unchanged": 0,
            "measurements": 1,
            "observations": 1,
        }
        shown = {
            f["field"]: (f["old"], f["new"]) for f in summary["changes"][0]["fields"]
        }
        assert shown == {
            "common_name": ("Test Tree", "Nuevo nombre"),
            "total_height_m": ("10", "12.5"),
            "phytosanitary_status": ("saludable", "enfermo"),
        }

    def test_download_sent_back_changes_nothing(self, api_client, tmp_path, tree):
        response = api_client.post(
            reverse("biodiversity:inventory-query"),
            {"format": "csv", "lang": "es"},
            format="json",
        )
        path = tmp_path / "descarga.csv"
        path.write_bytes(b"".join(response.streaming_content))
        plan = check(path)
        assert plan.errors == []
        assert plan.summary()["counts"]["unchanged"] == 1
        assert plan.summary()["ignored_columns"] == []

    def test_spanish_excel_csv(self, tmp_path, tree):
        """Semicolons, decimal comma, DD/MM/YYYY and a Windows encoding."""
        path = tmp_path / "t.csv"
        path.write_bytes(
            f"id;total_height_m;measurement_date;phytosanitary_status\n"
            f"{tree.id};12,5;10/11/2026;crítico\n".encode("cp1252")
        )
        plan = check(path)
        assert plan.errors == []
        assert plan.trees[0].measurements == [(HT, 12.5, "m")]
        assert plan.trees[0].observation == {"phytosanitary_status": "CR"}
        assert plan.trees[0].date == TODAY

    def test_errors(self, tmp_path, tree):
        rows = [
            [
                "id",
                "scientific_name",
                "total_height_m",
                "phytosanitary_status",
                "latitude",
                "longitude",
            ],
            [tree.id, "", 12, "", "", ""],  # measurement without date
            [tree.id, "", "", "", "", ""],  # repeated
            ["abc", "", "", "", "", ""],
            [999001, "Especie inventada", "", "", 4.4, -75.2],
            [999002, tree.species.scientific_name, "", "", "", ""],  # no location
            [999003, tree.species.scientific_name, "", "regular?", 4.4, -75.2],
            [999004, tree.species.scientific_name, "-3", "", 4.4, -75.2],
        ]
        plan = check(write(tmp_path, "t.csv", rows))
        errors = {(e["row"], e["column"]) for e in plan.errors}
        assert errors == {
            (2, "measurement_date"),
            (3, "id"),
            (4, "id"),
            (5, "scientific_name"),
            (6, "latitude"),
            (7, "phytosanitary_status"),
            (8, "total_height_m"),
        }

    def test_removed_tree_is_refused(self, tmp_path, tree):
        BiodiversityRecord.all_objects.filter(pk=tree.pk).update(
            status=BiodiversityRecord.Status.REMOVED
        )
        plan = check(write(tmp_path, "t.csv", [["id", "common_name"], [tree.id, "X"]]))
        assert [e["column"] for e in plan.errors] == ["id"]

    def test_file_errors(self, tmp_path):
        with pytest.raises(upload.UploadError):
            check(write(tmp_path, "t.csv", [["code", "common_name"], [1, "X"]]))
        with pytest.raises(upload.UploadError):
            check(write(tmp_path, "t.csv", [["id", "common_name"]]))


@pytest.mark.django_db
class TestApply:
    def test_history_and_latest(self, tmp_path, tree):
        rows = [
            ["id", "total_height_m", "measurement_date", "phytosanitary_status"],
            [tree.id, 12.5, "2026-11-10", "enfermo"],
        ]
        upload.apply(check(write(tmp_path, "t.csv", rows)))

        heights = Measurement.objects.filter(biodiversity_record=tree, attribute=HT)
        assert sorted(heights.values_list("value", "is_latest")) == [
            (10.0, False),
            (12.5, True),
        ]
        observations = Observation.objects.filter(biodiversity_record=tree)
        latest = observations.get(is_latest=True)
        assert observations.count() == 2
        assert (latest.phytosanitary_status, latest.date) == ("SI", TODAY)
        # The other fields are carried over from the previous observation.
        previous = observations.get(is_latest=False)
        assert latest.physical_condition == previous.physical_condition

        # Sending the same file again adds nothing.
        plan = check(write(tmp_path, "t.csv", rows))
        assert plan.summary()["counts"]["unchanged"] == 1

    def test_new_tree(self, tmp_path, tree):
        rows = [
            [
                "id",
                "common_name",
                "scientific_name",
                "latitude",
                "longitude",
                "record_date",
                "dbh_cm",
            ],
            [
                500000,
                "Ocobo",
                tree.species.scientific_name,
                4.44,
                -75.22,
                "2026-11-10",
                8,
            ],
        ]
        upload.apply(check(write(tmp_path, "t.csv", rows)))
        new = BiodiversityRecord.objects.get(pk=500000)
        # Barrio from the location (the test barrio covers Colombia).
        assert new.neighborhood == tree.neighborhood
        assert (new.common_name, new.date) == ("Ocobo", TODAY)
        assert new.measurements.get().date == TODAY  # dated by record_date
        # The id sequence follows the codes given in files.
        from apps.biodiversity.factories import BiodiversityRecordFactory

        assert BiodiversityRecordFactory().id > 500000

    def test_moves_a_tree(self, tmp_path, tree):
        rows = [["id", "latitude", "longitude"], [tree.id, 4.5, -75.1]]
        upload.apply(check(write(tmp_path, "t.csv", rows)))
        tree.refresh_from_db()
        assert (round(tree.latitude, 6), round(tree.longitude, 6)) == (4.5, -75.1)


@pytest.mark.django_db
class TestApi:
    def post(self, client, rows, name="t.csv", lang="es"):
        content = io.StringIO()
        csv.writer(content).writerows(rows)
        file = SimpleUploadedFile(name, content.getvalue().encode())
        return client.post(
            reverse("reports:upload-list") + f"?lang={lang}",
            {"file": file},
            format="multipart",
        )

    def test_staff_only(self, api_client, authenticated_client, tree):
        rows = [["id", "common_name"], [tree.id, "X"]]
        assert self.post(api_client, rows).status_code == status.HTTP_401_UNAUTHORIZED
        assert (
            self.post(authenticated_client, rows).status_code
            == status.HTTP_403_FORBIDDEN
        )

    def test_preview_then_apply(self, staff_client, tree):
        response = self.post(staff_client, [["id", "common_name"], [tree.id, "Nuevo"]])
        assert response.status_code == status.HTTP_201_CREATED
        assert response.data["status"] == Upload.Status.PREVIEW
        assert response.data["summary"]["counts"]["updated"] == 1
        tree.refresh_from_db()
        assert tree.common_name == "Test Tree"  # nothing written yet

        url = reverse("reports:upload-apply", args=[response.data["id"]])
        applied = staff_client.post(url)
        assert applied.data["status"] == Upload.Status.APPLIED
        tree.refresh_from_db()
        assert tree.common_name == "Nuevo"
        assert staff_client.post(url).status_code == status.HTTP_400_BAD_REQUEST

        listed = staff_client.get(reverse("reports:upload-list")).data["results"]
        assert listed[0]["name"] == "t.csv"
        assert "changes" not in listed[0]["summary"]

    def test_rows_with_errors_cannot_be_applied(self, staff_client, tree):
        response = self.post(staff_client, [["id", "dbh_cm"], [tree.id, "grueso"]])
        assert response.data["summary"]["error_count"] == 1
        assert "no es un número" in response.data["summary"]["errors"][0]["message"]
        url = reverse("reports:upload-apply", args=[response.data["id"]])
        assert staff_client.post(url).status_code == status.HTTP_400_BAD_REQUEST

    def test_unreadable_file(self, staff_client):
        response = self.post(staff_client, [["code"], ["1"]])
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "id" in response.data["error"]
        assert not Upload.objects.exists()
        bad = self.post(staff_client, [["id"]], name="t.pdf")
        assert bad.status_code == status.HTTP_400_BAD_REQUEST


@pytest.mark.django_db
def test_me(api_client, staff_client):
    assert api_client.get(reverse("me")).status_code == status.HTTP_401_UNAUTHORIZED
    data = staff_client.get(reverse("me")).data
    assert data["is_staff"] is True and data["username"]


@pytest.mark.django_db
def test_login_with_admin_credentials(api_client, admin_user):
    admin_user.set_password("clave-segura-1")
    admin_user.save()
    response = api_client.post(
        reverse("token_obtain_pair"),
        {"username": admin_user.username, "password": "clave-segura-1"},
        format="json",
    )
    assert response.status_code == status.HTTP_200_OK
    token = response.data["access"]
    api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")
    assert api_client.get(reverse("me")).data["is_staff"] is True
