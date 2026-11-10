//! Bindings to the vendored JS libraries (Leaflet 1.9.4, Chart.js 4.4.9).

pub mod chart;
pub mod leaflet;

use serde::Serialize;
use wasm_bindgen::JsValue;

/// Run `f` once `el` is attached to the document (checked once per animation frame, ~2 s max).
///
/// Needed because on client-side navigation leptos_router builds the route view
/// asynchronously: an `Effect` may run before the view is in the DOM. Gives up silently if the user
/// navigates away before the element is ever attached.
pub fn when_connected(el: web_sys::HtmlElement, f: impl FnOnce() + 'static) {
    fn poll(el: web_sys::HtmlElement, f: Box<dyn FnOnce()>, attempt: u32) {
        if el.is_connected() {
            f();
        } else if attempt < 120 {
            leptos::prelude::request_animation_frame(move || poll(el, f, attempt + 1));
        }
    }
    poll(el, Box::new(f), 0);
}

/// Convert a `serde_json::Value` into a plain JS object/array (maps become objects).
pub fn to_js(v: &serde_json::Value) -> JsValue {
    v.serialize(&serde_wasm_bindgen::Serializer::json_compatible())
        .expect("serializable JSON value")
}
