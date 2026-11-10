//! HTTP helpers and JS-semantics helpers.
//!
//! API responses are kept as untyped `serde_json::Value` (the API has no shared schema yet),
//! and the UI reproduces JavaScript `||` / truthiness rules for fallbacks.
//! TODO: introduce typed models once the API contract is settled.

use serde_json::Value;

/// Defaults to `http://localhost:8000`; overridable at build time with
/// `API_BASE_URL=... trunk build`.
pub const API_BASE: &str = match option_env!("API_BASE_URL") {
    Some(url) => url,
    None => "http://localhost:8000",
};

/// GET + JSON. A non-2xx status is an error.
pub async fn get_json(url: &str) -> Result<Value, String> {
    let resp = gloo_net::http::Request::get(url)
        .send()
        .await
        .map_err(|e| e.to_string())?;
    if !resp.ok() {
        return Err(format!(
            "Http failure response for {url}: {} {}",
            resp.status(),
            resp.status_text()
        ));
    }
    resp.json::<Value>().await.map_err(|e| e.to_string())
}

/// JavaScript truthiness of a JSON value (`undefined`/missing is represented as `Null`).
pub fn truthy(v: &Value) -> bool {
    match v {
        Value::Null => false,
        Value::Bool(b) => *b,
        Value::Number(n) => n.as_f64().is_some_and(|f| f != 0.0 && !f.is_nan()),
        Value::String(s) => !s.is_empty(),
        Value::Array(_) | Value::Object(_) => true,
    }
}

/// JavaScript `String(v)` for the value shapes we receive from the API.
pub fn js_string(v: Option<&Value>) -> String {
    match v {
        None => "undefined".into(),
        Some(Value::Null) => "null".into(),
        Some(Value::Bool(b)) => b.to_string(),
        Some(Value::String(s)) => s.clone(),
        Some(Value::Number(n)) => {
            if let Some(i) = n.as_i64() {
                i.to_string()
            } else {
                let f = n.as_f64().unwrap_or(f64::NAN);
                if f.fract() == 0.0 && f.abs() < 1e21 {
                    format!("{}", f as i64)
                } else {
                    format!("{f}")
                }
            }
        }
        Some(other) => other.to_string(),
    }
}

/// JavaScript `v || fallback`, rendered as text.
pub fn js_or(v: &Value, fallback: &str) -> String {
    if truthy(v) {
        js_string(Some(v))
    } else {
        fallback.to_string()
    }
}

pub fn console_error(msg: &str, err: &str) {
    web_sys::console::error_2(&msg.into(), &err.into());
}
