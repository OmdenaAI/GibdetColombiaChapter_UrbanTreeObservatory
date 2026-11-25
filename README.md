# Urban Tree Observatory

![CI](https://github.com/OmdenaAI/GibdetColombiaChapter_UrbanTreeObservatory/workflows/CI/badge.svg)

An open web platform to monitor, analyze and manage the urban forest of **Ibagué, Colombia**.
It brings the city's public tree census (101,228 trees surveyed by Cortolima in 2014, 2015 and
2017) into an interactive map, statistics by comuna and barrio, a species catalog and data
downloads.

## Who it is for

- **Residents** who want to know the trees of their barrio.
- **Researchers and students** of urban ecology, forestry and planning, who need the data in
  open formats.
- **Environmental authorities and institutions** (such as Cortolima and the city government)
  that plan planting, maintenance and tree removals.

## Features

- **Map**: comunas, barrios and individual trees by zoom level; each tree opens its census
  sheet. A toolbar queries trees by code, scientific or common name, comuna and barrio, and by
  an area of interest drawn on the map or loaded from a KML file; the result downloads as
  Excel, CSV or GeoJSON with every inventory column.
- **Species catalog**: the census species with their habit, origin, IUCN status, flower color
  and canopy shape, historical botanical plates from Wikimedia Commons and, where available,
  the species sheet of the Tolima arborization manual.
- **Trees**: the inventory with filters, the full record of each tree and CSV export.
- **Dashboard and Analytics**: trees per comuna, density, origin, health and threatened
  species.
- **Tree status**: trees that no longer exist (felled, fallen...) are kept in the database
  with the date, reason and a note of the removal, and hidden from the platform.
- **Reports (login)**: staff users sign in with their Django admin username and password and
  update the database from a file (Excel, CSV, zipped Shapefile or GeoJSON, with the columns
  of the downloads): edit trees, add new trees and add measurements and observations, which
  keep their history. The file is checked first and applied only when confirmed; every file
  is kept with its user.
- **Studies**: results of research on the census trees, loaded with their citation. The
  first is the instrumental assessment of 100 trees by Torres Payares (2025): visual
  (EVA) and biomechanical risk, acoustic tomography, wood densities and stiffness. Each
  tree's page shows the assessment and indicators computed from its measurements (crown
  area and asymmetry, slenderness, residual sound wall, biomass and CO₂, intervention
  criteria), with their formulas.
- **Bilingual**: Spanish (default) and English.

Alerts, meant for administrators and partner institutions, is hidden until it is defined with
them (see the [roadmap](ROADMAP.md)).

## Built with

- **Backend**: Python 3.12, Django 5.1, Django REST Framework and PostgreSQL with PostGIS.
- **Frontend**: Rust and [Leptos](https://book.leptos.dev/) 0.8 compiled to WebAssembly,
  [Trunk](https://trunkrs.dev/), Leaflet, Chart.js and Tailwind CSS.
- **Development**: Docker Compose, pytest, ruff and pre-commit, and GitHub Actions for CI.

## Development Environment Setup

### Prerequisites

- Docker and Docker Compose
- Git

### Getting Started

1. Clone this repository:

   ```bash
   git clone https://github.com/OmdenaAI/GibdetColombiaChapter_UrbanTreeObservatory
   cd GibdetColombiaChapter_UrbanTreeObservatory
   ```

2. Start the development environment:

   ```bash
   docker compose up
   ```

3. Access the different components:
   - Frontend (Leptos): <http://localhost:4200/>
   - Django backend: <http://localhost:8000/>
   - Django admin: <http://localhost:8000/admin/>
   - PostgreSQL database: localhost:5433 (port 5432 inside the Docker network)
   - PgAdmin: <http://localhost:5050/>

4. Stop the services when you are done:

   ```bash
   docker compose stop
   ```

### Setting up PgAdmin

To connect to the database through PgAdmin:

1. Go to <http://localhost:5050/browser/>
2. Login with:
   - Email: <admin@omdena.com>
   - Password: admin
3. Right-click on "Servers" and select "Register > Server"
4. In the General tab, name it "Local PostgreSQL"
5. In the Connection tab, enter:
   - Host: db
   - Port: 5432
   - Database: urban_tree_db
   - Username: postgres
   - Password: postgres

These are local development credentials only.

### First-Time Setup

After starting the containers for the first time, create a superuser:

```bash
docker compose exec backend python manage.py createsuperuser
```

### Initial Data Import

The census, places and climate data are published at:

1. [Hugging Face](https://huggingface.co/datasets/juanpac96/urban_tree_census_data)
2. [Google Drive](https://drive.google.com/drive/folders/1EgslMmVYdvtSXS22wDYCDCroOLV7TqmY?usp=sharing)

By default, the import command downloads the files from Hugging Face:

```bash
docker compose exec backend python manage.py import_initial_data
```

To import local copies instead, save the CSV files to `backend/data/csv` and the JSON files
to `backend/data/json`, then run:

```bash
docker compose exec backend python manage.py import_initial_data --local-dir=data
```

The import dates the trees whose survey date was empty (stored as 1899-12-30, Excel's
day zero) with the most frequent date of the trees within 200 m. On a database loaded
before this step, run it once (idempotent):

```bash
docker compose exec backend python manage.py fix_census_dates
```

It also gives each tree its planting site (park, sidewalk, road median...), which the
cleaned files lack, from the original census in `backend/apps/biodiversity/data/planting_sites.csv`,
matched by position. On a database loaded before this step, run it once (idempotent):

```bash
docker compose exec backend python manage.py load_planting_sites
```

It then gives each species the planting sites that the Tolima arborization manual
recommends for it (the species catalog filters by them), from the project's coding of the
manual in `backend/apps/taxonomy/data/planting_site_suitability.csv`. On a database loaded
before this step, run it once (idempotent):

```bash
docker compose exec backend python manage.py load_planting_site_suitability
```

Then mark the trees that no longer exist. The list is versioned in
`backend/apps/biodiversity/data/removed_trees.csv`:

```bash
docker compose exec backend python manage.py load_removed_trees
```

Then load the studies (see each study's README):

```bash
docker compose exec backend python manage.py import_study apps/reports/studies/torres_payares_2025
```

Finally, estimate each tree's ecosystem services (stored carbon and intercepted rain), which
the map, the dashboard and the tree sheets add up by barrio, comuna and city. The method and
its references are in `backend/apps/reports/ecosystem.py`; the rain curves and the wood
densities of the Global Wood Density Database (for trees without one) are in
`backend/apps/reports/data/`, exported by the analysis notebook. Missing inputs are filled
with census-wide medians, so run it again after any change to the census (new trees,
uploads, studies):

```bash
docker compose exec backend python manage.py compute_ecosystem_services
```

The species sheets of the Tolima arborization manual are optional. Their text is not in this
repository (see [Data sources and credits](#data-sources-and-credits)); to generate and load
them from your own copy of the PDF, follow [`scripts/README.md`](scripts/README.md).

## Project Structure

### Backend (Django REST API)

- `backend/` - Django project ([`backend/README.md`](backend/README.md))
  - `config/` - Django project settings
  - `apps/` - Django apps
    - `core/` - Core functionality and the initial data import
    - `users/` - User management
    - `places/` - Comunas, barrios and sites, with geometry and tree statistics
    - `taxonomy/` - Families, genera and species, and the manual's species sheets
    - `biodiversity/` - Trees: records with location and status, inventory, map queries and downloads
    - `reports/` - Measurements and observations, dashboard and analytics
    - `climate/` - Climate data

### Frontend (Leptos)

Rust + WebAssembly single-page app built with [Leptos](https://book.leptos.dev/) and served by
[Trunk](https://trunkrs.dev/). See [`frontend/README.md`](frontend/README.md) for details.

- `frontend/` - Leptos application
  - `src/app.rs` - Routes
  - `src/layout.rs` - Navbar and sidebar
  - `src/i18n.rs` - Spanish / English texts
  - `src/api.rs` - HTTP client for the Django API
  - `src/interop/` - Bindings to Leaflet (map) and Chart.js (charts)
  - `src/pages/` - One module per page: dashboard, map (and its toolbar, `map_tools/`), trees,
    species, analytics, about, reports and alerts

### Database

- PostgreSQL with PostGIS for geospatial data

### Scripts

- `scripts/` - Tools that prepare data outside the app, such as the extraction of the Tolima
  manual's species sheets ([`scripts/README.md`](scripts/README.md))

## Development Workflow

1. Run the application with Docker Compose
2. Make changes to your code (the backend and Trunk reload on save)
3. Run the tests and the pre-commit hooks
4. Commit and push your changes, and open a pull request to `main`

### Setting up Pre-commit Hooks

This project uses pre-commit hooks to ensure code quality; CI runs the same hooks. To set up
pre-commit:

```bash
# Install pre-commit
pip install pre-commit

# Install the git hooks
pre-commit install
```

Pre-commit will now run automatically on every commit. You can also run it manually:

```bash
pre-commit run --all-files
```

### Running Tests

```bash
# Backend tests
docker compose exec backend pytest

# Backend tests with coverage
docker compose exec backend pytest --cov=. --cov-config=.coveragerc

# Frontend tests and lints (from frontend/, with Rust installed)
cargo test
cargo clippy --target wasm32-unknown-unknown
```

## API Documentation

The API documentation is available at:

- Swagger UI: <http://localhost:8000/api/v1/swagger/>
- ReDoc: <http://localhost:8000/api/v1/redoc/>

## Roadmap

The planned work (login for institutions, Reports and Alerts, map improvements, mobile layout,
public deployment...) is in [ROADMAP.md](ROADMAP.md).

## Data sources and credits

- **Tree census**: Corporación Autónoma Regional del Tolima (Cortolima), urban tree census of
  Ibagué (2014, 2015 and 2017).
- **Botanical plates**: historical illustrations from Wikimedia Commons; author, source and
  license of each one in
  [`frontend/public/assets/species/CREDITS.csv`](frontend/public/assets/species/CREDITS.csv).
- **Tolima arborization manual**: Cortolima – Jardín Botánico San Jorge, *Manual de
  arborización para el departamento del Tolima* (2017). Its license is unknown, so its text is
  not included in this repository: only the code that extracts it.
- **Instrumental assessment of 100 urban trees**: Torres Payares, L. E. (2025), Universidad
  del Tolima, published with the author's authorization; sources and reconciliation in
  [`backend/apps/reports/studies/torres_payares_2025`](backend/apps/reports/studies/torres_payares_2025/README.md).
- **Wood density**: Global Wood Density Database (Chave et al., 2009; Zanne et al., 2009,
  Dryad, CC0), as distributed in the `wdData` table of the BIOMASS R package; used for the
  trees without a census density.
- **References**: the studies on urban trees that inspired the platform are cited on its
  About page.

## Team

The Urban Tree Observatory began as an [Omdena](https://www.omdena.com/) GibdetColombia
Chapter challenge, built by a team of volunteers. It is maintained by
[@juanpac96](https://github.com/juanpac96) through
[Fundación LEGUT](https://www.legut.org/), a non-profit.

Contributions are welcome: open an issue or a pull request.

## License

[MIT](LICENSE)
