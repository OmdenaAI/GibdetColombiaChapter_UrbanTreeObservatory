//! CSV export of the currently filtered species.

use std::sync::Arc;

use wasm_bindgen::JsCast;

use super::model::{self, Species, TRAITS};
use crate::api::console_error;
use crate::i18n::Lang;

const HEADER: &str = "common_name,scientific_name,accepted_scientific_name,family,genus,life_form,origin,iucn_status,canopy_shape,flower_color,functional_group,carbon_sequestration_pct,shade_index,canopy_diameter_m,max_height_m,gbif_url";

fn field(s: &str) -> String {
    if s.contains([',', '"', '\n', '\r']) {
        format!("\"{}\"", s.replace('"', "\"\""))
    } else {
        s.to_string()
    }
}

/// Header in English (stable column names); category values in the UI language.
pub fn to_csv(l: Lang, rows: &[Arc<Species>]) -> String {
    let mut out = String::from(HEADER);
    out.push_str("\r\n");
    for s in rows {
        let mut cols = vec![
            s.common_name().unwrap_or_default().to_string(),
            s.scientific_name.clone(),
            s.accepted_scientific_name.clone().unwrap_or_default(),
            s.family().to_string(),
            s.genus.name.clone(),
            model::life_form_label(l, &s.life_form).into(),
            model::origin_label(l, &s.origin).into(),
            s.iucn_status.clone(),
            model::canopy_label(l, &s.canopy_shape).into(),
            model::flower_label(l, &s.flower_color).into(),
            s.group().map(|g| g.to_string()).unwrap_or_default(),
        ];
        cols.extend(TRAITS.iter().map(|(ty, ..)| {
            let v = s.trait_value(ty);
            if v == "—" { String::new() } else { v.replace(" – ", "-") }
        }));
        cols.push(s.gbif_url.clone().unwrap_or_default());
        out.push_str(&cols.iter().map(|c| field(c)).collect::<Vec<_>>().join(","));
        out.push_str("\r\n");
    }
    out
}

/// Triggers a browser download of `species-catalog-YYYY-MM-DD.csv` (UTF-8 with BOM for Excel).
pub fn download_csv(l: Lang, rows: &[Arc<Species>]) {
    let csv = format!("\u{FEFF}{}", to_csv(l, rows));
    let href = format!("data:text/csv;charset=utf-8,{}", js_sys::encode_uri_component(&csv));
    let date: String = js_sys::Date::new_0().to_iso_string().into();
    let name = format!("species-catalog-{}.csv", &date[..10]);

    let anchor = web_sys::window()
        .and_then(|w| w.document())
        .and_then(|d| d.create_element("a").ok())
        .and_then(|e| e.dyn_into::<web_sys::HtmlAnchorElement>().ok());
    match anchor {
        Some(a) => {
            a.set_href(&href);
            a.set_download(&name);
            a.click();
        }
        None => console_error("CSV export failed:", "could not create the download link"),
    }
}

#[cfg(test)]
mod tests {
    use super::field;

    #[test]
    fn quotes_only_when_needed() {
        assert_eq!(field("Ficus"), "Ficus");
        assert_eq!(field("a, b"), "\"a, b\"");
        assert_eq!(field("say \"hi\""), "\"say \"\"hi\"\"\"");
    }
}
