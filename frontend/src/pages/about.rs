//! About page (static content): what an urban forest is, what this platform offers, who
//! develops it and the studies it builds on. Figures belong to the Dashboard, Map and
//! Analytics pages, not here.

use leptos::prelude::*;

use crate::i18n::I18n;

const REPO_URL: &str = "https://github.com/legut00/GibdetColombiaChapter_UrbanTreeObservatory/tree/main";
const LEGUT_URL: &str = "https://www.legut.org/";
const OMDENA_URL: &str =
    "https://www.omdena.com/chapter-challenges/urban-tree-observatory-data-driven-monitoring-conservation-in-ibague-colombia";

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

/// A piece of a reference: text (Spanish, English) and whether it is italic. APA joins the
/// last author with " y " in Spanish and ", & " in English.
type Seg = (Text, bool);

/// Same text in both languages (titles, names, journals stay as published).
const fn same(s: &'static str) -> Text {
    (s, s)
}

/// One APA 7 reference: its segments, then the link if any.
type Reference = (&'static [Seg], Option<&'static str>);

const AND: Seg = ((" y ", ", & "), false);
const OPEN_DATA: Text = same("Portal Nacional de Datos Abiertos de Colombia. ");

/// A stage of research on the urban trees of Ibagué and Tolima: period, name, headline,
/// summary (citing in APA style) and its references, oldest first (same year: by author).
struct Stage {
    period: &'static str,
    name: Text,
    title: Text,
    summary: Text,
    references: &'static [Reference],
}

/// The studies that inspired the platform and fed its development, by stage.
const STAGES: [Stage; 4] = [
    Stage {
        period: "2005 – 2010",
        name: ("Etapa fundacional", "Foundations"),
        title: ("Primeros diagnósticos botánicos", "First botanical surveys"),
        summary: (
            "Molina Prieto (2008) propone especies que fortalecen la Estructura Ecológica Principal de Ibagué y Esquivel (2010) cataloga 280 especies arbóreas de la ciudad.",
            "Molina Prieto (2008) proposes species that strengthen the Main Ecological Structure of Ibagué and Esquivel (2010) catalogs 280 tree species of the city.",
        ),
        references: &[
            (
                &[
                    (same("Molina Prieto, L. F. (2008). Árboles para Ibagué: Especies que fortalecen la Estructura Ecológica Principal. "), false),
                    (same("Revista Nodo, 3"), true),
                    (same("(5), 73–84. "), false),
                ],
                Some("https://revistas.uan.edu.co/index.php/nodo/article/view/149"),
            ),
            (
                &[
                    (same("Esquivel M., H. E. (2010). "), false),
                    (same("Flora arbórea de la ciudad de Ibagué"), true),
                    ((" [Catálogo taxonómico y fenológico de 280 especies]. Universidad del Tolima.", " [Taxonomic and phenological catalog of 280 species]. Universidad del Tolima."), false),
                ],
                None,
            ),
        ],
    },
    Stage {
        period: "2014 – 2017",
        name: ("Etapa censal y de planificación", "Census and planning"),
        title: ("Censo «Ibagué Ciudad Verde» y plan maestro", "The “Ibagué Ciudad Verde” census and master plan"),
        summary: (
            "Cortolima y la Universidad del Tolima levantan el censo del arbolado urbano y sus planes operativos por comuna (Universidad del Tolima y Cortolima, 2015). Le siguen el plan maestro de silvicultura urbana (Cortolima, 2016), el manual de arborización del Tolima (Cortolima y Jardín Botánico San Jorge, 2017) y los primeros criterios de diversidad funcional para elegir especies (Núñez-Florez, 2017).",
            "Cortolima and the Universidad del Tolima survey the urban tree census and its operational plans by comuna (Universidad del Tolima & Cortolima, 2015). They are followed by the urban forestry master plan (Cortolima, 2016), the Tolima arborization manual (Cortolima & Jardín Botánico San Jorge, 2017) and the first functional diversity criteria for choosing species (Núñez-Florez, 2017).",
        ),
        references: &[
            (
                &[
                    (same("Universidad del Tolima [UT]"), false),
                    AND,
                    (same("Corporación Autónoma Regional del Tolima [Cortolima]. (2015). "), false),
                    (same("Plan operativo detallado de silvicultura urbana para la Comuna 2 de Ibagué"), true),
                    ((" [Informe técnico del censo Ibagué Ciudad Verde]. Cortolima.", " [Technical report of the Ibagué Ciudad Verde census]. Cortolima."), false),
                ],
                None,
            ),
            (
                &[
                    (same("Corporación Autónoma Regional del Tolima [Cortolima]. (2016). "), false),
                    (same("Formulación del plan maestro de silvicultura urbana para la ciudad de Ibagué"), true),
                    ((" [Versión final; Contrato 507 de 2016, operado por Constructo Co S.A.S.]. ", " [Final version; Contract 507 of 2016, operated by Constructo Co S.A.S.]. "), false),
                ],
                Some("https://binet.cortolima.gov.co/images/estudio/bosques/PLAN_MAESTRO_SILVICULTURA_IBAGUE_2016.pdf"),
            ),
            (
                &[
                    (same("Corporación Autónoma Regional del Tolima [Cortolima]"), false),
                    AND,
                    (same("Jardín Botánico San Jorge. (2017). "), false),
                    (same("Manual de arborización para el departamento del Tolima"), true),
                    (same(". Cortolima."), false),
                ],
                None,
            ),
            (
                &[
                    (same("Núñez-Florez, R. (2017). "), false),
                    (same("Criterios de diversidad funcional para la selección de especies en el arbolado urbano de la comuna 3 de la ciudad de Ibagué, Tolima"), true),
                    (
                        (
                            " [Trabajo de grado de maestría, Universidad del Tolima]. Repositorio Institucional Universidad del Tolima (RIUT).",
                            " [Master's thesis, Universidad del Tolima]. Repositorio Institucional Universidad del Tolima (RIUT).",
                        ),
                        false,
                    ),
                ],
                None,
            ),
        ],
    },
    Stage {
        period: "2019 – 2022",
        name: ("Etapa funcional y ecosistémica", "Function and ecosystem services"),
        title: ("Rasgos funcionales, carbono y economía ambiental", "Functional traits, carbon and environmental economics"),
        summary: (
            "Núñez-Florez et al. (2019) publican criterios de diversidad funcional para seleccionar árboles urbanos. Acuña-Simbaqueva et al. (2021) estiman cuánto mitiga el arbolado las emisiones de los hogares y Sierra-Ramírez et al. (2022), cuánto pagarían por ello. Otros trabajos abordan el riesgo de fallo, los líquenes, la hojarasca, los servicios ecosistémicos y el crecimiento de los árboles, y la Alcaldía de Ibagué (2022) publica el censo como datos abiertos.",
            "Núñez-Florez et al. (2019) publish functional diversity criteria for selecting urban trees. Acuña-Simbaqueva et al. (2021) estimate how much the trees mitigate household emissions and Sierra-Ramírez et al. (2022), how much people would pay for it. Other works address failure risk, lichens, leaf litter, ecosystem services and tree growth, and the city government (Alcaldía de Ibagué, 2022) publishes the census as open data.",
        ),
        references: &[
            (
                &[
                    (same("Núñez-Florez, R., Pérez-Gómez, U."), false),
                    AND,
                    (same("Fernández-Méndez, F. (2019). Functional diversity criteria for selecting urban trees. "), false),
                    (same("Urban Forestry & Urban Greening, 38"), true),
                    (same(", 251–266. "), false),
                ],
                Some("https://doi.org/10.1016/j.ufug.2019.01.005"),
            ),
            (
                &[
                    (same("Barreto, L."), false),
                    AND,
                    (same("Esquivel, H. E. (2020). "), false),
                    (same("Diversidad y riqueza de líquenes epífitos en zonas verdes urbanas de Ibagué, Tolima, Colombia"), true),
                    (same(". Universidad del Tolima."), false),
                ],
                None,
            ),
            (
                &[
                    (same("Pérez-Gómez, U., et al. (2020). "), false),
                    (same("Evaluación del riesgo de fallo en el arbolado del campus de la Universidad del Tolima, Ibagué"), true),
                    ((" [Ponencia científica]. Universidad del Tolima.", " [Conference paper]. Universidad del Tolima."), false),
                ],
                None,
            ),
            (
                &[
                    (same("Acuña-Simbaqueva, L. M., Andrade, H. J., Segura, M. A., Sierra-Ramírez, E., Canal-Daza, D. S."), false),
                    AND,
                    (same("Greñas-Corrales, O. E. (2021). Mitigación de emisiones de gases de efecto invernadero de hogares por arbolado urbano en Ibagué-Colombia. "), false),
                    (same("Ambiente & Sociedade, 24"), true),
                    ((", Artículo e01911. ", ", Article e01911. "), false),
                ],
                Some("https://doi.org/10.1590/1809-4422asoc20200191vu2021L3AO"),
            ),
            (
                &[
                    (same("Oliveros, D."), false),
                    AND,
                    (same("Salguero, J. (2021). Dinámica de descomposición de hojarasca en el bosque urbano de ribera del campus de la Universidad de Ibagué. "), false),
                    (same("Revista Indagare"), true),
                    (same(", Universidad de Ibagué."), false),
                ],
                None,
            ),
            (
                &[
                    (same("Alcaldía Municipal de Ibagué. (2022). "), false),
                    (same("Censo del arbolado urbano de Ibagué por comuna — Proyecto Ibagué Ciudad Verde"), true),
                    ((" [Conjunto de datos abiertos, ID: sczr-x354]. ", " [Open dataset, ID: sczr-x354]. "), false),
                    (OPEN_DATA, false),
                ],
                Some("https://www.datos.gov.co/"),
            ),
            (
                &[
                    (same("Aragón Mora, D. J."), false),
                    AND,
                    (same("Valencia Vera, W. (2022). "), false),
                    (same("Oferta de servicios ecosistémicos de especies del arbolado urbano de la ciudad de Ibagué, Tolima, Colombia"), true),
                    ((" [Trabajo de grado, Universidad del Tolima]. Repositorio Institucional Universidad del Tolima. ", " [Undergraduate thesis, Universidad del Tolima]. Repositorio Institucional Universidad del Tolima. "), false),
                ],
                Some("https://repository.ut.edu.co/entities/publication/3a83cc95-87b7-488b-ae06-014cc5ff329e"),
            ),
            (
                &[
                    (same("Campos Pérez, W. F."), false),
                    AND,
                    (same("Vargas Salgado, W. S. (2022). "), false),
                    (same("Crecimiento diamétrico y captura de carbono de árboles individuales de "), true),
                    // APA: a species name inside an italic title goes back to roman.
                    (same("Tabebuia rosea"), false),
                    (same(" (Bertol) D.C en el arbolado urbano de Ibagué, Colombia"), true),
                    ((" [Trabajo de grado, Universidad del Tolima].", " [Undergraduate thesis, Universidad del Tolima]."), false),
                ],
                None,
            ),
            (
                &[
                    (same("Sierra-Ramírez, E., Andrade, H. J."), false),
                    AND,
                    (same("Segura, M. A. (2022). "), false),
                    (same("Disponibilidad a pagar por la mitigación de emisiones de gases de efecto invernadero mediante arborización urbana en Ibagué, Colombia"), true),
                    (same(". Grupo de Investigación PROECUT, Universidad del Tolima."), false),
                ],
                None,
            ),
        ],
    },
    Stage {
        period: "2023 – 2026",
        name: ("Etapa microclimática e instrumental", "Microclimate and instruments"),
        title: ("Confort térmico, evaluación instrumental y datos abiertos", "Thermal comfort, instrumental assessment and open data"),
        summary: (
            "Barrero-Mora y Francel (2023) miden el confort térmico y lumínico de los parques y Guevara y Francel (2023), la accesibilidad peatonal que ofrece el arbolado; Medina Mora (2023) analiza un bosque urbano de barrio y Díaz-Jaramillo et al. (2024) estudian las aves asociadas al arbolado del campus de la Universidad del Tolima y del Jardín Botánico San Jorge. Segura Madrigal et al. (2025) proponen estrategias de mitigación con arbolado y movilidad sostenible, Torres (2025) evalúa 100 árboles con tomografía y otros ensayos no destructivos, y la Alcaldía de Ibagué (2026) publica el inventario completo como datos abiertos.",
            "Barrero-Mora and Francel (2023) measure thermal and light comfort in parks and Guevara and Francel (2023), the pedestrian accessibility the trees provide; Medina Mora (2023) studies a neighborhood urban forest and Díaz-Jaramillo et al. (2024) study the birds associated with the trees of the Universidad del Tolima campus and the San Jorge Botanical Garden. Segura Madrigal et al. (2025) propose mitigation strategies with trees and sustainable mobility, Torres (2025) assesses 100 trees with tomography and other non-destructive tests, and the city government (Alcaldía de Ibagué, 2026) publishes the full inventory as open data.",
        ),
        references: &[
            (
                &[
                    (same("Barrero-Mora, L."), false),
                    AND,
                    (same("Francel, A. (2023). Confort térmico y lumínico en parques de fronteras urbanas de Ibagué, Colombia. "), false),
                    (same("Ciudad y Territorio Estudios Territoriales (CyTET), 55"), true),
                    (same("(216)."), false),
                ],
                None,
            ),
            (
                &[
                    (same("Guevara, M."), false),
                    AND,
                    (same("Francel, A. (2023). Accesibilidad peatonal y amenidad del arbolado urbano en Ibagué, Colombia. "), false),
                    (same("CIDADES, Comunidades e Territórios"), true),
                    (same("."), false),
                ],
                None,
            ),
            (
                &[
                    (
                        same("Medina Mora, E. (2023). La Ciudadela Comfenalco y su pequeño bosque urbano: La infraestructura verde como aliada en la creación del paisaje ambiental, social y económico. "),
                        false,
                    ),
                    (same("Revista B33 Arquitectura y Urbanismo"), true),
                    (same(", (9). "), false),
                ],
                Some("https://revistas.ut.edu.co/index.php/B33/article/view/3239"),
            ),
            (
                &[
                    (same("Díaz-Jaramillo, C., et al."), false),
                    AND,
                    (same("Parra-Hernández, R. M., et al. (2024). "), false),
                    (same("Avifauna asociada a remanentes boscosos y arbolado urbano del campus de la Universidad del Tolima y el Jardín Botánico San Jorge en Ibagué. "), false),
                    (same("Biota Colombiana"), true),
                    (same(". "), false),
                ],
                Some("https://repository.ut.edu.co/entities/publication/2d96b821-385c-4f0a-ab00-f7a2e2253d31"),
            ),
            (
                &[
                    (same("Segura Madrigal, M. A., Andrade Castañeda, H. J."), false),
                    AND,
                    (same("Sierra-Ramírez, E. (2025). "), false),
                    (same("Estrategias de mitigación de emisiones de gases de efecto invernadero de hogares mediante arbolado urbano y movilidad sostenible en Ibagué"), true),
                    (same(". Editorial Universidad del Tolima / Grupo de Investigación PROECUT."), false),
                ],
                None,
            ),
            (
                &[
                    (same("Torres Payares, L. E. (2025). "), false),
                    (
                        same("Evaluación instrumental del arbolado urbano a través de ensayos no destructivos en el marco del proyecto “Análisis del riesgo de árboles urbanos y sus servicios ecosistémicos”, en la ciudad de Ibagué, Tolima"),
                        true,
                    ),
                    ((" [Informe final de servicio social, Universidad del Tolima].", " [Final report of social service, Universidad del Tolima]."), false),
                ],
                None,
            ),
            (
                &[
                    (same("Alcaldía Municipal de Ibagué. (2026). "), false),
                    (same("Inventario del arbolado urbano de Ibagué (101.000 registros y 26 variables dasométricas)"), true),
                    ((" [Conjunto de datos abiertos, ID: am4p-tz7w]. ", " [Open dataset, ID: am4p-tz7w]. "), false),
                    (OPEN_DATA, false),
                ],
                Some("https://www.datos.gov.co/"),
            ),
        ],
    },
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
                        <p class="mt-2">{external(OMDENA_URL, "Omdena · Urban Tree Observatory")}</p>
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

            // References, as a timeline of research stages
            <div class=CARD>
                <h2 class=H2>{t(("Referencias", "References"))}</h2>
                <p class=format!("{P} mt-3")>
                    {t((
                        "Agradecemos a los autores de estos estudios sobre el arbolado urbano de Ibagué y el Tolima, que fueron fuente de inspiración y parte del desarrollo de esta plataforma. Los presentamos por etapas, de los más antiguos a los más recientes.",
                        "We thank the authors of these studies on the urban trees of Ibagué and Tolima, which inspired this platform and were part of its development. They are shown by stage, oldest first.",
                    ))}
                </p>
                <ol class="relative mt-8">
                    // The timeline's line, behind the dots.
                    <span class="absolute left-[11px] top-2 bottom-2 w-0.5 bg-primary-200" aria-hidden="true"></span>
                    {STAGES.into_iter().map(|stage| view! {
                        <li class="relative pl-10 pb-10 last:pb-0">
                            <span class="absolute left-0 top-1 h-6 w-6 rounded-full border-4 border-white bg-primary-600 ring-2 ring-primary-300" aria-hidden="true"></span>
                            <p class="inline-block rounded-md bg-primary-50 px-3 py-1 text-sm font-semibold text-primary-800">
                                {stage.period}" · "{t(stage.name)}
                            </p>
                            <h3 class="mt-2 text-lg font-semibold text-gray-900">{t(stage.title)}</h3>
                            <p class="mt-1 text-gray-600 leading-relaxed">{t(stage.summary)}</p>
                            <ul class="mt-4 space-y-2 text-sm text-gray-700 leading-relaxed">
                                {stage.references.iter().map(|&(segs, url)| view! {
                                    <li class="rounded-md border border-primary-100 border-l-4 border-l-primary-500 bg-white px-4 py-2.5 transition-colors hover:bg-primary-50/70">
                                        // Hanging indent, as in an APA reference list.
                                        <div class="pl-8 -indent-8">
                                            {segs.iter().map(|&(text, italic)| {
                                                if italic { view! { <i>{t(text)}</i> }.into_any() } else { view! { <span>{t(text)}</span> }.into_any() }
                                            }).collect_view()}
                                            {url.map(|u| view! {
                                                <a href=u target="_blank" rel="noopener noreferrer" class="text-primary-700 hover:underline break-all">{u}</a>
                                            })}
                                        </div>
                                    </li>
                                }).collect_view()}
                            </ul>
                        </li>
                    }).collect_view()}
                </ol>
            </div>
        </div>
    }
}
