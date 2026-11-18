# Roadmap

Planned work for the Urban Tree Observatory, roughly in order of priority. Each item becomes
an issue and a pull request when work on it starts; the numbers (#) are existing issues.

## 1. Login, Reports and Alerts for institutions

The platform is public and read-only. Reports and Alerts are meant for administrators and for
public and private institutions working on urban trees; they are hidden behind the
`restricted-pages` feature until there is a login.

- Login for administrators and partner institutions (django-allauth is already installed),
  with roles, and a working user icon in the navbar.
- Define Reports and Alerts with the institutions after the first demo, then build them on
  real data and translate them (they are English only).
- Edit trees from the platform for logged-in users: mark a tree as removed (today: the CSV in
  `backend/apps/biodiversity/data/removed_trees.csv` or the Django admin), or correct its data.

## 2. Map

- Satellite or orthophoto base map, with a switch between it and OpenStreetMap.
- Tree points styled by crown diameter, with a legend (for example by health).
- Comuna by location: 6,715 census trees have an unknown barrio and comuna; add the comuna
  computed from the tree's position as a separate column in downloads and filters, without
  changing the census value.
- Areas of interest from GeoJSON and KMZ files, besides KML.
- Free the Leaflet map and its listeners when leaving the page (`KNOWN ISSUE` in
  `frontend/src/pages/map.rs`).

## 3. Data and indicators

- Real tree-per-capita index and environmental figures (CO₂, oxygen) in the map panel; they
  are placeholders today (`KNOWN ISSUE` in `frontend/src/pages/map.rs`).
- Cite the sources of the climate and population data on the About page.
- Show "cultivated" species as their own origin group instead of "introduced", and translate
  the origin labels the API returns.
- Explain or reconcile the two ways comunas are counted: by the census field and by location
  (PostGIS).
- A workflow for new field surveys: import new measurements, observations and removals, and
  keep their history.
- Review the botanical plates flagged as doubtful (for example *Artocarpus heterophyllus*,
  *Plumeria rubra*, *Pachira aquatica*, *Cordia sebestena*, *Cycas revoluta*).

## 4. Interface

- Mobile layout: several pages overflow on small screens.
- Spanish translation of the backend texts (#143).

## 5. Quality and documentation

- Frontend checks in CI (`cargo test`, `cargo clippy`); CI only checks the backend today.
- Test suite warnings (#124), skipped GeoJSON and date filter tests (#116) and tests for the
  admin customizations (#103).
- CI image matching the development image (#97).
- Project documentation site (#4).

## 6. Deployment

- Public deployment of the demo: production settings, the API and the frontend's static build.
- Tagged releases with a changelog.
