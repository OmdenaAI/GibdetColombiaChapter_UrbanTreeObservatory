//! App shell: navbar + collapsible sidebar + content area.
//!
//! KNOWN ISSUE: toggling the sidebar does not notify the map page, so Leaflet never calls
//! `invalidateSize()` and the map keeps its previous size until the next reload.

use leptos::prelude::*;
use leptos_router::hooks::use_location;

const NAV_BASE: &str =
    "flex items-center px-4 py-2 text-gray-700 hover:bg-primary-50 transition-colors duration-200";
const NAV_ACTIVE: &str = "flex items-center px-4 py-2 text-gray-700 hover:bg-primary-50 transition-colors duration-200 bg-primary-50 text-primary-600";

const BTN: &str =
    "text-white hover:bg-primary-700 rounded-lg p-2 focus:outline-none focus:ring-2 focus:ring-primary-400";

const ICON_BELL: &str = "M15 17h5l-1.405-1.405A2.032 2.032 0 0118 14.158V11a6.002 6.002 0 00-4-5.659V5a2 2 0 10-4 0v.341C7.67 6.165 6 8.388 6 11v3.159c0 .538-.214 1.055-.595 1.436L4 17h5m6 0v1a3 3 0 11-6 0v-1m6 0H9";

/// (route, label, svg path), in sidebar order.
const NAV_ITEMS: [(&str, &str, &str); 7] = [
    ("/dashboard", "Dashboard", "M3 12l2-2m0 0l7-7 7 7M5 10v10a1 1 0 001 1h3m10-11l2 2m-2-2v10a1 1 0 01-1 1h-3m-6 0a1 1 0 001-1v-4a1 1 0 011-1h2a1 1 0 011 1v4a1 1 0 001 1m-6 0h6"),
    ("/map", "Map", "M9 20l-5.447-2.724A1 1 0 013 16.382V5.618a1 1 0 011.447-.894L9 7m0 13l6-3m-6 3V7m6 10l4.553 2.276A1 1 0 0021 18.382V7.618a1 1 0 00-.553-.894L15 4m0 13V4m0 0L9 7"),
    ("/trees", "Trees", "M3 6l3 1m0 0l-3 9a5.002 5.002 0 006.001 0M6 7l3 9M6 7l6-2m6 2l3-1m-3 1l-3 9a5.002 5.002 0 006.001 0M18 7l3 9m-3-9l-6-2m0-2v2m0 16V5m0 16H9m3 0h3"),
    ("/reports", "Reports", "M9 17v-2m3 2v-4m3 4v-6m2 10H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"),
    ("/alerts", "Alerts", ICON_BELL),
    ("/about", "About", "M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"),
    ("/analytics", "Analysis", "M16 8v8m-4-5v5m-4-2v2m-2 4h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z"),
];

#[component]
pub fn Layout(children: Children) -> impl IntoView {
    let is_sidebar_open = RwSignal::new(false);

    view! {
        <div class="min-h-screen bg-gray-100">
            // Navbar
            <nav class="bg-primary-600 w-[calc(100%-2rem)] z-10 shadow-lg m-4 rounded-lg">
                <div class="px-4 py-3">
                    <div class="flex items-center justify-between">
                        <div class="flex items-center">
                            <button on:click=move |_| is_sidebar_open.update(|v| *v = !*v) class=BTN>
                                <svg xmlns="http://www.w3.org/2000/svg" class="h-6 w-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 6h16M4 12h16M4 18h16" />
                                </svg>
                            </button>
                            <span class="text-white text-xl font-semibold ml-4">"Tree Management System"</span>
                        </div>

                        <div class="flex items-center space-x-4">
                            <button class=BTN>
                                <svg xmlns="http://www.w3.org/2000/svg" class="h-6 w-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d=ICON_BELL />
                                </svg>
                            </button>
                            <button class=BTN>
                                <svg xmlns="http://www.w3.org/2000/svg" class="h-6 w-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z" />
                                </svg>
                            </button>
                        </div>
                    </div>
                </div>
            </nav>

            <div class="flex gap-4 m-4">
                // Sidebar
                <aside class=move || {
                    if is_sidebar_open.get() {
                        "top-0 h-[calc(100vh-112px)] bg-white shadow transition-all duration-300 rounded-lg w-64"
                    } else {
                        "top-0 h-[calc(100vh-112px)] bg-white shadow transition-all duration-300 rounded-lg w-16"
                    }
                }>
                    <nav class="mt-4 space-y-2">
                        {NAV_ITEMS
                            .into_iter()
                            .map(|(href, label, d)| view! { <NavItem href label d open=is_sidebar_open /> })
                            .collect_view()}
                    </nav>
                </aside>

                // Main content
                <main class="flex-1 transition-all duration-300 h-[calc(100vh-112px)] overflow-y-auto">
                    {children()}
                </main>
            </div>
        </div>
    }
}

/// Sidebar link; highlighted with `bg-primary-50 text-primary-600` when its route is active.
/// A plain `<a>` is intercepted by leptos_router for client-side navigation.
#[component]
fn NavItem(
    href: &'static str,
    label: &'static str,
    d: &'static str,
    open: RwSignal<bool>,
) -> impl IntoView {
    let location = use_location();
    // Non-exact matching: also active on nested paths (prefix by URL segment).
    let class = move || {
        let path = location.pathname.get();
        if path == href || path.starts_with(&format!("{href}/")) {
            NAV_ACTIVE
        } else {
            NAV_BASE
        }
    };

    view! {
        <a href=href class=class>
            <svg xmlns="http://www.w3.org/2000/svg" class="h-6 w-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d=d />
            </svg>
            <span class=move || if open.get() { "ml-2" } else { "ml-2 hidden" }>{label}</span>
        </a>
    }
}
