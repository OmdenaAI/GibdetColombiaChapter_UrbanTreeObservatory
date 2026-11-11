//! Analytics page: urban forest indicators computed from the census in PostGIS
//! (`GET /api/v1/reports/analytics/`). Each block answers one management question:
//! diversity (10-20-30 rule), origin, size structure, density per comuna, health by
//! species and threatened species.

use std::sync::Arc;
use std::time::Duration;

use leptos::prelude::*;
use leptos::task::spawn_local;
use serde::Deserialize;
use serde_json::{Value, json};

use super::shared::HEALTH;
use crate::api::{API_BASE, console_error, fmt_thousands, get_json};
use crate::interop::chart::chart_by_id;
use crate::interop::when_connected;

// ---------------------------------------------------------------------------
// Data
// ---------------------------------------------------------------------------

#[derive(Deserialize)]
struct Summary {
    trees_per_1000_inhabitants: Option<i64>,
    issues_percent: Option<f64>,
    origin: Vec<Origin>,
    comunas: Comunas,
    species_health: Vec<SpeciesHealth>,
    threatened: Threatened,
}

#[derive(Deserialize)]
struct Origin {
    group: String,
    count: i64,
    percent: Option<f64>,
}

#[derive(Deserialize)]
struct Comunas {
    results: Vec<Comuna>,
    outside_comunas: i64,
    unknown_comuna_in_census: i64,
}

#[derive(Deserialize)]
struct Comuna {
    name: String,
    trees: i64,
    area_ha: f64,
    trees_per_ha: Option<f64>,
    trees_per_1000_inhabitants: Option<i64>,
    issues_percent: Option<f64>,
}

#[derive(Deserialize)]
struct SpeciesHealth {
    name: String,
    trees: i64,
    sick_percent: f64,
    critical_percent: f64,
    dead_percent: f64,
}

#[derive(Deserialize)]
struct Threatened {
    by_status: Vec<StatusCount>,
    species: Vec<ThreatenedSpecies>,
    species_count: i64,
}

#[derive(Deserialize)]
struct StatusCount {
    status: String,
    count: i64,
}

#[derive(Deserialize)]
struct ThreatenedSpecies {
    name: String,
    status: String,
    count: i64,
}

#[derive(Clone)]
enum Load {
    Loading,
    Failed,
    Ready(Arc<Summary>),
}

// ---------------------------------------------------------------------------
// Presentation helpers
// ---------------------------------------------------------------------------

/// Single hue for magnitudes (the app's green).
const BAR: &str = "#15803d";
const CARD: &str = "bg-white rounded-lg shadow border border-gray-200 p-5";
const H2: &str = "text-lg font-semibold text-gray-900";
const NOTE: &str = "text-sm text-gray-500 mt-0.5";

fn pct(v: Option<f64>) -> String {
    v.map(|v| format!("{v:.1}%")).unwrap_or_else(|| "—".into())
}

fn n(v: i64) -> String {
    fmt_thousands(v)
}

fn health_color(code: &str) -> &'static str {
    HEALTH.iter().find(|(c, ..)| *c == code).map(|(.., color)| *color).unwrap_or("#9ca3af")
}

fn iucn_label(code: &str) -> &'static str {
    match code {
        "CR" => "Critically endangered",
        "EN" => "Endangered",
        "VU" => "Vulnerable",
        _ => "Other",
    }
}

/// Recessive axes: light grid on the value axis only, small ticks.
fn axes(horizontal: bool, value_title: &str) -> Value {
    let value = json!({
        "beginAtZero": true,
        "grid": { "color": "rgba(0,0,0,0.06)" },
        "border": { "display": false },
        "ticks": { "font": { "size": 11 }, "color": "#6b7280" },
        "title": { "display": true, "text": value_title, "color": "#6b7280", "font": { "size": 11 } }
    });
    let category = json!({
        "grid": { "display": false },
        "ticks": { "font": { "size": 11 }, "color": "#374151" }
    });
    if horizontal {
        json!({ "x": value, "y": category })
    } else {
        json!({ "y": value, "x": category })
    }
}

fn bar_dataset(label: &str, data: Vec<Value>, color: &str) -> Value {
    json!({
        "label": label,
        "data": data,
        "backgroundColor": color,
        "borderRadius": 4,
        "borderSkipped": "start",
        "maxBarThickness": 22
    })
}

// ---------------------------------------------------------------------------
// Page
// ---------------------------------------------------------------------------

#[component]
pub fn Analytics() -> impl IntoView {
    let state = RwSignal::new(Load::Loading);
    let load = move || {
        state.set(Load::Loading);
        spawn_local(async move {
            let url = format!("{API_BASE}/api/v1/reports/analytics/");
            let res = get_json(&url)
                .await
                .and_then(|v| serde_json::from_value::<Summary>(v).map_err(|e| e.to_string()));
            match res {
                Ok(s) => state.try_set(Load::Ready(Arc::new(s))),
                Err(e) => {
                    console_error("Error loading analytics:", &e);
                    state.try_set(Load::Failed)
                }
            };
        });
    };
    load();

    let root = NodeRef::<leptos::html::Div>::new();
    Effect::new(move |_| {
        let ready = state.with(|s| match s {
            Load::Ready(s) => Some(s.clone()),
            _ => None,
        });
        if let (Some(el), Some(summary)) = (root.get(), ready) {
            when_connected(el.into(), move || {
                set_timeout(move || draw_charts(&summary), Duration::from_millis(100))
            });
        }
    });

    view! {
        <div node_ref=root class="block w-full">
            <div class="p-6 space-y-6">
                <div>
                    <h1 class="text-2xl font-bold text-green-700">"Urban Forest Analysis"</h1>
                    <p class="mt-1 text-gray-600">
                        "Indicators computed from the Cortolima tree census of Ibagué (2014–2017) stored in PostGIS."
                    </p>
                </div>
                {move || match state.get() {
                    Load::Loading => view! {
                        <div class="py-24 flex items-center justify-center text-gray-500">
                            <div class="h-8 w-8 mr-3 rounded-full border-4 border-green-200 border-t-green-600 animate-spin"></div>
                            "Computing indicators…"
                        </div>
                    }.into_any(),
                    Load::Failed => view! {
                        <div class="py-24 text-center text-red-600">
                            "Could not load the analysis. "
                            <button class="underline font-medium" on:click=move |_| load()>"Retry"</button>
                        </div>
                    }.into_any(),
                    Load::Ready(s) => content(&s).into_any(),
                }}
            </div>
        </div>
    }
}

fn content(s: &Summary) -> impl IntoView + use<> {
    view! {
        {origin_card(s)}
        {comunas_card(s)}
        <div class="grid grid-cols-1 xl:grid-cols-5 gap-6 items-stretch">
            <div class=format!("{CARD} xl:col-span-3 flex flex-col")>
                <h3 class=H2>"Health problems in the most common species"</h3>
                <p class=NOTE>
                    {format!("Share of each species' trees recorded sick, critical or dead (city average: {}). Highest first.",
                        pct(s.issues_percent))}
                </p>
                <div class="relative mt-3 flex-1 min-h-80"><canvas id="speciesHealthChart"></canvas></div>
            </div>
            <div class="xl:col-span-2">{threatened_card(s)}</div>
        </div>
    }
}

fn origin_card(s: &Summary) -> impl IntoView + use<> {
    // Native: the app's green; introduced: orange; not identified: neutral gray.
    let style_for = |g: &str| match g {
        "native" => ("Native", "#15803d"),
        "introduced" => ("Introduced", "#eb6834"),
        _ => ("Not identified", "#9ca3af"),
    };
    let segments = s
        .origin
        .iter()
        .map(|o| {
            let (label, color) = style_for(&o.group);
            let w = o.percent.unwrap_or(0.0);
            view! {
                <div class="h-full first:rounded-l last:rounded-r" style=format!("width:{w}%;background:{color}")
                    title=format!("{label}: {} trees ({})", n(o.count), pct(o.percent))></div>
            }
        })
        .collect_view();
    let legend = s
        .origin
        .iter()
        .map(|o| {
            let (label, color) = style_for(&o.group);
            view! {
                <div class="flex items-start gap-2">
                    <span class="mt-1 h-3 w-3 shrink-0 rounded-sm" style=format!("background:{color}")></span>
                    <div>
                        <p class="text-sm font-medium text-gray-900">{format!("{label} · {}", pct(o.percent))}</p>
                        <p class="text-xs text-gray-500">{format!("{} trees", n(o.count))}</p>
                    </div>
                </div>
            }
        })
        .collect_view();
    view! {
        <div class=CARD>
            <div class="grid grid-cols-1 lg:grid-cols-3 gap-x-8 gap-y-4 items-center">
                <div>
                    <h3 class=H2>"Origin of the trees"</h3>
                    <p class=NOTE>
                        "Native species are adapted to the local climate and support local fauna. Native includes native, endemic and native-cultivated species; introduced includes cultivated and naturalized ones."
                    </p>
                </div>
                <div class="lg:col-span-2">
                    <div class="flex h-8 gap-0.5 overflow-hidden rounded">{segments}</div>
                    <div class="mt-3 grid grid-cols-3 gap-3">{legend}</div>
                </div>
            </div>
        </div>
    }
}

fn comunas_card(s: &Summary) -> impl IntoView + use<> {
    let c = &s.comunas;
    let rows = c
        .results
        .iter()
        .map(|r| {
            view! {
                <tr class="hover:bg-gray-50">
                    <td class="px-3 py-1.5 text-sm text-gray-900 whitespace-nowrap">{r.name.clone()}</td>
                    <td class="px-3 py-1.5 text-sm text-right tabular-nums">{n(r.trees)}</td>
                    <td class="px-3 py-1.5 text-sm text-right tabular-nums text-gray-500">{format!("{:.0}", r.area_ha)}</td>
                    <td class="px-3 py-1.5 text-sm text-right tabular-nums">{r.trees_per_ha.map(|v| format!("{v:.1}")).unwrap_or_else(|| "—".into())}</td>
                    <td class="px-3 py-1.5 text-sm text-right tabular-nums">{r.trees_per_1000_inhabitants.map(n).unwrap_or_else(|| "—".into())}</td>
                    <td class="px-3 py-1.5 text-sm text-right tabular-nums">{pct(r.issues_percent)}</td>
                </tr>
            }
        })
        .collect_view();
    let th = "px-3 py-2 text-xs font-medium text-gray-500 uppercase text-right";
    view! {
        <div class=CARD>
            <div class="grid grid-cols-1 lg:grid-cols-2 gap-6">
                <div class="flex flex-col">
                    <h3 class=H2>"Trees per 1,000 inhabitants"</h3>
                    <p class=NOTE>
                        {format!("City-wide: {}. Highest first.", s.trees_per_1000_inhabitants.map(n).unwrap_or_else(|| "—".into()))}
                    </p>
                    <div class="relative mt-3 flex-1 min-h-80"><canvas id="comunaChart"></canvas></div>
                </div>
                <div>
                    <h3 class=H2>"Comuna figures"</h3>
                    <p class=NOTE>"Density per area, per inhabitant (population 2019) and health."</p>
                    <div class="mt-3 overflow-x-auto">
                        <table class="min-w-full divide-y divide-gray-200">
                            <thead>
                                <tr>
                                    <th class="px-3 py-2 text-xs font-medium text-gray-500 uppercase text-left">"Comuna"</th>
                                    <th class=th>"Trees"</th>
                                    <th class=th>"Area (ha)"</th>
                                    <th class=th>"Trees / ha"</th>
                                    <th class=th>"Per 1,000 inh."</th>
                                    <th class=th>"With problems"</th>
                                </tr>
                            </thead>
                            <tbody class="divide-y divide-gray-100">{rows}</tbody>
                        </table>
                    </div>
                </div>
            </div>
            <p class="mt-4 text-xs text-gray-500">
                {format!(
                    "Each tree is placed in a comuna by its coordinates (PostGIS point-in-polygon). The census field leaves {} trees in an unknown comuna; by location only {} fall outside the comuna boundaries.",
                    n(c.unknown_comuna_in_census), n(c.outside_comunas)
                )}
            </p>
        </div>
    }
}

fn threatened_card(s: &Summary) -> impl IntoView + use<> {
    let badge = |code: &str| match code {
        "CR" => "bg-red-100 text-red-800",
        "EN" => "bg-orange-100 text-orange-800",
        _ => "bg-yellow-100 text-yellow-800",
    };
    let summary = s
        .threatened
        .by_status
        .iter()
        .map(|b| {
            view! {
                <div class="text-center">
                    <p class="text-xl font-bold text-gray-900">{n(b.count)}</p>
                    <p class=format!("mt-1 inline-block px-2 py-0.5 rounded-full text-xs font-semibold {}", badge(&b.status))>
                        {format!("{} · {}", b.status, iucn_label(&b.status))}
                    </p>
                </div>
            }
        })
        .collect_view();
    let rows = s
        .threatened
        .species
        .iter()
        .map(|t| {
            view! {
                <tr>
                    <td class="py-1.5 text-sm italic text-gray-900">{t.name.clone()}</td>
                    <td class="py-1.5 text-center">
                        <span class=format!("px-2 py-0.5 rounded-full text-xs font-semibold {}", badge(&t.status))>{t.status.clone()}</span>
                    </td>
                    <td class="py-1.5 text-sm text-right tabular-nums">{n(t.count)}</td>
                </tr>
            }
        })
        .collect_view();
    view! {
        <div class=format!("{CARD} h-full")>
            <h3 class=H2>"Threatened species"</h3>
            <p class=NOTE>
                {format!("{} trees of {} species that are globally threatened (IUCN Red List). The category describes wild populations, not the planted trees.",
                    n(s.threatened.by_status.iter().map(|b| b.count).sum()), s.threatened.species_count)}
            </p>
            <div class="mt-4 grid grid-cols-3 gap-2">{summary}</div>
            <table class="mt-4 w-full">
                <thead>
                    <tr class="border-b border-gray-200">
                        <th class="py-1.5 text-left text-xs font-medium text-gray-500 uppercase">"Species"</th>
                        <th class="py-1.5 text-center text-xs font-medium text-gray-500 uppercase">"IUCN"</th>
                        <th class="py-1.5 text-right text-xs font-medium text-gray-500 uppercase">"Trees"</th>
                    </tr>
                </thead>
                <tbody class="divide-y divide-gray-100">{rows}</tbody>
            </table>
        </div>
    }
}

// ---------------------------------------------------------------------------
// Charts
// ---------------------------------------------------------------------------

fn draw_charts(s: &Summary) {
    comuna_chart(s);
    species_health_chart(s);
}

fn horizontal_bar(id: &str, labels: Vec<String>, datasets: Vec<Value>, value_title: &str, stacked: bool, legend: bool) {
    let mut scales = axes(true, value_title);
    if stacked {
        scales["x"]["stacked"] = json!(true);
        scales["y"]["stacked"] = json!(true);
    }
    chart_by_id(
        id,
        json!({
            "type": "bar",
            "data": { "labels": labels, "datasets": datasets },
            "options": {
                "indexAxis": "y",
                "responsive": true,
                "maintainAspectRatio": false,
                "scales": scales,
                "plugins": {
                    "legend": { "display": legend, "position": "bottom", "labels": { "boxWidth": 10, "font": { "size": 11 } } }
                }
            }
        }),
        true,
    );
}

fn comuna_chart(s: &Summary) {
    let mut rows: Vec<&Comuna> = s.comunas.results.iter().filter(|c| c.trees_per_1000_inhabitants.is_some()).collect();
    rows.sort_by_key(|c| std::cmp::Reverse(c.trees_per_1000_inhabitants));
    horizontal_bar(
        "comunaChart",
        rows.iter().map(|c| c.name.replace("COMUNA", "Comuna")).collect(),
        vec![bar_dataset("Trees per 1,000 inhabitants", rows.iter().map(|c| json!(c.trees_per_1000_inhabitants)).collect(), BAR)],
        "Trees per 1,000 inhabitants",
        false,
        false,
    );
}

fn species_health_chart(s: &Summary) {
    let rows = &s.species_health;
    let series = [
        ("Sick", "SI", rows.iter().map(|r| json!(r.sick_percent)).collect::<Vec<_>>()),
        ("Critical", "CR", rows.iter().map(|r| json!(r.critical_percent)).collect()),
        ("Dead", "DE", rows.iter().map(|r| json!(r.dead_percent)).collect()),
    ];
    let datasets = series
        .into_iter()
        .map(|(label, code, data)| {
            let mut d = bar_dataset(label, data, health_color(code));
            // Stacked segments: rounded ends only on the outer segment, 2px gap between fills.
            d["borderRadius"] = json!(0);
            d["borderColor"] = json!("#ffffff");
            d["borderWidth"] = json!({ "right": 2 });
            d
        })
        .collect();
    horizontal_bar(
        "speciesHealthChart",
        rows.iter().map(|r| format!("{} ({})", r.name, n(r.trees))).collect(),
        datasets,
        "% of the species' trees",
        true,
        true,
    );
}
