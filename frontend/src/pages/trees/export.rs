//! CSV downloads. The backend builds the files (`/biodiversity/inventory/export/`):
//! all matching trees through a plain link (the server streams it as an attachment),
//! the selected ones through a POST whose response is saved from a Blob (`post_download`,
//! also used by the map's queries).

use wasm_bindgen::JsCast;

use crate::api::console_error;

fn click_link(href: &str, file_name: Option<&str>) {
    let anchor = web_sys::window()
        .and_then(|w| w.document())
        .and_then(|d| d.create_element("a").ok())
        .and_then(|e| e.dyn_into::<web_sys::HtmlAnchorElement>().ok());
    match anchor {
        Some(a) => {
            a.set_href(href);
            if let Some(name) = file_name {
                a.set_download(name);
            }
            a.click();
        }
        None => console_error("Download failed:", "could not create the download link"),
    }
}

/// Every tree matching the filters (`query` = the list's query string, without `page`).
pub fn download_filtered(export_url: &str, query: &str) {
    let sep = if query.is_empty() { "" } else { "?" };
    click_link(&format!("{export_url}{sep}{query}"), None);
}

/// The selected trees. Returns an error message for the UI.
pub async fn download_selected(export_url: &str, ids: &[i64]) -> Result<(), String> {
    let date: String = js_sys::Date::new_0().to_iso_string().into();
    post_download(
        export_url,
        &serde_json::json!({ "ids": ids }),
        &format!("tree-inventory-selected-{}.csv", &date[..10]),
        "text/csv;charset=utf-8",
    )
    .await
}

/// POST `body` as JSON and save the response as `file_name`. The bytes are kept as sent
/// (a CSV keeps the server's BOM, which Excel needs to read it as UTF-8). Returns an error
/// message for the UI: the server's `{"error": ...}` when it sends one.
pub async fn post_download(
    url: &str,
    body: &serde_json::Value,
    file_name: &str,
    mime: &str,
) -> Result<(), String> {
    let resp = gloo_net::http::Request::post(url)
        .json(body)
        .map_err(|e| e.to_string())?
        .send()
        .await
        .map_err(|e| e.to_string())?;
    if !resp.ok() {
        let detail = resp
            .json::<serde_json::Value>()
            .await
            .ok()
            .and_then(|v| v["error"].as_str().map(str::to_string));
        return Err(detail.unwrap_or_else(|| {
            format!("export failed: {} {}", resp.status(), resp.status_text())
        }));
    }
    let bytes = resp.binary().await.map_err(|e| e.to_string())?;

    let parts = js_sys::Array::of1(&js_sys::Uint8Array::from(bytes.as_slice()));
    let options = web_sys::BlobPropertyBag::new();
    options.set_type(mime);
    let blob = web_sys::Blob::new_with_u8_array_sequence_and_options(&parts, &options)
        .map_err(|_| "could not build the file".to_string())?;
    let href = web_sys::Url::create_object_url_with_blob(&blob)
        .map_err(|_| "could not build the file".to_string())?;
    click_link(&href, Some(file_name));
    // Revoked later: some browsers read the Blob after `click()` returns.
    leptos::prelude::set_timeout(
        move || {
            let _ = web_sys::Url::revoke_object_url(&href);
        },
        std::time::Duration::from_secs(30),
    );
    Ok(())
}
