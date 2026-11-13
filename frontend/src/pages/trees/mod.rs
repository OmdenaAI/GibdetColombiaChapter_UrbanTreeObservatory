//! Tree inventory (read-only): search the census by ID, species, family, neighborhood and
//! health status, open a tree's full record, and export the selection or every matching
//! tree to CSV. Adding, editing and deleting trees is done in the Django admin.
//!
//! Data: `/api/v1/biodiversity/inventory/` (paginated list, detail, CSV export).

mod detail;
mod export;
mod minimap;

use std::collections::HashSet;
use std::time::Duration;

use leptos::prelude::*;
use leptos::task::spawn_local;
use serde::Deserialize;

use super::shared::{HEALTH, health_badge, health_label};
use super::species::model::fmt_num;
use crate::api::{API_BASE, console_error, fmt_thousands, get_json};
use crate::i18n::{I18n, pick};

fn inventory_url() -> String {
    format!("{API_BASE}/api/v1/biodiversity/inventory/")
}

const PAGE_SIZE: u64 = 25;
/// Text filters are applied after the user stops typing for this long.
const DEBOUNCE: Duration = Duration::from_millis(350);

const TH: &str = "px-3 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider whitespace-nowrap";
const TD: &str = "px-3 py-2.5 text-sm text-gray-700 whitespace-nowrap";
const INPUT: &str = "w-full border border-gray-300 rounded-md px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary-500";
const LABEL: &str = "text-xs font-medium text-gray-600 block mb-1";
const BTN: &str = "inline-flex items-center gap-2 font-medium py-2 px-4 rounded-lg text-sm disabled:opacity-50 disabled:cursor-not-allowed";
const ICON_DOWNLOAD: &str = "M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4";

#[derive(Clone, Deserialize, PartialEq)]
struct Row {
    id: i64,
    common_name: Option<String>,
    scientific_name: String,
    family: String,
    neighborhood: String,
    locality: String,
    height_m: Option<f64>,
    dbh_cm: Option<f64>,
    phytosanitary_status: Option<String>,
    date: Option<String>,
}

#[derive(Clone, Deserialize)]
struct Page {
    count: u64,
    results: Vec<Row>,
}

#[derive(Clone, Default, PartialEq)]
struct Filters {
    id: String,
    species: String,
    family: String,
    neighborhood: String,
    health: String,
}

impl Filters {
    fn is_active(&self) -> bool {
        *self != Self::default()
    }

    /// Query string for the API (`a=1&b=x`), empty values left out.
    fn query(&self) -> String {
        [
            ("id", self.id.trim()),
            ("species", self.species.trim()),
            ("family", self.family.trim()),
            ("neighborhood", self.neighborhood.trim()),
            ("health", self.health.as_str()),
        ]
        .iter()
        .filter(|(_, v)| !v.is_empty())
        .map(|(k, v)| format!("{k}={}", String::from(js_sys::encode_uri_component(v))))
        .collect::<Vec<_>>()
        .join("&")
    }
}

#[derive(Clone)]
enum Load {
    Loading,
    Failed,
    Ready(Page),
}

#[component]
pub fn Trees() -> impl IntoView {
    let i = I18n::use_ctx();
    // `draft` follows the inputs; `filters` is what was last sent to the API.
    let draft = RwSignal::new(Filters::default());
    let filters = RwSignal::new(Filters::default());
    let page = RwSignal::new(1u64);
    let data = RwSignal::new(Load::Loading);
    let selected = RwSignal::new(HashSet::<i64>::new());
    let open_tree = RwSignal::new(None::<i64>);
    let export_error = RwSignal::new(None::<String>);
    let exporting = RwSignal::new(false);
    // Ignores responses that arrive after a newer request was sent.
    let request_seq = StoredValue::new(0u64);
    let typing_seq = StoredValue::new(0u64);
    let retry = RwSignal::new(0u32);

    Effect::new(move |_| {
        let query = filters.get().query();
        let page_no = page.get();
        retry.track();
        let seq = request_seq.get_value() + 1;
        request_seq.set_value(seq);
        data.set(Load::Loading);
        spawn_local(async move {
            let sep = if query.is_empty() { "" } else { "&" };
            let url = format!("{}?page={page_no}&page_size={PAGE_SIZE}{sep}{query}", inventory_url());
            let res = get_json(&url)
                .await
                .and_then(|v| serde_json::from_value::<Page>(v).map_err(|e| e.to_string()));
            if request_seq.try_get_value() != Some(seq) {
                return;
            }
            match res {
                Ok(p) => data.try_set(Load::Ready(p)),
                Err(e) => {
                    console_error("Error loading the tree inventory:", &e);
                    data.try_set(Load::Failed)
                }
            };
        });
    });

    let apply = move |f: Filters| {
        if f != filters.get_untracked() {
            page.set(1);
            filters.set(f);
        }
    };
    // Text inputs: apply once typing pauses. Select / Enter / Clear: apply at once.
    let edit = move |change: Box<dyn FnOnce(&mut Filters)>, debounce: bool| {
        draft.update(|d| change(d));
        let seq = typing_seq.get_value() + 1;
        typing_seq.set_value(seq);
        if debounce {
            set_timeout(
                move || {
                    if typing_seq.try_get_value() == Some(seq) {
                        apply(draft.get_untracked());
                    }
                },
                DEBOUNCE,
            );
        } else {
            apply(draft.get_untracked());
        }
    };

    let count = move || match data.get() {
        Load::Ready(p) => Some(p.count),
        _ => None,
    };

    let export_selected = move |_| {
        let ids: Vec<i64> = {
            let mut v: Vec<i64> = selected.get_untracked().into_iter().collect();
            v.sort_unstable();
            v
        };
        if ids.is_empty() {
            return;
        }
        exporting.set(true);
        export_error.set(None);
        spawn_local(async move {
            let url = format!("{}export/?lang={}", inventory_url(), i.lang_untracked().code());
            let res = export::download_selected(&url, &ids).await;
            exporting.try_set(false);
            if let Err(e) = res {
                console_error("CSV export failed:", &e);
                export_error.try_set(Some(e));
            }
        });
    };
    let export_all = move |_| {
        export_error.set(None);
        let query = filters.get_untracked().query();
        let sep = if query.is_empty() { "" } else { "&" };
        let query = format!("lang={}{sep}{query}", i.lang_untracked().code());
        export::download_filtered(&format!("{}export/", inventory_url()), &query);
    };

    view! {
        <div class="bg-white shadow rounded-lg p-6 space-y-5">
            // Header
            <div class="flex flex-col md:flex-row md:items-end justify-between gap-4">
                <div>
                    <h1 class="text-2xl font-bold text-primary-600">{move || i.t("Inventario de árboles", "Tree Inventory")}</h1>
                    <p class="text-sm text-gray-500 mt-1">
                        {move || i.t("Censo de arbolado urbano de Ibagué (Cortolima). Solo consulta: los árboles se agregan y editan en el ", "Urban tree census of Ibagué (Cortolima). Read-only: trees are added and edited in the ")}
                        <a href=format!("{API_BASE}/admin/") target="_blank" rel="noopener noreferrer" class="text-primary-700 hover:underline">{move || i.t("sitio de administración", "administration site")}</a>
                        "."
                    </p>
                </div>
                <div class="flex flex-wrap gap-2">
                    <button
                        class=format!("{BTN} border border-primary-600 text-primary-700 hover:bg-primary-50")
                        disabled=move || selected.with(|s| s.is_empty()) || exporting.get()
                        on:click=export_selected
                        title=move || i.t("Descargar los árboles seleccionados en CSV", "Download the selected trees as CSV")
                    >
                        {download_icon()}
                        {move || if exporting.get() {
                            i.t("Exportando…", "Exporting…").to_string()
                        } else {
                            format!("{} ({})", i.t("Exportar selección", "Export selected"), fmt_thousands(selected.with(|s| s.len()) as i64))
                        }}
                    </button>
                    <button
                        class=format!("{BTN} bg-green-600 hover:bg-green-700 text-white")
                        disabled=move || count() == Some(0)
                        on:click=export_all
                        title=move || i.t("Descargar en CSV todos los árboles que cumplen los filtros", "Download every tree matching the filters as CSV")
                    >
                        {download_icon()}
                        {move || {
                            let n = count().map(|n| format!(" ({})", fmt_thousands(n as i64))).unwrap_or_default();
                            if filters.with(Filters::is_active) {
                                format!("{}{n}", i.t("Exportar filtrados", "Export filtered"))
                            } else {
                                format!("{}{n}", i.t("Exportar todo", "Export all"))
                            }
                        }}
                    </button>
                </div>
            </div>
            {move || export_error.get().map(|e| view! {
                <p class="text-sm text-red-600">{format!("{} ({e}).", i.t("No se pudo exportar la selección", "Could not export the selection"))}</p>
            })}

            // Filters
            <form
                class="grid grid-cols-2 md:grid-cols-6 gap-3 items-end"
                on:submit=move |ev| {
                    ev.prevent_default();
                    edit(Box::new(|_| {}), false);
                }
            >
                <div>
                    <label for="filterId" class=LABEL>"ID"</label>
                    <input id="filterId" type="number" min="1" inputmode="numeric" class=INPUT placeholder=move || i.t("ej. 95817", "e.g. 95817")
                        prop:value=move || draft.with(|d| d.id.clone())
                        on:input=move |ev| { let v = event_target_value(&ev); edit(Box::new(move |d| d.id = v), true) } />
                </div>
                <div class="col-span-2 md:col-span-1">
                    <label for="filterSpecies" class=LABEL>{move || i.t("Especie", "Species")}</label>
                    <input id="filterSpecies" type="search" class=INPUT placeholder=move || i.t("Nombre científico o común", "Scientific or common name")
                        prop:value=move || draft.with(|d| d.species.clone())
                        on:input=move |ev| { let v = event_target_value(&ev); edit(Box::new(move |d| d.species = v), true) } />
                </div>
                <div>
                    <label for="filterFamily" class=LABEL>{move || i.t("Familia", "Family")}</label>
                    <input id="filterFamily" type="search" class=INPUT placeholder=move || i.t("ej. Fabaceae", "e.g. Fabaceae")
                        prop:value=move || draft.with(|d| d.family.clone())
                        on:input=move |ev| { let v = event_target_value(&ev); edit(Box::new(move |d| d.family = v), true) } />
                </div>
                <div>
                    <label for="filterNeighborhood" class=LABEL>{move || i.t("Barrio", "Neighborhood")}</label>
                    <input id="filterNeighborhood" type="search" class=INPUT placeholder=move || i.t("ej. Belén", "e.g. Belen")
                        prop:value=move || draft.with(|d| d.neighborhood.clone())
                        on:input=move |ev| { let v = event_target_value(&ev); edit(Box::new(move |d| d.neighborhood = v), true) } />
                </div>
                <div>
                    <label for="filterHealth" class=LABEL>{move || i.t("Estado de salud", "Health status")}</label>
                    <select id="filterHealth" class=INPUT
                        prop:value=move || draft.with(|d| d.health.clone())
                        on:change=move |ev| { let v = event_target_value(&ev); edit(Box::new(move |d| d.health = v), false) }>
                        <option value="">{move || i.t("Todos", "All")}</option>
                        {HEALTH.iter().map(|(code, es, en, ..)| view! { <option value=*code>{move || i.t(es, en)}</option> }).collect_view()}
                    </select>
                </div>
                <div>
                    <button
                        type="button"
                        class="w-full border border-gray-300 rounded-md px-3 py-2 text-sm text-gray-700 hover:bg-gray-50 disabled:opacity-50"
                        disabled=move || !draft.with(Filters::is_active)
                        on:click=move |_| edit(Box::new(|d| *d = Filters::default()), false)
                    >
                        {move || i.t("Limpiar filtros", "Clear filters")}
                    </button>
                </div>
            </form>

            // Selection bar
            {move || {
                let n = selected.with(|s| s.len());
                (n > 0).then(|| view! {
                    <div class="flex items-center justify-between rounded-md bg-primary-50 border border-primary-100 px-3 py-2 text-sm text-primary-800">
                        <span>{move || {
                            let n_txt = fmt_thousands(n as i64);
                            if i.is_es() {
                                format!("{n_txt} árbol{} seleccionado{} (se conservan entre páginas y búsquedas)", if n == 1 { "" } else { "es" }, if n == 1 { "" } else { "s" })
                            } else {
                                format!("{n_txt} tree{} selected (kept across pages and searches)", if n == 1 { "" } else { "s" })
                            }
                        }}</span>
                        <button class="font-medium hover:underline" on:click=move |_| selected.update(HashSet::clear)>{move || i.t("Quitar selección", "Clear selection")}</button>
                    </div>
                })
            }}

            <TreesTable data selected open_tree retry />
            <Pager data page />

            {move || open_tree.get().map(|id| view! { <detail::TreeDetail id on_close=Callback::new(move |_| open_tree.set(None)) /> })}
        </div>
    }
}

fn download_icon() -> impl IntoView {
    view! {
        <svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d=ICON_DOWNLOAD />
        </svg>
    }
}

fn opt_num(v: Option<f64>) -> String {
    v.map(fmt_num).unwrap_or_else(|| "—".into())
}

#[component]
fn TreesTable(
    data: RwSignal<Load>,
    selected: RwSignal<HashSet<i64>>,
    open_tree: RwSignal<Option<i64>>,
    retry: RwSignal<u32>,
) -> impl IntoView {
    let i = I18n::use_ctx();
    let page_ids = move || match data.get() {
        Load::Ready(p) => p.results.iter().map(|r| r.id).collect::<Vec<_>>(),
        _ => Vec::new(),
    };
    let all_on_page = move || {
        let ids = page_ids();
        !ids.is_empty() && selected.with(|s| ids.iter().all(|id| s.contains(id)))
    };
    let toggle_page = move |_| {
        let ids = page_ids();
        let select = !all_on_page();
        selected.update(|s| {
            for id in ids {
                if select { s.insert(id); } else { s.remove(&id); }
            }
        });
    };

    let row = move |r: Row| {
        let id = r.id;
        let status = r.phytosanitary_status.clone().unwrap_or_else(|| "NR".into());
        let badge = health_badge(&status);
        view! {
            <tr class="hover:bg-gray-50" class:bg-primary-50=move || selected.with(|s| s.contains(&id))>
                <td class="pl-4 pr-2 py-2.5">
                    <input type="checkbox" class="h-4 w-4 rounded border-gray-300 text-primary-600"
                        aria-label=move || format!("{} {id}", i.t("Seleccionar árbol", "Select tree"))
                        prop:checked=move || selected.with(|s| s.contains(&id))
                        on:change=move |_| selected.update(|s| if !s.remove(&id) { s.insert(id); }) />
                </td>
                <td class=format!("{TD} font-medium text-gray-900")>{id}</td>
                <td class="px-3 py-2.5 text-sm">
                    <div class="text-gray-900">{r.common_name.clone().unwrap_or_else(|| "—".into())}</div>
                    <div class="text-gray-500 italic">{r.scientific_name.clone()}</div>
                </td>
                <td class=TD>{r.family.clone()}</td>
                <td class="px-3 py-2.5 text-sm text-gray-700">
                    <div>{r.neighborhood.clone()}</div>
                    <div class="text-xs text-gray-500">{r.locality.clone()}</div>
                </td>
                <td class=format!("{TD} text-right")>{opt_num(r.height_m)}</td>
                <td class=format!("{TD} text-right")>{opt_num(r.dbh_cm)}</td>
                <td class=TD>
                    <span class=format!("px-2 inline-flex text-xs leading-5 font-semibold rounded-full {badge}")>
                        {move || health_label(i.lang(), &status)}
                    </span>
                </td>
                <td class=TD>{r.date.clone().unwrap_or_else(|| "—".into())}</td>
                <td class=TD>
                    <button class="text-indigo-600 hover:text-indigo-900 font-medium" on:click=move |_| open_tree.set(Some(id))>{move || i.t("Ver", "View")}</button>
                </td>
            </tr>
        }
    };

    let body = move || match data.get() {
        Load::Loading => view! {
            <tr><td colspan="10" class="px-3 py-10 text-center text-sm text-gray-500">{move || i.t("Cargando árboles…", "Loading trees…")}</td></tr>
        }.into_any(),
        Load::Failed => view! {
            <tr><td colspan="10" class="px-3 py-10 text-center text-sm text-red-600">
                {move || i.t("No se pudo cargar el inventario. ", "Could not load the inventory. ")}
                <button class="underline font-medium" on:click=move |_| retry.update(|n| *n += 1)>{move || i.t("Reintentar", "Retry")}</button>
            </td></tr>
        }.into_any(),
        Load::Ready(p) if p.results.is_empty() => view! {
            <tr><td colspan="10" class="px-3 py-10 text-center text-sm text-gray-500">{move || i.t("Ningún árbol cumple estos filtros.", "No trees match these filters.")}</td></tr>
        }.into_any(),
        Load::Ready(p) => p.results.into_iter().map(row).collect_view().into_any(),
    };

    view! {
        <div class="overflow-x-auto border border-gray-200 rounded-lg">
            <table class="min-w-full divide-y divide-gray-200">
                <thead class="bg-gray-50">
                    <tr>
                        <th scope="col" class="pl-4 pr-2 py-3 w-8">
                            <input type="checkbox" class="h-4 w-4 rounded border-gray-300 text-primary-600"
                                title=move || i.t("Seleccionar todos los árboles de esta página", "Select all trees on this page")
                                aria-label=move || i.t("Seleccionar todos los árboles de esta página", "Select all trees on this page")
                                prop:checked=all_on_page on:change=toggle_page />
                        </th>
                        <th scope="col" class=TH>"ID"</th>
                        <th scope="col" class=TH>{move || i.t("Especie", "Species")}</th>
                        <th scope="col" class=TH>{move || i.t("Familia", "Family")}</th>
                        <th scope="col" class=TH>{move || i.t("Barrio", "Neighborhood")}</th>
                        <th scope="col" class=format!("{TH} text-right")>{move || i.t("Altura (m)", "Height (m)")}</th>
                        <th scope="col" class=format!("{TH} text-right")>{move || i.t("DAP (cm)", "DBH (cm)")}</th>
                        <th scope="col" class=TH>{move || i.t("Salud", "Health")}</th>
                        <th scope="col" class=TH>{move || i.t("Registrado", "Recorded")}</th>
                        <th scope="col" class=TH><span class="sr-only">{move || i.t("Acciones", "Actions")}</span></th>
                    </tr>
                </thead>
                <tbody class="bg-white divide-y divide-gray-200">{body}</tbody>
            </table>
        </div>
    }
}

#[component]
fn Pager(data: RwSignal<Load>, page: RwSignal<u64>) -> impl IntoView {
    let i = I18n::use_ctx();
    // Keep the last known total while the next page loads, so the pager doesn't jump.
    let total = Memo::new(move |prev: Option<&u64>| match data.get() {
        Load::Ready(p) => p.count,
        _ => prev.copied().unwrap_or(0),
    });
    let pages = move || total.get().div_ceil(PAGE_SIZE).max(1);
    let btn = "px-3 py-1.5 border border-gray-300 rounded-md text-sm text-gray-700 bg-white hover:bg-gray-50 disabled:opacity-40 disabled:cursor-not-allowed";
    let go = move |p: u64| page.set(p.clamp(1, pages()));

    view! {
        <div class="flex flex-col sm:flex-row items-center justify-between gap-3">
            <p class="text-sm text-gray-700">
                {move || {
                    let t = total.get();
                    if t == 0 {
                        i.t("Sin resultados", "No results").to_string()
                    } else {
                        let from = (page.get() - 1) * PAGE_SIZE + 1;
                        let to = (page.get() * PAGE_SIZE).min(t);
                        let (from, to, t) = (fmt_thousands(from as i64), fmt_thousands(to as i64), fmt_thousands(t as i64));
                        pick(i.lang(), format!("Mostrando {from} a {to} de {t} árboles"), format!("Showing {from} to {to} of {t} trees"))
                    }
                }}
            </p>
            <nav class="flex items-center gap-2" aria-label=move || i.t("Paginación", "Pagination")>
                <button class=btn disabled={move || page.get() <= 1} on:click=move |_| go(1)>{move || i.t("Primera", "First")}</button>
                <button class=btn disabled={move || page.get() <= 1} on:click=move |_| go(page.get_untracked() - 1)>{move || i.t("Anterior", "Previous")}</button>
                <span class="text-sm text-gray-700 px-1">
                    {move || format!("{} {} {} {}", i.t("Página", "Page"), fmt_thousands(page.get() as i64), i.t("de", "of"), fmt_thousands(pages() as i64))}
                </span>
                <button class=btn disabled={move || page.get() >= pages()} on:click=move |_| go(page.get_untracked() + 1)>{move || i.t("Siguiente", "Next")}</button>
                <button class=btn disabled={move || page.get() >= pages()} on:click=move |_| go(pages())>{move || i.t("Última", "Last")}</button>
            </nav>
        </div>
    }
}

#[cfg(test)]
mod tests {
    use super::Filters;

    #[test]
    fn empty_filters_send_no_query() {
        // Non-empty values go through `encode_uri_component` (JS), checked in the browser.
        let f = Filters { species: " rosea ".into(), ..Default::default() };
        assert!(f.is_active());
        assert!(!Filters::default().is_active());
        assert_eq!(Filters { id: "  ".into(), ..Default::default() }.query(), "");
    }
}
