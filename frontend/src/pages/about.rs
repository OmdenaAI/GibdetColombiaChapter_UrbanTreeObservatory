//! About page (static content): what an urban forest is, what this platform offers and
//! who develops it. Figures belong to the Dashboard, Map and Analytics pages, not here.

use leptos::prelude::*;

use crate::i18n::I18n;

const REPO_URL: &str = "https://github.com/legut00/GibdetColombiaChapter_UrbanTreeObservatory/tree/main";
const LEGUT_URL: &str = "https://www.legut.org/";
const OMDENA_URL: &str = "https://www.omdena.com/";

const CARD: &str = "bg-white rounded-lg shadow border border-gray-200 p-6";
const H2: &str = "text-xl font-semibold text-gray-900";
const P: &str = "text-gray-700 leading-relaxed";
const LINK: &str = "text-primary-700 font-medium hover:underline";
const KICKER: &str = "text-xs font-semibold uppercase tracking-wider text-primary-700";
const ICON_EXTERNAL: &str = "M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14";

/// A text in Spanish and English.
type Text = (&'static str, &'static str);

/// What urban trees do for a city (well-established benefits, no local figures).
const TREE_BENEFITS: [(Text, Text); 6] = [
    (
        ("Calles más frescas", "Cooler streets"),
        (
            "La sombra y la evapotranspiración bajan la temperatura del aire y de las superficies y atenúan las islas de calor urbanas.",
            "Shade and evapotranspiration lower surface and air temperatures and soften urban heat islands.",
        ),
    ),
    (
        ("Aire más limpio", "Cleaner air"),
        (
            "Las hojas retienen polvo y material particulado y absorben parte de los contaminantes gaseosos.",
            "Leaves trap dust and particulate matter and absorb part of the gaseous pollutants.",
        ),
    ),
    (
        ("Regulación del agua", "Water regulation"),
        (
            "Las copas interceptan la lluvia y las raíces ayudan a que el suelo la absorba, reduciendo la escorrentía y las inundaciones.",
            "Canopies intercept rain and roots help the soil absorb it, reducing runoff and flooding.",
        ),
    ),
    (
        ("Biodiversidad", "Biodiversity"),
        (
            "Los árboles dan alimento y refugio a aves, polinizadores y otra fauna urbana, en especial las especies nativas.",
            "Trees give food and shelter to birds, pollinators and other urban wildlife, especially native species.",
        ),
    ),
    (
        ("Salud y bienestar", "Health and well-being"),
        (
            "Las calles arborizadas y los parques invitan a caminar, reducen el estrés y hacen los barrios más habitables.",
            "Green streets and parks invite walking, reduce stress and make neighborhoods more liveable.",
        ),
    ),
    (
        ("Almacenamiento de carbono", "Carbon storage"),
        (
            "Al crecer, los árboles guardan carbono en su madera: un aporte pequeño pero duradero contra el cambio climático.",
            "Trees store carbon in their wood as they grow, a small but lasting contribution against climate change.",
        ),
    ),
];

/// What the platform is for.
const PLATFORM_BENEFITS: [(Text, Text); 4] = [
    (
        ("Saber qué tenemos", "Know what we have"),
        (
            "Un inventario público de los árboles de la ciudad: especie, ubicación, tamaño y estado, en lugar de hojas de cálculo dispersas.",
            "One public inventory of the city's trees: species, location, size and condition, instead of scattered spreadsheets.",
        ),
    ),
    (
        ("Planificar con evidencia", "Plan with evidence"),
        (
            "Ver qué comunas tienen menos árboles y qué tan diverso y nativo es el arbolado, para decidir dónde y qué sembrar.",
            "See which comunas lack trees and how diverse and native the urban forest is, to decide where and what to plant.",
        ),
    ),
    (
        ("Cuidar los árboles a tiempo", "Care for trees in time"),
        (
            "Identificar árboles enfermos, en estado crítico o muertos y las especies más afectadas, para priorizar el mantenimiento.",
            "Spot sick, critical or dead trees and the species most affected, to prioritize maintenance.",
        ),
    ),
    (
        ("Abierta y compartida", "Open and shared"),
        (
            "Código abierto y datos exportables, para que instituciones, investigadores y ciudadanos los usen y mejoren.",
            "Open-source code and exportable data, so institutions, researchers and citizens can use and improve them.",
        ),
    ),
];

/// The platform's sections: (route, name, what it is for).
const SECTIONS: [(&str, Text, Text); 5] = [
    (
        "/dashboard",
        ("Panel", "Dashboard"),
        ("Resumen del censo: árboles, salud, campañas y clima.", "Summary of the census: trees, health, campaigns and climate."),
    ),
    (
        "/map",
        ("Mapa", "Map"),
        ("Comunas, barrios y cada árbol en el mapa, con su ficha.", "Comunas, barrios and every tree on the map, with its data sheet."),
    ),
    (
        "/trees",
        ("Árboles", "Trees"),
        ("Consultar el inventario y exportarlo a CSV.", "Search the inventory and export it to CSV."),
    ),
    (
        "/species",
        ("Especies", "Species"),
        ("Catálogo de las especies presentes en la ciudad, con sus rasgos.", "Catalog of the species found in the city, with their traits."),
    ),
    (
        "/analytics",
        ("Análisis", "Analysis"),
        (
            "Indicadores de origen, densidad por comuna, salud y especies amenazadas.",
            "Indicators on origin, density by comuna, health and threatened species.",
        ),
    ),
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
    let i = I18n::use_ctx();
    let t = move |(es, en): Text| move || i.t(es, en);

    view! {
        <div class="p-6 space-y-6 max-w-6xl mx-auto">
            // What the platform is
            <div class=CARD>
                <h1 class="text-3xl font-bold text-primary-600">"Urban Tree Observatory"</h1>
                <p class=format!("{P} mt-3 text-lg")>
                    {t((
                        "Una plataforma abierta para explorar, entender y gestionar el arbolado urbano de Ibagué, Colombia. Reúne el censo de árboles de la ciudad, el catálogo de especies, los mapas de comunas y barrios y los registros de clima en una sola base de datos geográfica, y los convierte en mapas, fichas consultables e indicadores.",
                        "An open platform to explore, understand and manage the urban trees of Ibagué, Colombia. It brings together the city's tree census, the species catalog, maps of comunas and barrios and climate records in a single geographic database, and turns them into maps, searchable records and indicators.",
                    ))}
                </p>
            </div>

            // Who builds it (emphasis)
            <div class="rounded-lg border-2 border-primary-600 bg-primary-50 p-6">
                <h2 class=H2>{t(("Quién está detrás", "Who is behind it"))}</h2>
                <div class="mt-4 grid grid-cols-1 md:grid-cols-3 gap-6">
                    <div>
                        <p class=KICKER>{t(("Origen", "Origin"))}</p>
                        <p class=format!("{P} mt-1")>
                            {t(("Este proyecto es el producto final de un voluntariado con ", "This project is the final product of a volunteer project with "))}
                            <strong>"Omdena"</strong>
                            {t((
                                " (GibdetColombia Chapter), en el que voluntarios construyeron la primera versión del observatorio.",
                                " (GibdetColombia Chapter), where volunteers built the first version of the observatory.",
                            ))}
                        </p>
                        <p class="mt-2">{external(OMDENA_URL, "omdena.com")}</p>
                    </div>
                    <div>
                        <p class=KICKER>{t(("Mantenido y desarrollado por", "Maintained and developed by"))}</p>
                        <p class=format!("{P} mt-1")>
                            <strong>"Fundación LEGUT"</strong>
                            {t((" mantiene la plataforma y continúa su desarrollo.", " maintains the platform and continues its development."))}
                        </p>
                        <p class="mt-2">{external(LEGUT_URL, "legut.org")}</p>
                    </div>
                    <div>
                        <p class=KICKER>{t(("Código fuente", "Source code"))}</p>
                        <p class=format!("{P} mt-1")>
                            {t((
                                "El repositorio principal es de código abierto (licencia MIT). Allí son bienvenidos reportes, ideas y contribuciones.",
                                "The main repository is open source (MIT License). Issues, ideas and contributions are welcome there.",
                            ))}
                        </p>
                        <p class="mt-2">{external(REPO_URL, "GitHub")}</p>
                    </div>
                </div>
            </div>

            // What an urban forest is
            <div class=CARD>
                <h2 class=H2>{t(("¿Qué es el arbolado urbano?", "What is an urban forest?"))}</h2>
                <p class=format!("{P} mt-3")>
                    {t((
                        "El arbolado urbano es el conjunto de árboles, palmas y arbustos que crecen en una ciudad: en calles y avenidas, parques, plazas y zonas verdes, en las rondas de ríos y quebradas y en los jardines privados. Visto en conjunto, es parte de la infraestructura de la ciudad —infraestructura verde— que se debe planificar, sembrar y mantener como cualquier otra.",
                        "The urban forest is the set of all the trees, palms and shrubs that grow in a city: along streets and avenues, in parks, squares and green areas, along rivers and ravines, and in private gardens. Looked at together, they are part of the city's infrastructure — green infrastructure — that needs to be planned, planted and maintained like any other.",
                    ))}
                </p>
                <div class="mt-5 grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
                    {TREE_BENEFITS.into_iter().map(|(title, text)| view! {
                        <div class="rounded-md border border-gray-200 bg-gray-50 p-4">
                            <h3 class="font-semibold text-green-800">{t(title)}</h3>
                            <p class="mt-1 text-sm text-gray-600">{t(text)}</p>
                        </div>
                    }).collect_view()}
                </div>
            </div>

            // Why the platform
            <div class=CARD>
                <h2 class=H2>{t(("¿Por qué esta plataforma?", "Why this platform"))}</h2>
                <p class=format!("{P} mt-3")>
                    {t((
                        "Gestionar el arbolado empieza por conocerlo. La plataforma pone los datos del censo donde todos pueden verlos y usarlos:",
                        "Managing an urban forest starts with knowing it. The platform puts the census data where everyone can see it and use it:",
                    ))}
                </p>
                <div class="mt-5 grid grid-cols-1 md:grid-cols-2 gap-4">
                    {PLATFORM_BENEFITS.into_iter().map(|(title, text)| view! {
                        <div class="flex gap-3">
                            <span class="mt-1.5 h-2.5 w-2.5 shrink-0 rounded-full bg-primary-600"></span>
                            <div>
                                <h3 class="font-semibold text-gray-900">{t(title)}</h3>
                                <p class="text-sm text-gray-600">{t(text)}</p>
                            </div>
                        </div>
                    }).collect_view()}
                </div>
            </div>

            // Sections and data
            <div class="grid grid-cols-1 lg:grid-cols-2 gap-6">
                <div class=CARD>
                    <h2 class=H2>{t(("Qué puedes hacer aquí", "What you can do here"))}</h2>
                    <ul class="mt-4 divide-y divide-gray-100">
                        {SECTIONS.into_iter().map(|(href, name, text)| view! {
                            <li class="py-2.5">
                                <a href=href class=LINK>{t(name)}</a>
                                <p class="text-sm text-gray-600">{t(text)}</p>
                            </li>
                        }).collect_view()}
                    </ul>
                </div>
                <div class=CARD>
                    <h2 class=H2>{t(("Los datos", "The data"))}</h2>
                    <ul class=format!("{P} mt-4 space-y-3 text-sm list-disc pl-5")>
                        <li>
                            <strong>{t(("Censo de arbolado urbano", "Urban tree census"))}</strong>
                            {t((
                                " de Ibagué realizado por Cortolima (campañas de 2014, 2015 y 2017): especie, ubicación, medidas y estado de cada árbol.",
                                " of Ibagué by Cortolima (campaigns of 2014, 2015 and 2017): species, location, measurements and condition of each tree.",
                            ))}
                        </li>
                        <li>
                            <strong>{t(("Catálogo de especies", "Species catalog"))}</strong>
                            {t((
                                " con origen, rasgos y categoría de la Lista Roja de la UICN, enlazado a GBIF y a la base Useful Tropical Plants.",
                                " with origin, traits and IUCN Red List category, linked to GBIF and the Useful Tropical Plants database.",
                            ))}
                        </li>
                        <li>
                            <strong>{t(("Límites de comunas y barrios", "Comuna and barrio boundaries"))}</strong>
                            {t((" y la población de 2019 de cada comuna.", " and the 2019 population of each comuna."))}
                        </li>
                        <li>
                            <strong>{t(("Temperatura del aire", "Air temperature"))}</strong>
                            {t((" de estaciones meteorológicas automáticas en Ibagué.", " from automatic weather stations in Ibagué."))}
                        </li>
                        <li>
                            {t((
                                "Todo se almacena en una base de datos geográfica PostgreSQL / PostGIS. El censo refleja los árboles en el momento en que se levantó; no es un registro en vivo.",
                                "Everything is stored in a PostgreSQL / PostGIS geographic database. The census reflects the trees when they were surveyed; it is not a live record.",
                            ))}
                        </li>
                    </ul>
                </div>
            </div>
        </div>
    }
}
