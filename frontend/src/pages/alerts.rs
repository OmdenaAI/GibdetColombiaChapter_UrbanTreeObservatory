//! Alerts page (placeholder UI with sample data; not connected to the API yet).

use leptos::prelude::*;

use super::shared::{SearchBox, SimplePager};

struct Alert {
    ty: &'static str,
    severity: &'static str,
    date: &'static str,
    tree: &'static str,
    description: &'static str,
    status: &'static str,
}

const ALERTS: [Alert; 3] = [
    Alert { ty: "Disease", severity: "High", date: "2025-04-18", tree: "Maple (ID: 2)", description: "Signs of fungal infection detected on leaves", status: "New" },
    Alert { ty: "Maintenance", severity: "Medium", date: "2025-04-16", tree: "Oak (ID: 1)", description: "Scheduled pruning required", status: "In Progress" },
    Alert { ty: "Environmental", severity: "Low", date: "2025-04-14", tree: "Pine (ID: 3)", description: "Soil moisture levels below optimal range", status: "Resolved" },
];

const ALERT_TYPES: [&str; 6] = ["All Types", "Disease", "Pest", "Maintenance", "Environmental", "Damage"];
const SEVERITY_LEVELS: [&str; 5] = ["All Levels", "Low", "Medium", "High", "Critical"];

/// Severity colour classes: (row bg, icon bg, icon text, badge).
fn severity_classes(sev: &str) -> (&'static str, &'static str, &'static str, &'static str) {
    match sev {
        "High" | "Critical" => ("bg-red-50", "bg-red-100", "text-red-600", "bg-red-100 text-red-800"),
        "Medium" => ("bg-yellow-50", "bg-yellow-100", "text-yellow-600", "bg-yellow-100 text-yellow-800"),
        "Low" => ("bg-blue-50", "bg-blue-100", "text-blue-600", "bg-blue-100 text-blue-800"),
        _ => ("", "", "", ""),
    }
}

fn status_badge(status: &str) -> &'static str {
    match status {
        "New" => "bg-blue-100 text-blue-800",
        "In Progress" => "bg-yellow-100 text-yellow-800",
        "Resolved" => "bg-green-100 text-green-800",
        _ => "",
    }
}

#[component]
pub fn Alerts() -> impl IntoView {
    view! {
        <div class="bg-white shadow rounded-lg p-6">
            <h1 class="text-2xl font-bold text-primary-600 mb-6">"Alerts"</h1>

            <div class="mb-6 flex flex-wrap justify-between items-center gap-4">
                <div class="flex space-x-2">
                    <button class="bg-primary-600 text-white px-4 py-2 rounded-lg hover:bg-primary-700">"Create Alert"</button>
                    <button class="bg-green-600 text-white px-4 py-2 rounded-lg hover:bg-green-700">"Mark All as Read"</button>
                </div>

                <div class="flex items-center space-x-2">
                    <label for="alertType" class="text-sm font-medium text-gray-700">"Type:"</label>
                    <select id="alertType" class="border rounded-lg py-2 px-4 focus:outline-none focus:ring-2 focus:ring-primary-500">
                        {ALERT_TYPES.into_iter().map(|t| view! { <option>{t}</option> }).collect_view()}
                    </select>

                    <label for="severityLevel" class="text-sm font-medium text-gray-700 ml-4">"Severity:"</label>
                    <select id="severityLevel" class="border rounded-lg py-2 px-4 focus:outline-none focus:ring-2 focus:ring-primary-500">
                        {SEVERITY_LEVELS.into_iter().map(|l| view! { <option>{l}</option> }).collect_view()}
                    </select>
                </div>

                <SearchBox placeholder="Search alerts..." />
            </div>

            <div class="space-y-4">
                {ALERTS.iter().map(|a| view! { <AlertCard alert=a /> }).collect_view()}
            </div>

            <SimplePager to="3" of="3" noun="alerts" margin="mt-6" />
        </div>
    }
}

#[component]
fn AlertCard(alert: &'static Alert) -> impl IntoView {
    let (row_bg, icon_bg, icon_text, sev_badge) = severity_classes(alert.severity);
    let resolved = alert.status == "Resolved";
    let resolve_btn = if resolved {
        "text-sm px-4 py-2 border rounded-md border-gray-300 text-gray-400 cursor-not-allowed"
    } else {
        "text-sm px-4 py-2 border rounded-md border-green-500 text-green-600 hover:bg-green-50"
    };

    view! {
        <div class="border rounded-lg overflow-hidden">
            <div class=format!("flex items-center p-4 {row_bg}")>
                <div class="flex-shrink-0 mr-4">
                    <div class=format!("rounded-full p-2 {icon_bg}")>
                        <svg xmlns="http://www.w3.org/2000/svg" class=format!("h-6 w-6 {icon_text}") fill="none" viewBox="0 0 24 24" stroke="currentColor">
                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
                                d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
                        </svg>
                    </div>
                </div>
                <div class="flex-1">
                    <div class="flex items-center justify-between">
                        <h3 class="text-lg font-medium text-gray-900">{format!("{} Alert - {}", alert.ty, alert.tree)}</h3>
                        <div class="flex items-center space-x-2">
                            <span class=format!("px-2 py-1 text-xs font-semibold rounded-full {}", status_badge(alert.status))>
                                {alert.status}
                            </span>
                            <span class=format!("px-2 py-1 text-xs font-semibold rounded-full {sev_badge}")>
                                {format!("{} Severity", alert.severity)}
                            </span>
                        </div>
                    </div>
                    <p class="mt-1 text-sm text-gray-600">{alert.description}</p>
                    <div class="mt-2 text-xs text-gray-500">{format!("Reported on: {}", alert.date)}</div>
                </div>
            </div>
            <div class="bg-white p-4 flex justify-end space-x-2">
                <button class="text-sm px-4 py-2 border border-gray-300 rounded-md text-gray-700 hover:bg-gray-50">"Assign"</button>
                <button class="text-sm px-4 py-2 border border-primary-500 rounded-md text-primary-600 hover:bg-primary-50">"View Details"</button>
                <button class=resolve_btn>{if resolved { "Resolved" } else { "Mark as Resolved" }}</button>
            </div>
        </div>
    }
}
