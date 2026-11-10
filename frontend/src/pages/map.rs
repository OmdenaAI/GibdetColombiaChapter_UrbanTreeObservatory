//! Map page: Leaflet map with zoom-dependent layers (comunas < 17, barrios 17-18,
//! tree points >= 19) and a side panel with statistics.
//!
//! KNOWN ISSUES (inherited behaviour, kept until decided; marked `KNOWN ISSUE:` below):
//!  - 687 neighborhood requests fired up-front with all-or-nothing semantics (the DB has 710).
//!  - points are requested on both `zoomend` and `moveend` (double request on zoom), with no
//!    cancellation of in-flight requests.
//!  - panel fallbacks use JS `||`, so 0 / missing stats show the hardcoded city-wide numbers
//!    (the API currently returns no `statistics`).
//!  - no cleanup of the Leaflet map / listeners when leaving the route.

use std::cell::RefCell;
use std::collections::HashSet;
use std::rc::Rc;

use futures::future::try_join_all;
use js_sys::{Object, Reflect};
use leptos::prelude::*;
use leptos::task::spawn_local;
use serde_json::{Value, json};
use wasm_bindgen::prelude::*;
use wasm_bindgen::JsCast;

use crate::api::{API_BASE, console_error, get_json, js_or, js_string, truthy};
use crate::interop::leaflet::{self as L, LMap, Layer};
use crate::interop::{to_js, when_connected};

#[derive(Clone)]
struct Region {
    name: String,
    statistics: Value,
    environmental: Value,
}

#[derive(Clone)]
struct SelectedTree {
    common_name: String,
    scientific_name: String,
    life_form: String,
    neighborhood: String,
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
    selected_region: RwSignal<Region>,
    selected_tree: RwSignal<Option<SelectedTree>>,
}

#[component]
pub fn MapPage() -> impl IntoView {
    let selected_region = RwSignal::new(Region {
        name: "Ibagué Overview".into(),
        statistics: json!({ "totalTrees": 0, "speciesCount": 0, "avgHeight": 0, "healthIndex": 0 }),
        environmental: json!({ "co2Absorption": 0, "oxygenProduction": 0 }),
    });
    let selected_tree = RwSignal::new(None::<SelectedTree>);

    // On client-side navigation leptos_router builds the route view asynchronously, so an
    // Effect can run before `<div id="map">` is attached to the document. Wait for the
    // NodeRef, then for the element to be connected, before creating the Leaflet map.
    let map_ref = NodeRef::<leptos::html::Div>::new();
    Effect::new(move |_| {
        if let Some(el) = map_ref.get() {
            let container: web_sys::HtmlElement = el.into();
            let c = container.clone();
            when_connected(container, move || init_map(&c, selected_region, selected_tree));
        }
    });

    let name = move || selected_region.with(|r| js_or(&json!(r.name), "Ibagué Overview"));
    let stat = move |k: &'static str, fb: &'static str| {
        move || selected_region.with(|r| js_or(&r.statistics[k], fb))
    };
    let env = move |k: &'static str, fb: &'static str| {
        move || selected_region.with(|r| js_or(&r.environmental[k], fb))
    };

    view! {
        <div style="display: block; width: 100%; height: 100%;">
            <div class="flex flex-row h-full gap-4">
                <div class="bg-white rounded-lg shadow-lg border border-gray-200 p-4 w-[16rem]">
                    <div class="grid grid-cols-1 gap-6">
                        <div>
                            <h2 class="text-2xl font-bold text-gray-800 mb-4">{name}</h2>
                            <div class="space-y-4">
                                <h3 class="text-lg font-semibold text-gray-700">"Tree Statistics"</h3>
                                <div class="grid grid-cols-2 gap-x-8 gap-y-4">
                                    <div>
                                        <p class="text-2xl font-bold text-green-700">{stat("totalTrees", "101,283")}</p>
                                        <p class="text-sm text-gray-600">"Total Trees"</p>
                                    </div>
                                    <div>
                                        <p class="text-2xl font-bold text-green-700">{stat("speciesCount", "407")}</p>
                                        <p class="text-sm text-gray-600">"Species Count"</p>
                                    </div>
                                    <div>
                                        <p class="text-2xl font-bold text-green-700">{move || format!("{} m", stat("avgHeight", "17.30")())}</p>
                                        <p class="text-sm text-gray-600">"Average Height"</p>
                                    </div>
                                    <div>
                                        <p class="text-2xl font-bold text-green-700">{stat("healthIndex", "0.18")}</p>
                                        <p class="text-sm text-gray-600">"Tree-per-capita index"</p>
                                    </div>
                                </div>
                            </div>
                        </div>
                        <div>
                            <h3 class="text-lg font-semibold text-gray-700 mb-4">"Environmental Impact"</h3>
                            <div class="space-y-4">
                                <div>
                                    <p class="text-2xl font-bold text-green-700">{move || format!("{} Ton", env("co2Absorption", "646,867.27")())}</p>
                                    <p class="text-sm text-gray-600">"CO₂ Absorption"</p>
                                </div>
                                <div>
                                    <p class="text-2xl font-bold text-green-700">{move || format!("{} Ton/year", env("oxygenProduction", "1,727,135.62")())}</p>
                                    <p class="text-sm text-gray-600">"Oxygen Production"</p>
                                </div>
                            </div>
                        </div>

                        {move || selected_tree.get().map(|t| view! {
                            <div class="mt-6 border-t pt-4">
                                <h3 class="text-lg font-semibold text-gray-700 mb-4">"Selected Tree"</h3>
                                <div class="space-y-2">
                                    <p><span class="font-semibold text-gray-700">"Common Name:"</span> {format!(" {}", t.common_name)}</p>
                                    <p><span class="font-semibold text-gray-700">"Scientific Name:"</span> " " <em>{t.scientific_name}</em></p>
                                    <p><span class="font-semibold text-gray-700">"Life Form:"</span> {format!(" {}", t.life_form)}</p>
                                    <p><span class="font-semibold text-gray-700">"Neighborhood:"</span> {format!(" {}", t.neighborhood)}</p>
                                </div>
                            </div>
                        })}
                    </div>
                </div>
                <div node_ref=map_ref id="map" class="flex-1 rounded-lg shadow-lg border border-gray-200 min-h-[500px]"></div>
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
    selected_tree: RwSignal<Option<SelectedTree>>,
) {
    let map = match L::map(container) {
        Ok(map) => map,
        Err(e) => return web_sys::console::error_2(&"Error initializing map:".into(), &e),
    };
    map.set_view(&to_js(&json!([4.4389, -75.2322])), 14.0);

    L::tile_layer(
        "https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png",
        &to_js(&json!({
            "maxZoom": 23,
            "attribution": "© OpenStreetMap contributors",
            "errorTileUrl": "https://upload.wikimedia.org/wikipedia/commons/a/ac/No_image_available.svg",
            "keepBuffer": 10
        })),
    )
    .add_to(&map);

    let st = Rc::new(MapState {
        map,
        shown_labels: RefCell::new(HashSet::new()),
        point_layer: L::layer_group(),
        locality_layer: L::feature_group(),
        neighborhood_layer: L::feature_group(),
        locality_labels: L::layer_group(),
        selected_region,
        selected_tree,
    });

    load_localities(st.clone());
    load_neighborhoods(st.clone());
    st.map.remove_layer(&st.neighborhood_layer);

    {
        let st = st.clone();
        st.clone().map.on(
            "zoomend",
            &js_fn1(move |_| {
                toggle_layers_by_zoom(&st);
                load_points_by_zoom(st.clone());
            }),
        );
    }
    {
        let st = st.clone();
        st.clone().map.on("moveend", &js_fn1(move |_| load_points_by_zoom(st.clone())));
    }
}

fn load_localities(st: Rc<MapState>) {
    spawn_local(async move {
        let requests = (1..=13)
            .map(|id| format!("{API_BASE}/api/v1/places/localities/{id}/"))
            .collect::<Vec<_>>();
        // KNOWN ISSUE: all-or-nothing, one failed request discards every comuna.
        let result = try_join_all(requests.iter().map(|u| get_json(u))).await;

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
            let statistics = if truthy(&data["statistics"]) { data["statistics"].clone() } else { json!({}) };
            let environmental = if truthy(&data["environmental"]) { data["environmental"].clone() } else { json!({}) };

            let feature = json!({
                "type": "Feature",
                "geometry": data["boundary"],
                "properties": { "name": name, "statistics": statistics, "environmental": environmental }
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
        let l = event_target(&e);
        let bounds = l.get_bounds();
        st.map.fit_bounds(&bounds, &to_js(&json!({ "padding": [10, 10], "maxZoom": 16 })));

        let statistics = if truthy(&props["statistics"]) {
            props["statistics"].clone()
        } else {
            json!({ "totalTrees": "N/A", "speciesCount": "N/A", "avgHeight": "N/A", "healthIndex": "N/A" })
        };
        let environmental = if truthy(&props["environmental"]) {
            props["environmental"].clone()
        } else {
            json!({ "co2Absorption": "N/A", "oxygenProduction": "N/A" })
        };
        st.selected_region.try_set(Region { name: comuna.clone(), statistics, environmental });
    }));
}

fn load_neighborhoods(st: Rc<MapState>) {
    spawn_local(async move {
        // KNOWN ISSUE: 687 parallel requests, all-or-nothing.
        let requests = (1..=687)
            .map(|id| format!("{API_BASE}/api/v1/places/neighborhoods/{id}/"))
            .collect::<Vec<_>>();
        let responses = match try_join_all(requests.iter().map(|u| get_json(u))).await {
            Ok(r) => r,
            Err(e) => return console_error("Error loading neighborhoods:", &e),
        };

        for data in responses {
            if !truthy(&data["boundary"]["coordinates"]) {
                continue;
            }
            let name = if truthy(&data["name"]) {
                js_string(Some(&data["name"]))
            } else {
                format!("Barrio {}", js_string(data.get("id")))
            };
            let feature = json!({
                "type": "Feature",
                "geometry": data["boundary"],
                "properties": { "name": name }
            });
            let geo_layer = L::geo_json(
                &to_js(&feature),
                &to_js(&json!({
                    "style": { "color": "#3333ff", "weight": 1, "fillColor": "#32CD32", "fillOpacity": 0.3 }
                })),
            );
            geo_layer.add_to(&st.neighborhood_layer);
        }
    });
}

fn toggle_layers_by_zoom(st: &MapState) {
    let zoom = st.map.get_zoom();
    if zoom >= 19.0 {
        st.map.remove_layer(&st.locality_layer);
        st.map.remove_layer(&st.locality_labels);
        st.map.remove_layer(&st.neighborhood_layer);
    } else if zoom >= 17.0 {
        st.map.add_layer(&st.neighborhood_layer);
        st.map.remove_layer(&st.locality_layer);
        st.map.remove_layer(&st.locality_labels);
    } else {
        st.map.add_layer(&st.locality_layer);
        st.map.add_layer(&st.locality_labels);
        st.map.remove_layer(&st.neighborhood_layer);
    }
}

fn load_points_by_zoom(st: Rc<MapState>) {
    let zoom = st.map.get_zoom();
    if zoom < 19.0 {
        st.map.remove_layer(&st.point_layer);
        return;
    }

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
                &to_js(&json!({
                    "radius": 5,
                    "color": "#000000",
                    "weight": 1,
                    "fillColor": "#006400",
                    "fillOpacity": 0.6
                })),
            );

            let tree = SelectedTree {
                common_name: js_or(&record["common_name"], "N/A"),
                scientific_name: js_or(&record["species"]["scientific_name"], "N/A"),
                life_form: js_or(&record["species"]["life_form"], "N/A"),
                neighborhood: js_or(&record["neighborhood"]["name"], "N/A"),
            };
            let selected_tree = st.selected_tree;
            marker.on("click", &js_fn1(move |_| {
                selected_tree.try_set(Some(tree.clone()));
            }));

            marker.add_to(&st.point_layer);
        }

        st.point_layer.add_to(&st.map);
    });
}
