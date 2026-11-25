//! Map page: Leaflet map with zoom-dependent layers (comunas < 17, barrios 17-18,
//! tree points >= 19) and a side panel with statistics. Clicking a tree point replaces the
//! statistics with that tree's sheet (`tree_panel::TreePanel`) and highlights the point.
//! The toolbar at the bottom (`map_tools`) queries trees by filters and area of interest;
//! this page draws its area, the polygon being drawn and the matching trees.
//!
//! KNOWN ISSUES (inherited behaviour, kept until decided; marked `KNOWN ISSUE:` below):
//!
//! Barrios (zoom 17-18) and tree points (zoom >= 19) are loaded for the visible area only,
//! once per `moveend` (Leaflet also fires it after every zoom). Barrios are kept once drawn;
//! points are replaced on every move and stale responses are dropped.
//!  - panel fallbacks use JS `||`, so missing stats show hardcoded city-wide numbers. Tree
//!    count, species count, average height, carbon stock and intercepted rain come from
//!    `/places/*/statistics/`; the tree-per-capita index is still a placeholder.
//!  - no cleanup of the Leaflet map / listeners when leaving the route.

use std::cell::{Cell, RefCell};
use std::collections::{HashMap, HashSet};
use std::rc::Rc;

use futures::future::try_join_all;
use js_sys::{Object, Reflect};
use leptos::prelude::*;
use leptos::task::spawn_local;
use serde_json::{Value, json};
use wasm_bindgen::prelude::*;
use wasm_bindgen::JsCast;

use crate::api::{API_BASE, console_error, fmt_thousands, get_json, js_or, js_string, truthy};
use crate::i18n::{I18n, Lang, pick};
use crate::interop::leaflet::{self as L, LMap, Layer};
use crate::interop::{to_js, when_connected};

use super::map_tools::{MapToolbar, PANEL_ID, QueryResult, ToolSignals, Zone};
use super::tree_panel::{TreePanel, TreeRecord};

#[derive(Clone)]
struct Region {
    name: String,
    statistics: Value,
}

/// Tree point styles: normal and selected (larger, light green, drawn on top).
const POINT_STYLE: &str = r##"{"radius": 5, "color": "#000000", "weight": 1, "fillColor": "#006400", "fillOpacity": 0.6}"##;
const SELECTED_STYLE: &str = r##"{"color": "#14532D", "weight": 2, "fillColor": "#4ADE80", "fillOpacity": 1}"##;
const SELECTED_RADIUS: f64 = 12.0;

/// The highlighted point (record id + its Leaflet marker). Local storage: `Layer` is a JS
/// object and not `Send`.
type Highlight = StoredValue<Option<(i64, Layer)>, LocalStorage>;

fn style(json_str: &str) -> JsValue {
    to_js(&serde_json::from_str::<Value>(json_str).unwrap_or_default())
}

fn highlight(h: Highlight, id: i64, marker: &Layer) {
    unhighlight(h);
    marker.set_style(&style(SELECTED_STYLE));
    marker.set_radius(SELECTED_RADIUS);
    marker.bring_to_front();
    h.set_value(Some((id, marker.clone())));
}

fn unhighlight(h: Highlight) {
    if let Some((_, m)) = h.try_update_value(Option::take).flatten() {
        m.set_style(&style(POINT_STYLE));
        m.set_radius(5.0);
    }
}

// ---------------------------------------------------------------------------
// Tree statistics (count, species, average height) per comuna / barrio
// ---------------------------------------------------------------------------

const OVERVIEW: &str = "Ibagué Overview";

/// API entry -> the panel's `statistics` shape. `healthIndex` keeps its previous
/// placeholder (`fallback_health`); the rest is computed by the backend.
fn panel_stats(s: &Value, fallback_health: Value) -> Value {
    json!({
        "totalTrees": fmt_thousands(s["total_trees"].as_i64().unwrap_or(0)),
        "speciesCount": s["species_count"].as_i64().unwrap_or(0).to_string(),
        "avgHeight": s["avg_height_m"].as_f64().map(|h| format!("{h:.2}")).unwrap_or_else(|| "N/A".into()),
        "healthIndex": fallback_health,
        "carbonStock": s["carbon_t"].as_f64().map(fmt_amount).unwrap_or_else(|| "N/A".into()),
        "rainInterception": s["rain_interception_m3"].as_f64().map(fmt_amount).unwrap_or_else(|| "N/A".into()),
    })
}

/// Thousands separator for large amounts, one decimal below 100 (a barrio's few t C).
fn fmt_amount(v: f64) -> String {
    if v.abs() < 100.0 {
        format!("{v:.1}")
    } else {
        fmt_thousands(v.round() as i64)
    }
}

/// Panel statistics when a region has none.
fn missing_stats() -> Value {
    json!({ "totalTrees": "N/A", "speciesCount": "N/A", "avgHeight": "N/A", "healthIndex": "N/A",
            "carbonStock": "N/A", "rainInterception": "N/A" })
}

/// `{id: panel statistics}` + city-wide totals from `/places/<kind>/statistics/`.
/// Failures are logged and leave the map without counts (labels then read "N/A").
async fn load_statistics(kind: &str) -> (HashMap<i64, Value>, Option<Value>) {
    let url = format!("{API_BASE}/api/v1/places/{kind}/statistics/");
    match get_json(&url).await {
        Ok(data) => {
            let by_id = data["results"]
                .as_array()
                .into_iter()
                .flatten()
                .filter_map(|r| Some((r["id"].as_i64()?, panel_stats(r, json!("N/A")))))
                .collect();
            (by_id, data.get("overall").cloned())
        }
        Err(e) => {
            console_error(&format!("Error loading {kind} statistics:"), &e);
            (HashMap::new(), None)
        }
    }
}

/// `"8.14" + "m"` -> `"8.14 m"`; `"N/A"` stays without a unit (and is shown as "N/D" in
/// Spanish).
fn with_unit(l: Lang, value: String, unit: &str) -> String {
    if value == "N/A" { na(l, value) } else { format!("{value} {unit}") }
}

/// The panel keeps "N/A" as its "no data" marker; this is how it reads on screen.
fn na(l: Lang, value: String) -> String {
    if value == "N/A" { pick(l, "N/D", "N/A").into() } else { value }
}

fn escape_html(s: &str) -> String {
    s.replace('&', "&amp;").replace('<', "&lt;").replace('>', "&gt;")
}

/// Manually tuned label positions per comuna id.
fn comuna_coords(id: i64) -> Option<(f64, f64)> {
    match id {
        1 => Some((4.444155773015618, -75.23969864493603)),
        3 => Some((4.44314777205183, -75.2229990060045)),
        5 => Some((4.4414122157367455, -75.19866063473717)),
        6 => Some((4.448946582667143, -75.19216298371211)),
        7 => Some((4.447054612850441, -75.15486397564855)),
        8 => Some((4.439440632646043, -75.17641129077383)),
        9 => Some((4.43193067187494, -75.1956365655411)),
        11 => Some((4.428197280276076, -75.2300237422717)),
        12 => Some((4.429748394627603, -75.24106640852413)),
        _ => None,
    }
}

/// Leaflet objects shared by the map callbacks.
struct MapState {
    map: LMap,
    shown_labels: RefCell<HashSet<String>>,
    point_layer: Layer,
    locality_layer: Layer,
    neighborhood_layer: Layer,
    locality_labels: Layer,
    neighborhood_labels: Layer,
    /// Barrios already drawn (sent as `exclude` so their geometry is not downloaded again).
    loaded_neighborhoods: RefCell<HashSet<i64>>,
    /// Sequence number of the latest point request; older responses are ignored.
    point_seq: Cell<u64>,
    selected_region: RwSignal<Region>,
    selected_tree: RwSignal<Option<TreeRecord>>,
    highlight: Highlight,
    tools: ToolSignals,
    /// Area of interest, polygon being drawn (pane `zone`) and query result (pane `results`,
    /// drawn on a canvas: up to 20,000 points).
    zone_layer: Layer,
    draft_layer: Layer,
    result_layer: Layer,
    result_renderer: JsValue,
}

#[component]
pub fn MapPage() -> impl IntoView {
    let selected_region = RwSignal::new(Region {
        name: OVERVIEW.into(),
        statistics: json!({ "totalTrees": 0, "speciesCount": 0, "avgHeight": 0, "healthIndex": 0 }),
    });
    let selected_tree = RwSignal::new(None::<TreeRecord>);
    let highlight: Highlight = StoredValue::new_local(None);
    let tools = ToolSignals::new();
    // The Leaflet side, once created (for the Effects that draw the toolbar's state).
    let map_state: StoredValue<Option<Rc<MapState>>, LocalStorage> = StoredValue::new_local(None);
    let map_ready = RwSignal::new(false);

    // Closing the tree sheet (or clicking a region) un-highlights the point.
    Effect::new(move |_| {
        if selected_tree.with(Option::is_none) {
            unhighlight(highlight);
        }
    });

    // On client-side navigation leptos_router builds the route view asynchronously, so an
    // Effect can run before `<div id="map">` is attached to the document. Wait for the
    // NodeRef, then for the element to be connected, before creating the Leaflet map.
    let map_ref = NodeRef::<leptos::html::Div>::new();
    Effect::new(move |_| {
        if let Some(el) = map_ref.get() {
            let container: web_sys::HtmlElement = el.into();
            let c = container.clone();
            when_connected(container, move || {
                if let Some(st) = init_map(&c, selected_region, selected_tree, highlight, tools) {
                    map_state.try_update_value(|s| *s = Some(st));
                    map_ready.try_set(true);
                }
            });
        }
    });

    // Draw the toolbar's state. Each Effect also tracks `map_ready`, so what was set before
    // the map existed is drawn once it does.
    let with_map = move |f: &dyn Fn(&MapState)| {
        if map_ready.get() {
            map_state.with_value(|s| {
                if let Some(s) = s {
                    f(s);
                }
            });
        }
    };
    Effect::new(move |_| {
        let zone = tools.zone.get();
        with_map(&|st| draw_zone(st, zone.as_ref()));
    });
    Effect::new(move |_| {
        let draft = tools.draft.get();
        with_map(&|st| draw_draft(st, draft.as_deref()));
    });
    Effect::new(move |_| {
        let result = tools.result.get();
        with_map(&|st| draw_result(st, result.as_ref()));
    });

    let i = I18n::use_ctx();
    let name = move || {
        let n = selected_region.with(|r| js_or(&json!(r.name), OVERVIEW));
        if n == OVERVIEW { i.t("Resumen de Ibagué", "Ibagué Overview").to_string() } else { n }
    };
    let stat = move |k: &'static str, fb: &'static str| {
        move || na(i.lang(), selected_region.with(|r| js_or(&r.statistics[k], fb)))
    };

    // Region / city summary, shown while no tree is selected.
    let summary = move || {
        view! {
            <div class="grid grid-cols-1 gap-6">
                <div>
                    <h2 class="text-2xl font-bold text-gray-800 mb-4">{name}</h2>
                    <div class="space-y-4">
                        <h3 class="text-lg font-semibold text-gray-700">{move || i.t("Estadísticas de árboles", "Tree Statistics")}</h3>
                        <div class="grid grid-cols-2 gap-x-8 gap-y-4">
                            <div>
                                <p class="text-2xl font-bold text-green-700">{stat("totalTrees", "101,283")}</p>
                                <p class="text-sm text-gray-600">{move || i.t("Total de árboles", "Total Trees")}</p>
                            </div>
                            <div>
                                <p class="text-2xl font-bold text-green-700">{stat("speciesCount", "407")}</p>
                                <p class="text-sm text-gray-600">{move || i.t("Número de especies", "Species Count")}</p>
                            </div>
                            <div>
                                <p class="text-2xl font-bold text-green-700">{move || with_unit(i.lang(), stat("avgHeight", "17.30")(), "m")}</p>
                                <p class="text-sm text-gray-600">{move || i.t("Altura promedio", "Average Height")}</p>
                            </div>
                            <div>
                                <p class="text-2xl font-bold text-green-700">{stat("healthIndex", "0.18")}</p>
                                <p class="text-sm text-gray-600">{move || i.t("Índice de árboles por habitante", "Tree-per-capita index")}</p>
                            </div>
                        </div>
                    </div>
                </div>
                <div>
                    <h3 class="text-lg font-semibold text-gray-700 mb-4">{move || i.t("Servicios ecosistémicos", "Ecosystem Services")}</h3>
                    <div class="space-y-4">
                        <div>
                            <p class="text-2xl font-bold text-green-700">{move || with_unit(i.lang(), stat("carbonStock", "N/A")(), "t C")}</p>
                            <p class="text-sm text-gray-600">{move || i.t("Carbono almacenado", "Stored carbon")}</p>
                        </div>
                        <div>
                            <p class="text-2xl font-bold text-green-700">{move || with_unit(i.lang(), stat("rainInterception", "N/A")(), i.t("m³/año", "m³/year"))}</p>
                            <p class="text-sm text-gray-600">{move || i.t("Lluvia interceptada", "Intercepted rain")}</p>
                        </div>
                        <p class="text-xs text-gray-400">{move || i.t(
                            "Carbono: acumulado en la vida de los árboles. Lluvia: cota inferior (lo que retienen las copas, sin la evaporación durante el aguacero).",
                            "Carbon: accumulated over the trees' lives. Rain: lower bound (what the crowns hold, without evaporation during the storm).",
                        )}</p>
                    </div>
                </div>
            </div>
        }
    };

    view! {
        <div style="display: block; width: 100%; height: 100%;">
            <div class="flex flex-row h-full gap-4">
                <div class="bg-white rounded-lg shadow-lg border border-gray-200 p-4 w-[16rem] shrink-0 overflow-y-auto">
                    {move || match selected_tree.get() {
                        Some(tree) => view! {
                            <TreePanel tree on_close=Callback::new(move |_| selected_tree.set(None)) />
                        }
                        .into_any(),
                        None => summary().into_any(),
                    }}
                </div>
                <div class="relative flex-1 min-h-[500px]">
                    <div node_ref=map_ref id="map" class="absolute inset-0 rounded-lg shadow-lg border border-gray-200"></div>
                    <MapToolbar tools />
                </div>
            </div>
        </div>
    }
}

// ---------------------------------------------------------------------------
// Leaflet logic
// ---------------------------------------------------------------------------

/// Wrap a Rust closure as a JS function. Leaked on purpose: Leaflet keeps the handlers
/// for the map's lifetime (KNOWN ISSUE: they are never unregistered).
fn js_fn1(f: impl FnMut(JsValue) + 'static) -> JsValue {
    Closure::<dyn FnMut(JsValue)>::new(f).into_js_value()
}

fn set(obj: &Object, key: &str, val: &JsValue) {
    let _ = Reflect::set(obj, &key.into(), val);
}

fn event_target(e: &JsValue) -> Layer {
    Reflect::get(e, &"target".into())
        .unwrap_or(JsValue::UNDEFINED)
        .unchecked_into()
}

fn init_map(
    container: &web_sys::HtmlElement,
    selected_region: RwSignal<Region>,
    selected_tree: RwSignal<Option<TreeRecord>>,
    highlight: Highlight,
    tools: ToolSignals,
) -> Option<Rc<MapState>> {
    let map = match L::map(container) {
        Ok(map) => map,
        Err(e) => {
            web_sys::console::error_2(&"Error initializing map:".into(), &e);
            return None;
        }
    };
    map.set_view(&to_js(&json!([4.4389, -75.2322])), 14.0);

    // OSM publishes tiles up to zoom 19. `maxNativeZoom` makes Leaflet upscale the z19 tiles
    // for zooms 20-23 (where the tree points are) instead of requesting tiles that do not
    // exist. A tile that really fails to load is left empty.
    L::tile_layer(
        "https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png",
        &to_js(&json!({
            "maxZoom": 23,
            "maxNativeZoom": 19,
            "attribution": "© OpenStreetMap contributors",
            "keepBuffer": 10
        })),
    )
    .add_to(&map);

    // Above the comunas / barrios (overlayPane, 400) and below the markers (600). Not
    // clickable: clicks reach the layers underneath (and the map, while drawing).
    for (pane, z) in [("zone", "440"), ("results", "450")] {
        let style = map.create_pane(pane).style();
        let _ = style.set_property("z-index", z);
        let _ = style.set_property("pointer-events", "none");
    }
    let zone_layer = L::feature_group();
    let draft_layer = L::layer_group();
    let result_layer = L::layer_group();
    for layer in [&zone_layer, &draft_layer, &result_layer] {
        layer.add_to(&map);
    }

    let st = Rc::new(MapState {
        map,
        shown_labels: RefCell::new(HashSet::new()),
        point_layer: L::layer_group(),
        locality_layer: L::feature_group(),
        neighborhood_layer: L::feature_group(),
        locality_labels: L::layer_group(),
        neighborhood_labels: L::layer_group(),
        loaded_neighborhoods: RefCell::new(HashSet::new()),
        point_seq: Cell::new(0),
        selected_region,
        selected_tree,
        highlight,
        tools,
        zone_layer,
        draft_layer,
        result_layer,
        result_renderer: L::canvas(&to_js(&json!({ "pane": "results" }))),
    });

    load_localities(st.clone());

    // Drawing the area of interest: each click adds a vertex, a double click closes it.
    st.map.on(
        "click",
        &js_fn1(move |e| {
            if tools.is_drawing() {
                let latlng = Reflect::get(&e, &"latlng".into()).unwrap_or(JsValue::UNDEFINED);
                let coord = |k: &str| Reflect::get(&latlng, &k.into()).ok().and_then(|v| v.as_f64());
                if let (Some(lat), Some(lng)) = (coord("lat"), coord("lng")) {
                    tools.add_vertex(lat, lng);
                }
            }
        }),
    );
    st.map.on(
        "dblclick",
        &js_fn1(move |_| {
            if tools.is_drawing() {
                tools.finish_drawing();
            }
        }),
    );

    {
        let st = st.clone();
        st.clone().map.on("zoomend", &js_fn1(move |_| toggle_layers_by_zoom(&st)));
    }
    {
        let st = st.clone();
        st.clone().map.on(
            "moveend",
            &js_fn1(move |_| {
                load_neighborhoods_in_view(st.clone());
                load_points_by_zoom(st.clone());
            }),
        );
    }
    Some(st)
}

// ---------------------------------------------------------------------------
// Toolbar: area of interest, polygon being drawn, query result
// ---------------------------------------------------------------------------

const ZONE_STYLE: &str = r##"{"pane": "zone", "interactive": false, "color": "#1D4ED8", "weight": 3, "fillColor": "#3B82F6", "fillOpacity": 0.08}"##;
const DRAFT_LINE: &str = r##"{"pane": "zone", "interactive": false, "color": "#1D4ED8", "weight": 2, "dashArray": "6 6", "fillColor": "#3B82F6", "fillOpacity": 0.1}"##;
const DRAFT_VERTEX: &str = r##"{"pane": "zone", "interactive": false, "radius": 5, "color": "#1D4ED8", "weight": 2, "fillColor": "#FFFFFF", "fillOpacity": 1}"##;

fn draw_zone(st: &MapState, zone: Option<&Zone>) {
    st.zone_layer.clear_layers();
    let Some(zone) = zone else { return };
    let opts = Object::new();
    set(&opts, "style", &style(ZONE_STYLE));
    let layer = L::geo_json(&to_js(&zone.geometry), &opts);
    layer.add_to(&st.zone_layer);
    let bounds = layer.get_bounds();
    if bounds.is_valid() {
        fit_above_toolbar(st, &bounds, 19.0);
    }
}

/// Frame `bounds` in the part of the map not covered by the toolbar and its open panel
/// (bottom center), keeping at least 200 px of map.
fn fit_above_toolbar(st: &MapState, bounds: &L::LatLngBounds, max_zoom: f64) {
    let map_height = f64::from(st.map.get_container().client_height());
    let panel = web_sys::window()
        .and_then(|w| w.document())
        .and_then(|d| d.get_element_by_id(PANEL_ID))
        .map_or(0.0, |p| f64::from(p.client_height()) + 12.0);
    // Toolbar: 24 px from the bottom + ~50 px high, plus a margin.
    let bottom = (panel + 100.0).min((map_height - 200.0).max(60.0));
    st.map.fit_bounds(
        bounds,
        &to_js(&json!({ "paddingTopLeft": [40, 40], "paddingBottomRight": [40, bottom], "maxZoom": max_zoom })),
    );
}

/// Dashed outline (closed once there are three vertices) and a dot per vertex.
fn draw_draft(st: &MapState, draft: Option<&[[f64; 2]]>) {
    st.draft_layer.clear_layers();
    // While drawing, a double click closes the polygon instead of zooming, and the cursor
    // marks the drawing mode.
    let drawing = draft.is_some();
    toggle_map_handler(&st.map, "doubleClickZoom", !drawing);
    let css = st.map.get_container().style();
    let _ = if drawing { css.set_property("cursor", "crosshair") } else { css.remove_property("cursor").map(|_| ()) };

    let Some(vertices) = draft else { return };
    let latlngs = to_js(&json!(vertices));
    if vertices.len() >= 3 {
        L::polygon(&latlngs, &style(DRAFT_LINE)).add_to(&st.draft_layer);
    } else if vertices.len() == 2 {
        L::polyline(&latlngs, &style(DRAFT_LINE)).add_to(&st.draft_layer);
    }
    for [lat, lng] in vertices {
        L::circle_marker(&L::lat_lng(*lat, *lng), &style(DRAFT_VERTEX)).add_to(&st.draft_layer);
    }
}

/// `map.<handler>.enable()` / `.disable()` (e.g. `doubleClickZoom`).
fn toggle_map_handler(map: &LMap, handler: &str, enable: bool) {
    let Ok(h) = Reflect::get(map, &handler.into()) else { return };
    let method = if enable { "enable" } else { "disable" };
    if let Ok(f) = Reflect::get(&h, &method.into()).and_then(|f| f.dyn_into::<js_sys::Function>()) {
        let _ = f.call0(&h);
    }
}

/// The matching trees as amber dots; a single tree (a search by code) larger. Without an
/// area of interest the map moves to the result (the area already framed it otherwise).
fn draw_result(st: &MapState, result: Option<&QueryResult>) {
    st.result_layer.clear_layers();
    let Some(result) = result else { return };
    let single = result.count == 1;
    let opts = style(&json!({
        "pane": "results",
        "interactive": false,
        "radius": if single { 10 } else { 4 },
        "color": "#78350F",
        "weight": if single { 2 } else { 1 },
        "fillColor": "#FBBF24",
        "fillOpacity": 0.9
    }).to_string());
    set(opts.unchecked_ref(), "renderer", &st.result_renderer);
    for (_, lat, lon) in &result.points {
        L::circle_marker(&L::lat_lng(*lat, *lon), &opts).add_to(&st.result_layer);
    }
    let framed_by_zone = st.tools.zone.with_untracked(Option::is_some);
    if let (Some([w, s, e, n]), false) = (result.bbox, framed_by_zone) {
        let bounds = L::lat_lng_bounds(&to_js(&json!([[s, w], [n, e]])));
        fit_above_toolbar(st, &bounds, 20.0);
    }
}

fn load_localities(st: Rc<MapState>) {
    spawn_local(async move {
        let requests = (1..=13)
            .map(|id| format!("{API_BASE}/api/v1/places/localities/{id}/"))
            .collect::<Vec<_>>();
        // KNOWN ISSUE: all-or-nothing, one failed request discards every comuna.
        let (result, (stats, overall)) = futures::join!(
            try_join_all(requests.iter().map(|u| get_json(u))),
            load_statistics("localities"),
        );

        // City-wide totals for the default panel (only while it is still showing).
        if let Some(overall) = overall {
            st.selected_region.try_update(|r| {
                if r.name == OVERVIEW {
                    // healthIndex 0 keeps the panel's tree-per-capita placeholder.
                    r.statistics = panel_stats(&overall, json!(0));
                }
            });
        }

        let responses = match result {
            Ok(r) => r,
            Err(e) => return console_error("Error loading communes:", &e),
        };

        st.shown_labels.borrow_mut().clear();
        st.locality_labels.clear_layers();

        for data in responses {
            if !truthy(&data["boundary"]["coordinates"]) {
                continue;
            }

            let name = if truthy(&data["name"]) {
                js_string(Some(&data["name"]))
            } else {
                format!("Comuna {}", js_string(data.get("id")))
            };
            let statistics = data["id"]
                .as_i64()
                .and_then(|id| stats.get(&id).cloned())
                .unwrap_or_else(|| json!({}));

            let feature = json!({
                "type": "Feature",
                "geometry": data["boundary"],
                "properties": { "name": name, "statistics": statistics }
            });

            let on_each_feature = {
                let st = st.clone();
                let data = data.clone();
                let props = feature["properties"].clone();
                Closure::<dyn FnMut(JsValue, JsValue)>::new(move |_feature: JsValue, layer: JsValue| {
                    on_each_locality(&st, &data, &props, layer.unchecked_into());
                })
                .into_js_value()
            };

            let opts = Object::new();
            set(&opts, "style", &to_js(&json!({
                "color": "#ffffff",
                "weight": 1,
                "fillColor": "#2F7B3D",
                "fillOpacity": 0.5
            })));
            set(&opts, "onEachFeature", &on_each_feature);

            let geo_layer = L::geo_json(&to_js(&feature), &opts);
            geo_layer.add_to(&st.locality_layer);
        }

        st.locality_layer.add_to(&st.map);
        st.locality_labels.add_to(&st.map);
    });
}

/// Body of the `onEachFeature` callback for comunas.
fn on_each_locality(st: &Rc<MapState>, data: &Value, props: &Value, layer: Layer) {
    let comuna = js_or(&props["name"], "Unknown Region");

    if !st.shown_labels.borrow().contains(&comuna) {
        let center = match data["id"].as_i64().and_then(comuna_coords) {
            Some((lat, lng)) => L::lat_lng(lat, lng),
            None => {
                let bounds = layer.get_bounds();
                if !bounds.is_valid() {
                    // KNOWN ISSUE: this `return` exits the whole callback, so the hover/click
                    // handlers below are never registered for this comuna.
                    return;
                }
                bounds.get_center()
            }
        };

        let stats_html = if truthy(&props["statistics"]) {
            format!(
                r#"<div class="statistics">{}</div>"#,
                js_or(&props["statistics"]["totalTrees"], "N/A")
            )
        } else {
            String::new()
        };
        let icon = L::div_icon(&to_js(&json!({
            "className": "region-label",
            "html": format!(r#"<div class="label-content"><div class="region-name">{comuna}</div>{stats_html}</div>"#),
            "iconSize": [200, 50],
            "iconAnchor": [100, 25]
        })));

        let marker_opts = Object::new();
        set(&marker_opts, "icon", &icon);
        set(&marker_opts, "interactive", &JsValue::FALSE);
        let marker = L::marker(&center, &marker_opts);

        st.locality_labels.add_child(&marker);
        st.shown_labels.borrow_mut().insert(comuna.clone());
    }

    layer.on("mouseover", &js_fn1(|e| {
        event_target(&e).set_style(&to_js(&json!({ "fillOpacity": 0.7 })));
    }));
    layer.on("mouseout", &js_fn1(|e| {
        event_target(&e).set_style(&to_js(&json!({ "fillOpacity": 0.5 })));
    }));

    let st = st.clone();
    let props = props.clone();
    layer.on("click", &js_fn1(move |e| {
        // While drawing, clicks only add vertices (the map's own handler).
        if st.tools.is_drawing() {
            return;
        }
        let l = event_target(&e);
        let bounds = l.get_bounds();
        st.map.fit_bounds(&bounds, &to_js(&json!({ "padding": [10, 10], "maxZoom": 16 })));

        let statistics = if truthy(&props["statistics"]) { props["statistics"].clone() } else { missing_stats() };
        st.selected_region.try_set(Region { name: comuna.clone(), statistics });
        st.selected_tree.try_set(None);
    }));
}

/// Fetch the barrios intersecting the visible area (plus a margin, so small pans need no
/// request) that are not drawn yet, with their statistics, in one request.
fn load_neighborhoods_in_view(st: Rc<MapState>) {
    let zoom = st.map.get_zoom();
    if !(17.0..19.0).contains(&zoom) {
        return;
    }
    let b = st.map.get_bounds().pad(0.25);
    let exclude = {
        let mut ids: Vec<i64> = st.loaded_neighborhoods.borrow().iter().copied().collect();
        ids.sort_unstable();
        ids.iter().map(i64::to_string).collect::<Vec<_>>().join(",")
    };
    let url = format!(
        "{API_BASE}/api/v1/places/neighborhoods/bbox/?min_lon={}&min_lat={}&max_lon={}&max_lat={}&exclude={exclude}",
        b.get_west(),
        b.get_south(),
        b.get_east(),
        b.get_north()
    );

    spawn_local(async move {
        let data = match get_json(&url).await {
            Ok(d) => d,
            Err(e) => return console_error("Error loading neighborhoods:", &e),
        };
        for n in data["results"].as_array().into_iter().flatten() {
            let Some(id) = n["id"].as_i64() else { continue };
            // Two overlapping requests may both return a barrio: draw it once.
            if !truthy(&n["boundary"]["coordinates"]) || !st.loaded_neighborhoods.borrow_mut().insert(id) {
                continue;
            }
            let name = if truthy(&n["name"]) { js_string(Some(&n["name"])) } else { format!("Barrio {id}") };
            let statistics = panel_stats(n, json!("N/A"));
            let feature = json!({
                "type": "Feature",
                "geometry": n["boundary"],
                "properties": { "name": name }
            });
            let geo_layer = L::geo_json(
                &to_js(&feature),
                &to_js(&json!({
                    "style": { "color": "#3333ff", "weight": 1, "fillColor": "#32CD32", "fillOpacity": 0.3 }
                })),
            );
            geo_layer.add_to(&st.neighborhood_layer);
            add_neighborhood_label(&st, &geo_layer, &name, Some(&statistics));
            on_neighborhood_events(&st, &geo_layer, name, Some(statistics));
        }
    });
}

/// "Name / tree count" label at the barrio's center (shown with the barrios, zoom 17-18).
fn add_neighborhood_label(st: &MapState, layer: &Layer, name: &str, statistics: Option<&Value>) {
    let bounds = layer.get_bounds();
    if !bounds.is_valid() {
        return;
    }
    let count = statistics.map(|s| js_or(&s["totalTrees"], "N/A")).unwrap_or_else(|| "N/A".into());
    let icon = L::div_icon(&to_js(&json!({
        "className": "region-label neighborhood-label",
        "html": format!(
            r#"<div class="label-content"><div class="region-name">{}</div><div class="statistics">{}</div></div>"#,
            escape_html(name),
            count
        ),
        "iconSize": [160, 40],
        "iconAnchor": [80, 20]
    })));
    let marker_opts = Object::new();
    set(&marker_opts, "icon", &icon);
    set(&marker_opts, "interactive", &JsValue::FALSE);
    st.neighborhood_labels.add_child(&L::marker(&bounds.get_center(), &marker_opts));
}

/// Hover highlight; click shows the barrio's statistics in the side panel.
fn on_neighborhood_events(st: &Rc<MapState>, layer: &Layer, name: String, statistics: Option<Value>) {
    layer.on("mouseover", &js_fn1(|e| {
        event_target(&e).set_style(&to_js(&json!({ "fillOpacity": 0.5 })));
    }));
    layer.on("mouseout", &js_fn1(|e| {
        event_target(&e).set_style(&to_js(&json!({ "fillOpacity": 0.3 })));
    }));

    let (region, tree, tools) = (st.selected_region, st.selected_tree, st.tools);
    layer.on("click", &js_fn1(move |_| {
        if tools.is_drawing() {
            return;
        }
        let statistics = statistics.clone().unwrap_or_else(missing_stats);
        region.try_set(Region { name: name.clone(), statistics });
        tree.try_set(None);
    }));
}

fn toggle_layers_by_zoom(st: &MapState) {
    let zoom = st.map.get_zoom();
    if zoom >= 19.0 {
        st.map.remove_layer(&st.locality_layer);
        st.map.remove_layer(&st.locality_labels);
        st.map.remove_layer(&st.neighborhood_layer);
        st.map.remove_layer(&st.neighborhood_labels);
    } else if zoom >= 17.0 {
        st.map.add_layer(&st.neighborhood_layer);
        st.map.add_layer(&st.neighborhood_labels);
        st.map.remove_layer(&st.locality_layer);
        st.map.remove_layer(&st.locality_labels);
    } else {
        st.map.add_layer(&st.locality_layer);
        st.map.add_layer(&st.locality_labels);
        st.map.remove_layer(&st.neighborhood_layer);
        st.map.remove_layer(&st.neighborhood_labels);
    }
}

fn load_points_by_zoom(st: Rc<MapState>) {
    let zoom = st.map.get_zoom();
    if zoom < 19.0 {
        st.map.remove_layer(&st.point_layer);
        return;
    }

    let seq = st.point_seq.get() + 1;
    st.point_seq.set(seq);
    let b = st.map.get_bounds();
    let url = format!(
        "{API_BASE}/api/v1/biodiversity/records/bbox/?min_lon={}&min_lat={}&max_lon={}&max_lat={}",
        b.get_west(),
        b.get_south(),
        b.get_east(),
        b.get_north()
    );

    spawn_local(async move {
        let data = match get_json(&url).await {
            Ok(d) => d,
            Err(e) => return console_error("Error loading points:", &e),
        };
        // The map moved again while this request was in flight.
        if st.point_seq.get() != seq || st.map.get_zoom() < 19.0 {
            return;
        }

        st.point_layer.clear_layers();

        let Some(records) = data.as_array() else {
            return console_error("Error loading points:", "response is not an array");
        };

        for record in records {
            if !(truthy(&record["latitude"]) && truthy(&record["longitude"])) {
                continue;
            }
            let marker = L::circle_marker(
                &to_js(&json!([record["latitude"], record["longitude"]])),
                &style(POINT_STYLE),
            );

            let Some(id) = record["id"].as_i64() else { continue };
            let text = |v: &Value| v.as_str().map(str::trim).filter(|s| !s.is_empty()).map(str::to_string);
            let tree = TreeRecord {
                id,
                common_name: text(&record["common_name"]),
                scientific_name: text(&record["species"]["scientific_name"]).unwrap_or_else(|| "N/A".into()),
                species_id: record["species"]["id"].as_i64(),
                life_form: text(&record["species"]["life_form"]).unwrap_or_default(),
                neighborhood: text(&record["neighborhood"]["name"]),
                site: text(&record["site"]["name"]),
            };

            // Points are rebuilt on every pan/zoom: keep the selected one highlighted.
            if st.selected_tree.with_untracked(|t| t.as_ref().map(|t| t.id)) == Some(id) {
                highlight(st.highlight, id, &marker);
            }

            let (selected_tree, h, m, tools) = (st.selected_tree, st.highlight, marker.clone(), st.tools);
            marker.on("click", &js_fn1(move |_| {
                if tools.is_drawing() {
                    return;
                }
                highlight(h, id, &m);
                selected_tree.try_set(Some(tree.clone()));
            }));

            marker.add_to(&st.point_layer);
        }

        st.point_layer.add_to(&st.map);
    });
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn thousands_separator() {
        assert_eq!(fmt_thousands(0), "0");
        assert_eq!(fmt_thousands(936), "936");
        assert_eq!(fmt_thousands(6646), "6,646");
        assert_eq!(fmt_thousands(101228), "101,228");
        assert_eq!(fmt_thousands(1234567), "1,234,567");
    }

    #[test]
    fn panel_stats_shape() {
        let s = panel_stats(&json!({"total_trees": 7759, "species_count": 240, "avg_height_m": 8.1}), json!("N/A"));
        assert_eq!(s["totalTrees"], "7,759");
        assert_eq!(s["speciesCount"], "240");
        assert_eq!(s["avgHeight"], "8.10");
        let empty = panel_stats(&json!({"total_trees": 0, "species_count": 0, "avg_height_m": null}), json!("N/A"));
        assert_eq!(empty["avgHeight"], "N/A");
        assert_eq!(empty["carbonStock"], "N/A");
        let services = panel_stats(&json!({"total_trees": 1, "carbon_t": 21081.9, "rain_interception_m3": 303101.0}), json!("N/A"));
        assert_eq!(services["carbonStock"], "21,082");
        assert_eq!(services["rainInterception"], "303,101");
        assert_eq!(panel_stats(&json!({"carbon_t": 12.34}), json!("N/A"))["carbonStock"], "12.3");
    }
}
