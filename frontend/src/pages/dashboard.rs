//! Dashboard page.
//!
//! KNOWN ISSUE: all figures and records are hardcoded sample data (some rows are from other
//! cities); charts are created via `document.getElementById` and never destroyed.

use std::time::Duration;

use leptos::prelude::*;
use serde_json::json;

use crate::interop::chart::chart_by_id;
use crate::interop::when_connected;

struct Activity {
    ty: &'static str,
    description: &'static str,
    time: &'static str,
    user: &'static str,
}

const RECENT_ACTIVITIES: [Activity; 4] = [
    Activity { ty: "added", description: "New Ceiba pentandra added in Comuna 6", time: "2 hours ago", user: "Maria Lopez" },
    Activity { ty: "updated", description: "Updated health assessment for Quercus #IBG-235", time: "5 hours ago", user: "John Smith" },
    Activity { ty: "maintenance", description: "Scheduled pruning for Tabebuia cluster in Comuna 2", time: "Yesterday", user: "Carlos Rodriguez" },
    Activity { ty: "added", description: "Added 5 new Ficus benjamina saplings in Comuna 4", time: "2 days ago", user: "Maria Lopez" },
];

struct TreeRecord {
    id: &'static str,
    species: &'static str,
    height: &'static str,
    health: &'static str,
    location: &'static str,
}

const RECENT_TREE_RECORDS: [TreeRecord; 5] = [
    TreeRecord { id: "T001", species: "Ceiba pentandra", height: "25.4m", health: "Healthy", location: "Bogotá" },
    TreeRecord { id: "T002", species: "Quercus humboldtii", height: "18.2m", health: "Moderate", location: "Medellín" },
    TreeRecord { id: "T003", species: "Tabebuia rosea", height: "12.8m", health: "Healthy", location: "Cali" },
    TreeRecord { id: "T004", species: "Ficus benjamina", height: "15.6m", health: "Poor", location: "Cartagena" },
    TreeRecord { id: "T005", species: "Samanea saman", height: "22.1m", health: "Healthy", location: "Barranquilla" },
];

struct Climate {
    station: &'static str,
    date: &'static str,
    temperature: &'static str,
    rainfall: &'static str,
    humidity: &'static str,
}

const CLIMATE_DATA: [Climate; 5] = [
    Climate { station: "BOG001", date: "2024-03-15", temperature: "18.5", rainfall: "2.3", humidity: "65" },
    Climate { station: "MED002", date: "2024-03-15", temperature: "22.1", rainfall: "0.0", humidity: "58" },
    Climate { station: "CAL003", date: "2024-03-15", temperature: "25.8", rainfall: "1.5", humidity: "72" },
    Climate { station: "BAR004", date: "2024-03-15", temperature: "28.2", rainfall: "0.8", humidity: "75" },
    Climate { station: "CTG005", date: "2024-03-15", temperature: "29.5", rainfall: "0.0", humidity: "80" },
];

const CARD: &str = "bg-white rounded-lg shadow border border-gray-200 p-4";
const TH: &str = "px-2 py-2 text-left text-xs font-medium text-gray-500 uppercase";

#[component]
pub fn Dashboard() -> impl IntoView {
    // Charts are created 100 ms after the view is attached to the document
    // (on client-side navigation the route view is mounted asynchronously).
    let root = NodeRef::<leptos::html::Div>::new();
    Effect::new(move |_| {
        if let Some(el) = root.get() {
            when_connected(el.into(), || set_timeout(initialize_charts, Duration::from_millis(100)));
        }
    });

    view! {
        <div node_ref=root class="block w-full">
            <div class="bg-white rounded-lg p-6">
                <div class="mb-6">
                    <h1 class="text-2xl font-bold text-green-600">"Ibagué Urban Forest Dashboard"</h1>
                    <p class="text-gray-600 mt-1">"Overview of urban tree census data and environmental impact in Ibagué"</p>
                </div>

                <div class="mb-8">
                    <h2 class="text-xl font-semibold text-gray-800 mb-3">"Overview"</h2>
                    <h3 class="text-lg font-medium text-gray-700 mb-3">"Tree Statistics"</h3>
                    <StatCards />
                    <HealthAndActivity />
                    <ImpactAndSpecies />
                </div>

                <AnalyticsSection />
                <RecordsSection />
            </div>
        </div>
    }
}

#[component]
fn StatCards() -> impl IntoView {
    view! {
        <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
            <div class="bg-green-50 p-4 rounded-lg shadow border border-green-100">
                <h4 class="text-xs font-medium text-gray-500 uppercase">"Total Trees"</h4>
                <p class="text-3xl font-bold text-green-600">"96,943"</p>
                <p class="text-green-600 text-xs mt-1">"Urban Tree Census"</p>
            </div>
            <div class="bg-blue-50 p-4 rounded-lg shadow border border-blue-100">
                <h4 class="text-xs font-medium text-gray-500 uppercase">"Species Count"</h4>
                <p class="text-3xl font-bold text-blue-600">"439"</p>
                <p class="text-blue-600 text-xs mt-1">"Total species diversity"</p>
            </div>
            <div class="bg-purple-50 p-4 rounded-lg shadow border border-purple-100">
                <h4 class="text-xs font-medium text-gray-500 uppercase">"Average Height"</h4>
                <p class="text-3xl font-bold text-purple-600">"17.30 m"</p>
                <p class="text-purple-600 text-xs mt-1">"Tree canopy height"</p>
            </div>
            <div class="bg-amber-50 p-4 rounded-lg shadow border border-amber-100">
                <h4 class="text-xs font-medium text-gray-500 uppercase">"Tree-per-capita"</h4>
                <p class="text-3xl font-bold text-amber-600">"0.18"</p>
                <p class="text-amber-600 text-xs mt-1">"Urban tree index"</p>
            </div>
        </div>
    }
}

#[component]
fn HealthAndActivity() -> impl IntoView {
    let legend = [
        ("bg-green-500", "Healthy", "67,890 trees"),
        ("bg-yellow-500", "Needs Attention", "19,389 trees"),
        ("bg-red-500", "Critical", "5,817 trees"),
        ("bg-gray-400", "Unknown", "3,847 trees"),
    ];

    view! {
        <div class="grid grid-cols-1 md:grid-cols-2 gap-6 mb-6">
            // Tree Health Distribution
            <div class=CARD>
                <h3 class="text-lg font-medium text-gray-700 mb-3">"Tree Health Distribution"</h3>
                <div class="flex justify-center">
                    <div class="h-64 w-64">
                        <canvas id="healthDistributionChart"></canvas>
                    </div>
                </div>
                <div class="flex justify-between mt-4 text-center">
                    {legend
                        .into_iter()
                        .map(|(dot, label, count)| view! {
                            <div class="text-center">
                                <span class=format!("block w-4 h-4 mx-auto rounded-full {dot}")></span>
                                <span class="text-xs font-medium block mt-1">{label}</span>
                                <span class="text-xs text-gray-500">{count}</span>
                            </div>
                        })
                        .collect_view()}
                </div>
            </div>

            // Recent Activity
            <div class=CARD>
                <h3 class="text-lg font-medium text-gray-700 mb-3">"Recent Activity"</h3>
                <ul class="space-y-3">
                    {RECENT_ACTIVITIES
                        .iter()
                        .map(|a| {
                            let badge = match a.ty {
                                "added" => "bg-green-100 text-green-800",
                                "updated" => "bg-blue-100 text-blue-800",
                                "maintenance" => "bg-amber-100 text-amber-800",
                                _ => "",
                            };
                            view! {
                                <li class="flex items-start">
                                    <span class=format!("px-2 py-0.5 inline-flex text-xs leading-5 font-semibold rounded-full mr-3 mt-0.5 {badge}")>
                                        {a.ty}
                                    </span>
                                    <div>
                                        <p class="text-sm font-medium text-gray-900">{a.description}</p>
                                        <p class="text-xs text-gray-500">{format!("{} by {}", a.time, a.user)}</p>
                                    </div>
                                </li>
                            }
                        })
                        .collect_view()}
                </ul>
            </div>
        </div>
    }
}

#[component]
fn ImpactAndSpecies() -> impl IntoView {
    let species = [
        ("Tabebuia rosea", "width: 15%", "9,463 (9.76%)"),
        ("Dypsis lutescens", "width: 12%", "7,430 (7.66%)"),
        ("Syzygium malaccense", "width: 10%", "7,175 (7.40%)"),
    ];

    view! {
        <div class="grid grid-cols-1 md:grid-cols-2 gap-6 mb-6">
            // Environmental Impact
            <div class=CARD>
                <h3 class="text-lg font-medium text-gray-700 mb-3">"Environmental Impact"</h3>
                <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
                    <div class="bg-green-50 p-4 rounded-lg border border-green-100">
                        <h4 class="text-xs font-medium text-gray-500 uppercase">"CO₂ Absorption"</h4>
                        <p class="text-2xl font-bold text-green-600">"646,867.27"</p>
                        <p class="text-green-600 text-xs mt-1">"Tons"</p>
                    </div>
                    <div class="bg-blue-50 p-4 rounded-lg border border-blue-100">
                        <h4 class="text-xs font-medium text-gray-500 uppercase">"Oxygen Production"</h4>
                        <p class="text-2xl font-bold text-blue-600">"1,727,135.62"</p>
                        <p class="text-blue-600 text-xs mt-1">"Tons/year"</p>
                    </div>
                </div>
            </div>

            // Top Species Distribution
            <div class=CARD>
                <h3 class="text-lg font-medium text-gray-700 mb-3">"Top Species Distribution"</h3>
                <div class="space-y-2">
                    {species
                        .into_iter()
                        .map(|(name, width, label)| view! {
                            <div class="flex flex-col">
                                <span class="text-sm">{name}</span>
                                <div class="flex items-center mt-1">
                                    <div class="h-2 bg-green-500 rounded" style=width></div>
                                    <span class="ml-2 text-xs">{label}</span>
                                </div>
                            </div>
                        })
                        .collect_view()}
                </div>
            </div>
        </div>
    }
}

/// Card with a title, the "more" (⋯) button and a `h-64` canvas.
#[component]
fn ChartCard(title: &'static str, canvas_id: &'static str) -> impl IntoView {
    view! {
        <div class=CARD>
            <div class="flex justify-between mb-3">
                <h3 class="text-lg font-medium text-gray-700">{title}</h3>
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

#[component]
fn AnalyticsSection() -> impl IntoView {
    view! {
        <div>
            <h2 class="text-xl font-semibold text-gray-800 mb-3">"Analytics"</h2>
            <div class="grid grid-cols-1 md:grid-cols-2 gap-6 mb-6">
                <ChartCard title="Monthly Growth Trends" canvas_id="growthTrendsChart" />
                <ChartCard title="Geographic Distribution" canvas_id="geoDistributionChart" />
            </div>
            <div class="grid grid-cols-1 md:grid-cols-2 gap-6 mb-6">
                <ChartCard title="Temperature Trends" canvas_id="temperatureTrendsChart" />
                <ChartCard title="Functional Groups" canvas_id="functionalGroupsChart" />
            </div>
        </div>
    }
}

#[component]
fn RecordsSection() -> impl IntoView {
    view! {
        <div>
            <h2 class="text-xl font-semibold text-gray-800 mb-3">"Records"</h2>
            <div class="grid grid-cols-1 md:grid-cols-2 gap-6">
                // Recent Tree Records
                <div class="bg-white rounded-lg shadow border border-gray-200 p-4 overflow-x-auto">
                    <h3 class="text-lg font-medium text-gray-700 mb-3">"Recent Tree Records"</h3>
                    <table class="min-w-full divide-y divide-gray-200">
                        <thead>
                            <tr>
                                <th class=TH>"ID"</th>
                                <th class=TH>"Species"</th>
                                <th class=TH>"Height"</th>
                                <th class=TH>"Health"</th>
                                <th class=TH>"Location"</th>
                            </tr>
                        </thead>
                        <tbody class="divide-y divide-gray-200">
                            {RECENT_TREE_RECORDS
                                .iter()
                                .map(|t| {
                                    let badge = match t.health {
                                        "Healthy" => "bg-green-100 text-green-800",
                                        "Moderate" => "bg-yellow-100 text-yellow-800",
                                        "Poor" => "bg-red-100 text-red-800",
                                        _ => "",
                                    };
                                    view! {
                                        <tr>
                                            <td class="px-2 py-2 text-sm">{t.id}</td>
                                            <td class="px-2 py-2 text-sm">{t.species}</td>
                                            <td class="px-2 py-2 text-sm">{t.height}</td>
                                            <td class="px-2 py-2">
                                                <span class=format!("px-2 py-0.5 inline-flex text-xs leading-5 font-semibold rounded-full {badge}")>
                                                    {t.health}
                                                </span>
                                            </td>
                                            <td class="px-2 py-2 text-sm">{t.location}</td>
                                        </tr>
                                    }
                                })
                                .collect_view()}
                        </tbody>
                    </table>
                </div>

                // Recent Climate Data
                <div class="bg-white rounded-lg shadow border border-gray-200 p-4 overflow-x-auto">
                    <h3 class="text-lg font-medium text-gray-700 mb-3">"Recent Climate Data"</h3>
                    <table class="min-w-full divide-y divide-gray-200">
                        <thead>
                            <tr>
                                <th class=TH>"Station"</th>
                                <th class=TH>"Date"</th>
                                <th class=TH>"Temperature"</th>
                                <th class=TH>"Rainfall"</th>
                                <th class=TH>"Humidity"</th>
                            </tr>
                        </thead>
                        <tbody class="divide-y divide-gray-200">
                            {CLIMATE_DATA
                                .iter()
                                .map(|r| view! {
                                    <tr>
                                        <td class="px-2 py-2 text-sm">{r.station}</td>
                                        <td class="px-2 py-2 text-sm">{r.date}</td>
                                        <td class="px-2 py-2 text-sm">{format!("{}°C", r.temperature)}</td>
                                        <td class="px-2 py-2 text-sm">{format!("{}mm", r.rainfall)}</td>
                                        <td class="px-2 py-2 text-sm">{format!("{}%", r.humidity)}</td>
                                    </tr>
                                })
                                .collect_view()}
                        </tbody>
                    </table>
                </div>
            </div>
        </div>
    }
}

// ---------------------------------------------------------------------------
// Charts
// ---------------------------------------------------------------------------

fn initialize_charts() {
    create_health_distribution_chart();
    create_growth_trends_chart();
    create_geo_distribution_chart();
    create_temperature_trends_chart();
    create_functional_groups_chart();
}

fn small_ticks_xy() -> serde_json::Value {
    json!({
        "y": { "beginAtZero": true, "grid": { "display": true, "color": "rgba(0, 0, 0, 0.05)" }, "ticks": { "font": { "size": 10 } } },
        "x": { "grid": { "display": false }, "ticks": { "font": { "size": 10 } } }
    })
}

fn create_health_distribution_chart() {
    chart_by_id(
        "healthDistributionChart",
        json!({
            "type": "doughnut",
            "data": {
                "labels": ["Healthy", "Needs Attention", "Critical", "Unknown"],
                "datasets": [{
                    "data": [70, 20, 6, 4],
                    "backgroundColor": ["#10b981", "#f59e0b", "#ef4444", "#9ca3af"],
                    "borderWidth": 0
                }]
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

fn create_growth_trends_chart() {
    chart_by_id(
        "growthTrendsChart",
        json!({
            "type": "line",
            "data": {
                "labels": ["Jan", "Feb", "Mar", "Apr", "May", "Jun"],
                "datasets": [{
                    "label": "Growth (cm)",
                    "data": [5, 7, 10, 14, 12, 8],
                    "borderColor": "#10b981",
                    "backgroundColor": "rgba(16, 185, 129, 0.1)",
                    "fill": true,
                    "tension": 0.4,
                    "pointBackgroundColor": "#10b981",
                    "borderWidth": 2
                }]
            },
            "options": { "scales": small_ticks_xy(), "plugins": { "legend": { "display": false } } }
        }),
        true,
    );
}

fn create_geo_distribution_chart() {
    chart_by_id(
        "geoDistributionChart",
        json!({
            "type": "bar",
            "data": {
                "labels": [
                    "Comuna 1", "Comuna 2", "Comuna 3", "Comuna 4",
                    "Comuna 5", "Comuna 6", "Comuna 7", "Comuna 8",
                    "Comuna 9", "Comuna 10", "Comuna 11", "Comuna 12",
                    "Comuna 13", "Comuna 14"
                ],
                "datasets": [{
                    "label": "Total Trees",
                    "data": [3269, 2311, 2476, 3220, 8492, 5590, 10890, 16893, 13503, 7768, 9087, 3658, 4077, 5709],
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
                        "title": { "display": true, "text": "Total de árboles" }
                    },
                    "x": {
                        "grid": { "display": false },
                        "ticks": { "font": { "size": 10 } },
                        "title": { "display": true, "text": "Comunas" }
                    }
                },
                "plugins": { "legend": { "display": false } }
            }
        }),
        true,
    );
}

fn create_temperature_trends_chart() {
    chart_by_id(
        "temperatureTrendsChart",
        json!({
            "type": "line",
            "data": {
                "labels": ["Jan", "Feb", "Mar", "Apr", "May", "Jun"],
                "datasets": [{
                    "label": "Temperature (°C)",
                    "data": [7, 9, 12, 14, 10, 7],
                    "borderColor": "#f97316",
                    "backgroundColor": "rgba(249, 115, 22, 0.1)",
                    "fill": true,
                    "tension": 0.4,
                    "pointBackgroundColor": "#f97316",
                    "borderWidth": 2
                }]
            },
            "options": { "scales": small_ticks_xy(), "plugins": { "legend": { "display": false } } }
        }),
        true,
    );
}

fn create_functional_groups_chart() {
    chart_by_id(
        "functionalGroupsChart",
        json!({
            "type": "radar",
            "data": {
                "labels": ["Shade", "Fruit", "Native", "Medicinal", "Ornamental"],
                "datasets": [{
                    "label": "Tree Functions",
                    "data": [85, 60, 90, 70, 75],
                    "backgroundColor": "rgba(16, 185, 129, 0.2)",
                    "borderColor": "#10b981",
                    "borderWidth": 2,
                    "pointBackgroundColor": "#10b981",
                    "pointRadius": 3
                }]
            },
            "options": {
                "scales": {
                    "r": {
                        "beginAtZero": true,
                        "ticks": { "display": false, "stepSize": 20 },
                        "pointLabels": { "font": { "size": 10 } }
                    }
                },
                "plugins": { "legend": { "display": false } }
            }
        }),
        true,
    );
}
