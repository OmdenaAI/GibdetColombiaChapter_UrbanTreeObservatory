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
    total_trees: i64,
    species_count: i64,
    population: i64,
    trees_per_1000_inhabitants: Option<i64>,
    native_percent: Option<f64>,
    issues_percent: Option<f64>,
    concentration: Concentration,
    origin: Vec<Origin>,
    dbh_classes: DbhClasses,
    comunas: Comunas,
    species_health: Vec<SpeciesHealth>,
    threatened: Threatened,
}

#[derive(Deserialize)]
struct Concentration {
    rule: Vec<RuleRow>,
    top_species: Vec<Share>,
}

#[derive(Deserialize)]
struct RuleRow {
    level: String,
    name: String,
    percent: f64,
    limit: f64,
}

#[derive(Deserialize)]
struct Share {
    name: String,
    count: i64,
    percent: f64,
}

#[derive(Deserialize)]
struct Origin {
    group: String,
    count: i64,
    percent: Option<f64>,
}

#[derive(Deserialize)]
struct DbhClasses {
    trees_measured: i64,
    classes: Vec<DbhClass>,
}

#[derive(Deserialize)]
struct DbhClass {
    from_cm: i64,
    to_cm: Option<i64>,
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
const SECTION: &str = "text-xs font-semibold text-gray-500 uppercase tracking-wider";

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

fn dbh_label(c: &DbhClass) -> String {
    match c.to_cm {
        Some(to) => format!("{}–{}", c.from_cm, to),
        None => format!("≥ {}", c.from_cm),
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
        {kpis(s)}
        <h2 class=SECTION>"Diversity"</h2>
        <div class="grid grid-cols-1 lg:grid-cols-5 gap-4">
            <div class="lg:col-span-2">{rule_card(s)}</div>
            <div class=format!("{CARD} lg:col-span-3")>
                <h3 class=H2>"Most planted species"</h3>
                <p class=NOTE>
                    {format!("Share of all {} trees. The 10 most common of {} species make up {:.0}% of the urban forest.",
                        n(s.total_trees), s.species_count,
                        s.concentration.top_species.iter().map(|t| t.percent).sum::<f64>())}
                </p>
                <div class="h-72 mt-3"><canvas id="topSpeciesChart"></canvas></div>
            </div>
        </div>

        <h2 class=SECTION>"Composition and structure"</h2>
        <div class="grid grid-cols-1 lg:grid-cols-2 gap-4">
            {origin_card(s)}
            <div class=CARD>
                <h3 class=H2>"Size structure (trunk diameter)"</h3>
                <p class=NOTE>{dbh_note(s)}</p>
                <div class="h-60 mt-3"><canvas id="dbhChart"></canvas></div>
            </div>
        </div>

        <h2 class=SECTION>"Distribution by comuna"</h2>
        {comunas_card(s)}

        <h2 class=SECTION>"Health and conservation"</h2>
        <div class="grid grid-cols-1 lg:grid-cols-5 gap-4">
            <div class=format!("{CARD} lg:col-span-3")>
                <h3 class=H2>"Health problems in the most common species"</h3>
                <p class=NOTE>
                    {format!("Share of each species' trees recorded sick, critical or dead (city average: {}). Highest first.",
                        pct(s.issues_percent))}
                </p>
                <div class="h-72 mt-3"><canvas id="speciesHealthChart"></canvas></div>
            </div>
            <div class="lg:col-span-2">{threatened_card(s)}</div>
        </div>
    }
}

fn kpis(s: &Summary) -> impl IntoView + use<> {
    let top = s.concentration.rule.iter().find(|r| r.level == "species");
    let threatened: i64 = s.threatened.by_status.iter().map(|b| b.count).sum();
    let per_1000 = s.trees_per_1000_inhabitants;
    let tile = |label: &'static str, value: String, note: String| {
        view! {
            <div class=CARD>
                <p class="text-xs font-medium text-gray-500 uppercase tracking-wider">{label}</p>
                <p class="mt-1 text-3xl font-bold text-gray-900">{value}</p>
                <p class="mt-1 text-sm text-gray-500">{note}</p>
            </div>
        }
    };
    view! {
        <div class="grid grid-cols-2 lg:grid-cols-5 gap-4">
            {tile(
                "Trees per 1,000 inhabitants",
                per_1000.map(n).unwrap_or_else(|| "—".into()),
                match per_1000 {
                    Some(v) if v > 0 => format!("About 1 tree per {:.0} people (pop. 2019: {})", 1000.0 / v as f64, n(s.population)),
                    _ => "No population data".into(),
                },
            )}
            {tile("Native origin", pct(s.native_percent), "Trees of native or endemic species".into())}
            {tile("With health problems", pct(s.issues_percent), "Recorded sick, critical or dead".into())}
            {tile(
                "Most planted species",
                top.map(|t| format!("{:.1}%", t.percent)).unwrap_or_else(|| "—".into()),
                top.map(|t| format!("{} (recommended max. {:.0}%)", t.name, t.limit)).unwrap_or_default(),
            )}
            {tile("Threatened species", n(threatened), format!("Trees of {} species in IUCN CR, EN or VU", s.threatened.species_count))}
        </div>
    }
}

fn rule_card(s: &Summary) -> impl IntoView + use<> {
    let rows = s
        .concentration
        .rule
        .iter()
        .map(|r| {
            let over = r.percent > r.limit;
            let (badge, icon, text) = if over {
                ("bg-red-100 text-red-800", "✕", "Above limit")
            } else {
                ("bg-green-100 text-green-800", "✓", "Within limit")
            };
            // Bar scale: 0-40%, so the 30% family limit fits.
            let width = (r.percent / 40.0 * 100.0).min(100.0);
            let mark = r.limit / 40.0 * 100.0;
            let fill = if over { "bg-red-500" } else { "bg-green-600" };
            let level = match r.level.as_str() {
                "species" => "Species",
                "genus" => "Genus",
                _ => "Family",
            };
            view! {
                <div>
                    <div class="flex items-baseline justify-between gap-2">
                        <p class="text-sm text-gray-900">
                            <span class="font-semibold">{level}</span>
                            " · "
                            <span class:italic=r.level != "family">{r.name.clone()}</span>
                        </p>
                        <span class=format!("shrink-0 px-2 py-0.5 rounded-full text-xs font-semibold {badge}")>{format!("{icon} {text}")}</span>
                    </div>
                    <div class="relative mt-1.5 h-3 rounded bg-gray-100">
                        <div class=format!("absolute inset-y-0 left-0 rounded {fill}") style=format!("width:{width:.1}%")></div>
                        <div class="absolute -inset-y-1 w-0.5 bg-gray-800" style=format!("left:{mark:.1}%") title=format!("Limit {:.0}%", r.limit)></div>
                    </div>
                    <p class="mt-1 text-xs text-gray-500">{format!("{:.1}% of all trees · limit {:.0}%", r.percent, r.limit)}</p>
                </div>
            }
        })
        .collect_view();
    view! {
        <div class=format!("{CARD} h-full")>
            <h3 class=H2>"10-20-30 rule"</h3>
            <p class=NOTE>
                "To limit the damage a single pest or disease can do, no species should exceed 10% of the urban forest, no genus 20% and no family 30% (Santamour). Largest of each:"
            </p>
            <div class="mt-4 space-y-4">{rows}</div>
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
            <h3 class=H2>"Origin of the trees"</h3>
            <p class=NOTE>
                "Native species are adapted to the local climate and support local fauna. Origin follows each species' record in the catalog."
            </p>
            <div class="mt-5 flex h-8 gap-0.5 overflow-hidden rounded">{segments}</div>
            <div class="mt-4 grid grid-cols-3 gap-3">{legend}</div>
            <p class="mt-4 text-xs text-gray-500">
                "Native includes native, endemic and native-cultivated species; introduced includes cultivated and naturalized ones."
            </p>
        </div>
    }
}

fn dbh_note(s: &Summary) -> String {
    let d = &s.dbh_classes;
    let small: f64 = d.classes.iter().filter(|c| c.to_cm.is_some_and(|t| t <= 20)).filter_map(|c| c.percent).sum();
    let large: f64 = d.classes.iter().filter(|c| c.from_cm >= 60).filter_map(|c| c.percent).sum();
    format!(
        "{} trees (palms and shrubs excluded). {small:.0}% are under 20 cm — a young population — and only {large:.1}% reach 60 cm or more.",
        n(d.trees_measured)
    )
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
                <div>
                    <h3 class=H2>"Trees per 1,000 inhabitants"</h3>
                    <p class=NOTE>
                        {format!("City-wide: {}. Highest first.", s.trees_per_1000_inhabitants.map(n).unwrap_or_else(|| "—".into()))}
                    </p>
                    <div class="h-80 mt-3"><canvas id="comunaChart"></canvas></div>
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
            <p class=NOTE>"Trees whose species is globally threatened (IUCN Red List). The category describes wild populations, not the planted trees."</p>
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
    top_species_chart(s);
    dbh_chart(s);
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

fn top_species_chart(s: &Summary) {
    let rows = &s.concentration.top_species;
    horizontal_bar(
        "topSpeciesChart",
        rows.iter().map(|r| format!("{} ({})", r.name, n(r.count))).collect(),
        vec![bar_dataset("Share of all trees (%)", rows.iter().map(|r| json!(r.percent)).collect(), BAR)],
        "% of all trees",
        false,
        false,
    );
}

fn dbh_chart(s: &Summary) {
    let c = &s.dbh_classes.classes;
    chart_by_id(
        "dbhChart",
        json!({
            "type": "bar",
            "data": {
                "labels": c.iter().map(dbh_label).collect::<Vec<_>>(),
                "datasets": [bar_dataset("Trees", c.iter().map(|x| json!(x.count)).collect(), BAR)]
            },
            "options": {
                "responsive": true,
                "maintainAspectRatio": false,
                "scales": {
                    "y": axes(false, "Trees")["y"],
                    "x": {
                        "grid": { "display": false },
                        "ticks": { "font": { "size": 11 }, "color": "#374151" },
                        "title": { "display": true, "text": "Diameter at breast height (cm)", "color": "#6b7280", "font": { "size": 11 } }
                    }
                },
                "plugins": { "legend": { "display": false } }
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
