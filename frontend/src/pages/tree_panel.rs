//! Map side panel for a clicked tree (layout of the project's "Figure 5B"): common name,
//! scientific name, illustration, IUCN status, a data table and GBIF / Tropical Plants links.
//!
//! The point itself (from `/biodiversity/records/bbox/`) carries the record, species and
//! place names; the panel then loads the species detail (family, IUCN, links, illustration)
//! and the tree's measurements (DBH, total height) in parallel.

use std::sync::Arc;

use leptos::prelude::*;
use leptos::task::spawn_local;
use serde::Deserialize;

use super::species::card::{ILLUSTRATION_BG, illustration_img, photo_placeholder};
use super::species::model::{self, Species, fmt_num};
use crate::api::{API_BASE, console_error, get_json};
use crate::i18n::I18n;

/// What the map knows about a point before any extra request.
#[derive(Clone, PartialEq)]
pub struct TreeRecord {
    pub id: i64,
    pub common_name: Option<String>,
    pub scientific_name: String,
    pub species_id: Option<i64>,
    pub life_form: String,
    pub neighborhood: Option<String>,
    pub site: Option<String>,
}

#[derive(Clone)]
enum Load<T> {
    Loading,
    Ready(T),
    Failed,
}

#[derive(Clone, Default)]
struct Measures {
    dbh_cm: Option<f64>,
    height_m: Option<f64>,
}

#[derive(Deserialize)]
struct MeasurementPage {
    results: Vec<Measurement>,
}

#[derive(Deserialize)]
struct Measurement {
    attribute: String,
    value: f64,
    unit: String,
}

/// Measurements come newest first; keep the first DBH and total height found.
fn measures_from(rows: &[Measurement]) -> Measures {
    let mut m = Measures::default();
    for r in rows {
        match r.attribute.as_str() {
            "DBH" if m.dbh_cm.is_none() => {
                m.dbh_cm = Some(if r.unit == "m" { r.value * 100.0 } else { r.value });
            }
            "HT" if m.height_m.is_none() => {
                m.height_m = Some(if r.unit == "cm" { r.value / 100.0 } else { r.value });
            }
            _ => {}
        }
    }
    m
}

fn fetch_species(id: i64, out: RwSignal<Load<Arc<Species>>>) {
    spawn_local(async move {
        let url = format!("{API_BASE}/api/v1/taxonomy/species/{id}/");
        let res = get_json(&url)
            .await
            .and_then(|v| serde_json::from_value::<Species>(v).map_err(|e| e.to_string()));
        // `try_set`: the panel may already be gone (another tree was clicked).
        match res {
            Ok(s) => out.try_set(Load::Ready(Arc::new(s))),
            Err(e) => {
                console_error("Error loading species:", &e);
                out.try_set(Load::Failed)
            }
        };
    });
}

fn fetch_measures(record_id: i64, out: RwSignal<Load<Measures>>) {
    spawn_local(async move {
        // `page=1` is required: without it the endpoint filters only within the latest
        // 1000 measurements (see MeasurementViewSet.get_queryset) and returns nothing.
        let url = format!("{API_BASE}/api/v1/reports/measurements/?biodiversity_record={record_id}&page=1");
        let res = get_json(&url)
            .await
            .and_then(|v| serde_json::from_value::<MeasurementPage>(v).map_err(|e| e.to_string()));
        match res {
            Ok(p) => out.try_set(Load::Ready(measures_from(&p.results))),
            Err(e) => {
                console_error("Error loading measurements:", &e);
                out.try_set(Load::Failed)
            }
        };
    });
}

const TD: &str = "border border-gray-900 px-2 py-1.5 text-center align-middle";

#[component]
pub fn TreePanel(tree: TreeRecord, on_close: Callback<()>) -> impl IntoView {
    let i = I18n::use_ctx();
    let species = RwSignal::new(Load::<Arc<Species>>::Loading);
    let measures = RwSignal::new(Load::<Measures>::Loading);
    match tree.species_id {
        Some(id) => fetch_species(id, species),
        None => species.set(Load::Failed),
    }
    fetch_measures(tree.id, measures);

    // Text for a value that depends on a request: "…" while loading, "—" when missing.
    let from_species = move |f: fn(&Species) -> String| {
        move || species.with(|s| match s {
            Load::Loading => "…".to_string(),
            Load::Ready(s) => f(s),
            Load::Failed => "—".to_string(),
        })
    };
    let from_measures = move |f: fn(&Measures) -> Option<f64>| {
        move || measures.with(|m| match m {
            Load::Loading => "…".to_string(),
            Load::Ready(m) => f(m).map(fmt_num).unwrap_or_else(|| "—".into()),
            Load::Failed => "—".to_string(),
        })
    };

    // The record's own common name; the species' most frequent one as fallback.
    let record_common = tree.common_name.clone();
    let common = move || {
        record_common.clone().or_else(|| {
            species.with(|s| match s {
                Load::Ready(s) => s.common_name().map(str::to_string),
                _ => None,
            })
        })
        .unwrap_or_else(|| "—".into())
    };

    let scientific = tree.scientific_name.clone();
    let illustration = move || {
        species.with(|s| match s {
            Load::Ready(s) => s.illustration().map(|src| (src, s.scientific_name.clone())),
            _ => None,
        })
    };

    let iucn = move || {
        species.with(|s| match s {
            Load::Ready(s) => {
                let code = s.iucn_status.clone();
                let (label, _, desc) = model::iucn_info(i.lang(), &code);
                let (bg, fg) = model::iucn_colors(&code);
                view! {
                    <div
                        class="flex items-center rounded-full border-2 border-gray-900 p-0.5"
                        style=format!("background:{bg};color:{fg}")
                        title=desc
                    >
                        <span class="h-8 w-8 shrink-0 rounded-full border-2 border-gray-900 flex items-center justify-center text-xs font-bold">
                            {code.clone()}
                        </span>
                        <span class="flex-1 text-center text-lg font-semibold pr-3">{label}</span>
                    </div>
                }
                .into_any()
            }
            Load::Loading => view! { <div class="h-10 rounded-full bg-gray-100 animate-pulse"></div> }.into_any(),
            Load::Failed => ().into_any(),
        })
    };

    let links = move || {
        species.with(|s| match s {
            Load::Ready(s) => {
                let link = |href: Option<String>, name: &'static str| {
                    href.filter(|h| !h.is_empty()).map(|h| {
                        view! {
                            <a href=h target="_blank" rel="noopener noreferrer" class="flex flex-col items-center group">
                                <span class="text-lg font-bold text-gray-900">{name}</span>
                                <span class="text-xs italic text-blue-700 underline group-hover:text-blue-900">{i.t("Ver más…", "View more…")}</span>
                            </a>
                        }
                    })
                };
                view! {
                    <div class="flex items-start justify-around pt-1">
                        {link(s.gbif_url.clone(), "GBIF")}
                        {link(s.tropical_plants_url.clone(), "Tropical Plants")}
                    </div>
                }
                .into_any()
            }
            _ => ().into_any(),
        })
    };

    let row = move |es: &'static str, en: &'static str, value: AnyView| {
        view! {
            <tr>
                <th class=format!("{TD} font-normal w-1/2")>{move || i.t(es, en)}</th>
                <td class=TD>{value}</td>
            </tr>
        }
    };
    let place = |v: Option<String>| v.map(|s| s.replace('_', " ")).unwrap_or_else(|| "—".into());

    view! {
        <div class="space-y-3">
            <button
                class="inline-flex items-center gap-1 text-sm text-primary-700 hover:underline"
                on:click=move |_| on_close.run(())
            >
                {move || i.t("← Volver al resumen", "← Back to summary")}
            </button>

            <div class="border-2 border-gray-900 rounded px-2 py-1 text-center text-xl font-semibold text-gray-900 truncate">
                {common}
            </div>
            <p class="text-center text-lg italic text-gray-900 leading-tight">{scientific.clone()}</p>

            {move || {
                let img = illustration();
                let bg = if img.is_some() { ILLUSTRATION_BG } else { "bg-[#DFE1E6]" };
                view! {
                    <div class=format!("relative h-56 overflow-hidden rounded border-2 border-gray-900 flex items-center justify-center {bg}")>
                        {match img {
                            Some((src, name)) => illustration_img(i.lang(), src, &name).into_any(),
                            None => photo_placeholder().into_any(),
                        }}
                    </div>
                }
            }}

            {iucn}

            <table class="w-full border-collapse text-sm text-gray-900">
                <tbody>
                    {row("Id", "Id", tree.id.to_string().into_any())}
                    {row("Familia", "Family", from_species(|s| s.family().to_string()).into_any())}
                    {row("Forma de vida", "Life form", {
                        let code = tree.life_form.clone();
                        (move || model::life_form_label(i.lang(), &code)).into_any()
                    })}
                    {row("Diámetro (cm)", "Diameter (cm)", from_measures(|m| m.dbh_cm).into_any())}
                    {row("Altura total (m)", "Total height (m)", from_measures(|m| m.height_m).into_any())}
                    {row("Barrio", "Neighborhood", place(tree.neighborhood.clone()).into_any())}
                    {row("Sitio", "Site", place(tree.site.clone()).into_any())}
                </tbody>
            </table>

            {links}
        </div>
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn keeps_newest_dbh_and_height() {
        let rows = vec![
            Measurement { attribute: "HT".into(), value: 12.5, unit: "m".into() },
            Measurement { attribute: "CD".into(), value: 7.0, unit: "m".into() },
            Measurement { attribute: "DBH".into(), value: 12.6, unit: "cm".into() },
            Measurement { attribute: "HT".into(), value: 9.0, unit: "m".into() },
        ];
        let m = measures_from(&rows);
        assert_eq!(m.dbh_cm, Some(12.6));
        assert_eq!(m.height_m, Some(12.5));
    }
}
