import csv
import io
import json
import zipfile
from xml.etree import ElementTree as ET

import pytest
from django.contrib.gis.geos import Point
from django.urls import reverse
from rest_framework import status

from apps.biodiversity.xlsx import column_letter, write_xlsx

URL = "biodiversity:inventory-query"

# A square around the first tree (lon -75.20..-75.18, lat 4.43..4.45).
SQUARE = {
    "type": "Polygon",
    "coordinates": [
        [[-75.20, 4.43], [-75.18, 4.43], [-75.18, 4.45], [-75.20, 4.45], [-75.20, 4.43]]
    ],
}


@pytest.fixture
def trees(neighborhood, species):
    from apps.biodiversity.factories import BiodiversityRecordFactory
    from apps.reports.factories import MeasurementFactory

    inside = BiodiversityRecordFactory(
        neighborhood=neighborhood,
        species=species,
        common_name="Caucho",
        location=Point(-75.19, 4.44, srid=4326),
    )
    outside = BiodiversityRecordFactory(
        neighborhood=neighborhood,
        species=species,
        common_name="Ocobo",
        location=Point(-75.30, 4.50, srid=4326),
    )
    MeasurementFactory(biodiversity_record=inside, attribute="HT", value=9.5, unit="m")
    return inside, outside


def post(client, **body):
    return client.post(reverse(URL), body, format="json")


@pytest.mark.django_db
class TestTreeQuery:
    def test_summary_with_area_and_filters(self, api_client, trees):
        inside, outside = trees

        everything = post(api_client).data
        assert everything["count"] == 2

        area = post(api_client, geometry=SQUARE).data
        assert area["count"] == 1
        assert area["points"] == [[inside.id, 4.44, -75.19]]
        assert area["bbox"] == [-75.19, 4.44, -75.19, 4.44]
        assert area["truncated"] is False

        assert post(api_client, common_name="ocob").data["count"] == 1
        assert post(api_client, id=outside.id).data["points"][0][0] == outside.id
        hood = inside.neighborhood
        assert post(api_client, neighborhood=hood.id).data["count"] == 2
        assert post(api_client, comuna=hood.locality_id).data["count"] == 2
        genus = inside.species.genus.name
        assert post(api_client, scientific_name=genus.upper()).data["count"] == 2
        # Filters and area combine.
        assert post(api_client, geometry=SQUARE, common_name="ocobo").data["count"] == 0

    def test_self_intersecting_drawing_is_repaired(self, api_client, trees):
        bow_tie = {
            "type": "Polygon",
            "coordinates": [
                [
                    [-75.20, 4.43],
                    [-75.18, 4.45],
                    [-75.18, 4.43],
                    [-75.20, 4.45],
                    [-75.20, 4.43],
                ]
            ],
        }
        response = post(api_client, geometry=bow_tie)
        assert response.status_code == status.HTTP_200_OK
        assert response.data["count"] == 1

    @pytest.mark.parametrize(
        "body",
        [
            {"id": "abc"},
            {"comuna": -1},
            {"format": "pdf"},
            {"geometry": {"type": "Point", "coordinates": [0, 0]}},
            {"geometry": {"type": "Polygon", "coordinates": "nope"}},
            {"common_name": "x" * 500},
        ],
    )
    def test_rejects_bad_bodies(self, api_client, body):
        response = api_client.post(reverse(URL), body, format="json")
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "error" in response.data

    def test_csv_download(self, api_client, trees):
        response = post(api_client, geometry=SQUARE, format="csv", lang="es")
        assert response.status_code == status.HTTP_200_OK
        assert 'filename="tree-query-' in response["Content-Disposition"]
        text = b"".join(response.streaming_content).decode("utf-8-sig")
        rows = list(csv.DictReader(io.StringIO(text)))
        assert [int(r["id"]) for r in rows] == [trees[0].id]
        assert rows[0]["total_height_m"] == "9.5"

    def test_geojson_download(self, api_client, trees):
        response = post(api_client, format="geojson")
        assert response["Content-Type"] == "application/geo+json"
        data = json.loads(b"".join(response.streaming_content))
        assert data["type"] == "FeatureCollection"
        first = data["features"][0]
        assert first["geometry"] == {"type": "Point", "coordinates": [-75.19, 4.44]}
        assert first["properties"]["id"] == trees[0].id
        assert first["properties"]["total_height_m"] == 9.5
        assert len(data["features"]) == 2

    def test_xlsx_download(self, api_client, trees):
        response = post(api_client, geometry=SQUARE, format="xlsx")
        assert response.status_code == status.HTTP_200_OK
        assert "spreadsheetml" in response["Content-Type"]
        book = zipfile.ZipFile(io.BytesIO(b"".join(response.streaming_content)))
        sheet = ET.fromstring(book.read("xl/worksheets/sheet1.xml"))
        ns = {"x": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}
        rows = sheet.findall(".//x:row", ns)
        assert len(rows) == 2  # header + the tree inside the square
        header = [c.findtext(".//x:t", namespaces=ns) for c in rows[0]]
        assert header[0] == "id"
        assert rows[1][0].findtext("x:v", namespaces=ns) == str(trees[0].id)

    def test_options_lists_comunas_and_barrios_with_trees(self, api_client, trees):
        hood = trees[0].neighborhood
        data = api_client.get(reverse("biodiversity:inventory-options")).data
        assert data["comunas"] == [{"id": hood.locality_id, "name": hood.locality.name}]
        assert data["neighborhoods"] == [
            {"id": hood.id, "name": hood.name, "comuna": hood.locality_id}
        ]


def test_xlsx_writer_escapes_and_types():
    assert [column_letter(i) for i in (0, 25, 26, 27)] == ["A", "Z", "AA", "AB"]
    out = write_xlsx([["a", "b"], [1, "x <&> \x01y"], [2.5, None]])
    book = zipfile.ZipFile(out)
    assert set(book.namelist()) >= {
        "[Content_Types].xml",
        "xl/workbook.xml",
        "xl/worksheets/sheet1.xml",
        "xl/styles.xml",
    }
    xml = book.read("xl/worksheets/sheet1.xml").decode()
    ET.fromstring(xml)  # well-formed
    assert "x &lt;&amp;&gt; y" in xml
    assert '<c r="A3"><v>2.5</v></c>' in xml
