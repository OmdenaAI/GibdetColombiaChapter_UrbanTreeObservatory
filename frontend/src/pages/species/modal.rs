//! Species detail sheet (overlay). Closes on backdrop click, the X button or Escape.

use std::sync::Arc;

use leptos::prelude::*;
use leptos::task::spawn_local;

use super::card::{
    BookmarkButton, ILLUSTRATION_BG, NAME_BAR, SCI_BAR, illustration_img, plate_credit, flower_swatch, group_tag, iucn_badge, life_form_icon,
    photo_placeholder, svg,
};
use super::model::{self, ManualEntry, Species, TRAITS};
use super::{Ctx, ICON_X};
use crate::api::console_error;
use crate::i18n::{Lang, pick};

const ICON_EXTERNAL: &str = "M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14";
const LABEL: &str = "text-xs font-semibold text-gray-500 uppercase tracking-wider";

#[component]
pub(super) fn SpeciesModal(species: Arc<Species>, ctx: Ctx, l: Lang) -> impl IntoView {
    let close = move || ctx.selected.set(None);
    let handle = window_event_listener(leptos::ev::keydown, move |ev| {
        if ev.key() == "Escape" {
            close();
        }
    });
    on_cleanup(move || handle.remove());

    let s = species;
    let (_, _, iucn_desc) = model::iucn_info(l, &s.iucn_status);
    let accepted = s
        .accepted_scientific_name
        .clone()
        .filter(|a| !a.is_empty() && *a != s.scientific_name);
    let common = s.common_name().map(str::to_string);
    let illustration = s.illustration();
    let image_bg = if illustration.is_some() { ILLUSTRATION_BG } else { "bg-[#DFE1E6]" };

    // Sheet in the Tolima manual, fetched only for species that have one.
    let manual = RwSignal::new(None::<ManualEntry>);
    if s.has_manual_entry {
        let id = s.id;
        spawn_local(async move {
            match model::fetch_manual(id).await {
                // The sheet may have been closed before the answer arrived.
                Ok(m) => drop(manual.try_set(Some(m))),
                Err(e) => console_error("Manual entry", &e),
            }
        });
    }

    let t = move |es: &'static str, en: &'static str| pick(l, es, en);
    let fact = move |es: &'static str, en: &'static str, value: AnyView| {
        view! {
            <div>
                <dt class=LABEL>{t(es, en)}</dt>
                <dd class="mt-0.5 text-sm text-gray-900">{value}</dd>
            </div>
        }
    };

    let link = |href: Option<String>, label: &'static str| {
        href.filter(|h| !h.is_empty()).map(|h| {
            view! {
                <a href=h target="_blank" rel="noopener noreferrer"
                    class=format!("inline-flex items-center gap-1.5 px-4 py-2 rounded-lg {SCI_BAR} text-white text-sm font-medium hover:opacity-90")>
                    {label}
                    {svg(ICON_EXTERNAL, "h-4 w-4")}
                </a>
            }
        })
    };

    view! {
        <div class="fixed inset-0 z-50 bg-black/50 flex items-center justify-center p-4" on:click=move |_| close()>
            <div
                class="bg-white rounded-lg shadow-xl w-full max-w-3xl max-h-[90vh] overflow-y-auto p-5 space-y-4"
                role="dialog"
                aria-modal="true"
                on:click=|ev| ev.stop_propagation()
            >
                // Common name bar (template header) + actions
                <div class="flex items-center gap-2">
                    <div class=format!("{NAME_BAR} flex-1 min-w-0 rounded flex items-center gap-2 pl-3")>
                        <h2 class="flex-1 min-w-0 text-center text-2xl font-bold text-gray-900 truncate py-1">
                            {common.unwrap_or_else(|| "—".into())}
                        </h2>
                        {group_tag(l, s.group())}
                    </div>
                    <BookmarkButton id=s.id ctx />
                    <button class="p-1 rounded hover:bg-black/10 text-gray-700" title=t("Cerrar", "Close") on:click=move |_| close()>
                        {svg(ICON_X, "h-6 w-6")}
                    </button>
                </div>

                <div class="grid gap-4 sm:grid-cols-[2fr_3fr]">
                    <div class="flex flex-col gap-1">
                        <div class=format!("relative overflow-hidden h-64 sm:h-auto sm:min-h-[16rem] sm:flex-1 flex items-center justify-center {image_bg}")>
                            {match illustration {
                                Some(src) => illustration_img(l, src, &s.scientific_name).into_any(),
                                None => photo_placeholder().into_any(),
                            }}
                        </div>
                        {s.plate().map(|p| plate_credit(l, p))}
                    </div>
                    <div class="space-y-3">
                        <div class=format!("{SCI_BAR} rounded px-3 py-1.5 text-white")>
                            <h3 class="text-xl font-semibold italic">{s.scientific_name.clone()}</h3>
                            {accepted.map(|a| view! { <p class="text-sm text-gray-200">{t("Nombre aceptado: ", "Accepted name: ")} <i>{a}</i></p> })}
                        </div>
                        <dl class="grid grid-cols-2 gap-3">
                            {fact("Familia", "Family", s.family().to_string().into_any())}
                            {fact("Género", "Genus", view! { <i>{s.genus.name.clone()}</i> }.into_any())}
                            {fact("Hábito", "Habit", view! {
                                <span class="inline-flex items-center gap-1">
                                    {life_form_icon(l, &s.life_form, "h-6 w-6")}
                                    {model::life_form_label(l, &s.life_form)}
                                </span>
                            }.into_any())}
                            {fact("Origen", "Origin", model::origin_label(l, &s.origin).into_any())}
                            {fact("Forma de la copa", "Canopy shape", model::canopy_label(l, &s.canopy_shape).into_any())}
                            {fact("Color de la flor", "Flower color", flower_swatch(l, &s.flower_color).into_any())}
                        </dl>
                    </div>
                </div>

                <div class="rounded-lg border border-gray-200 p-4">
                    <div class="flex items-center gap-2 mb-1">
                        <span class=LABEL>{t("Lista Roja de la UICN", "IUCN Red List")}</span>
                        {iucn_badge(l, &s.iucn_status)}
                    </div>
                    <p class="text-sm text-gray-700">{iucn_desc}</p>
                </div>

                {move || manual.get().map(|m| manual_section(l, m))}

                <div>
                    <h4 class=format!("{LABEL} mb-2")>
                        {match s.group() {
                            Some(g) => pick(l, format!("Grupo funcional {g} — rasgos"), format!("Functional group {g} — traits")),
                            None => t("Rasgos del grupo funcional", "Functional-group traits").to_string(),
                        }}
                    </h4>
                    {if s.functional_group.is_some() {
                        view! {
                            <div class="grid grid-cols-2 sm:grid-cols-4 gap-3">
                                {TRAITS.iter().map(|(ty, es, en)| view! {
                                    <div class="rounded-lg border border-gray-200 px-3 py-2">
                                        <div class="text-xs text-gray-500">{t(es, en)}</div>
                                        <div class="text-lg font-semibold text-gray-900">{s.trait_value(ty)}</div>
                                    </div>
                                }).collect_view()}
                            </div>
                            <p class="mt-2 text-xs text-gray-400">{t("Los rangos son los valores registrados para el grupo funcional de la especie.", "Ranges are the values recorded for the species' functional group.")}</p>
                        }
                        .into_any()
                    } else {
                        view! { <p class="text-sm text-gray-400 italic">{t("Esta especie aún no tiene grupo funcional asignado.", "This species has no functional group assigned yet.")}</p> }.into_any()
                    }}
                </div>

                <div class="flex flex-wrap items-center justify-between gap-3 border-t border-gray-100 pt-4">
                    <div class="flex flex-wrap gap-2">
                        {link(s.gbif_url.clone(), "GBIF")}
                        {link(s.tropical_plants_url.clone(), "Tropical Plants")}
                    </div>
                    <span class="text-xs text-gray-400">
                        {s.identified_by.clone().filter(|v| !v.is_empty()).map(|v| format!("{} {v}", t("Identificada por", "Identified by")))}
                    </span>
                </div>
            </div>
        </div>
    }
}

/// The species' sheet in the Tolima arborization manual, verbatim and in the manual's order:
/// header fields, then one collapsible block per section ("Descripción" open), then the source.
fn manual_section(l: Lang, m: ManualEntry) -> impl IntoView {
    let t = move |es: &'static str, en: &'static str| pick(l, es, en);
    let pages = m.pages();
    let (binomial, author) = m.name_parts();
    let (binomial, author) = (binomial.to_string(), author.to_string());
    view! {
        <section class="rounded-lg border border-gray-200 p-4 space-y-3" lang="es">
            <div class="flex flex-wrap items-baseline justify-between gap-2">
                <h4 class=LABEL>{t("Manual de arborización del Tolima", "Tolima arborization manual")}</h4>
                {(l != Lang::Es).then(|| view! {
                    <span class="text-xs text-gray-400 italic" lang="en">"Original text in Spanish"</span>
                })}
            </div>
            <div class="text-sm text-gray-800 space-y-0.5">
                <p>
                    <span class="font-semibold">"Nombre científico: "</span>
                    <i>{binomial}</i>
                    {(!author.is_empty()).then(|| format!(" {author}"))}
                </p>
                {m.header.into_iter().map(|f| view! {
                    <p><span class="font-semibold">{f.label}": "</span>{f.value}</p>
                }).collect_view()}
            </div>
            <div class="divide-y divide-gray-100 border-y border-gray-100">
                {m.sections.into_iter().map(|sec| {
                    let open = sec.title == "Descripción";
                    view! {
                        <details class="group py-2" open=open>
                            <summary class="cursor-pointer select-none text-sm font-semibold text-gray-900 marker:text-gray-400">
                                {sec.title}
                            </summary>
                            <div class="mt-1.5 space-y-2 text-sm text-gray-700 leading-relaxed">
                                {sec.text.split("\n\n").map(|para| view! {
                                    <p>
                                        {model::bold_runs(para).into_iter().map(|(run, bold)| {
                                            let run = run.to_string();
                                            if bold { view! { <strong>{run}</strong> }.into_any() } else { run.into_any() }
                                        }).collect_view()}
                                    </p>
                                }).collect_view()}
                            </div>
                        </details>
                    }
                }).collect_view()}
            </div>
            <p class="text-xs text-gray-500">
                {t("Fuente: ", "Source: ")}{m.source}", "<span class="whitespace-nowrap">{pages}"."</span>
            </p>
        </section>
    }
}
