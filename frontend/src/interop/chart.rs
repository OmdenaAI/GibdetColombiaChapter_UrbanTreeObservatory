//! Chart.js (global `Chart` from chart.umd.js).

use wasm_bindgen::prelude::*;

#[wasm_bindgen]
extern "C" {
    pub type Chart;

    /// `catch`: a Chart.js exception becomes an `Err` instead of aborting the wasm module.
    #[wasm_bindgen(catch, constructor)]
    fn new(item: &JsValue, config: &JsValue) -> Result<Chart, JsValue>;
}

/// `document.getElementById(id)` (or `null`).
fn element_by_id(id: &str) -> JsValue {
    web_sys::window()
        .and_then(|w| w.document())
        .and_then(|d| d.get_element_by_id(id))
        .map(JsValue::from)
        .unwrap_or(JsValue::NULL)
}

/// `new Chart(document.getElementById(id), config)`.
///
/// `skip_if_missing` skips silently when the canvas is absent (Dashboard); otherwise the
/// Chart.js error is logged (Analytics).
/// KNOWN ISSUE: charts are never destroyed when leaving the page.
pub fn chart_by_id(id: &str, config: serde_json::Value, skip_if_missing: bool) {
    let el = element_by_id(id);
    if skip_if_missing && el.is_null() {
        return;
    }
    if let Err(e) = Chart::new(&el, &super::to_js(&config)) {
        web_sys::console::error_2(&format!("Error creating chart #{id}:").into(), &e);
    }
}
