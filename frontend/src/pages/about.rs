//! About page (static content): what an urban forest is, what this platform offers and
//! who develops it. Figures belong to the Dashboard, Map and Analytics pages, not here.

use leptos::prelude::*;

const REPO_URL: &str = "https://github.com/legut00/GibdetColombiaChapter_UrbanTreeObservatory/tree/main";
const LEGUT_URL: &str = "https://www.legut.org/";
const OMDENA_URL: &str = "https://www.omdena.com/";

const CARD: &str = "bg-white rounded-lg shadow border border-gray-200 p-6";
const H2: &str = "text-xl font-semibold text-gray-900";
const P: &str = "text-gray-700 leading-relaxed";
const LINK: &str = "text-primary-700 font-medium hover:underline";
const ICON_EXTERNAL: &str = "M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14";

/// What urban trees do for a city (well-established benefits, no local figures).
const TREE_BENEFITS: [(&str, &str); 6] = [
    ("Cooler streets", "Shade and evapotranspiration lower surface and air temperatures and soften urban heat islands."),
    ("Cleaner air", "Leaves trap dust and particulate matter and absorb part of the gaseous pollutants."),
    ("Water regulation", "Canopies intercept rain and roots help the soil absorb it, reducing runoff and flooding."),
    ("Biodiversity", "Trees give food and shelter to birds, pollinators and other urban wildlife, especially native species."),
    ("Health and well-being", "Green streets and parks invite walking, reduce stress and make neighborhoods more liveable."),
    ("Carbon storage", "Trees store carbon in their wood as they grow, a small but lasting contribution against climate change."),
];

/// What the platform is for.
const PLATFORM_BENEFITS: [(&str, &str); 4] = [
    ("Know what we have", "One public inventory of the city's trees: species, location, size and condition, instead of scattered spreadsheets."),
    ("Plan with evidence", "See which comunas lack trees and how diverse and native the urban forest is, to decide where and what to plant."),
    ("Care for trees in time", "Spot sick, critical or dead trees and the species most affected, to prioritize maintenance."),
    ("Open and shared", "Open-source code and exportable data, so institutions, researchers and citizens can use and improve them."),
];

/// The platform's sections: (route, name, what it is for).
const SECTIONS: [(&str, &str, &str); 5] = [
    ("/dashboard", "Dashboard", "Summary of the census: trees, health, campaigns and climate."),
    ("/map", "Map", "Comunas, barrios and every tree on the map, with its data sheet."),
    ("/trees", "Trees", "Search the inventory and export it to CSV."),
    ("/species", "Species", "Catalog of the species found in the city, with their traits."),
    ("/analytics", "Analysis", "Indicators on origin, density by comuna, health and threatened species."),
];

fn external(href: &'static str, label: &'static str) -> impl IntoView {
    view! {
        <a href=href target="_blank" rel="noopener noreferrer" class=format!("{LINK} inline-flex items-center gap-1")>
            {label}
            <svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" aria-hidden="true">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d=ICON_EXTERNAL />
            </svg>
        </a>
    }
}

#[component]
pub fn About() -> impl IntoView {
    view! {
        <div class="p-6 space-y-6 max-w-6xl mx-auto">
            // What the platform is
            <div class=CARD>
                <h1 class="text-3xl font-bold text-primary-600">"Urban Tree Observatory"</h1>
                <p class=format!("{P} mt-3 text-lg")>
                    "An open platform to explore, understand and manage the urban trees of Ibagué, Colombia. It brings together the city's tree census, the species catalog, maps of comunas and barrios and climate records in a single geographic database, and turns them into maps, searchable records and indicators."
                </p>
            </div>

            // Who builds it (emphasis)
            <div class="rounded-lg border-2 border-primary-600 bg-primary-50 p-6">
                <h2 class=H2>"Who is behind it"</h2>
                <div class="mt-4 grid grid-cols-1 md:grid-cols-3 gap-6">
                    <div>
                        <p class="text-xs font-semibold uppercase tracking-wider text-primary-700">"Origin"</p>
                        <p class=format!("{P} mt-1")>
                            "This project is the final product of a volunteer project with "
                            <strong>"Omdena"</strong>
                            " (GibdetColombia Chapter), where volunteers built the first version of the observatory."
                        </p>
                        <p class="mt-2">{external(OMDENA_URL, "omdena.com")}</p>
                    </div>
                    <div>
                        <p class="text-xs font-semibold uppercase tracking-wider text-primary-700">"Maintained and developed by"</p>
                        <p class=format!("{P} mt-1")>
                            <strong>"Fundación LEGUT"</strong>
                            " maintains the platform and continues its development."
                        </p>
                        <p class="mt-2">{external(LEGUT_URL, "legut.org")}</p>
                    </div>
                    <div>
                        <p class="text-xs font-semibold uppercase tracking-wider text-primary-700">"Source code"</p>
                        <p class=format!("{P} mt-1")>
                            "The main repository is open source (MIT License). Issues, ideas and contributions are welcome there."
                        </p>
                        <p class="mt-2">{external(REPO_URL, "GitHub repository")}</p>
                    </div>
                </div>
            </div>

            // What an urban forest is
            <div class=CARD>
                <h2 class=H2>"What is an urban forest?"</h2>
                <p class=format!("{P} mt-3")>
                    "The urban forest is the set of all the trees, palms and shrubs that grow in a city: along streets and avenues, in parks, squares and green areas, along rivers and ravines, and in private gardens. Looked at together, they are part of the city's infrastructure — green infrastructure — that needs to be planned, planted and maintained like any other."
                </p>
                <div class="mt-5 grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
                    {TREE_BENEFITS.into_iter().map(|(title, text)| view! {
                        <div class="rounded-md border border-gray-200 bg-gray-50 p-4">
                            <h3 class="font-semibold text-green-800">{title}</h3>
                            <p class="mt-1 text-sm text-gray-600">{text}</p>
                        </div>
                    }).collect_view()}
                </div>
            </div>

            // Why the platform
            <div class=CARD>
                <h2 class=H2>"Why this platform"</h2>
                <p class=format!("{P} mt-3")>
                    "Managing an urban forest starts with knowing it. The platform puts the census data where everyone can see it and use it:"
                </p>
                <div class="mt-5 grid grid-cols-1 md:grid-cols-2 gap-4">
                    {PLATFORM_BENEFITS.into_iter().map(|(title, text)| view! {
                        <div class="flex gap-3">
                            <span class="mt-1.5 h-2.5 w-2.5 shrink-0 rounded-full bg-primary-600"></span>
                            <div>
                                <h3 class="font-semibold text-gray-900">{title}</h3>
                                <p class="text-sm text-gray-600">{text}</p>
                            </div>
                        </div>
                    }).collect_view()}
                </div>
            </div>

            // Sections and data
            <div class="grid grid-cols-1 lg:grid-cols-2 gap-6">
                <div class=CARD>
                    <h2 class=H2>"What you can do here"</h2>
                    <ul class="mt-4 divide-y divide-gray-100">
                        {SECTIONS.into_iter().map(|(href, name, text)| view! {
                            <li class="py-2.5">
                                <a href=href class=LINK>{name}</a>
                                <p class="text-sm text-gray-600">{text}</p>
                            </li>
                        }).collect_view()}
                    </ul>
                </div>
                <div class=CARD>
                    <h2 class=H2>"The data"</h2>
                    <ul class=format!("{P} mt-4 space-y-3 text-sm list-disc pl-5")>
                        <li>
                            <strong>"Urban tree census"</strong>
                            " of Ibagué by Cortolima (campaigns of 2014, 2015 and 2017): species, location, measurements and condition of each tree."
                        </li>
                        <li>
                            <strong>"Species catalog"</strong>
                            " with origin, traits and IUCN Red List category, linked to GBIF and the Useful Tropical Plants database."
                        </li>
                        <li><strong>"Comuna and barrio boundaries"</strong>" and the 2019 population of each comuna."</li>
                        <li><strong>"Air temperature"</strong>" from automatic weather stations in Ibagué."</li>
                        <li>
                            "Everything is stored in a PostgreSQL / PostGIS geographic database. The census reflects the trees when they were surveyed; it is not a live record."
                        </li>
                    </ul>
                </div>
            </div>
        </div>
    }
}
