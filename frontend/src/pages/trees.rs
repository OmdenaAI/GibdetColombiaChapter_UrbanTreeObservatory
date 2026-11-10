//! Trees page (placeholder UI with sample data; not connected to the API yet).

use leptos::prelude::*;

use super::shared::TH;

struct Tree {
    id: &'static str,
    species: &'static str,
    location: &'static str,
    age: u32,
    health_status: &'static str,
    last_updated: &'static str,
}

const TREES: [Tree; 5] = [
    Tree { id: "T-1001", species: "Oak", location: "North Park", age: 12, health_status: "Healthy", last_updated: "2025-04-22" },
    Tree { id: "T-1002", species: "Maple", location: "City Center", age: 8, health_status: "Needs Attention", last_updated: "2025-04-20" },
    Tree { id: "T-1003", species: "Pine", location: "West Gardens", age: 15, health_status: "Healthy", last_updated: "2025-04-19" },
    Tree { id: "T-1004", species: "Birch", location: "River Walk", age: 5, health_status: "Critical", last_updated: "2025-04-18" },
    Tree { id: "T-1005", species: "Cherry", location: "East Park", age: 7, health_status: "Healthy", last_updated: "2025-04-17" },
];

const TREE_SPECIES: [&str; 10] = [
    "Oak", "Maple", "Pine", "Birch", "Cherry", "Willow", "Cypress", "Redwood", "Elm", "Ash",
];

fn health_class(status: &str) -> &'static str {
    match status {
        "Healthy" => "px-2 inline-flex text-xs leading-5 font-semibold rounded-full bg-green-100 text-green-800",
        "Needs Attention" => "px-2 inline-flex text-xs leading-5 font-semibold rounded-full bg-yellow-100 text-yellow-800",
        "Critical" => "px-2 inline-flex text-xs leading-5 font-semibold rounded-full bg-red-100 text-red-800",
        _ => "px-2 inline-flex text-xs leading-5 font-semibold rounded-full",
    }
}

const PAGE_LINK: &str = "bg-white border-gray-300 text-gray-500 hover:bg-gray-50 relative inline-flex items-center px-4 py-2 border text-sm font-medium";

#[component]
pub fn Trees() -> impl IntoView {
    view! {
        <div class="bg-white shadow rounded-lg p-6">
            <TreesHeader />
            <TreesFilters />
            <TreesTable />
            <TreesPagination />
        </div>
    }
}

#[component]
fn TreesHeader() -> impl IntoView {
    view! {
        <div class="flex flex-col md:flex-row justify-between items-center mb-6">
            <h1 class="text-2xl font-bold text-primary-600">"Tree Inventory"</h1>
            <div class="flex space-x-2 mt-4 md:mt-0">
                <button class="bg-primary-600 hover:bg-primary-700 text-white font-medium py-2 px-4 rounded-lg flex items-center">
                    <svg xmlns="http://www.w3.org/2000/svg" class="h-5 w-5 mr-2" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 6v6m0 0v6m0-6h6m-6 0H6" />
                    </svg>
                    "Add Tree"
                </button>
                <button class="bg-green-600 hover:bg-green-700 text-white font-medium py-2 px-4 rounded-lg flex items-center">
                    <svg xmlns="http://www.w3.org/2000/svg" class="h-5 w-5 mr-2" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-8l-4-4m0 0L8 8m4-4v12" />
                    </svg>
                    "Export Data"
                </button>
            </div>
        </div>
    }
}

#[component]
fn TreesFilters() -> impl IntoView {
    view! {
        <div class="flex flex-col md:flex-row justify-between mb-6">
            <div class="flex items-center space-x-4 mb-4 md:mb-0">
                <div>
                    <label for="filterSpecies" class="text-sm font-medium text-gray-700 block mb-1">"Filter by Species"</label>
                    <select id="filterSpecies" class="border border-gray-300 rounded-md px-3 py-2">
                        <option value="">"All Species"</option>
                        {TREE_SPECIES.into_iter().map(|s| view! { <option>{s}</option> }).collect_view()}
                    </select>
                </div>
                <div>
                    <label for="filterHealth" class="text-sm font-medium text-gray-700 block mb-1">"Health Status"</label>
                    <select id="filterHealth" class="border border-gray-300 rounded-md px-3 py-2">
                        <option value="">"All"</option>
                        <option value="healthy">"Healthy"</option>
                        <option value="needs-attention">"Needs Attention"</option>
                        <option value="critical">"Critical"</option>
                    </select>
                </div>
            </div>
            <div class="relative">
                <label for="search" class="text-sm font-medium text-gray-700 block mb-1">"Search"</label>
                <div class="relative">
                    <div class="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
                        <svg class="h-5 w-5 text-gray-400" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor" aria-hidden="true">
                            <path fill-rule="evenodd" d="M8 4a4 4 0 100 8 4 4 0 000-8zM2 8a6 6 0 1110.89 3.476l4.817 4.817a1 1 0 01-1.414 1.414l-4.816-4.816A6 6 0 012 8z" clip-rule="evenodd" />
                        </svg>
                    </div>
                    <input type="text" id="search" class="border border-gray-300 rounded-md py-2 pl-10 pr-4 w-full" placeholder="Search trees..." />
                </div>
            </div>
        </div>
    }
}

#[component]
fn TreesTable() -> impl IntoView {
    view! {
        <div class="overflow-x-auto">
            <table class="min-w-full divide-y divide-gray-200">
                <thead class="bg-gray-50">
                    <tr>
                        <th scope="col" class=TH>"ID"</th>
                        <th scope="col" class=TH>"Species"</th>
                        <th scope="col" class=TH>"Location"</th>
                        <th scope="col" class=TH>"Age (Years)"</th>
                        <th scope="col" class=TH>"Health Status"</th>
                        <th scope="col" class=TH>"Last Updated"</th>
                        <th scope="col" class=TH>"Actions"</th>
                    </tr>
                </thead>
                <tbody class="bg-white divide-y divide-gray-200">
                    {TREES
                        .iter()
                        .map(|tree| view! {
                            <tr>
                                <td class="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900">{tree.id}</td>
                                <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-500">{tree.species}</td>
                                <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-500">{tree.location}</td>
                                <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-500">{tree.age}</td>
                                <td class="px-6 py-4 whitespace-nowrap">
                                    <span class=health_class(tree.health_status)>{tree.health_status}</span>
                                </td>
                                <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-500">{tree.last_updated}</td>
                                <td class="px-6 py-4 whitespace-nowrap text-sm font-medium">
                                    <div class="flex space-x-2">
                                        <button class="text-indigo-600 hover:text-indigo-900">"View"</button>
                                        <button class="text-green-600 hover:text-green-900">"Edit"</button>
                                        <button class="text-red-600 hover:text-red-900">"Delete"</button>
                                    </div>
                                </td>
                            </tr>
                        })
                        .collect_view()}
                </tbody>
            </table>
        </div>
    }
}

#[component]
fn TreesPagination() -> impl IntoView {
    view! {
        <div class="flex items-center justify-between border-t border-gray-200 px-4 py-3 sm:px-6 mt-4">
            <div class="hidden sm:flex-1 sm:flex sm:items-center sm:justify-between">
                <div>
                    <p class="text-sm text-gray-700">
                        "Showing " <span class="font-medium">"1"</span> " to " <span class="font-medium">"10"</span>
                        " of " <span class="font-medium">{TREES.len()}</span> " results"
                    </p>
                </div>
                <div>
                    <nav class="relative z-0 inline-flex rounded-md shadow-sm -space-x-px" aria-label="Pagination">
                        <a href="#" class="relative inline-flex items-center px-2 py-2 rounded-l-md border border-gray-300 bg-white text-sm font-medium text-gray-500 hover:bg-gray-50">
                            <span class="sr-only">"Previous"</span>
                            <svg class="h-5 w-5" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor" aria-hidden="true">
                                <path fill-rule="evenodd" d="M12.707 5.293a1 1 0 010 1.414L9.414 10l3.293 3.293a1 1 0 01-1.414 1.414l-4-4a1 1 0 010-1.414l4-4a1 1 0 011.414 0z" clip-rule="evenodd" />
                            </svg>
                        </a>
                        <a href="#" aria-current="page" class="z-10 bg-primary-50 border-primary-500 text-primary-600 relative inline-flex items-center px-4 py-2 border text-sm font-medium">"1"</a>
                        <a href="#" class=PAGE_LINK>"2"</a>
                        <a href="#" class=PAGE_LINK>"3"</a>
                        <span class="relative inline-flex items-center px-4 py-2 border border-gray-300 bg-white text-sm font-medium text-gray-700">"..."</span>
                        <a href="#" class=PAGE_LINK>"10"</a>
                        <a href="#" class="relative inline-flex items-center px-2 py-2 rounded-r-md border border-gray-300 bg-white text-sm font-medium text-gray-500 hover:bg-gray-50">
                            <span class="sr-only">"Next"</span>
                            <svg class="h-5 w-5" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor" aria-hidden="true">
                                <path fill-rule="evenodd" d="M7.293 14.707a1 1 0 010-1.414L10.586 10 7.293 6.707a1 1 0 011.414-1.414l4 4a1 1 0 010 1.414l-4 4a1 1 0 01-1.414 0z" clip-rule="evenodd" />
                            </svg>
                        </a>
                    </nav>
                </div>
            </div>
        </div>
    }
}
