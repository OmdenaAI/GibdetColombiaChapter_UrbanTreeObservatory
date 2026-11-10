//! About page (static content).

use leptos::prelude::*;

const CHECK_ICON: &str = "M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z";

const FEATURES: [(&str, &str); 5] = [
    ("Interactive Tree Mapping", "Visualize and explore urban trees with detailed geospatial data"),
    ("Comprehensive Tree Database", "Detailed records of species, health status, and maintenance history"),
    ("Environmental Monitoring", "Track climate data and assess environmental impacts"),
    ("Analytics and Reports", "Generate insights through data visualization and analysis"),
    ("Alert System", "Get notified about critical tree health issues and maintenance needs"),
];

const USE_CASES: [(&str, &str); 4] = [
    ("Urban Planning", "City planners use our platform to assess tree coverage, identify areas requiring more green spaces, and plan sustainable urban development."),
    ("Environmental Research", "Researchers analyze tree data and climate information to study urban heat islands, air quality, and biodiversity patterns."),
    ("Maintenance Management", "Municipal tree care teams use alerts and health indicators to prioritize maintenance activities and prevent tree damage."),
    ("Public Education", "Schools and community organizations access tree data to educate about urban ecology, biodiversity, and environmental stewardship."),
];

#[component]
pub fn About() -> impl IntoView {
    view! {
        <div class="bg-white shadow rounded-lg p-6">
            <h1 class="text-2xl font-bold text-primary-600 mb-6">"About the Urban Tree Observatory"</h1>

            <div class="mb-8">
                <h2 class="text-xl font-semibold text-gray-800 mb-4">"Project Overview"</h2>
                <p class="text-gray-700 mb-4">
                    "The Urban Tree Observatory is a comprehensive platform developed by GibdetColombia Chapter to monitor, analyze, and manage urban forests in Colombia, starting with Ibague. Our mission is to promote sustainable urban forestry practices through data-driven decision making and community engagement."
                </p>
                <p class="text-gray-700 mb-4">
                    "By collecting and analyzing data on tree health, biodiversity, and environmental impact, we aim to improve urban forest management, enhance urban biodiversity, and mitigate the effects of climate change in urban environments."
                </p>
            </div>

            <div class="grid grid-cols-1 md:grid-cols-2 gap-6 mb-8">
                <FeaturesCard />
                <UseCasesCard />
            </div>

            <ImpactSection />
            <BenefitsSection />
            <SponsorsSection />

            <div class="border-t pt-6">
                <h2 class="text-lg font-semibold text-gray-800 mb-4">"Get Involved"</h2>
                <p class="text-gray-700 mb-4">
                    "We welcome collaboration from researchers, municipal partners, and community organizations. If you're interested in contributing to the Urban Tree Observatory or using our data for research purposes, please contact us at "
                    <a href="mailto:contact@gibdetcolombia.org" class="text-primary-600 hover:underline">"contact@gibdetcolombia.org"</a>
                    "."
                </p>
            </div>
        </div>
    }
}

#[component]
fn FeaturesCard() -> impl IntoView {
    view! {
        <div class="border rounded-lg shadow p-4">
            <h2 class="text-lg font-semibold text-gray-800 mb-4">"Key Features"</h2>
            <ul class="space-y-3">
                {FEATURES
                    .into_iter()
                    .map(|(title, desc)| view! {
                        <li class="flex items-start">
                            <svg class="h-5 w-5 text-green-500 mr-2 mt-0.5" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor">
                                <path fill-rule="evenodd" d=CHECK_ICON clip-rule="evenodd" />
                            </svg>
                            <div>
                                <p class="font-medium">{title}</p>
                                <p class="text-sm text-gray-600">{desc}</p>
                            </div>
                        </li>
                    })
                    .collect_view()}
            </ul>
        </div>
    }
}

#[component]
fn UseCasesCard() -> impl IntoView {
    view! {
        <div class="border rounded-lg shadow p-4">
            <h2 class="text-lg font-semibold text-gray-800 mb-4">"Use Cases"</h2>
            <div class="space-y-4">
                {USE_CASES
                    .into_iter()
                    .map(|(title, desc)| view! {
                        <div class="bg-gray-50 p-3 rounded-md border border-gray-200">
                            <h3 class="font-medium text-primary-700">{title}</h3>
                            <p class="text-sm text-gray-600 mt-1">{desc}</p>
                        </div>
                    })
                    .collect_view()}
            </div>
        </div>
    }
}

#[component]
fn ImpactSection() -> impl IntoView {
    view! {
        <div class="mb-8">
            <h2 class="text-lg font-semibold text-gray-800 mb-4">"Our Impact"</h2>
            <div class="grid grid-cols-1 md:grid-cols-3 gap-4 mb-6">
                <div class="bg-green-50 p-4 rounded-lg text-center">
                    <div class="text-3xl font-bold text-green-700 mb-1">"96,943"</div>
                    <div class="text-sm text-green-600">"Trees Monitored"</div>
                </div>
                <div class="bg-blue-50 p-4 rounded-lg text-center">
                    <div class="text-3xl font-bold text-blue-700 mb-1">"439"</div>
                    <div class="text-sm text-blue-600">"Species Documented"</div>
                </div>
                <div class="bg-purple-50 p-4 rounded-lg text-center">
                    <div class="text-3xl font-bold text-purple-700 mb-1">"17.30 m"</div>
                    <div class="text-sm text-purple-600">"Average Tree Height"</div>
                </div>
            </div>

            <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div class="bg-amber-50 p-4 rounded-lg text-center">
                    <div class="text-3xl font-bold text-amber-700 mb-1">"0.18"</div>
                    <div class="text-sm text-amber-600">"Tree-per-capita Index"</div>
                </div>
                <div class="bg-teal-50 p-4 rounded-lg text-center">
                    <div class="text-3xl font-bold text-teal-700 mb-1">"5"</div>
                    <div class="text-sm text-teal-600">"Research Partnerships"</div>
                </div>
            </div>
        </div>
    }
}

#[component]
fn BenefitsSection() -> impl IntoView {
    view! {
        <div class="mb-8">
            <h2 class="text-lg font-semibold text-gray-800 mb-4">"Environmental Benefits"</h2>
            <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div class="bg-green-50 p-4 rounded-lg border border-green-100">
                    <h3 class="font-medium text-green-800 mb-2">"CO₂ Absorption"</h3>
                    <div class="text-2xl font-bold text-green-700">"646,867.27 Tons"</div>
                    <p class="text-sm text-green-600 mt-2">
                        "Our urban forest captures carbon dioxide, mitigating greenhouse gas effects and combating climate change."
                    </p>
                </div>
                <div class="bg-blue-50 p-4 rounded-lg border border-blue-100">
                    <h3 class="font-medium text-blue-800 mb-2">"Oxygen Production"</h3>
                    <div class="text-2xl font-bold text-blue-700">"1,727,135.62 Tons/year"</div>
                    <p class="text-sm text-blue-600 mt-2">
                        "Ibagué's trees generate life-sustaining oxygen, enhancing air quality for the community."
                    </p>
                </div>
            </div>
        </div>
    }
}

#[component]
fn SponsorsSection() -> impl IntoView {
    view! {
        <div class="border rounded-lg shadow p-4">
            <h2 class="text-lg font-semibold text-gray-800 mb-4">"Sponsors"</h2>
            <div class="grid grid-cols-1 md:grid-cols-4 gap-4">
                {(1..=4)
                    .map(|n| view! {
                        <div class="bg-gray-50 p-3 rounded-md border border-gray-200">
                            <div class="flex justify-center items-center">
                                <svg xmlns="http://www.w3.org/2000/svg" width="200" height="200" fill="currentColor">
                                    <rect width="100%" height="100%" fill="#e0e0e0" stroke="#a0a0a0" stroke-dasharray="5,5" />
                                    <text x="100" y="100" font-family="sans-serif" font-size="20" fill="#555" text-anchor="middle" dominant-baseline="middle">
                                        {format!("Logo Sponsor {n}")}
                                    </text>
                                </svg>
                            </div>
                            <h3 class="font-medium text-primary-700 text-center">{format!("Sponsor {n}")}</h3>
                        </div>
                    })
                    .collect_view()}
            </div>
        </div>
    }
}
