//! Analytics page.
//!
//! KNOWN ISSUE: all charts and tables use hardcoded sample data (Colombia-wide, not Ibagué).

use leptos::prelude::*;
use serde_json::json;

use crate::interop::chart::chart_by_id;
use crate::interop::when_connected;

struct TreeRow {
    id: &'static str,
    species: &'static str,
    height: f64,
    health_status: &'static str,
    location: &'static str,
}

const RECENT_TREES: [TreeRow; 5] = [
    TreeRow { id: "T001", species: "Ceiba pentandra", height: 25.4, health_status: "Healthy", location: "Bogotá" },
    TreeRow { id: "T002", species: "Quercus humboldtii", height: 18.2, health_status: "Moderate", location: "Medellín" },
    TreeRow { id: "T003", species: "Tabebuia rosea", height: 12.8, health_status: "Healthy", location: "Cali" },
    TreeRow { id: "T004", species: "Ficus benjamina", height: 15.6, health_status: "Poor", location: "Cartagena" },
    TreeRow { id: "T005", species: "Samanea saman", height: 22.1, health_status: "Healthy", location: "Barranquilla" },
];

struct ClimateRow {
    station: &'static str,
    date: &'static str,
    temperature: f64,
    rainfall: f64,
    humidity: f64,
}

const CLIMATE_DATA: [ClimateRow; 5] = [
    ClimateRow { station: "BOG001", date: "2024-03-15", temperature: 18.5, rainfall: 2.3, humidity: 65.0 },
    ClimateRow { station: "MED002", date: "2024-03-15", temperature: 22.1, rainfall: 0.0, humidity: 58.0 },
    ClimateRow { station: "CAL003", date: "2024-03-15", temperature: 25.8, rainfall: 1.5, humidity: 72.0 },
    ClimateRow { station: "BAR004", date: "2024-03-15", temperature: 28.2, rainfall: 0.8, humidity: 75.0 },
    ClimateRow { station: "CTG005", date: "2024-03-15", temperature: 29.5, rainfall: 0.0, humidity: 80.0 },
];

/// JS number interpolation: `{{ 0.0 }}` renders "0", `{{ 65 }}` renders "65".
fn js_num(n: f64) -> String {
    crate::api::js_string(Some(&json!(n)))
}

fn get_health_status_class(status: &str) -> String {
    let base = "px-2 py-1 text-xs font-medium rounded-full";
    match status.to_lowercase().as_str() {
        "healthy" => format!("{base} bg-green-100 text-green-800"),
        "moderate" => format!("{base} bg-yellow-100 text-yellow-800"),
        "poor" => format!("{base} bg-red-100 text-red-800"),
        _ => format!("{base} bg-gray-100 text-gray-800"),
    }
}

/// `<div class="bg-white p-4 rounded-lg shadow"><h2>..</h2><canvas id=..></canvas></div>`
#[component]
fn ChartBox(title: &'static str, canvas_id: &'static str) -> impl IntoView {
    view! {
        <div class="bg-white p-4 rounded-lg shadow">
            <h2 class="text-lg font-semibold mb-4">{title}</h2>
            <canvas id=canvas_id></canvas>
        </div>
    }
}

#[component]
pub fn Analytics() -> impl IntoView {
    // Build the charts once the root (and so every canvas) is attached; see `when_connected`.
    let root = NodeRef::<leptos::html::Div>::new();
    Effect::new(move |_| {
        if let Some(el) = root.get() {
            when_connected(el.into(), initialize_charts);
        }
    });

    view! {
        <div node_ref=root class="block w-full">
            <div class="p-6 space-y-6">
                // Header
                <div class="mb-8">
                    <h1 class="text-3xl font-bold text-gray-900">"Tree Analytics Dashboard"</h1>
                    <p class="mt-2 text-gray-600">"Comprehensive analysis of urban tree data in Colombia"</p>
                </div>

                <div class="space-y-4">
                    // Circular Charts Row
                    <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
                        <ChartBox title="Species Distribution" canvas_id="speciesChart" />
                        <ChartBox title="Tree Health Status" canvas_id="healthChart" />
                        <ChartBox title="Family Distribution" canvas_id="familyChart" />
                        <ChartBox title="Functional Groups" canvas_id="functionalGroupChart" />
                    </div>
                    // Line Charts Row
                    <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
                        <ChartBox title="Monthly Growth Trends" canvas_id="growthChart" />
                        <ChartBox title="Temperature Trends" canvas_id="temperatureChart" />
                        <ChartBox title="Observation Trends" canvas_id="observationChart" />
                        <ChartBox title="Trait Distribution" canvas_id="traitChart" />
                    </div>
                    // Bar Charts Row
                    <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
                        <ChartBox title="Environmental Impact" canvas_id="impactChart" />
                        <ChartBox title="Geographic Distribution" canvas_id="geographicChart" />
                        <ChartBox title="Measurement Types" canvas_id="measurementChart" />
                        <ChartBox title="Rainfall Patterns" canvas_id="rainfallChart" />
                    </div>
                </div>

                <DataTables />
            </div>
        </div>
    }
}

#[component]
fn DataTables() -> impl IntoView {
    const TH: &str = "px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase";
    view! {
        <div class="grid grid-cols-1 lg:grid-cols-2 gap-4 mt-8">
            // Recent Tree Data Table
            <div class="bg-white p-4 rounded-lg shadow">
                <h2 class="text-lg font-semibold mb-4">"Recent Tree Records"</h2>
                <div class="overflow-x-auto">
                    <table class="min-w-full divide-y divide-gray-200">
                        <thead class="bg-gray-50">
                            <tr>
                                <th class=TH>"ID"</th>
                                <th class=TH>"Species"</th>
                                <th class=TH>"Height"</th>
                                <th class=TH>"Health"</th>
                                <th class=TH>"Location"</th>
                            </tr>
                        </thead>
                        <tbody class="divide-y divide-gray-200">
                            {RECENT_TREES
                                .iter()
                                .map(|t| view! {
                                    <tr>
                                        <td class="px-4 py-2 text-sm">{t.id}</td>
                                        <td class="px-4 py-2 text-sm">{t.species}</td>
                                        <td class="px-4 py-2 text-sm">{format!("{}m", js_num(t.height))}</td>
                                        <td class="px-4 py-2">
                                            <span class=get_health_status_class(t.health_status)>{t.health_status}</span>
                                        </td>
                                        <td class="px-4 py-2 text-sm">{t.location}</td>
                                    </tr>
                                })
                                .collect_view()}
                        </tbody>
                    </table>
                </div>
            </div>

            // Recent Climate Data Table
            <div class="bg-white p-4 rounded-lg shadow">
                <h2 class="text-lg font-semibold mb-4">"Recent Climate Data"</h2>
                <div class="overflow-x-auto">
                    <table class="min-w-full divide-y divide-gray-200">
                        <thead class="bg-gray-50">
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
                                        <td class="px-4 py-2 text-sm">{r.station}</td>
                                        <td class="px-4 py-2 text-sm">{r.date}</td>
                                        <td class="px-4 py-2 text-sm">{format!("{}°C", js_num(r.temperature))}</td>
                                        <td class="px-4 py-2 text-sm">{format!("{}mm", js_num(r.rainfall))}</td>
                                        <td class="px-4 py-2 text-sm">{format!("{}%", js_num(r.humidity))}</td>
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

fn chart(id: &str, config: serde_json::Value) {
    chart_by_id(id, config, false);
}

fn no_legend() -> serde_json::Value {
    json!({ "legend": { "display": false } })
}

fn initialize_charts() {
    // Species
    chart("speciesChart", json!({
        "type": "pie",
        "data": {
            "labels": ["Ceiba pentandra", "Quercus humboldtii", "Tabebuia rosea", "Others"],
            "datasets": [{ "data": [30, 25, 20, 25], "backgroundColor": ["#4CAF50", "#8BC34A", "#CDDC39", "#FF9800"] }]
        },
        "options": { "responsive": true, "plugins": { "legend": { "position": "bottom", "display": false } } }
    }));
    // Health
    chart("healthChart", json!({
        "type": "doughnut",
        "data": {
            "labels": ["Healthy", "Moderate", "Poor"],
            "datasets": [{ "data": [65, 25, 10], "backgroundColor": ["#4CAF50", "#FFC107", "#F44336"] }]
        },
        "options": { "responsive": true, "plugins": { "legend": { "position": "bottom", "display": false } } }
    }));
    // Growth
    chart("growthChart", json!({
        "type": "line",
        "data": {
            "labels": ["Jan", "Feb", "Mar", "Apr", "May", "Jun"],
            "datasets": [{ "label": "Growth (cm)", "data": [5, 8, 12, 15, 10, 7], "borderColor": "#4CAF50", "tension": 0.4 }]
        },
        "options": { "responsive": true, "plugins": no_legend(), "scales": { "y": { "beginAtZero": true } } }
    }));
    // Impact
    chart("impactChart", json!({
        "type": "bar",
        "data": {
            "labels": ["CO₂", "O₂", "Shade", "Water"],
            "datasets": [{ "label": "Impact", "data": [75, 82, 60, 45], "backgroundColor": "#2196F3" }]
        },
        "options": { "responsive": true, "plugins": no_legend(), "scales": { "y": { "beginAtZero": true, "max": 100 } } }
    }));
    // Family
    chart("familyChart", json!({
        "type": "polarArea",
        "data": {
            "labels": ["Fabaceae", "Moraceae", "Bignoniaceae", "Others"],
            "datasets": [{ "data": [40, 30, 20, 10], "backgroundColor": ["#FF9800", "#F44336", "#9C27B0", "#2196F3"] }]
        },
        "options": { "responsive": true, "plugins": no_legend() }
    }));
    // Functional groups
    chart("functionalGroupChart", json!({
        "type": "radar",
        "data": {
            "labels": ["Shade", "Fruit", "Native", "Ornamental", "Medicinal"],
            "datasets": [{ "label": "Distribution", "data": [85, 60, 75, 90, 45], "borderColor": "#4CAF50", "backgroundColor": "rgba(76, 175, 80, 0.2)" }]
        },
        "options": { "responsive": true, "plugins": no_legend() }
    }));
    // Geographic
    chart("geographicChart", json!({
        "type": "bar",
        "data": {
            "labels": ["Bogotá", "Medellín", "Cali", "Barranquilla", "Cartagena"],
            "datasets": [{ "label": "Trees", "data": [1200, 800, 600, 400, 300], "backgroundColor": "#3F51B5" }]
        },
        "options": { "responsive": true, "plugins": no_legend(), "scales": { "y": { "beginAtZero": true } } }
    }));
    // Temperature
    chart("temperatureChart", json!({
        "type": "line",
        "data": {
            "labels": ["Jan", "Feb", "Mar", "Apr", "May", "Jun"],
            "datasets": [{ "label": "Avg Temp (°C)", "data": [22, 23, 25, 24, 23, 22], "borderColor": "#FF5722", "tension": 0.4 }]
        },
        "options": { "responsive": true, "plugins": no_legend() }
    }));
    // Traits
    chart("traitChart", json!({
        "type": "bubble",
        "data": {
            "datasets": [{
                "label": "Traits",
                "data": [
                    { "x": 20, "y": 30, "r": 15 },
                    { "x": 40, "y": 10, "r": 10 },
                    { "x": 30, "y": 20, "r": 8 },
                    { "x": 10, "y": 40, "r": 12 }
                ],
                "backgroundColor": "rgba(156, 39, 176, 0.6)"
            }]
        },
        "options": { "responsive": true, "plugins": no_legend(), "scales": { "x": { "beginAtZero": true }, "y": { "beginAtZero": true } } }
    }));
    // Measurement
    chart("measurementChart", json!({
        "type": "bar",
        "data": {
            "labels": ["Height", "DBH", "Crown", "Health"],
            "datasets": [{ "label": "Count", "data": [150, 120, 90, 180], "backgroundColor": ["#009688", "#00BCD4", "#03A9F4", "#3F51B5"] }]
        },
        "options": { "responsive": true, "plugins": no_legend(), "scales": { "y": { "beginAtZero": true } } }
    }));
    // Observation
    chart("observationChart", json!({
        "type": "line",
        "data": {
            "labels": ["Week 1", "Week 2", "Week 3", "Week 4"],
            "datasets": [{
                "label": "Observations", "data": [45, 60, 35, 80], "borderColor": "#673AB7",
                "tension": 0.4, "fill": true, "backgroundColor": "rgba(103, 58, 183, 0.1)"
            }]
        },
        "options": { "responsive": true, "plugins": no_legend() }
    }));
    // Rainfall
    chart("rainfallChart", json!({
        "type": "bar",
        "data": {
            "labels": ["Jan", "Feb", "Mar", "Apr", "May", "Jun"],
            "datasets": [{ "label": "Rainfall (mm)", "data": [120, 90, 150, 180, 60, 30], "backgroundColor": "#1976D2" }]
        },
        "options": { "responsive": true, "plugins": no_legend() }
    }));
}
