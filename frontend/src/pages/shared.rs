//! Small markup pieces shared by several pages.

use leptos::prelude::*;

pub const TH: &str = "px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider";
pub const SEARCH_ICON: &str = "M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z";

/// `<input placeholder=".."> + magnifier icon` block used by Reports and Alerts.
#[component]
pub fn SearchBox(placeholder: &'static str) -> impl IntoView {
    view! {
        <div class="relative">
            <input
                type="text"
                placeholder=placeholder
                class="border rounded-lg py-2 px-4 pl-10 focus:outline-none focus:ring-2 focus:ring-primary-500"
            />
            <svg xmlns="http://www.w3.org/2000/svg" class="h-5 w-5 absolute left-3 top-3 text-gray-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d=SEARCH_ICON />
            </svg>
        </div>
    }
}

/// "Showing 1 to N of N <noun>" + Previous/Next buttons (Reports, Alerts).
#[component]
pub fn SimplePager(to: &'static str, of: &'static str, noun: &'static str, #[prop(default = "mt-4")] margin: &'static str) -> impl IntoView {
    view! {
        <div class=format!("{margin} flex justify-between items-center")>
            <div class="text-sm text-gray-700">
                "Showing " <span class="font-medium">"1"</span> " to " <span class="font-medium">{to}</span>
                " of " <span class="font-medium">{of}</span> {format!(" {noun}")}
            </div>
            <div class="flex space-x-2">
                <button class="px-3 py-1 border rounded-md bg-gray-100 text-gray-700 hover:bg-gray-200">"Previous"</button>
                <button class="px-3 py-1 border rounded-md bg-primary-600 text-white hover:bg-primary-700">"Next"</button>
            </div>
        </div>
    }
}
