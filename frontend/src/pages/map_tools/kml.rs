//! KML -> GeoJSON (Multi)Polygon, for the map's area of interest.
//!
//! Every `<Polygon>` in the file is read (any namespace prefix): its outer boundary and its
//! holes. Altitudes are dropped. One polygon gives a `Polygon`, several a `MultiPolygon`.
//! KMZ (zipped KML) is not read.

use serde_json::{Value, json};

#[derive(Clone, Copy, Debug, PartialEq)]
pub enum KmlError {
    /// Not well-formed XML.
    Xml,
    /// Well-formed, but without any polygon.
    NoPolygon,
    /// A ring with fewer than three points or coordinates outside lon/lat ranges.
    BadCoordinates,
}

#[derive(Debug)]
pub struct KmlArea {
    /// The first `<name>` in the file (document or placemark), if any.
    pub name: Option<String>,
    pub geometry: Value,
    pub polygons: usize,
    pub vertices: usize,
}

type Ring = Vec<[f64; 2]>;

/// `"lon,lat[,alt] lon,lat ..."` -> a closed ring of `[lon, lat]`.
fn ring(text: &str) -> Result<Ring, KmlError> {
    let mut points: Ring = Vec::new();
    for tuple in text.split_whitespace() {
        let mut parts = tuple.split(',');
        let lon: f64 = parts.next().and_then(|v| v.parse().ok()).ok_or(KmlError::BadCoordinates)?;
        let lat: f64 = parts.next().and_then(|v| v.parse().ok()).ok_or(KmlError::BadCoordinates)?;
        if !(-180.0..=180.0).contains(&lon) || !(-90.0..=90.0).contains(&lat) {
            return Err(KmlError::BadCoordinates);
        }
        if points.last() != Some(&[lon, lat]) {
            points.push([lon, lat]);
        }
    }
    if points.first() != points.last() {
        points.push(points[0]);
    }
    // A closed ring needs three distinct points plus the closing one.
    if points.len() < 4 {
        return Err(KmlError::BadCoordinates);
    }
    Ok(points)
}

fn boundary_rings(polygon: roxmltree::Node, boundary: &str) -> Result<Vec<Ring>, KmlError> {
    polygon
        .children()
        .filter(|n| n.has_tag_name(boundary))
        .filter_map(|b| b.descendants().find(|n| n.has_tag_name("coordinates")))
        .map(|c| ring(c.text().unwrap_or("")))
        .collect()
}

pub fn parse(text: &str) -> Result<KmlArea, KmlError> {
    let text = text.trim_start_matches('\u{FEFF}');
    let doc = roxmltree::Document::parse(text).map_err(|_| KmlError::Xml)?;

    let mut polygons: Vec<Vec<Ring>> = Vec::new();
    for polygon in doc.descendants().filter(|n| n.has_tag_name("Polygon")) {
        let mut rings = boundary_rings(polygon, "outerBoundaryIs")?;
        if rings.is_empty() {
            continue;
        }
        rings.truncate(1);
        rings.extend(boundary_rings(polygon, "innerBoundaryIs")?);
        polygons.push(rings);
    }
    if polygons.is_empty() {
        return Err(KmlError::NoPolygon);
    }

    let name = doc
        .descendants()
        .find(|n| n.has_tag_name("name"))
        .and_then(|n| n.text())
        .map(str::trim)
        .filter(|s| !s.is_empty())
        .map(str::to_string);
    let vertices = polygons.iter().flatten().map(|r| r.len() - 1).sum();
    let count = polygons.len();
    let geometry = if count == 1 {
        json!({ "type": "Polygon", "coordinates": polygons[0] })
    } else {
        json!({ "type": "MultiPolygon", "coordinates": polygons })
    };
    Ok(KmlArea { name, geometry, polygons: count, vertices })
}

#[cfg(test)]
mod tests {
    use super::*;

    const SQUARE: &str = r#"<?xml version="1.0" encoding="UTF-8"?>
<kml xmlns="http://www.opengis.net/kml/2.2"><Document><name>Parque Centenario</name>
<Placemark><name>Zona</name><Polygon><outerBoundaryIs><LinearRing><coordinates>
  -75.24,4.44,0 -75.23,4.44,0 -75.23,4.45,0 -75.24,4.45,0 -75.24,4.44,0
</coordinates></LinearRing></outerBoundaryIs>
<innerBoundaryIs><LinearRing><coordinates>-75.236,4.444 -75.234,4.444 -75.234,4.446</coordinates></LinearRing></innerBoundaryIs>
</Polygon></Placemark></Document></kml>"#;

    #[test]
    fn polygon_with_hole_and_name() {
        let area = parse(SQUARE).unwrap();
        assert_eq!(area.name.as_deref(), Some("Parque Centenario"));
        assert_eq!(area.polygons, 1);
        assert_eq!(area.vertices, 4 + 3);
        assert_eq!(area.geometry["type"], "Polygon");
        let rings = area.geometry["coordinates"].as_array().unwrap();
        assert_eq!(rings.len(), 2);
        assert_eq!(rings[0][0], json!([-75.24, 4.44]));
        // The hole was not closed in the file: it is closed here.
        assert_eq!(rings[1].as_array().unwrap().len(), 4);
        assert_eq!(rings[1][0], rings[1][3]);
    }

    #[test]
    fn prefixed_namespace_and_several_polygons() {
        let kml = r#"<kml:kml xmlns:kml="http://www.opengis.net/kml/2.2"><kml:Document>
          <kml:Placemark><kml:MultiGeometry>
            <kml:Polygon><kml:outerBoundaryIs><kml:LinearRing><kml:coordinates>0,0 1,0 1,1</kml:coordinates></kml:LinearRing></kml:outerBoundaryIs></kml:Polygon>
            <kml:Polygon><kml:outerBoundaryIs><kml:LinearRing><kml:coordinates>2,2 3,2 3,3 2,2</kml:coordinates></kml:LinearRing></kml:outerBoundaryIs></kml:Polygon>
          </kml:MultiGeometry></kml:Placemark></kml:Document></kml:kml>"#;
        let area = parse(kml).unwrap();
        assert_eq!(area.name, None);
        assert_eq!(area.polygons, 2);
        assert_eq!(area.geometry["type"], "MultiPolygon");
        assert_eq!(area.geometry["coordinates"][1][0][2], json!([3.0, 3.0]));
    }

    #[test]
    fn errors() {
        assert_eq!(parse("not xml <").unwrap_err(), KmlError::Xml);
        let point = r#"<kml><Placemark><Point><coordinates>-75,4</coordinates></Point></Placemark></kml>"#;
        assert_eq!(parse(point).unwrap_err(), KmlError::NoPolygon);
        let line = r#"<kml><Polygon><outerBoundaryIs><LinearRing><coordinates>0,0 1,1 0,0</coordinates></LinearRing></outerBoundaryIs></Polygon></kml>"#;
        assert_eq!(parse(line).unwrap_err(), KmlError::BadCoordinates);
        let far = r#"<kml><Polygon><outerBoundaryIs><LinearRing><coordinates>0,0 1,0 1,95</coordinates></LinearRing></outerBoundaryIs></Polygon></kml>"#;
        assert_eq!(parse(far).unwrap_err(), KmlError::BadCoordinates);
    }
}
