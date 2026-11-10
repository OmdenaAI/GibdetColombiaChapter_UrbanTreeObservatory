# Urban Tree Observatory — Frontend

Single-page app written in Rust with [Leptos](https://book.leptos.dev/) 0.8, compiled to
WebAssembly and rendered client-side (CSR). Built and served with [Trunk](https://trunkrs.dev/).

| | |
|---|---|
| URL | <http://localhost:4200> |
| Styling | Tailwind CSS 3.4.17 (standalone CLI downloaded by Trunk — no Node.js needed) |
| Map | Leaflet 1.9.4, called from Rust via `wasm-bindgen` (`src/interop/leaflet.rs`) |
| Charts | Chart.js 4.4.9, called from Rust via `wasm-bindgen` (`src/interop/chart.rs`) |
| API | Django REST API, default `http://localhost:8000` |

## Run

With Docker (from the repository root):

```bash
docker compose up frontend      # also starts db + backend
```

Locally:

```bash
rustup target add wasm32-unknown-unknown
cargo install --locked trunk --version "~0.21"   # 0.22 requires rustc >= 1.96
trunk serve                                      # http://localhost:4200
```

The API base URL is set at build time: `API_BASE_URL=http://host:8000 trunk build --release`.

## Structure

```
index.html            Trunk entry: styles, vendored JS, wasm
styles/tailwind.css   Tailwind directives + map label styles
public/vendor/        leaflet.js/.css, chart.umd.js (vendored, pinned versions)
public/assets/        static assets
src/
├── main.rs           mounts <App/>
├── app.rs            router: /dashboard (default), /map, /trees, /reports, /alerts, /analytics, /about
├── layout.rs         navbar + collapsible sidebar
├── api.rs            HTTP (gloo-net) + JS `||`/truthiness helpers
├── interop/          Leaflet & Chart.js bindings, `when_connected` DOM helper
└── pages/            one module per route
```

Only the **Map** page talks to the API. The other pages currently use hardcoded sample data.

## Known issues

The current behaviour was carried over from the previous Angular frontend and is marked in the
code with `KNOWN ISSUE:`. Main ones:

- Map: 687 neighborhood requests are sent up front, and a single failure discards all of them.
  The database has 710 neighborhoods.
- Map: tree points are requested twice on every zoom, and in-flight requests are never cancelled.
- Map: the side panel falls back to hardcoded city-wide figures, because the API returns no
  `statistics`.
- Toggling the sidebar does not resize the map.
- Dashboard and Analytics: all figures are sample data. Charts are never destroyed when leaving
  the page.

## Gotcha: DOM access after navigation

On client-side navigation `leptos_router` mounts the new route asynchronously, so an `Effect`
can run before the page's elements are in the document. Any code that needs a real DOM node
(Leaflet, Chart.js) must go through `interop::when_connected`.
