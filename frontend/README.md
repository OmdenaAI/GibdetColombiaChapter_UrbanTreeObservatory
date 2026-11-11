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
├── app.rs            router: /dashboard (default), /map, /trees, /species, /reports, /alerts, /analytics, /about
├── layout.rs         navbar + collapsible sidebar
├── api.rs            HTTP (gloo-net) + JS `||`/truthiness helpers
├── interop/          Leaflet & Chart.js bindings, `when_connected` DOM helper
└── pages/            one module per route (species/ = catalog: model, filters, cards, CSV;
                      trees/ = inventory: list, detail, CSV export)
```

The **Map** and **Species** pages talk to the API. On the map (zoom ≥ 19), clicking a tree point replaces the
statistics panel with that tree's sheet — common and scientific name, illustration, IUCN status,
id, family, life form, DBH, total height, neighborhood, site and GBIF / Tropical Plants links — and
highlights the point; "Back to summary" restores the statistics. Comuna labels (zoom < 17) and barrio labels (zoom
17–18) show each area's tree count; clicking one shows its trees, distinct species and average
height in the panel. Barrios and tree points are loaded only for the visible area (one request per
pan/zoom: `/places/neighborhoods/bbox/` with geometry + statistics, `/biodiversity/records/bbox/`);
barrios already drawn are kept and sent as `exclude`, and stale point responses are dropped. The **Dashboard**, **Trees** and **Analytics** pages also use real data;
Reports and Alerts still use hardcoded sample data.

### Analytics (`/analytics`)

Urban forest indicators from `GET /api/v1/reports/analytics/` (computed in PostGIS, cached one
hour; ~4 s uncached): origin of the trees (native / introduced / not identified), trees per
1,000 inhabitants per comuna with a comuna table (trees, area, trees per hectare, per 1,000
inhabitants, share with health problems), health problems in the 10 most common species and
trees of threatened IUCN species. Comunas are assigned by the trees' coordinates
(point-in-polygon), not by the census field.

### Tree inventory (`/trees`)

Read-only query page over the census (`/api/v1/biodiversity/inventory/`, public). Adding,
editing and deleting trees is done in the Django admin. Filters (applied server-side; text
filters after a short pause in typing): ID, species (scientific or common name), family,
neighborhood (all case-insensitive, partial match) and health status. 25 trees per page with
latest total height, DBH and health. "View" opens the tree's full record: species, location,
every measurement with its method and date (older ones listed as history) and all fields of the
census observation (the cryptic form codes are shown as recorded). CSV export, built by the
backend: "Export selected" (checkboxes, kept across pages and searches; POST with the ids) and
"Export all / filtered" (every tree matching the filters, streamed; ~15 s for the whole census).

### Species catalog (`/species`)

Lists the 438 species from `GET /api/v1/taxonomy/species/` (public, read-only). All pages are
downloaded once and filtered client-side: common name, scientific name (a genus lists all its species), family, functional group range,
habit, IUCN status, origin, flower color and canopy shape. Results are rendered in batches of 25 ("Show next 25"; any filter change goes back to the first batch), because drawing the cards — not filtering — is the expensive part. It offers grid/list views, a detail
sheet with GBIF / Tropical Plants links, and CSV export of the filtered rows. Cards follow the team's
"card blockframe" template: common name + functional-group tag, photo placeholder, scientific
name, traits and an icon strip (flower color, habit, IUCN, origin, canopy). The common name is the
most frequent one in the species' biodiversity records (`common_name`, annotated by the API). Saved species
(bookmarks) are stored in the browser's `localStorage` only. Functional-group metrics appear only
for the 168 species that have a group. Trait ranges are shown sorted, because some records have
`min > max`.

## Known issues

The current behaviour was carried over from the previous Angular frontend and is marked in the
code with `KNOWN ISSUE:`. Main ones:

- Map: the tree-per-capita index and the environmental figures (CO₂, oxygen) are still
  placeholders. Tree count, species count and average height are real
  (`/api/v1/places/{localities,neighborhoods}/statistics/`).
- Toggling the sidebar does not resize the map.
- Dashboard: real figures from `GET /api/v1/reports/dashboard/` (census, taxonomy, climate,
  population 2019). CO₂ absorption and oxygen production show N/A: there is no model for them
  yet. Temperature trends are one line per station (stations report in different periods).
- Dashboard and Analytics charts are never destroyed when leaving the page.

## Gotcha: DOM access after navigation

On client-side navigation `leptos_router` mounts the new route asynchronously, so an `Effect`
can run before the page's elements are in the document. Any code that needs a real DOM node
(Leaflet, Chart.js) must go through `interop::when_connected`.

### Species illustrations

Cover illustrations live in `public/assets/species/<genus>-<epithet>.webp` (lowercase, 640×640
WebP, ~30 KB each) and are listed in `ILLUSTRATIONS` in `src/pages/species/model.rs`. A species
matches by scientific name or accepted name. Species without one show a placeholder; the sidebar
has a "With illustration only" filter. To add one:

```bash
convert "Genus epithet.png" -resize 640x640 -strip -quality 80 public/assets/species/genus-epithet.webp
# then add "Genus epithet" to ILLUSTRATIONS
```
