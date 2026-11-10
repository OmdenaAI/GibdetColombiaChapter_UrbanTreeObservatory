//! Minimal Leaflet (global `L`) bindings covering exactly what MapComponent uses.

use wasm_bindgen::prelude::*;

#[wasm_bindgen]
extern "C" {
    // ---- L.Map ----
    pub type LMap;

    /// `L.map(element)`. `catch`: a Leaflet exception becomes an `Err` instead of
    /// unwinding through the wasm module (which would leave the Leptos runtime broken).
    #[wasm_bindgen(catch, js_namespace = L, js_name = map)]
    pub fn map(container: &JsValue) -> Result<LMap, JsValue>;
    #[wasm_bindgen(method, js_name = setView)]
    pub fn set_view(this: &LMap, center: &JsValue, zoom: f64) -> LMap;
    #[wasm_bindgen(method)]
    pub fn on(this: &LMap, event: &str, f: &JsValue) -> LMap;
    #[wasm_bindgen(method, js_name = getZoom)]
    pub fn get_zoom(this: &LMap) -> f64;
    #[wasm_bindgen(method, js_name = getBounds)]
    pub fn get_bounds(this: &LMap) -> LatLngBounds;
    #[wasm_bindgen(method, js_name = fitBounds)]
    pub fn fit_bounds(this: &LMap, bounds: &LatLngBounds, options: &JsValue) -> LMap;
    #[wasm_bindgen(method, js_name = addLayer)]
    pub fn add_layer(this: &LMap, layer: &Layer) -> LMap;
    #[wasm_bindgen(method, js_name = removeLayer)]
    pub fn remove_layer(this: &LMap, layer: &Layer) -> LMap;

    // ---- L.Layer / LayerGroup / FeatureGroup / GeoJSON / Marker / Path ----
    #[derive(Clone)]
    pub type Layer;

    #[wasm_bindgen(method, js_name = addTo)]
    pub fn add_to(this: &Layer, target: &JsValue) -> Layer;
    #[wasm_bindgen(method, js_name = addLayer)]
    pub fn add_child(this: &Layer, layer: &Layer) -> Layer;
    #[wasm_bindgen(method, js_name = clearLayers)]
    pub fn clear_layers(this: &Layer) -> Layer;
    #[wasm_bindgen(method, js_name = getBounds)]
    pub fn get_bounds(this: &Layer) -> LatLngBounds;
    #[wasm_bindgen(method, js_name = setStyle)]
    pub fn set_style(this: &Layer, style: &JsValue) -> Layer;
    #[wasm_bindgen(method)]
    pub fn on(this: &Layer, event: &str, f: &JsValue) -> Layer;

    #[wasm_bindgen(js_namespace = L, js_name = tileLayer)]
    pub fn tile_layer(url: &str, options: &JsValue) -> Layer;
    #[wasm_bindgen(js_namespace = L, js_name = layerGroup)]
    pub fn layer_group() -> Layer;
    #[wasm_bindgen(js_namespace = L, js_name = featureGroup)]
    pub fn feature_group() -> Layer;
    #[wasm_bindgen(js_namespace = L, js_name = geoJSON)]
    pub fn geo_json(data: &JsValue, options: &JsValue) -> Layer;
    #[wasm_bindgen(js_namespace = L, js_name = marker)]
    pub fn marker(latlng: &JsValue, options: &JsValue) -> Layer;
    #[wasm_bindgen(js_namespace = L, js_name = circleMarker)]
    pub fn circle_marker(latlng: &JsValue, options: &JsValue) -> Layer;
    #[wasm_bindgen(js_namespace = L, js_name = divIcon)]
    pub fn div_icon(options: &JsValue) -> JsValue;
    #[wasm_bindgen(js_namespace = L, js_name = latLng)]
    pub fn lat_lng(lat: f64, lng: f64) -> JsValue;

    // ---- L.LatLngBounds ----
    pub type LatLngBounds;

    #[wasm_bindgen(method, js_name = isValid)]
    pub fn is_valid(this: &LatLngBounds) -> bool;
    #[wasm_bindgen(method, js_name = getCenter)]
    pub fn get_center(this: &LatLngBounds) -> JsValue;
    #[wasm_bindgen(method, js_name = getSouth)]
    pub fn get_south(this: &LatLngBounds) -> f64;
    #[wasm_bindgen(method, js_name = getNorth)]
    pub fn get_north(this: &LatLngBounds) -> f64;
    #[wasm_bindgen(method, js_name = getWest)]
    pub fn get_west(this: &LatLngBounds) -> f64;
    #[wasm_bindgen(method, js_name = getEast)]
    pub fn get_east(this: &LatLngBounds) -> f64;
}
