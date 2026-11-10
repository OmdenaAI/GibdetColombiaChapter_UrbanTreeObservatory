//! Reports page (placeholder UI with sample data; not connected to the API yet).

use leptos::prelude::*;

use super::shared::{SearchBox, SimplePager, TH};

struct Report {
    id: u32,
    ty: &'static str,
    date: &'static str,
    tree: &'static str,
    status: &'static str,
}

const REPORTS: [Report; 3] = [
    Report { id: 1, ty: "Inspection", date: "2025-04-15", tree: "Oak (ID: 1)", status: "Completed" },
    Report { id: 2, ty: "Maintenance", date: "2025-04-10", tree: "Maple (ID: 2)", status: "Pending" },
    Report { id: 3, ty: "Health Assessment", date: "2025-04-05", tree: "Pine (ID: 3)", status: "Completed" },
];

const REPORT_TYPES: [&str; 5] = [
    "All Types", "Inspection", "Maintenance", "Health Assessment", "Growth Measurement",
];

fn status_class(status: &str) -> &'static str {
    match status {
        "Completed" => "px-2 inline-flex text-xs leading-5 font-semibold rounded-full bg-green-100 text-green-800",
        "Pending" => "px-2 inline-flex text-xs leading-5 font-semibold rounded-full bg-yellow-100 text-yellow-800",
        "In Progress" => "px-2 inline-flex text-xs leading-5 font-semibold rounded-full bg-blue-100 text-blue-800",
        _ => "px-2 inline-flex text-xs leading-5 font-semibold rounded-full",
    }
}

#[component]
pub fn Reports() -> impl IntoView {
    view! {
        <div class="bg-white shadow rounded-lg p-6">
            <h1 class="text-2xl font-bold text-primary-600 mb-6">"Reports"</h1>

            <div class="mb-6 flex flex-wrap justify-between items-center gap-4">
                <div class="flex space-x-2">
                    <button class="bg-primary-600 text-white px-4 py-2 rounded-lg hover:bg-primary-700">"Create New Report"</button>
                    <button class="bg-gray-200 text-gray-700 px-4 py-2 rounded-lg hover:bg-gray-300">"Export Reports"</button>
                </div>

                <div class="flex items-center space-x-2">
                    <label for="reportType" class="text-sm font-medium text-gray-700">"Filter by Type:"</label>
                    <select id="reportType" class="border rounded-lg py-2 px-4 focus:outline-none focus:ring-2 focus:ring-primary-500">
                        {REPORT_TYPES.into_iter().map(|t| view! { <option>{t}</option> }).collect_view()}
                    </select>
                </div>

                <SearchBox placeholder="Search reports..." />
            </div>

            <div class="overflow-x-auto">
                <table class="min-w-full divide-y divide-gray-200">
                    <thead class="bg-gray-50">
                        <tr>
                            <th scope="col" class=TH>"ID"</th>
                            <th scope="col" class=TH>"Type"</th>
                            <th scope="col" class=TH>"Date"</th>
                            <th scope="col" class=TH>"Tree"</th>
                            <th scope="col" class=TH>"Status"</th>
                            <th scope="col" class=TH>"Actions"</th>
                        </tr>
                    </thead>
                    <tbody class="bg-white divide-y divide-gray-200">
                        {REPORTS
                            .iter()
                            .map(|r| view! {
                                <tr>
                                    <td class="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900">{r.id}</td>
                                    <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-500">{r.ty}</td>
                                    <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-500">{r.date}</td>
                                    <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-500">{r.tree}</td>
                                    <td class="px-6 py-4 whitespace-nowrap">
                                        <span class=status_class(r.status)>{r.status}</span>
                                    </td>
                                    <td class="px-6 py-4 whitespace-nowrap text-sm font-medium">
                                        <button class="text-primary-600 hover:text-primary-900 mr-3">"View"</button>
                                        <button class="text-red-600 hover:text-red-900">"Delete"</button>
                                    </td>
                                </tr>
                            })
                            .collect_view()}
                    </tbody>
                </table>
            </div>

            <SimplePager to="3" of="3" noun="reports" />
        </div>
    }
}
