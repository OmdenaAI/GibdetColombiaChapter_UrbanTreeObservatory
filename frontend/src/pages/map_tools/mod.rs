//! Map toolbar (bottom center), with two panels that build one tree query:
//!
//! - Layers: the area of interest, drawn on the map or loaded from a KML file.
//! - Filters: tree code, scientific name, common name, comuna and barrio.
//!
//! Filters and area combine (AND) in a POST to `/biodiversity/inventory/query/`. The answer
//! (count, points, bounding box) goes to `ToolSignals::result`, which the map page draws; the
//! same query downloads as Excel, CSV or GeoJSON with every inventory column.
//!
//! The map page owns the Leaflet side: it adds vertices to `ToolSignals::draft` on clicks
//! while drawing and draws `zone`, `draft` and `result`.

pub mod kml;

use leptos::prelude::*;
use leptos::task::spawn_local;
use serde_json::{Value, json};

use super::trees::export::post_download;
use crate::api::{API_BASE, console_error, fmt_thousands, get_json, post_json};
use crate::i18n::{I18n, Lang, pick};
use kml::KmlError;

const MAX_KML_BYTES: f64 = 5_000_000.0;

/// The open panel's element id: the map keeps what it frames above it.
pub const PANEL_ID: &str = "map-tool-panel";

fn query_url() -> String {
    format!("{API_BASE}/api/v1/biodiversity/inventory/query/")
}

// ---------------------------------------------------------------------------
// State shared with the map page
// ---------------------------------------------------------------------------

/// The area of interest.
#[derive(Clone, Debug, PartialEq)]
pub struct Zone {
    /// KML name (or file name); `None` for a polygon drawn on the map.
    pub label: Option<String>,
    /// GeoJSON Polygon / MultiPolygon, `[lon, lat]`.
    pub geometry: Value,
    pub polygons: usize,
    pub vertices: usize,
}

/// A polygon drawn on the map: vertices as `[lat, lng]` (Leaflet order) -> GeoJSON ring.
pub fn drawn_zone(vertices: &[[f64; 2]]) -> Zone {
    let mut ring: Vec<[f64; 2]> = vertices.iter().map(|[lat, lng]| [*lng, *lat]).collect();
    if let Some(first) = ring.first().copied() {
        ring.push(first);
    }
    Zone {
        label: None,
        geometry: json!({ "type": "Polygon", "coordinates": [ring] }),
        polygons: 1,
        vertices: vertices.len(),
    }
}

#[derive(Clone, Debug, PartialEq)]
pub struct QueryResult {
    pub count: i64,
    /// `(id, lat, lon)`, at most 20,000 (the server's limit).
    pub points: Vec<(i64, f64, f64)>,
    pub truncated: bool,
    /// `[west, south, east, north]`.
    pub bbox: Option<[f64; 4]>,
}

impl QueryResult {
    fn from_json(v: &Value) -> Option<Self> {
        let points = v["points"]
            .as_array()?
            .iter()
            .filter_map(|p| Some((p[0].as_i64()?, p[1].as_f64()?, p[2].as_f64()?)))
            .collect();
        let bbox = v["bbox"].as_array().and_then(|b| {
            let n: Vec<f64> = b.iter().filter_map(Value::as_f64).collect();
            <[f64; 4]>::try_from(n).ok()
        });
        Some(Self {
            count: v["count"].as_i64()?,
            points,
            truncated: v["truncated"].as_bool().unwrap_or(false),
            bbox,
        })
    }
}

#[derive(Clone, Copy)]
pub struct ToolSignals {
    pub zone: RwSignal<Option<Zone>>,
    /// Vertices (`[lat, lng]`) of the polygon being drawn; `None` when not drawing.
    pub draft: RwSignal<Option<Vec<[f64; 2]>>>,
    pub result: RwSignal<Option<QueryResult>>,
}

impl ToolSignals {
    pub fn new() -> Self {
        Self { zone: RwSignal::new(None), draft: RwSignal::new(None), result: RwSignal::new(None) }
    }

    /// For Leaflet callbacks (they may run after the page is gone: `try_`).
    pub fn is_drawing(&self) -> bool {
        self.draft.try_with_untracked(Option::is_some).unwrap_or(false)
    }

    pub fn add_vertex(&self, lat: f64, lng: f64) {
        self.draft.try_update(|d| {
            // The two clicks of a double click land on the same point: keep one.
            if let Some(v) = d
                && v.last() != Some(&[lat, lng])
            {
                v.push([lat, lng]);
            }
        });
    }

    /// Close the drawn polygon into the area of interest. Needs three vertices.
    pub fn finish_drawing(&self) {
        let Some(Some(vertices)) = self.draft.try_get_untracked() else { return };
        if vertices.len() >= 3 {
            self.draft.try_set(None);
            self.zone.try_set(Some(drawn_zone(&vertices)));
        }
    }
}

// ---------------------------------------------------------------------------
// Filters -> request body
// ---------------------------------------------------------------------------

#[derive(Clone, Debug, Default, PartialEq)]
struct FilterValues {
    code: String,
    scientific: String,
    common: String,
    comuna: Option<i64>,
    neighborhood: Option<i64>,
}

#[derive(Debug, PartialEq)]
enum BodyError {
    BadCode,
}

impl FilterValues {
    fn is_empty(&self) -> bool {
        self.code.trim().is_empty()
            && self.scientific.trim().is_empty()
            && self.common.trim().is_empty()
            && self.comuna.is_none()
            && self.neighborhood.is_none()
    }

    fn body(&self, zone: Option<&Value>, format: &str, lang: Lang) -> Result<Value, BodyError> {
        let mut body = json!({ "format": format, "lang": lang.code() });
        let code = self.code.trim();
        if !code.is_empty() {
            let id: i64 = code.parse().ok().filter(|n| *n > 0).ok_or(BodyError::BadCode)?;
            body["id"] = json!(id);
        }
        for (key, value) in [("scientific_name", &self.scientific), ("common_name", &self.common)] {
            if !value.trim().is_empty() {
                body[key] = json!(value.trim());
            }
        }
        if let Some(c) = self.comuna {
            body["comuna"] = json!(c);
        }
        if let Some(n) = self.neighborhood {
            body["neighborhood"] = json!(n);
        }
        if let Some(g) = zone {
            body["geometry"] = g.clone();
        }
        Ok(body)
    }
}

#[derive(Clone, Copy)]
struct Filters {
    code: RwSignal<String>,
    scientific: RwSignal<String>,
    common: RwSignal<String>,
    comuna: RwSignal<Option<i64>>,
    neighborhood: RwSignal<Option<i64>>,
}

impl Filters {
    fn new() -> Self {
        Self {
            code: RwSignal::new(String::new()),
            scientific: RwSignal::new(String::new()),
            common: RwSignal::new(String::new()),
            comuna: RwSignal::new(None),
            neighborhood: RwSignal::new(None),
        }
    }

    /// Tracked read: an Effect calling this reruns on every change.
    fn values(&self) -> FilterValues {
        FilterValues {
            code: self.code.get(),
            scientific: self.scientific.get(),
            common: self.common.get(),
            comuna: self.comuna.get(),
            neighborhood: self.neighborhood.get(),
        }
    }

    fn values_untracked(&self) -> FilterValues {
        untrack(|| self.values())
    }

    fn clear(&self) {
        self.code.set(String::new());
        self.scientific.set(String::new());
        self.common.set(String::new());
        self.comuna.set(None);
        self.neighborhood.set(None);
    }
}

/// Comunas and barrios with trees, for the selects.
#[derive(Clone, Default)]
struct Places {
    comunas: Vec<(i64, String)>,
    /// `(id, name, comuna id)`.
    neighborhoods: Vec<(i64, String, i64)>,
}

async fn load_places() -> Places {
    let url = format!("{API_BASE}/api/v1/biodiversity/inventory/options/");
    match get_json(&url).await {
        Ok(v) => Places {
            comunas: v["comunas"]
                .as_array()
                .into_iter()
                .flatten()
                .filter_map(|c| Some((c["id"].as_i64()?, c["name"].as_str()?.to_string())))
                .collect(),
            neighborhoods: v["neighborhoods"]
                .as_array()
                .into_iter()
                .flatten()
                .filter_map(|n| Some((n["id"].as_i64()?, n["name"].as_str()?.to_string(), n["comuna"].as_i64()?)))
                .collect(),
        },
        Err(e) => {
            console_error("Error loading the filter lists:", &e);
            Places::default()
        }
    }
}

/// "COMUNA 7" -> "Comuna 7".
fn comuna_name(name: &str) -> String {
    let lower = name.to_lowercase();
    let mut chars = lower.chars();
    chars.next().map(|c| c.to_uppercase().chain(chars).collect()).unwrap_or_default()
}

// ---------------------------------------------------------------------------
// Downloads
// ---------------------------------------------------------------------------

#[derive(Clone, Copy, PartialEq, Debug)]
enum Format {
    Xlsx,
    Csv,
    GeoJson,
}

impl Format {
    fn code(self) -> &'static str {
        match self {
            Format::Xlsx => "xlsx",
            Format::Csv => "csv",
            Format::GeoJson => "geojson",
        }
    }

    fn label(self) -> &'static str {
        match self {
            Format::Xlsx => "Excel",
            Format::Csv => "CSV",
            Format::GeoJson => "GeoJSON",
        }
    }

    fn mime(self) -> &'static str {
        match self {
            Format::Xlsx => "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            Format::Csv => "text/csv;charset=utf-8",
            Format::GeoJson => "application/geo+json",
        }
    }
}

fn file_name(lang: Lang, format: Format) -> String {
    let date: String = js_sys::Date::new_0().to_iso_string().into();
    format!("{}-{}.{}", pick(lang, "consulta-arboles", "tree-query"), &date[..10], format.code())
}

// ---------------------------------------------------------------------------
// Messages
// ---------------------------------------------------------------------------

#[derive(Clone, Debug, PartialEq)]
enum Problem {
    Kml(KmlError),
    Kmz,
    TooBig,
    Read,
    BadCode,
    Server(String),
}

fn problem_text(lang: Lang, p: &Problem) -> String {
    match p {
        Problem::Kml(KmlError::Xml) => pick(lang, "El archivo no es un KML válido.", "The file is not a valid KML.").into(),
        Problem::Kml(KmlError::NoPolygon) => {
            pick(lang, "El KML no contiene ningún polígono.", "The KML contains no polygon.").into()
        }
        Problem::Kml(KmlError::BadCoordinates) => pick(
            lang,
            "Un polígono del KML tiene coordenadas inválidas o menos de tres vértices.",
            "A polygon in the KML has invalid coordinates or fewer than three vertices.",
        )
        .into(),
        Problem::Kmz => pick(
            lang,
            "Los archivos KMZ no se pueden leer; guárdalo como KML (en Google Earth: «Guardar lugar como… → KML»).",
            "KMZ files cannot be read; save it as KML (in Google Earth: “Save Place As… → KML”).",
        )
        .into(),
        Problem::TooBig => pick(lang, "El archivo pesa más de 5 MB.", "The file is larger than 5 MB.").into(),
        Problem::Read => pick(lang, "No se pudo leer el archivo.", "The file could not be read.").into(),
        Problem::BadCode => pick(
            lang,
            "El código del árbol debe ser un número entero.",
            "The tree code must be a whole number.",
        )
        .into(),
        Problem::Server(msg) => format!("{} ({msg})", pick(lang, "La consulta falló", "The query failed")),
    }
}

// ---------------------------------------------------------------------------
// Icons (Heroicons outline, MIT)
// ---------------------------------------------------------------------------

const ICON_LAYERS: &str = "M6.429 9.75 2.25 12l4.179 2.25m0-4.5 5.571 3 5.571-3m-11.142 0L2.25 7.5 12 2.25l9.75 5.25-4.179 2.25m0 0L21.75 12l-4.179 2.25m0 0 4.179 2.25L12 21.75 2.25 16.5l4.179-2.25m11.142 0-5.571 3-5.571-3";
const ICON_FILTER: &str = "M12 3c2.755 0 5.455.232 8.083.678.533.09.917.556.917 1.096v1.044a2.25 2.25 0 0 1-.659 1.591l-5.432 5.432a2.25 2.25 0 0 0-.659 1.591v2.927a2.25 2.25 0 0 1-1.244 2.013L9.75 21v-6.568a2.25 2.25 0 0 0-.659-1.591L3.659 7.409A2.25 2.25 0 0 1 3 5.818V4.774c0-.54.384-1.006.917-1.096A48.32 48.32 0 0 1 12 3Z";
const ICON_PENCIL: &str = "m16.862 4.487 1.687-1.688a1.875 1.875 0 1 1 2.652 2.652L10.582 16.07a4.5 4.5 0 0 1-1.897 1.13L6 18l.8-2.685a4.5 4.5 0 0 1 1.13-1.897l8.932-8.931Zm0 0L19.5 7.125";
const ICON_UPLOAD: &str = "M3 16.5v2.25A2.25 2.25 0 0 0 5.25 21h13.5A2.25 2.25 0 0 0 21 18.75V16.5m-13.5-9L12 3m0 0 4.5 4.5M12 3v13.5";
const ICON_DOWNLOAD: &str = "M3 16.5v2.25A2.25 2.25 0 0 0 5.25 21h13.5A2.25 2.25 0 0 0 21 18.75V16.5M16.5 12 12 16.5m0 0L7.5 12m4.5 4.5V3";
const ICON_CLOSE: &str = "M6 18 18 6M6 6l12 12";

fn icon(path: &'static str, class: &'static str) -> impl IntoView {
    view! {
        <svg xmlns="http://www.w3.org/2000/svg" class=class fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor" aria-hidden="true">
            <path stroke-linecap="round" stroke-linejoin="round" d=path />
        </svg>
    }
}

const KICKER: &str = "text-xs font-semibold uppercase tracking-wide text-primary-700";
const BTN: &str = "inline-flex items-center justify-center gap-1.5 rounded-md px-3 py-1.5 text-sm font-medium transition-colors disabled:opacity-50 disabled:cursor-not-allowed";
const BTN_PRIMARY: &str = "bg-primary-700 text-white hover:bg-primary-800";
const BTN_SECONDARY: &str = "border border-gray-300 bg-white text-gray-700 hover:bg-gray-50";
const INPUT: &str = "w-full rounded-md border border-gray-300 px-2.5 py-1.5 text-sm focus:border-primary-600 focus:outline-none focus:ring-1 focus:ring-primary-600";
const LABEL: &str = "block text-xs font-medium text-gray-600 mb-1";

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

#[derive(Clone, Copy, PartialEq)]
enum Panel {
    Layers,
    Filters,
}

#[component]
pub fn MapToolbar(tools: ToolSignals) -> impl IntoView {
    let i = I18n::use_ctx();
    let open = RwSignal::new(None::<Panel>);
    let filters = Filters::new();
    let places = RwSignal::new(Places::default());
    let loading = RwSignal::new(false);
    let downloading = RwSignal::new(None::<Format>);
    let problem = RwSignal::new(None::<Problem>);
    // Answers of superseded queries are dropped.
    let seq = StoredValue::new(0u64);

    spawn_local(async move {
        let p = load_places().await;
        places.try_set(p);
    });

    let zone_geometry = move || tools.zone.with_untracked(|z| z.as_ref().map(|z| z.geometry.clone()));

    let run = move || {
        let body = match filters.values_untracked().body(zone_geometry().as_ref(), "json", i.lang_untracked()) {
            Ok(b) => b,
            Err(BodyError::BadCode) => return problem.set(Some(Problem::BadCode)),
        };
        let n = seq.get_value() + 1;
        seq.set_value(n);
        loading.set(true);
        problem.set(None);
        spawn_local(async move {
            let answer = post_json(&query_url(), &body).await;
            if seq.try_get_value() != Some(n) {
                return;
            }
            match answer {
                Ok(v) => {
                    tools.result.try_set(QueryResult::from_json(&v));
                }
                Err(e) => {
                    tools.result.try_set(None);
                    problem.try_set(Some(Problem::Server(e)));
                }
            }
            loading.try_set(false);
        });
    };

    // Editing a filter invalidates the shown result (its downloads would not match).
    Effect::new(move |first: Option<()>| {
        filters.values();
        if first.is_some() {
            tools.result.set(None);
            problem.set(None);
        }
    });
    // A new (or removed) area of interest runs the query at once. Without area and filters
    // there is nothing to ask: the result is cleared.
    Effect::new(move |first: Option<()>| {
        let has_zone = tools.zone.with(Option::is_some);
        if first.is_some() {
            if has_zone || !filters.values_untracked().is_empty() {
                run();
            } else {
                tools.result.set(None);
            }
        }
    });

    let download = move |format: Format| {
        let lang = i.lang_untracked();
        let Ok(body) = filters.values_untracked().body(zone_geometry().as_ref(), format.code(), lang) else {
            return problem.set(Some(Problem::BadCode));
        };
        downloading.set(Some(format));
        problem.set(None);
        spawn_local(async move {
            if let Err(e) = post_download(&query_url(), &body, &file_name(lang, format), format.mime()).await {
                problem.try_set(Some(Problem::Server(e)));
            }
            downloading.try_set(None);
        });
    };

    // ---- result, shared by both panels ----
    let result_box = move || {
        let lang = i.lang();
        let message = problem.get().map(|p| {
            view! { <p class="rounded-md bg-red-50 border border-red-200 px-3 py-2 text-sm text-red-800">{problem_text(lang, &p)}</p> }
        });
        let body = if loading.get() {
            Some(view! { <p class="text-sm text-gray-600">{pick(lang, "Consultando…", "Querying…")}</p> }.into_any())
        } else {
            tools.result.get().map(|r| {
                let count = r.count;
                let truncated = r.truncated.then(|| {
                    view! {
                        <p class="text-xs text-gray-500">
                            {pick(lang, "En el mapa se resaltan los primeros ", "The map highlights the first ")}
                            {fmt_thousands(r.points.len() as i64)}
                            {pick(lang, "; las descargas incluyen todos.", "; the downloads include all of them.")}
                        </p>
                    }
                });
                let buttons = (count > 0).then(|| {
                    let button = move |f: Format| {
                        view! {
                            <button type="button" class=format!("{BTN} {BTN_SECONDARY}")
                                disabled=move || downloading.get().is_some()
                                on:click=move |_| download(f)>
                                {icon(ICON_DOWNLOAD, "h-4 w-4")}
                                {move || if downloading.get() == Some(f) { pick(i.lang(), "Preparando…", "Preparing…") } else { f.label() }}
                            </button>
                        }
                    };
                    view! {
                        <div>
                            <p class=LABEL>{pick(lang, "Descargar con todos los datos de cada árbol", "Download with every tree's data")}</p>
                            <div class="flex flex-wrap gap-2">
                                {button(Format::Xlsx)}
                                {button(Format::Csv)}
                                {button(Format::GeoJson)}
                            </div>
                        </div>
                    }
                });
                view! {
                    <div class="space-y-3">
                        <p class="text-sm text-gray-700">
                            {if count == 0 {
                                pick(lang, "Ningún árbol cumple la consulta.", "No tree matches the query.").to_string()
                            } else {
                                String::new()
                            }}
                            {(count > 0).then(|| view! {
                                <span class="text-2xl font-bold text-primary-700">{fmt_thousands(count)}</span>
                                " "
                                {if count == 1 { pick(lang, "árbol encontrado", "tree found") } else { pick(lang, "árboles encontrados", "trees found") }}
                            })}
                        </p>
                        {truncated}
                        {buttons}
                    </div>
                }
                .into_any()
            })
        };
        (message.is_some() || body.is_some()).then(|| {
            view! { <div class="mt-4 border-t border-gray-200 pt-4 space-y-3">{message}{body}</div> }
        })
    };

    // ---- area of interest card (both panels) ----
    let zone_card = move || {
        tools.zone.get().map(|z| {
            let lang = i.lang();
            let name = z.label.clone().unwrap_or_else(|| pick(lang, "Polígono dibujado", "Drawn polygon").to_string());
            view! {
                <div class="flex items-start justify-between gap-3 rounded-md border border-blue-200 border-l-4 border-l-blue-700 bg-blue-50/70 px-3 py-2">
                    <div class="min-w-0">
                        <p class="text-sm font-medium text-gray-800 truncate" title=name.clone()>{name.clone()}</p>
                        <p class="text-xs text-gray-600">
                            {(z.polygons > 1).then(|| format!("{}{} · ", z.polygons, pick(lang, " polígonos", " polygons")))}
                            {z.vertices}{pick(lang, " vértices", " vertices")}
                        </p>
                    </div>
                    <button type="button" class="text-sm text-blue-800 hover:underline shrink-0" on:click=move |_| tools.zone.set(None)>
                        {pick(lang, "Quitar", "Remove")}
                    </button>
                </div>
            }
        })
    };

    // ---- Layers panel ----
    let on_file = move |ev: leptos::ev::Event| {
        let input = event_target::<web_sys::HtmlInputElement>(&ev);
        let Some(file) = input.files().and_then(|f| f.get(0)) else { return };
        // Choosing the same file again must fire `change` again.
        input.set_value("");
        let name = file.name();
        if name.to_lowercase().ends_with(".kmz") {
            return problem.set(Some(Problem::Kmz));
        }
        if file.size() > MAX_KML_BYTES {
            return problem.set(Some(Problem::TooBig));
        }
        problem.set(None);
        spawn_local(async move {
            let text = wasm_bindgen_futures::JsFuture::from(file.text()).await.ok().and_then(|v| v.as_string());
            let Some(text) = text else {
                problem.try_set(Some(Problem::Read));
                return;
            };
            match kml::parse(&text) {
                Ok(area) => {
                    tools.draft.try_set(None);
                    tools.zone.try_set(Some(Zone {
                        label: Some(area.name.unwrap_or(name)),
                        geometry: area.geometry,
                        polygons: area.polygons,
                        vertices: area.vertices,
                    }));
                }
                Err(e) => {
                    problem.try_set(Some(Problem::Kml(e)));
                }
            }
        });
    };
    let file_ref = NodeRef::<leptos::html::Input>::new();

    let layers_panel = move || {
        let drawing = tools.draft.with(Option::is_some);
        let vertices = tools.draft.with(|d| d.as_ref().map_or(0, Vec::len));
        view! {
            <p class=KICKER>{move || i.t("Zona de interés", "Area of interest")}</p>
            <p class="mt-1 mb-3 text-sm text-gray-600">
                {move || i.t(
                    "Dibuja un polígono en el mapa o carga uno desde un archivo KML para consultar los árboles que contiene.",
                    "Draw a polygon on the map or load one from a KML file to query the trees inside it.",
                )}
            </p>
            {if drawing {
                view! {
                    <div class="rounded-md bg-amber-50 border border-amber-200 px-3 py-2 text-sm text-amber-900 mb-3">
                        <p>{move || i.t(
                            "Haz clic en el mapa para marcar cada vértice. Doble clic o «Terminar» cierra el polígono.",
                            "Click on the map to place each vertex. Double-click or “Finish” closes the polygon.",
                        )}</p>
                        <p class="mt-1 font-medium">{vertices}{move || i.t(" vértices", " vertices")}</p>
                    </div>
                    <div class="flex flex-wrap gap-2">
                        <button type="button" class=format!("{BTN} {BTN_PRIMARY}") disabled=vertices < 3
                            on:click=move |_| tools.finish_drawing()>
                            {move || i.t("Terminar", "Finish")}
                        </button>
                        <button type="button" class=format!("{BTN} {BTN_SECONDARY}") disabled=vertices == 0
                            on:click=move |_| tools.draft.update(|d| { if let Some(v) = d { v.pop(); } })>
                            {move || i.t("Deshacer vértice", "Undo vertex")}
                        </button>
                        <button type="button" class=format!("{BTN} {BTN_SECONDARY}") on:click=move |_| tools.draft.set(None)>
                            {move || i.t("Cancelar", "Cancel")}
                        </button>
                    </div>
                }
                .into_any()
            } else {
                view! {
                    <div class="flex flex-wrap gap-2">
                        <button type="button" class=format!("{BTN} {BTN_PRIMARY}")
                            on:click=move |_| { problem.set(None); tools.draft.set(Some(Vec::new())); }>
                            {icon(ICON_PENCIL, "h-4 w-4")}
                            {move || i.t("Dibujar polígono", "Draw polygon")}
                        </button>
                        <button type="button" class=format!("{BTN} {BTN_SECONDARY}")
                            on:click=move |_| { if let Some(input) = file_ref.get() { input.click(); } }>
                            {icon(ICON_UPLOAD, "h-4 w-4")}
                            {move || i.t("Cargar KML", "Load KML")}
                        </button>
                    </div>
                }
                .into_any()
            }}
            <div class="mt-3">{zone_card}</div>
            {move || (tools.zone.with(Option::is_some) && !filters.values().is_empty()).then(|| view! {
                <p class="mt-2 text-xs text-gray-500">{move || i.t(
                    "La consulta también aplica los filtros activos.",
                    "The query also applies the active filters.",
                )}</p>
            })}
        }
    };

    // ---- Filters panel ----
    let hood_options = move || {
        let comuna = filters.comuna.get();
        places.with(|p| {
            p.neighborhoods
                .iter()
                .filter(|(_, _, c)| comuna.is_none_or(|sel| sel == *c))
                .map(|(id, name, _)| view! { <option value=id.to_string()>{name.clone()}</option> })
                .collect_view()
        })
    };
    let comuna_options = move || {
        places.with(|p| {
            p.comunas
                .iter()
                .map(|(id, name)| view! { <option value=id.to_string()>{comuna_name(name)}</option> })
                .collect_view()
        })
    };
    let parse_id = |s: String| s.parse::<i64>().ok();
    let text_input = move |label: (&'static str, &'static str), sig: RwSignal<String>, placeholder: (&'static str, &'static str), numeric: bool| {
        view! {
            <label class="block">
                <span class=LABEL>{move || i.t(label.0, label.1)}</span>
                <input type="text" class=INPUT
                    inputmode=if numeric { "numeric" } else { "text" }
                    placeholder=move || i.t(placeholder.0, placeholder.1)
                    prop:value=move || sig.get()
                    on:input=move |ev| sig.set(event_target_value(&ev)) />
            </label>
        }
    };

    let filters_panel = move || {
        view! {
            <form class="space-y-3" on:submit=move |ev| { ev.prevent_default(); run(); }>
                {text_input(("Código del árbol", "Tree code"), filters.code, ("Ej.: 1922", "E.g. 1922"), true)}
                {text_input(("Nombre científico", "Scientific name"), filters.scientific, ("Ej.: Tabebuia rosea", "E.g. Tabebuia rosea"), false)}
                {text_input(("Nombre común", "Common name"), filters.common, ("Ej.: Ocobo", "E.g. Ocobo"), false)}
                <div class="grid grid-cols-2 gap-3">
                    <label class="block">
                        <span class=LABEL>{move || i.t("Comuna", "Comuna")}</span>
                        <select class=INPUT
                            prop:value=move || filters.comuna.get().map(|c| c.to_string()).unwrap_or_default()
                            on:change=move |ev| {
                                filters.comuna.set(parse_id(event_target_value(&ev)));
                                filters.neighborhood.set(None);
                            }>
                            <option value="">{move || i.t("Todas", "All")}</option>
                            {comuna_options}
                        </select>
                    </label>
                    <label class="block">
                        <span class=LABEL>{move || i.t("Barrio", "Barrio")}</span>
                        <select class=INPUT
                            prop:value=move || filters.neighborhood.get().map(|c| c.to_string()).unwrap_or_default()
                            on:change=move |ev| filters.neighborhood.set(parse_id(event_target_value(&ev)))>
                            <option value="">{move || i.t("Todos", "All")}</option>
                            {hood_options}
                        </select>
                    </label>
                </div>
                {move || tools.zone.with(Option::is_some).then(|| view! {
                    <div>
                        <p class="text-xs text-gray-500 mb-1">{move || i.t("Se combina con la zona de interés:", "Combined with the area of interest:")}</p>
                        {zone_card}
                    </div>
                })}
                <div class="flex gap-2 pt-1">
                    <button type="submit" class=format!("{BTN} {BTN_PRIMARY}") disabled=move || loading.get()>
                        {move || i.t("Consultar", "Search")}
                    </button>
                    <button type="button" class=format!("{BTN} {BTN_SECONDARY}") on:click=move |_| filters.clear()>
                        {move || i.t("Limpiar filtros", "Clear filters")}
                    </button>
                </div>
            </form>
        }
    };

    let panel = move || {
        open.get().map(|which| {
            let title = move || match which {
                Panel::Layers => i.t("Capas", "Layers"),
                Panel::Filters => i.t("Filtros", "Filters"),
            };
            view! {
                <div id=PANEL_ID class="pointer-events-auto mb-3 w-[23rem] max-w-[calc(100vw-2rem)] max-h-[60vh] overflow-y-auto rounded-lg border border-gray-200 bg-white p-4 shadow-xl"
                    role="dialog" aria-label=title>
                    <div class="flex items-center justify-between mb-3">
                        <h2 class="text-base font-semibold text-gray-800">{title}</h2>
                        <button type="button" class="rounded p-1 text-gray-500 hover:bg-gray-100 hover:text-gray-700"
                            aria-label=move || i.t("Cerrar", "Close") on:click=move |_| open.set(None)>
                            {icon(ICON_CLOSE, "h-5 w-5")}
                        </button>
                    </div>
                    {match which {
                        Panel::Layers => layers_panel.into_any(),
                        Panel::Filters => filters_panel().into_any(),
                    }}
                    {result_box}
                </div>
            }
        })
    };

    let tool_button = move |which: Panel, path: &'static str, label: (&'static str, &'static str)| {
        view! {
            <button type="button"
                class=move || format!(
                    "flex items-center gap-2 rounded-full px-4 py-2 text-sm font-medium transition-colors {}",
                    if open.get() == Some(which) { "bg-primary-700 text-white" } else { "text-gray-700 hover:bg-primary-50" }
                )
                aria-pressed=move || (open.get() == Some(which)).to_string()
                on:click=move |_| open.update(|o| *o = if *o == Some(which) { None } else { Some(which) })>
                {icon(path, "h-5 w-5")}
                {move || i.t(label.0, label.1)}
            </button>
        }
    };

    view! {
        <div class="pointer-events-none absolute bottom-6 left-1/2 z-[1001] flex -translate-x-1/2 flex-col items-center">
            {panel}
            <input node_ref=file_ref type="file" class="hidden" accept=".kml,.kmz,application/vnd.google-earth.kml+xml" on:change=on_file />
            <div class="pointer-events-auto flex gap-1 rounded-full border border-gray-200 bg-white/95 p-1.5 shadow-lg">
                {tool_button(Panel::Layers, ICON_LAYERS, ("Capas", "Layers"))}
                {tool_button(Panel::Filters, ICON_FILTER, ("Filtros", "Filters"))}
            </div>
        </div>
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn body_combines_filters_and_area() {
        let f = FilterValues {
            code: " 1922 ".into(),
            scientific: " tabebuia ".into(),
            common: String::new(),
            comuna: Some(10),
            neighborhood: None,
        };
        let zone = json!({ "type": "Polygon", "coordinates": [] });
        let body = f.body(Some(&zone), "xlsx", Lang::Es).unwrap();
        assert_eq!(
            body,
            json!({ "format": "xlsx", "lang": "es", "id": 1922, "scientific_name": "tabebuia", "comuna": 10, "geometry": zone })
        );
        assert!(!f.is_empty());
        assert!(FilterValues::default().is_empty());
        assert_eq!(FilterValues::default().body(None, "json", Lang::En).unwrap(), json!({ "format": "json", "lang": "en" }));
    }

    #[test]
    fn bad_code() {
        for code in ["abc", "-3", "0", "1.5"] {
            let f = FilterValues { code: code.into(), ..Default::default() };
            assert_eq!(f.body(None, "json", Lang::Es), Err(BodyError::BadCode));
        }
    }

    #[test]
    fn drawn_polygon_is_closed_lon_lat() {
        let z = drawn_zone(&[[4.0, -75.0], [4.0, -74.9], [4.1, -74.9]]);
        assert_eq!(z.vertices, 3);
        assert_eq!(z.geometry["coordinates"][0], json!([[-75.0, 4.0], [-74.9, 4.0], [-74.9, 4.1], [-75.0, 4.0]]));
    }

    #[test]
    fn result_from_json() {
        let r = QueryResult::from_json(&json!({
            "count": 3, "points": [[7, 4.4, -75.2]], "truncated": true, "bbox": [-75.2, 4.4, -75.2, 4.4]
        }))
        .unwrap();
        assert_eq!(r.points, vec![(7, 4.4, -75.2)]);
        assert!(r.truncated);
        assert_eq!(r.bbox, Some([-75.2, 4.4, -75.2, 4.4]));
    }

    #[test]
    fn comuna_names() {
        assert_eq!(comuna_name("COMUNA 7"), "Comuna 7");
        assert_eq!(comuna_name(""), "");
    }
}
