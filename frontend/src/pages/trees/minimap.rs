//! Small OpenStreetMap view of one tree in the tree detail: the tree's point only, the zoom
//! buttons and a "home" button that brings the view back to the tree.

use std::time::Duration;

use leptos::prelude::*;
use serde_json::json;

use crate::i18n::{Lang, pick};
use crate::interop::leaflet::{self as L, LMap};
use crate::interop::{to_js, when_connected};

/// Streets, parks and their names are readable at this zoom.
const ZOOM: f64 = 16.0;
const ICON_HOME: &str = "M3 12l2-2m0 0l7-7 7 7M5 10v10a1 1 0 001 1h3m10-11l2 2m-2-2v10a1 1 0 01-1 1h-3m-6 0a1 1 0 001-1v-4a1 1 0 011-1h2a1 1 0 011 1v4a1 1 0 001 1m-6 0h6";

#[component]
pub(super) fn MiniMap(lat: f64, lon: f64, l: Lang) -> impl IntoView {
    let el = NodeRef::<leptos::html::Div>::new();
    // `LMap` is a JS object (not `Send`): local storage.
    let map: StoredValue<Option<LMap>, LocalStorage> = StoredValue::new_local(None);
    let home = move || {
        map.with_value(|m| {
            if let Some(m) = m {
                m.set_view(&L::lat_lng(lat, lon), ZOOM);
            }
        })
    };

    Effect::new(move |_| {
        let Some(div) = el.get() else { return };
        let container: web_sys::HtmlElement = div.into();
        let c = container.clone();
        when_connected(container, move || {
            let m = match L::map_with(&c, &to_js(&json!({ "zoomControl": false, "scrollWheelZoom": false }))) {
                Ok(m) => m,
                Err(e) => return web_sys::console::error_2(&"Error initializing the mini map:".into(), &e),
            };
            m.set_view(&L::lat_lng(lat, lon), ZOOM);
            L::control_zoom(&to_js(&json!({
                "position": "topleft",
                "zoomInTitle": pick(l, "Acercar", "Zoom in"),
                "zoomOutTitle": pick(l, "Alejar", "Zoom out"),
            })))
            .add_to(&m);
            // Same tiles as the main map (z19 tiles upscaled beyond that).
            L::tile_layer(
                "https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png",
                &to_js(&json!({ "maxZoom": 21, "maxNativeZoom": 19, "attribution": "© OpenStreetMap contributors" })),
            )
            .add_to(&m);
            L::circle_marker(
                &L::lat_lng(lat, lon),
                &to_js(&json!({ "radius": 8, "color": "#14532D", "weight": 2, "fillColor": "#4ADE80", "fillOpacity": 1 })),
            )
            .add_to(&m);
            // The dialog may still be settling its size when the map is created.
            let again = m.clone();
            set_timeout(move || { again.invalidate_size(); }, Duration::from_millis(150));
            map.set_value(Some(m));
        });
    });
    on_cleanup(move || {
        if let Some(m) = map.try_update_value(Option::take).flatten() {
            m.remove();
        }
    });

    let title = pick(l, "Volver al árbol", "Back to the tree");
    view! {
        <div class="relative h-64 rounded-lg overflow-hidden border border-gray-300">
            <div node_ref=el class="absolute inset-0"></div>
            // Below Leaflet's zoom buttons, with their look (`leaflet-bar`).
            <div class="leaflet-bar absolute left-[10px] top-[84px] z-[1000] bg-white">
                <a
                    href="#"
                    role="button"
                    title=title
                    aria-label=title
                    class="minimap-home !flex items-center justify-center text-gray-800"
                    on:click=move |ev| {
                        ev.prevent_default();
                        home();
                    }
                >
                    <svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d=ICON_HOME />
                    </svg>
                </a>
            </div>
        </div>
    }
}
