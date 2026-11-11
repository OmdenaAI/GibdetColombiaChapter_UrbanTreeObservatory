//! Dashboard page: census, taxonomy and climate figures from `GET /api/v1/reports/dashboard/`
//! (one request, aggregated in the database).
//!
//! Blocks without a data source are labeled as such instead of showing sample numbers:
//! CO₂ absorption and oxygen production (no model yet). The former "monthly growth" and
//! "recent activity" blocks were replaced by the height distribution and the census
//! campaigns, because the census has one measurement per tree and no activity log.
//!
//! Texts follow the selected language: the content is rebuilt and the charts redrawn when
//! it changes.

use std::time::Duration;

use leptos::prelude::*;
use leptos::task::spawn_local;
use serde::Deserialize;
use serde_json::{Value, json};

use crate::api::{API_BASE, console_error, fmt_thousands, get_json};
use crate::i18n::{I18n, Lang, pick};
use crate::interop::chart::chart_by_id;
use crate::interop::when_connected;
use super::shared::{HEALTH, health_badge, health_label};

// ---------------------------------------------------------------------------
// API types
// ---------------------------------------------------------------------------

#[derive(Clone, Deserialize)]
struct Summary {
    overall: Overall,
    trees_per_capita: PerCapita,
    phytosanitary_status: std::collections::HashMap<String, i64>,
    top_species: Vec<TopSpecies>,
    records_by_year: RecordsByYear,
    height_distribution: Vec<HeightBin>,
    localities: Vec<LocalityStats>,
    functional_groups: Vec<GroupCount>,
    monthly_temperature: Temperature,
    recent_records: Vec<RecentRecord>,
    recent_climate: Vec<ClimateReading>,
}

#[derive(Clone, Deserialize)]
struct Overall {
    total_trees: i64,
    species_count: i64,
    avg_height_m: Option<f64>,
}

#[derive(Clone, Deserialize)]
struct PerCapita {
    population: Option<i64>,
    value: Option<f64>,
}

#[derive(Clone, Deserialize)]
struct TopSpecies {
    scientific_name: String,
    count: i64,
    percent: f64,
}

#[derive(Clone, Deserialize)]
struct RecordsByYear {
    years: Vec<YearCount>,
    invalid_dates: i64,
}

#[derive(Clone, Deserialize)]
struct YearCount {
    year: i32,
    count: i64,
}

#[derive(Clone, Deserialize)]
struct HeightBin {
    from_m: i64,
    to_m: Option<i64>,
    count: i64,
}

#[derive(Clone, Deserialize)]
struct LocalityStats {
    name: String,
    total_trees: i64,
}

#[derive(Clone, Deserialize)]
struct GroupCount {
    group: Option<i64>,
    count: i64,
}

#[derive(Clone, Deserialize)]
struct Temperature {
    months: Vec<String>,
    stations: Vec<StationSeries>,
}

#[derive(Clone, Deserialize)]
struct StationSeries {
    station: String,
    values: Vec<Option<f64>>,
}

/// Line colors for the temperature series (one per station).
const SERIES_COLORS: [&str; 5] = ["#f97316", "#2563eb", "#16a34a", "#9333ea", "#dc2626"];

#[derive(Clone, Deserialize)]
struct RecentRecord {
    id: i64,
    scientific_name: String,
    date: Option<String>,
    height_m: Option<f64>,
    phytosanitary_status: Option<String>,
    neighborhood: String,
    locality: String,
}

#[derive(Clone, Deserialize)]
struct ClimateReading {
    station: String,
    date: String,
    value: f64,
    unit: String,
}

#[derive(Clone)]
enum Load {
    Loading,
    Failed(String),
    Ready(std::sync::Arc<Summary>),
}

const CARD: &str = "bg-white rounded-lg shadow border border-gray-200 p-4";
const TH: &str = "px-2 py-2 text-left text-xs font-medium text-gray-500 uppercase";

fn month_label(l: Lang, ym: &str) -> String {
    const MONTHS_EN: [&str; 12] = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];
    const MONTHS_ES: [&str; 12] = ["Ene", "Feb", "Mar", "Abr", "May", "Jun", "Jul", "Ago", "Sep", "Oct", "Nov", "Dic"];
    let months = pick(l, MONTHS_ES, MONTHS_EN);
    let (y, m) = ym.split_once('-').unwrap_or((ym, "1"));
    let m: usize = m.parse().unwrap_or(1);
    format!("{} {}", months[(m.clamp(1, 12)) - 1], &y[y.len().saturating_sub(2)..])
}

// ---------------------------------------------------------------------------
// Page
// ---------------------------------------------------------------------------

#[component]
pub fn Dashboard() -> impl IntoView {
    let i = I18n::use_ctx();
    let state = RwSignal::new(Load::Loading);
    let load = move || {
        state.set(Load::Loading);
        spawn_local(async move {
            let url = format!("{API_BASE}/api/v1/reports/dashboard/");
            let res = get_json(&url)
                .await
                .and_then(|v| serde_json::from_value::<Summary>(v).map_err(|e| e.to_string()));
            match res {
                Ok(s) => state.try_set(Load::Ready(std::sync::Arc::new(s))),
                Err(e) => {
                    console_error("Error loading dashboard:", &e);
                    state.try_set(Load::Failed(e))
                }
            };
        });
    };
    load();

    // Charts need their canvases in the document: once the data is rendered, wait for the
    // page to be connected (route views mount asynchronously), then draw.
    let root = NodeRef::<leptos::html::Div>::new();
    Effect::new(move |_| {
        let ready = state.with(|s| match s {
            Load::Ready(s) => Some(s.clone()),
            _ => None,
        });
        let l = i.lang();
        if let (Some(el), Some(summary)) = (root.get(), ready) {
            when_connected(el.into(), move || {
                set_timeout(move || initialize_charts(&summary, l), Duration::from_millis(100))
            });
        }
    });

    view! {
        <div node_ref=root class="block w-full">
            <div class="bg-white rounded-lg p-6">
                <div class="mb-6">
                    <h1 class="text-2xl font-bold text-green-600">{move || i.t("Panel del arbolado urbano de Ibagué", "Ibagué Urban Forest Dashboard")}</h1>
                    <p class="text-gray-600 mt-1">{move || i.t("Resumen del censo de arbolado urbano y su impacto ambiental en Ibagué", "Overview of urban tree census data and environmental impact in Ibagué")}</p>
                </div>

                {move || { let l = i.lang(); match state.get() {
                    Load::Loading => view! {
                        <div class="py-24 flex items-center justify-center text-gray-500">
                            <div class="h-8 w-8 mr-3 rounded-full border-4 border-green-200 border-t-green-600 animate-spin"></div>
                            {pick(l, "Cargando el panel…", "Loading dashboard…")}
                        </div>
                    }
                    .into_any(),
                    Load::Failed(err) => view! {
                        <div class="py-24 flex flex-col items-center justify-center gap-3 text-gray-600">
                            <p class="font-medium text-red-600">{pick(l, "No se pudieron cargar los datos del panel.", "Could not load the dashboard data.")}</p>
                            <p class="text-sm text-gray-500">{err}</p>
                            <button class="px-4 py-2 rounded-lg bg-green-600 text-white hover:bg-green-700" on:click=move |_| load()>
                                {pick(l, "Reintentar", "Retry")}
                            </button>
                        </div>
                    }
                    .into_any(),
                    Load::Ready(s) => view! {
                        <div class="mb-8">
                            <h2 class="text-xl font-semibold text-gray-800 mb-3">{pick(l, "Resumen", "Overview")}</h2>
                            <h3 class="text-lg font-medium text-gray-700 mb-3">{pick(l, "Estadísticas del arbolado", "Tree Statistics")}</h3>
                            {stat_cards(&s, l)}
                            {health_and_campaigns(&s, l)}
                            {impact_and_species(&s, l)}
                        </div>
                        {analytics_section(l)}
                        {records_section(&s, l)}
                    }
                    .into_any(),
                }}}
            </div>
        </div>
    }
}

fn stat_cards(s: &Summary, l: Lang) -> impl IntoView + use<> {
    let height = s.overall.avg_height_m.map(|h| format!("{h:.2} m")).unwrap_or_else(|| "N/A".into());
    let per_capita = s.trees_per_capita.value.map(|v| format!("{v:.2}")).unwrap_or_else(|| "N/A".into());
    let population = s
        .trees_per_capita
        .population
        .map(|p| pick(l, format!("Árboles por habitante (pobl. 2019: {})", fmt_thousands(p)), format!("Trees per inhabitant (pop. 2019: {})", fmt_thousands(p))))
        .unwrap_or_else(|| pick(l, "Árboles por habitante", "Trees per inhabitant").into());

    view! {
        <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
            <div class="bg-green-50 p-4 rounded-lg shadow border border-green-100">
                <h4 class="text-xs font-medium text-gray-500 uppercase">{pick(l, "Total de árboles", "Total Trees")}</h4>
                <p class="text-3xl font-bold text-green-600">{fmt_thousands(s.overall.total_trees)}</p>
                <p class="text-green-600 text-xs mt-1">{pick(l, "Censo de arbolado urbano", "Urban Tree Census")}</p>
            </div>
            <div class="bg-blue-50 p-4 rounded-lg shadow border border-blue-100">
                <h4 class="text-xs font-medium text-gray-500 uppercase">{pick(l, "Número de especies", "Species Count")}</h4>
                <p class="text-3xl font-bold text-blue-600">{fmt_thousands(s.overall.species_count)}</p>
                <p class="text-blue-600 text-xs mt-1">{pick(l, "Diversidad total de especies", "Total species diversity")}</p>
            </div>
            <div class="bg-purple-50 p-4 rounded-lg shadow border border-purple-100">
                <h4 class="text-xs font-medium text-gray-500 uppercase">{pick(l, "Altura promedio", "Average Height")}</h4>
                <p class="text-3xl font-bold text-purple-600">{height}</p>
                <p class="text-purple-600 text-xs mt-1">{pick(l, "Altura total media", "Mean total height")}</p>
            </div>
            <div class="bg-amber-50 p-4 rounded-lg shadow border border-amber-100">
                <h4 class="text-xs font-medium text-gray-500 uppercase">{pick(l, "Árboles per cápita", "Tree-per-capita")}</h4>
                <p class="text-3xl font-bold text-amber-600">{per_capita}</p>
                <p class="text-amber-600 text-xs mt-1">{population}</p>
            </div>
        </div>
    }
}

fn health_and_campaigns(s: &Summary, l: Lang) -> impl IntoView + use<> {
    let legend = HEALTH
        .iter()
        .map(|(code, es, en, dot, _)| {
            let n = s.phytosanitary_status.get(*code).copied().unwrap_or(0);
            view! {
                <div class="text-center">
                    <span class=format!("block w-4 h-4 mx-auto rounded-full {dot}")></span>
                    <span class="text-xs font-medium block mt-1">{pick(l, *es, *en)}</span>
                    <span class="text-xs text-gray-500">{format!("{} {}", fmt_thousands(n), pick(l, "árboles", "trees"))}</span>
                </div>
            }
        })
        .collect_view();

    let max = s.records_by_year.years.iter().map(|y| y.count).max().unwrap_or(1).max(1);
    let years = s
        .records_by_year
        .years
        .iter()
        .map(|y| {
            let width = format!("width: {:.1}%", 100.0 * y.count as f64 / max as f64);
            view! {
                <li>
                    <div class="flex justify-between text-sm">
                        <span class="font-medium text-gray-900">{y.year}</span>
                        <span class="text-gray-600">{format!("{} {}", fmt_thousands(y.count), pick(l, "registros", "records"))}</span>
                    </div>
                    <div class="mt-1 h-2 rounded bg-gray-100">
                        <div class="h-2 rounded bg-green-500" style=width></div>
                    </div>
                </li>
            }
        })
        .collect_view();
    let invalid = s.records_by_year.invalid_dates;

    view! {
        <div class="grid grid-cols-1 md:grid-cols-2 gap-6 mb-6">
            // Tree Health Distribution (phytosanitary status of the census observations)
            <div class=CARD>
                <h3 class="text-lg font-medium text-gray-700 mb-3">{pick(l, "Estado fitosanitario", "Tree Health Distribution")}</h3>
                <div class="flex justify-center">
                    <div class="h-64 w-64">
                        <canvas id="healthDistributionChart"></canvas>
                    </div>
                </div>
                <div class="flex justify-between mt-4 text-center">{legend}</div>
            </div>

            // Census campaigns (records per year)
            <div class=CARD>
                <h3 class="text-lg font-medium text-gray-700 mb-3">{pick(l, "Campañas del censo", "Census Campaigns")}</h3>
                <p class="text-sm text-gray-500 mb-4">{pick(l, "Árboles registrados por año (fuente: Cortolima)", "Trees recorded per year (source: Cortolima)")}</p>
                <ul class="space-y-4">{years}</ul>
                {(invalid > 0).then(|| view! {
                    <p class="mt-4 text-xs text-gray-400">
                        {pick(l, format!("{invalid} registro(s) con fecha inválida no se muestran."), format!("{invalid} record(s) with an invalid date are not shown."))}
                    </p>
                })}
            </div>
        </div>
    }
}

fn impact_and_species(s: &Summary, l: Lang) -> impl IntoView + use<> {
    let top = s.top_species.first().map(|t| t.count).unwrap_or(1).max(1);
    let species = s
        .top_species
        .iter()
        .map(|t| {
            let width = format!("width: {:.1}%", 100.0 * t.count as f64 / top as f64);
            view! {
                <div class="flex flex-col">
                    <span class="text-sm italic">{t.scientific_name.clone()}</span>
                    <div class="flex items-center mt-1">
                        <div class="flex-1 h-2 rounded bg-gray-100">
                            <div class="h-2 bg-green-500 rounded" style=width></div>
                        </div>
                        <span class="ml-2 text-xs w-28 text-right">{format!("{} ({:.2}%)", fmt_thousands(t.count), t.percent)}</span>
                    </div>
                </div>
            }
        })
        .collect_view();

    view! {
        <div class="grid grid-cols-1 md:grid-cols-2 gap-6 mb-6">
            // Environmental Impact: no data source yet
            <div class=CARD>
                <h3 class="text-lg font-medium text-gray-700 mb-3">{pick(l, "Impacto ambiental", "Environmental Impact")}</h3>
                <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
                    <div class="bg-green-50 p-4 rounded-lg border border-green-100">
                        <h4 class="text-xs font-medium text-gray-500 uppercase">{pick(l, "Absorción de CO₂", "CO₂ Absorption")}</h4>
                        <p class="text-2xl font-bold text-gray-400">"N/A"</p>
                        <p class="text-green-600 text-xs mt-1">{pick(l, "Toneladas", "Tons")}</p>
                    </div>
                    <div class="bg-blue-50 p-4 rounded-lg border border-blue-100">
                        <h4 class="text-xs font-medium text-gray-500 uppercase">{pick(l, "Producción de oxígeno", "Oxygen Production")}</h4>
                        <p class="text-2xl font-bold text-gray-400">"N/A"</p>
                        <p class="text-blue-600 text-xs mt-1">{pick(l, "Toneladas/año", "Tons/year")}</p>
                    </div>
                </div>
                <p class="mt-3 text-xs text-gray-400">
                    {pick(l, "Aún no se calcula: la base de datos no tiene un modelo de carbono ni de oxígeno para los árboles del censo.", "Not computed yet: the database has no carbon or oxygen model for the census trees.")}
                </p>
            </div>

            // Top Species Distribution
            <div class=CARD>
                <h3 class="text-lg font-medium text-gray-700 mb-3">{pick(l, "Especies más frecuentes", "Top Species Distribution")}</h3>
                <div class="space-y-3">{species}</div>
            </div>
        </div>
    }
}

/// Card with a title, the "more" (⋯) button and a `h-64` canvas.
#[component]
fn ChartCard(title: &'static str, canvas_id: &'static str, #[prop(optional)] note: &'static str) -> impl IntoView {
    view! {
        <div class=CARD>
            <div class="flex justify-between mb-3">
                <div>
                    <h3 class="text-lg font-medium text-gray-700">{title}</h3>
                    {(!note.is_empty()).then(|| view! { <p class="text-xs text-gray-400">{note}</p> })}
                </div>
                <button class="text-gray-400 hover:text-gray-600">
                    <svg xmlns="http://www.w3.org/2000/svg" class="h-5 w-5" viewBox="0 0 20 20" fill="currentColor">
                        <path d="M6 10a2 2 0 11-4 0 2 2 0 014 0zM12 10a2 2 0 11-4 0 2 2 0 014 0zM16 12a2 2 0 100-4 2 2 0 000 4z" />
                    </svg>
                </button>
            </div>
            <div class="h-64">
                <canvas id=canvas_id></canvas>
            </div>
        </div>
    }
}

fn analytics_section(l: Lang) -> impl IntoView {
    view! {
        <div>
            <h2 class="text-xl font-semibold text-gray-800 mb-3">{pick(l, "Gráficas", "Analytics")}</h2>
            <div class="grid grid-cols-1 md:grid-cols-2 gap-6 mb-6">
                <ChartCard title=pick(l, "Distribución de alturas", "Height Distribution") canvas_id="heightDistributionChart" note=pick(l, "Árboles por rango de altura total", "Trees per total-height range") />
                <ChartCard title=pick(l, "Distribución geográfica", "Geographic Distribution") canvas_id="geoDistributionChart" note=pick(l, "Árboles por comuna", "Trees per comuna") />
            </div>
            <div class="grid grid-cols-1 md:grid-cols-2 gap-6 mb-6">
                <ChartCard title=pick(l, "Tendencia de temperatura", "Temperature Trends") canvas_id="temperatureTrendsChart" note=pick(l, "Temperatura media mensual del aire por estación, últimos 12 meses con datos", "Monthly mean air temperature per station, last 12 months with data") />
                <ChartCard title=pick(l, "Grupos funcionales", "Functional Groups") canvas_id="functionalGroupsChart" note=pick(l, "Árboles por grupo funcional de su especie", "Trees per functional group of their species") />
            </div>
        </div>
    }
}

fn records_section(s: &Summary, l: Lang) -> impl IntoView + use<> {
    let records = s
        .recent_records
        .iter()
        .map(|t| {
            let status = t.phytosanitary_status.clone().unwrap_or_default();
            let badge = health_badge(&status);
            view! {
                <tr>
                    <td class="px-2 py-2 text-sm">{t.id}</td>
                    <td class="px-2 py-2 text-sm italic">{t.scientific_name.clone()}</td>
                    <td class="px-2 py-2 text-sm whitespace-nowrap">
                        {t.height_m.map(|h| format!("{h:.1} m")).unwrap_or_else(|| "—".into())}
                    </td>
                    <td class="px-2 py-2">
                        <span class=format!("px-2 py-0.5 inline-flex text-xs leading-5 font-semibold rounded-full {badge}")>
                            {health_label(l, &status)}
                        </span>
                    </td>
                    <td class="px-2 py-2 text-sm">{format!("{}, {}", t.neighborhood, t.locality)}</td>
                    <td class="px-2 py-2 text-sm whitespace-nowrap">{t.date.clone().unwrap_or_default()}</td>
                </tr>
            }
        })
        .collect_view();

    let climate = s
        .recent_climate
        .iter()
        .map(|r| view! {
            <tr>
                <td class="px-2 py-2 text-sm">{r.station.clone()}</td>
                <td class="px-2 py-2 text-sm whitespace-nowrap">{r.date.clone()}</td>
                <td class="px-2 py-2 text-sm whitespace-nowrap">{format!("{:.1} {}", r.value, r.unit)}</td>
            </tr>
        })
        .collect_view();

    view! {
        <div>
            <h2 class="text-xl font-semibold text-gray-800 mb-3">{pick(l, "Registros", "Records")}</h2>
            <div class="grid grid-cols-1 md:grid-cols-2 gap-6">
                <div class="bg-white rounded-lg shadow border border-gray-200 p-4 overflow-x-auto">
                    <h3 class="text-lg font-medium text-gray-700 mb-3">{pick(l, "Registros recientes de árboles", "Recent Tree Records")}</h3>
                    <table class="min-w-full divide-y divide-gray-200">
                        <thead>
                            <tr>
                                <th class=TH>"ID"</th>
                                <th class=TH>{pick(l, "Especie", "Species")}</th>
                                <th class=TH>{pick(l, "Altura", "Height")}</th>
                                <th class=TH>{pick(l, "Salud", "Health")}</th>
                                <th class=TH>{pick(l, "Ubicación", "Location")}</th>
                                <th class=TH>{pick(l, "Fecha", "Date")}</th>
                            </tr>
                        </thead>
                        <tbody class="divide-y divide-gray-200">{records}</tbody>
                    </table>
                </div>

                <div class="bg-white rounded-lg shadow border border-gray-200 p-4 overflow-x-auto">
                    <h3 class="text-lg font-medium text-gray-700 mb-3">{pick(l, "Últimas lecturas de clima", "Latest Climate Readings")}</h3>
                    <table class="min-w-full divide-y divide-gray-200">
                        <thead>
                            <tr>
                                <th class=TH>{pick(l, "Estación", "Station")}</th>
                                <th class=TH>{pick(l, "Fecha", "Date")}</th>
                                <th class=TH>{pick(l, "Temperatura del aire", "Air temperature")}</th>
                            </tr>
                        </thead>
                        <tbody class="divide-y divide-gray-200">{climate}</tbody>
                    </table>
                    <p class="mt-3 text-xs text-gray-400">{pick(l, "Última lectura de cada estación. Las estaciones solo reportan temperatura del aire.", "Last reading of each station. The stations only report air temperature.")}</p>
                </div>
            </div>
        </div>
    }
}

// ---------------------------------------------------------------------------
// Charts
// ---------------------------------------------------------------------------

fn initialize_charts(s: &Summary, l: Lang) {
    create_health_distribution_chart(s, l);
    create_height_distribution_chart(s, l);
    create_geo_distribution_chart(s, l);
    create_temperature_trends_chart(s, l);
    create_functional_groups_chart(s, l);
}

fn small_ticks_xy() -> Value {
    json!({
        "y": { "beginAtZero": true, "grid": { "display": true, "color": "rgba(0, 0, 0, 0.05)" }, "ticks": { "font": { "size": 10 } } },
        "x": { "grid": { "display": false }, "ticks": { "font": { "size": 10 } } }
    })
}

fn bar_chart(id: &str, labels: Vec<String>, data: Vec<i64>, label: &str, y_title: &str, x_title: &str) {
    chart_by_id(
        id,
        json!({
            "type": "bar",
            "data": {
                "labels": labels,
                "datasets": [{
                    "label": label,
                    "data": data,
                    "backgroundColor": "#2F7B3D",
                    "borderRadius": 4,
                    "borderSkipped": false
                }]
            },
            "options": {
                "responsive": true,
                "maintainAspectRatio": false,
                "scales": {
                    "y": {
                        "beginAtZero": true,
                        "grid": { "display": true, "color": "rgba(0, 0, 0, 0.05)" },
                        "ticks": { "font": { "size": 10 } },
                        "title": { "display": true, "text": y_title }
                    },
                    "x": {
                        "grid": { "display": false },
                        "ticks": { "font": { "size": 10 } },
                        "title": { "display": true, "text": x_title }
                    }
                },
                "plugins": { "legend": { "display": false } }
            }
        }),
        true,
    );
}

fn create_health_distribution_chart(s: &Summary, l: Lang) {
    let labels: Vec<_> = HEALTH.iter().map(|(_, es, en, ..)| pick(l, *es, *en)).collect();
    let data: Vec<_> = HEALTH.iter().map(|(c, ..)| s.phytosanitary_status.get(*c).copied().unwrap_or(0)).collect();
    let colors: Vec<_> = HEALTH.iter().map(|(.., color)| *color).collect();
    chart_by_id(
        "healthDistributionChart",
        json!({
            "type": "doughnut",
            "data": {
                "labels": labels,
                "datasets": [{ "data": data, "backgroundColor": colors, "borderWidth": 0 }]
            },
            "options": {
                "responsive": true,
                "cutout": "70%",
                "plugins": { "legend": { "display": false }, "tooltip": { "enabled": true } }
            }
        }),
        true,
    );
}

fn create_height_distribution_chart(s: &Summary, l: Lang) {
    let labels = s
        .height_distribution
        .iter()
        .map(|b| match b.to_m {
            Some(to) => format!("{}–{} m", b.from_m, to),
            None => format!("≥ {} m", b.from_m),
        })
        .collect();
    let data = s.height_distribution.iter().map(|b| b.count).collect();
    let trees = pick(l, "Árboles", "Trees");
    bar_chart("heightDistributionChart", labels, data, trees, trees, pick(l, "Altura total", "Total height"));
}

fn create_geo_distribution_chart(s: &Summary, l: Lang) {
    let labels = s.localities.iter().map(|l| l.name.clone()).collect();
    let data = s.localities.iter().map(|l| l.total_trees).collect();
    let trees = pick(l, "Total de árboles", "Total trees");
    bar_chart("geoDistributionChart", labels, data, trees, trees, "Comunas");
}

fn create_temperature_trends_chart(s: &Summary, l: Lang) {
    let labels: Vec<_> = s.monthly_temperature.months.iter().map(|m| month_label(l, m)).collect();
    let datasets: Vec<_> = s
        .monthly_temperature
        .stations
        .iter()
        .enumerate()
        .map(|(i, st)| {
            let color = SERIES_COLORS[i % SERIES_COLORS.len()];
            json!({
                "label": st.station,
                "data": st.values,
                "borderColor": color,
                "backgroundColor": color,
                "tension": 0.3,
                "pointRadius": 3,
                "borderWidth": 2,
                "spanGaps": false
            })
        })
        .collect();
    let mut scales = small_ticks_xy();
    scales["y"]["beginAtZero"] = json!(false);
    scales["y"]["title"] = json!({ "display": true, "text": "°C" });
    chart_by_id(
        "temperatureTrendsChart",
        json!({
            "type": "line",
            "data": { "labels": labels, "datasets": datasets },
            "options": {
                "responsive": true,
                "maintainAspectRatio": false,
                "scales": scales,
                "plugins": { "legend": { "display": true, "position": "bottom", "labels": { "boxWidth": 10, "font": { "size": 10 } } } }
            }
        }),
        true,
    );
}

fn create_functional_groups_chart(s: &Summary, l: Lang) {
    let labels = s
        .functional_groups
        .iter()
        .map(|g| g.group.map(|n| n.to_string()).unwrap_or_else(|| pick(l, "Ninguno", "None").into()))
        .collect();
    let data = s.functional_groups.iter().map(|g| g.count).collect();
    let trees = pick(l, "Árboles", "Trees");
    bar_chart("functionalGroupsChart", labels, data, trees, trees, pick(l, "Grupo funcional", "Functional group"));
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn month_labels() {
        assert_eq!(month_label(Lang::En, "2025-04"), "Apr 25");
        assert_eq!(month_label(Lang::Es, "2024-12"), "Dic 24");
    }
}
