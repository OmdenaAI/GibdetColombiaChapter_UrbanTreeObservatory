//! Species catalog (`/species`): the 438 species from `/api/v1/taxonomy/species/`.
//!
//! Everything is downloaded once and filtered client-side. Bookmarks ("saved" species) live in
//! `localStorage`, so they are per browser and are not sent to the backend.

pub(crate) mod card;
mod export;
mod modal;
pub(crate) mod model;
mod sidebar;

use std::collections::HashSet;
use std::sync::Arc;

use leptos::prelude::*;
use leptos::task::spawn_local;

use crate::api::console_error;
use crate::i18n::{I18n, pick};
use card::{ICON_BOOKMARK, SpeciesCard, SpeciesTable, svg};
use modal::SpeciesModal;
use model::{Catalog, Category, Filters, Species, fetch_all_species};
use sidebar::FilterSidebar;

/// Cards rendered per batch ("Show next" adds another batch).
const BATCH: usize = 25;

const SAVED_KEY: &str = "urban-tree-observatory:saved-species";

const ICON_GRID: &str = "M4 6a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2H6a2 2 0 01-2-2V6zM14 6a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2h-2a2 2 0 01-2-2V6zM4 16a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2H6a2 2 0 01-2-2v-2zM14 16a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2h-2a2 2 0 01-2-2v-2z";
const ICON_LIST: &str = "M4 6h16M4 12h16M4 18h16";
const ICON_DOWNLOAD: &str = "M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4";
pub(super) const ICON_X: &str = "M6 18L18 6M6 6l12 12";

const BTN: &str = "inline-flex items-center gap-2 px-3 py-2 rounded-lg border text-sm font-medium transition-colors";
const BTN_IDLE: &str = "bg-white border-gray-300 text-gray-700 hover:bg-gray-50";
const BTN_ON: &str = "bg-primary-600 border-primary-600 text-white hover:bg-primary-700";

#[derive(Clone)]
enum Load {
    Loading,
    Failed(String),
    Ready(Catalog),
}

/// State shared by the catalog's components.
#[derive(Clone, Copy)]
pub(crate) struct Ctx {
    pub filters: RwSignal<Filters>,
    pub saved: RwSignal<HashSet<i64>>,
    pub selected: RwSignal<Option<Arc<Species>>>,
}

impl Ctx {
    pub fn is_saved(&self, id: i64) -> bool {
        self.saved.with(|s| s.contains(&id))
    }

    pub fn toggle_saved(&self, id: i64) {
        self.saved.update(|s| {
            if !s.remove(&id) {
                s.insert(id);
            }
        });
    }
}

#[component]
pub fn SpeciesCatalog() -> impl IntoView {
    let state = RwSignal::new(Load::Loading);
    let ctx = Ctx {
        filters: RwSignal::new(Filters::default()),
        saved: RwSignal::new(load_saved()),
        selected: RwSignal::new(None),
    };
    let grid = RwSignal::new(true);
    let i = I18n::use_ctx();

    let load = move || {
        state.set(Load::Loading);
        spawn_local(async move {
            match fetch_all_species().await {
                Ok(c) => state.set(Load::Ready(c)),
                Err(e) => {
                    console_error("Error loading species:", &e);
                    state.set(Load::Failed(e));
                }
            }
        });
    };
    load();

    Effect::new(move |_| ctx.saved.with(store_saved));

    let filtered = Memo::new(move |_| {
        let f = ctx.filters.get();
        ctx.saved.with(|saved| {
            state.with(|s| match s {
                Load::Ready(all) => all.iter().filter(|s| f.matches(s, saved)).cloned().collect(),
                _ => Vec::new(),
            })
        })
    });

    // Rendering cards is the expensive part (filtering 438 items is not), so only `BATCH`
    // cards are shown at first. The extra batches remember the filters they were requested
    // for, so any filter change goes back to the first batch without rendering the full list.
    let extra = RwSignal::new((0usize, Filters::default()));
    let limit = Memo::new(move |_| {
        let f = ctx.filters.get();
        extra.with(|(n, at)| BATCH * (1 + if *at == f { *n } else { 0 }))
    });
    // Forget the extra batches once the filters change, so that going back to earlier
    // filters (e.g. clearing a search) also starts again from the first batch. `limit` is
    // already `BATCH` at this point, so this reset does not re-render anything.
    Effect::new(move |_| {
        let f = ctx.filters.get();
        if extra.with_untracked(|(_, at)| *at != f) {
            extra.set((0, f));
        }
    });
    let visible = Memo::new(move |_| {
        let n = limit.get();
        filtered.with(|v| v[..v.len().min(n)].to_vec())
    });
    let show_more = move |_| {
        let f = ctx.filters.get_untracked();
        extra.update(|(n, at)| {
            *n = if *at == f { *n + 1 } else { 1 };
            *at = f;
        });
    };

    let saved_only = move || ctx.filters.with(|f| f.saved_only);

    view! {
        <div class="flex flex-col h-full gap-4">
            // Header
            <div class="bg-white rounded-lg shadow p-4 flex flex-wrap items-center justify-between gap-4">
                <div>
                    <h1 class="text-2xl font-semibold text-gray-800">{move || i.t("Catálogo de especies", "Species Catalog")}</h1>
                    <p class="text-sm text-gray-500">{move || i.t("Especies de árboles y plantas registradas en el bosque urbano de Ibagué", "Tree and plant species recorded in Ibagué's urban forest")}</p>
                </div>
                <div class="flex flex-wrap items-center gap-2">
                    <button
                        class=move || format!("{BTN} {}", if saved_only() { BTN_ON } else { BTN_IDLE })
                        on:click=move |_| ctx.filters.update(|f| f.saved_only = !f.saved_only)
                    >
                        {svg(ICON_BOOKMARK, "h-5 w-5")}
                        {move || format!("{} ({})", i.t("Guardadas", "Saved"), ctx.saved.with(HashSet::len))}
                    </button>
                    <button
                        class=format!("{BTN} {BTN_IDLE} disabled:opacity-50 disabled:cursor-not-allowed")
                        disabled=move || filtered.with(Vec::is_empty)
                        on:click=move |_| filtered.with(|rows| export::download_csv(i.lang_untracked(), rows))
                    >
                        {svg(ICON_DOWNLOAD, "h-5 w-5")}
                        {move || i.t("Exportar CSV", "Export CSV")}
                    </button>
                    <div class="inline-flex rounded-lg border border-gray-300 overflow-hidden">
                        <button
                            title=move || i.t("Vista de cuadrícula", "Grid view")
                            class=move || if grid.get() { "p-2 bg-primary-600 text-white" } else { "p-2 bg-white text-gray-600 hover:bg-gray-50" }
                            on:click=move |_| grid.set(true)
                        >
                            {svg(ICON_GRID, "h-5 w-5")}
                        </button>
                        <button
                            title=move || i.t("Vista de lista", "List view")
                            class=move || if grid.get() { "p-2 bg-white text-gray-600 hover:bg-gray-50" } else { "p-2 bg-primary-600 text-white" }
                            on:click=move |_| grid.set(false)
                        >
                            {svg(ICON_LIST, "h-5 w-5")}
                        </button>
                    </div>
                </div>
            </div>

            {move || match state.get() {
                Load::Loading => view! {
                    <div class="flex-1 flex items-center justify-center text-gray-500">
                        <div class="h-8 w-8 mr-3 rounded-full border-4 border-primary-200 border-t-primary-600 animate-spin"></div>
                        {move || i.t("Cargando especies…", "Loading species…")}
                    </div>
                }
                .into_any(),
                Load::Failed(err) => view! {
                    <div class="flex-1 flex flex-col items-center justify-center gap-3 text-gray-600">
                        <p class="font-medium text-red-600">{move || i.t("No se pudo cargar el catálogo de especies.", "Could not load the species catalog.")}</p>
                        <p class="text-sm text-gray-500">{err}</p>
                        <button class=format!("{BTN} {BTN_ON}") on:click=move |_| load()>{move || i.t("Reintentar", "Retry")}</button>
                    </div>
                }
                .into_any(),
                Load::Ready(all) => view! {
                    <div class="flex flex-1 gap-4 min-h-0">
                        <FilterSidebar catalog=all.clone() ctx />
                        <section class="flex-1 min-w-0 overflow-y-auto pr-1">
                            <ResultsBar total=all.len() shown=Signal::derive(move || filtered.with(Vec::len)) ctx />
                            <Show
                                when=move || !filtered.with(Vec::is_empty)
                                fallback=move || view! {
                                    <div class="bg-white rounded-lg shadow p-8 text-center text-gray-500">
                                        {move || i.t("Ninguna especie coincide con los filtros actuales.", "No species match the current filters.")}
                                    </div>
                                }
                            >
                                {move || if grid.get() {
                                    let l = i.lang();
                                    view! {
                                        <div class="grid gap-4 grid-cols-1 sm:grid-cols-2 xl:grid-cols-3 2xl:grid-cols-4">
                                            <For
                                                each=move || visible.get()
                                                key=|s| s.id
                                                children={move |s: Arc<Species>| view! { <SpeciesCard species=s ctx l /> }}
                                            />
                                        </div>
                                    }
                                    .into_any()
                                } else {
                                    view! { <SpeciesTable rows=visible ctx l=i.lang() /> }.into_any()
                                }}
                                <div class="flex flex-col items-center gap-2 py-6">
                                    <span class="text-sm text-gray-500">
                                        {move || {
                                            let (n, of) = (visible.with(Vec::len), filtered.with(Vec::len));
                                            pick(i.lang(), format!("Mostrando {n} de {of} especies"), format!("Showing {n} of {of} species"))
                                        }}
                                    </span>
                                    <Show when=move || visible.with(Vec::len) < filtered.with(Vec::len)>
                                        <button class=format!("{BTN} {BTN_ON} px-5") on:click=show_more>
                                            {move || {
                                                let left = filtered.with(Vec::len) - visible.with(Vec::len);
                                                format!("{} {}", i.t("Mostrar siguientes", "Show next"), left.min(BATCH))
                                            }}
                                        </button>
                                    </Show>
                                </div>
                            </Show>
                        </section>
                    </div>
                }
                .into_any(),
            }}

            {move || {
                let l = i.lang();
                ctx.selected.get().map(|s| view! { <SpeciesModal species=s ctx l /> })
            }}
        </div>
    }
}

/// "Results: n/total" + one removable chip per active filter.
#[component]
fn ResultsBar(total: usize, shown: Signal<usize>, ctx: Ctx) -> impl IntoView {
    let f = ctx.filters;
    let i = I18n::use_ctx();
    let chip = move |label: String, clear: Box<dyn Fn() + Send + Sync>| {
        view! {
            <span class="inline-flex items-center gap-1 pl-3 pr-1 py-1 rounded-full bg-primary-50 text-primary-800 text-xs font-medium">
                {label}
                <button class="rounded-full p-0.5 hover:bg-primary-100" title=move || i.t("Quitar filtro", "Remove filter") on:click=move |_| clear()>
                    {svg(ICON_X, "h-3.5 w-3.5")}
                </button>
            </span>
        }
    };

    let chips = move || {
        let cur = f.get();
        let l = i.lang();
        let t = move |es, en| pick(l, es, en);
        let mut out = Vec::new();
        if !cur.common_name.trim().is_empty() {
            out.push(chip(
                format!("{}: {}", t("Nombre común", "Common name"), cur.common_name.trim()),
                Box::new(move || f.update(|f| f.common_name.clear())),
            ));
        }
        if !cur.scientific_name.trim().is_empty() {
            out.push(chip(
                format!("{}: {}", t("Nombre científico", "Scientific name"), cur.scientific_name.trim()),
                Box::new(move || f.update(|f| f.scientific_name.clear())),
            ));
        }
        if !cur.family.trim().is_empty() {
            out.push(chip(
                format!("{}: {}", t("Familia", "Family"), cur.family.trim()),
                Box::new(move || f.update(|f| f.family.clear())),
            ));
        }
        for (cat, code) in cur.selected.iter().copied() {
            out.push(chip(
                format!("{}: {}", cat.chip_prefix(l), Category::label(cat, l, code)),
                Box::new(move || f.update(|f| f.toggle(cat, code))),
            ));
        }
        if cur.group_range_active() {
            out.push(chip(
                format!("{}: {}–{}", t("Grupo", "Group"), cur.group_min, cur.group_max),
                Box::new(move || {
                    f.update(|f| {
                        f.group_min = model::GROUP_MIN;
                        f.group_max = model::GROUP_MAX;
                    })
                }),
            ));
        }
        if cur.illustrated_only {
            out.push(chip(t("Con ilustración", "With illustration").into(), Box::new(move || f.update(|f| f.illustrated_only = false))));
        }
        if cur.saved_only {
            out.push(chip(t("Solo guardadas", "Saved only").into(), Box::new(move || f.update(|f| f.saved_only = false))));
        }
        out
    };

    view! {
        <div class="mb-4 flex flex-wrap items-center gap-2">
            <span class="text-sm text-gray-600 mr-2">
                {move || i.t("Resultados: ", "Results: ")} <span class="font-semibold text-gray-800">{move || format!("{}/{total}", shown.get())}</span>
            </span>
            {chips}
            <Show when=move || f.with(Filters::is_active)>
                <button class="text-xs text-primary-700 hover:underline ml-1" on:click=move |_| f.set(Filters::default())>
                    {move || i.t("Limpiar todo", "Clear all")}
                </button>
            </Show>
        </div>
    }
}

// ---------------------------------------------------------------------------
// Bookmarks persistence
// ---------------------------------------------------------------------------

fn storage() -> Option<web_sys::Storage> {
    web_sys::window()?.local_storage().ok().flatten()
}

fn load_saved() -> HashSet<i64> {
    storage()
        .and_then(|s| s.get_item(SAVED_KEY).ok().flatten())
        .and_then(|raw| serde_json::from_str::<Vec<i64>>(&raw).ok())
        .map(|ids| ids.into_iter().collect())
        .unwrap_or_default()
}

fn store_saved(ids: &HashSet<i64>) {
    let Some(s) = storage() else { return };
    let mut v: Vec<_> = ids.iter().copied().collect();
    v.sort_unstable();
    if let Ok(json) = serde_json::to_string(&v) {
        let _ = s.set_item(SAVED_KEY, &json);
    }
}
