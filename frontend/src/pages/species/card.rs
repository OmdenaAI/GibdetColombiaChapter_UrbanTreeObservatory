//! Grid card (layout from the team's "card blockframe" template), list table and shared pieces.
//!
//! Card, top to bottom: common name + functional-group tag, photo placeholder (the API has no
//! photos yet), scientific name, the four functional-group traits, and an icon strip with
//! flower color, habit, IUCN status, origin and canopy shape.

use std::sync::Arc;

use leptos::prelude::*;

use super::Ctx;
use super::model::{self, Species, TRAITS};
use crate::i18n::{I18n, Lang, pick};

const TH_SM: &str = "px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider";

/// Template colors.
pub(super) const NAME_BAR: &str = "bg-[#CBC3A3]";
pub(super) const SCI_BAR: &str = "bg-[#4B525E]";
/// Paper color of the illustrations, so `object-contain` letterboxing blends in.
pub(crate) const ILLUSTRATION_BG: &str = "bg-[#F8F1E1]";

pub(super) const ICON_BOOKMARK: &str = "M5 5a2 2 0 012-2h10a2 2 0 012 2v16l-7-3.5L5 21V5z";

/// Heroicons-style outline icon.
pub(super) fn svg(d: &'static str, class: &'static str) -> impl IntoView {
    view! {
        <svg xmlns="http://www.w3.org/2000/svg" class=class fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d=d />
        </svg>
    }
}

/// Codes are interpolated into SVG markup, so only short alphanumeric ones are accepted.
fn safe_code(code: &str) -> &str {
    if !code.is_empty() && code.len() <= 3 && code.chars().all(|c| c.is_ascii_alphanumeric()) {
        code
    } else {
        "?"
    }
}

/// Raw SVG markup rendered through `inner_html` (static shapes, codes checked by `safe_code`).
fn raw_svg(view_box: &'static str, class: &'static str, title: String, inner: String) -> impl IntoView {
    view! {
        <span class="inline-flex" title=title>
            <svg xmlns="http://www.w3.org/2000/svg" class=class viewBox=view_box inner_html=inner></svg>
        </span>
    }
}

// ---------------------------------------------------------------------------
// Strip icons
// ---------------------------------------------------------------------------

/// Colored drawing for each life form.
fn life_form_markup(code: &str) -> &'static str {
    match code {
        // Tree: round crown + trunk
        "TR" => r##"<path d="M17.5 22h5l1 15h-7z" fill="#92400E"/><path d="M20 30l-4-4M20 28l4-4" stroke="#92400E" stroke-width="2" stroke-linecap="round"/><circle cx="20" cy="13" r="9" fill="#16A34A"/><circle cx="12.5" cy="19" r="6.5" fill="#15803D"/><circle cx="27.5" cy="19" r="6.5" fill="#15803D"/><circle cx="20" cy="20" r="6" fill="#22C55E"/>"##,
        // Shrub: low wide bush
        "SH" => r##"<path d="M18.5 30h3v7h-3z" fill="#92400E"/><ellipse cx="11" cy="25" rx="8" ry="7" fill="#15803D"/><ellipse cx="29" cy="25" rx="8" ry="7" fill="#15803D"/><ellipse cx="20" cy="21" rx="10" ry="9" fill="#16A34A"/><ellipse cx="20" cy="27" rx="9" ry="5" fill="#22C55E"/>"##,
        // Palm: curved trunk + fronds
        "PT" => r##"<path d="M19 12c1 9 0 17-2 26h4c1.5-9 2-17 1-26z" fill="#A16207"/><path d="M20 12C15 6 8 6 3 10c5-1 10 0 17 2zM20 12c5-6 12-6 17-2-5-1-10 0-17 2zM20 12c-4-1-9 2-12 8 4-4 8-6 12-8zM20 12c4-1 9 2 12 8-4-4-8-6-12-8zM20 12c-1-5 1-9 5-11-2 4-3 7-5 11z" fill="#16A34A" stroke="#15803D" stroke-width=".8"/>"##,
        // Other: sprout
        _ => r##"<path d="M20 37V20" stroke="#15803D" stroke-width="3" stroke-linecap="round"/><path d="M20 22C12 22 7 16 7 8c8 0 13 6 13 14z" fill="#22C55E"/><path d="M20 20c0-7 5-12 13-12 0 7-5 12-13 12z" fill="#16A34A"/><path d="M8 37h24" stroke="#92400E" stroke-width="3" stroke-linecap="round"/>"##,
    }
}

pub(super) fn life_form_icon(l: Lang, code: &str, class: &'static str) -> impl IntoView + use<> {
    raw_svg(
        "0 0 40 40",
        class,
        format!("{}: {}", pick(l, "Hábito", "Habit"), model::life_form_label(l, code)),
        life_form_markup(code).to_string(),
    )
}

fn flower_icon(l: Lang, code: &str) -> impl IntoView + use<> {
    let (fill, text) = model::flower_fill(code);
    let petals = [(20.0, 8.0), (27.6, 13.5), (24.7, 22.5), (15.3, 22.5), (12.4, 13.5)]
        .iter()
        .map(|(x, y)| format!(r##"<circle cx="{x}" cy="{y}" r="6.5" fill="{fill}" stroke="#14532D" stroke-width="1.5"/>"##))
        .collect::<String>();
    let inner = format!(
        r##"<path d="M20 26v19" stroke="#14532D" stroke-width="2.5"/><path d="M20 41c-6 0-10-3.5-10-8 6 0 10 3 10 8zM20 41c6 0 10-3.5 10-8-6 0-10 3-10 8z" fill="#4ADE80" stroke="#14532D" stroke-width="1.5"/>{petals}<circle cx="20" cy="16" r="7.5" fill="{fill}"/><text x="20" y="19.6" text-anchor="middle" font-size="10" font-weight="700" font-family="sans-serif" fill="{text}">{}</text>"##,
        safe_code(code)
    );
    raw_svg("0 0 40 48", "h-12 w-10", format!("{}: {}", pick(l, "Color de la flor", "Flower color"), model::flower_label(l, code)), inner)
}

fn iucn_icon(l: Lang, code: &str) -> impl IntoView + use<> {
    let (bg, fg) = model::iucn_colors(code);
    let (label, ..) = model::iucn_info(l, code);
    view! {
        <span
            class="h-11 w-11 rounded-full border-2 border-gray-800 flex items-center justify-center font-bold text-base"
            style=format!("background:{bg};color:{fg}")
            title=format!("{}: {label}", pick(l, "UICN", "IUCN"))
        >
            {code.to_string()}
        </span>
    }
}

fn origin_icon(l: Lang, code: &str) -> impl IntoView + use<> {
    let inner = format!(
        r##"<path d="M20 2.5l17 12.3-6.5 20.2h-21L3 14.8z" fill="#DCDCF8" stroke="#111827" stroke-width="2" stroke-linejoin="round"/><text x="20" y="25" text-anchor="middle" font-size="11" font-weight="700" font-family="sans-serif" fill="#111827">{}</text>"##,
        safe_code(code)
    );
    raw_svg("0 0 40 38", "h-10 w-10", format!("{}: {}", pick(l, "Origen", "Origin"), model::origin_label(l, code)), inner)
}

fn canopy_icon(l: Lang, code: &str) -> impl IntoView + use<> {
    let inner = format!(
        r##"<circle cx="20" cy="20" r="17.5" fill="#E8799A" stroke="#111827" stroke-width="2.5"/><path d="M8 26a14 14 0 0 0 22 4" stroke="#D45C80" stroke-width="3" fill="none" stroke-linecap="round"/><text x="20" y="24" text-anchor="middle" font-size="11" font-weight="700" font-family="sans-serif" fill="#111827">{}</text>"##,
        safe_code(code)
    );
    raw_svg("0 0 40 40", "h-11 w-11", format!("{}: {}", pick(l, "Forma de la copa", "Canopy shape"), model::canopy_label(l, code)), inner)
}

/// Bottom strip inside a bracket frame (rounded border, open in the middle of each side).
fn icon_strip(l: Lang, s: &Species) -> impl IntoView + use<> {
    view! {
        <div class="relative mt-auto border-[3px] border-gray-900 rounded-xl px-2 py-1.5 flex items-center justify-around">
            <span class="absolute -left-[3px] top-1/4 bottom-1/4 w-[3px] bg-white"></span>
            <span class="absolute -right-[3px] top-1/4 bottom-1/4 w-[3px] bg-white"></span>
            {flower_icon(l, &s.flower_color)}
            {life_form_icon(l, &s.life_form, "h-11 w-11")}
            {iucn_icon(l, &s.iucn_status)}
            {origin_icon(l, &s.origin)}
            {canopy_icon(l, &s.canopy_shape)}
        </div>
    }
}

// ---------------------------------------------------------------------------
// Badges shared with the list and the detail sheet
// ---------------------------------------------------------------------------

/// Yellow arrow tag with the functional-group number (gray "–" without a group).
pub(super) fn group_tag(l: Lang, group: Option<u8>) -> impl IntoView + use<> {
    let (fill, text, title) = match group {
        Some(g) => ("#FCD116", g.to_string(), format!("{} {g}", pick(l, "Grupo funcional", "Functional group"))),
        None => ("#E5E7EB", "–".to_string(), pick(l, "Sin grupo funcional asignado", "No functional group assigned").to_string()),
    };
    view! {
        <span class="relative inline-flex h-8 w-14 shrink-0 items-center" title=title>
            <svg xmlns="http://www.w3.org/2000/svg" class="absolute inset-0 h-full w-full" viewBox="0 0 56 32" preserveAspectRatio="none">
                <path d="M3 1.5h40l11 14.5-11 14.5H3A1.5 1.5 0 0 1 1.5 29V3A1.5 1.5 0 0 1 3 1.5z" fill=fill stroke="#111827" stroke-width="1.5" />
            </svg>
            <span class="relative w-11 text-center text-lg font-medium text-gray-900">{text}</span>
        </span>
    }
}

pub(super) fn iucn_badge(l: Lang, code: &str) -> impl IntoView + use<> {
    let (label, _, desc) = model::iucn_info(l, code);
    let (bg, fg) = model::iucn_colors(code);
    view! {
        <span
            class="inline-flex items-center px-2 py-0.5 rounded text-xs font-semibold border border-gray-300"
            style=format!("background:{bg};color:{fg}")
            title=desc
        >
            {format!("{code} · {label}")}
        </span>
    }
}

pub(super) fn flower_swatch(l: Lang, code: &str) -> impl IntoView + use<> {
    let (_, es, en, swatch) = model::FLOWER_COLORS
        .iter()
        .copied()
        .find(|(c, ..)| *c == code)
        .unwrap_or(("NI", "Sin información", "No information", "border border-gray-400"));
    let label = pick(l, es, en);
    view! {
        <span class="inline-flex items-center gap-1.5 text-sm text-gray-800" title=pick(l, "Color de la flor", "Flower color")>
            <span class=format!("h-3 w-3 rounded-full {swatch}")></span>
            {label}
        </span>
    }
}

#[component]
pub(super) fn BookmarkButton(
    id: i64,
    ctx: Ctx,
    #[prop(default = "p-1 rounded hover:bg-black/10 text-gray-700")] class: &'static str,
) -> impl IntoView {
    let saved = move || ctx.is_saved(id);
    let i = I18n::use_ctx();
    view! {
        <button
            class=class
            title=move || if saved() { i.t("Quitar de guardadas", "Remove from saved") } else { i.t("Guardar especie", "Save species") }
            on:click=move |ev| {
                ev.stop_propagation();
                ctx.toggle_saved(id);
            }
        >
            <svg xmlns="http://www.w3.org/2000/svg" class="h-5 w-5" viewBox="0 0 24 24" stroke="currentColor"
                fill=move || if saved() { "currentColor" } else { "none" }>
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d=ICON_BOOKMARK />
            </svg>
        </button>
    }
}

/// Square illustration fitted in a wider box. A blurred, zoomed copy of the same image fills
/// the sides, so the letterboxing takes the paper color of each illustration.
pub(crate) fn illustration_img(l: Lang, src: String, scientific_name: &str) -> impl IntoView + use<> {
    view! {
        <img src=src.clone() alt="" aria-hidden="true" loading="lazy" decoding="async"
            class="absolute inset-0 h-full w-full object-cover scale-125 blur-xl" />
        <img src=src alt=format!("{} {scientific_name}", pick(l, "Ilustración de", "Illustration of")) loading="lazy" decoding="async"
            class="relative h-full w-full object-contain" />
    }
}

/// Gray "image" placeholder from the template (no species photos in the API yet).
pub(crate) fn photo_placeholder() -> impl IntoView {
    view! {
        <svg xmlns="http://www.w3.org/2000/svg" class="h-28 w-28" viewBox="0 0 64 64" aria-hidden="true">
            <rect x="14" y="4" width="36" height="56" rx="1.5" fill="#9AA0AB" />
            <circle cx="24" cy="18" r="5" fill="#fff" />
            <path d="M10 44l13-19 7 10 11-17 17 26z" fill="#fff" />
        </svg>
    }
}

// ---------------------------------------------------------------------------
// Card and table
// ---------------------------------------------------------------------------

#[component]
pub(super) fn SpeciesCard(species: Arc<Species>, ctx: Ctx, l: Lang) -> impl IntoView {
    let s = species.clone();
    let open = move |_| ctx.selected.set(Some(species.clone()));
    let common = s.common_name().map(str::to_string);
    let common_title = common.clone().unwrap_or_default();
    let illustration = s.illustration();
    let image_bg = if illustration.is_some() { ILLUSTRATION_BG } else { "bg-[#DFE1E6]" };

    view! {
        <article
            class="bg-white rounded-lg shadow hover:shadow-lg hover:-translate-y-0.5 transition cursor-pointer flex flex-col gap-3 p-3"
            on:click=open
        >
            <div class=format!("{NAME_BAR} rounded flex items-center gap-2 pl-3")>
                <h3
                    class="flex-1 min-w-0 text-center text-lg font-bold text-gray-900 truncate py-1"
                    title=common_title
                >
                    {common.unwrap_or_else(|| "—".into())}
                </h3>
                {group_tag(l, s.group())}
            </div>

            <div class=format!("relative h-48 flex items-center justify-center overflow-hidden {image_bg}")>
                {match illustration {
                    Some(src) => illustration_img(l, src, &s.scientific_name).into_any(),
                    None => photo_placeholder().into_any(),
                }}
                <BookmarkButton id=s.id ctx class="absolute top-2 right-2 p-1.5 rounded-full bg-white/80 hover:bg-white text-gray-800 shadow-sm" />
            </div>

            <div class=format!("{SCI_BAR} rounded px-3 py-1")>
                <h4 class="text-center text-lg font-semibold italic text-white truncate" title=s.scientific_name.clone()>
                    {s.scientific_name.clone()}
                </h4>
            </div>

            <dl class="px-1 text-sm text-gray-900 space-y-1">
                {TRAITS
                    .iter()
                    .map(|(ty, es, en)| {
                        let label = pick(l, *es, *en);
                        let v = s.trait_value(ty);
                        let v = if v == "—" { "-".to_string() } else { v };
                        view! { <div><dt class="inline">{format!("{label}: ")}</dt><dd class="inline font-medium">{v}</dd></div> }
                    })
                    .collect_view()}
            </dl>

            {icon_strip(l, &s)}
        </article>
    }
}

#[component]
pub(super) fn SpeciesTable(rows: Memo<Vec<Arc<Species>>>, ctx: Ctx, l: Lang) -> impl IntoView {
    view! {
        <div class="bg-white rounded-lg shadow overflow-x-auto">
            <table class="min-w-full divide-y divide-gray-200">
                <thead class="bg-gray-50">
                    <tr>
                        <th class=TH_SM>{pick(l, "Nombre común", "Common name")}</th>
                        <th class=TH_SM>{pick(l, "Nombre científico", "Scientific name")}</th>
                        <th class=TH_SM>{pick(l, "Familia", "Family")}</th>
                        <th class=TH_SM>{pick(l, "Hábito", "Habit")}</th>
                        <th class=TH_SM>{pick(l, "UICN", "IUCN")}</th>
                        <th class=TH_SM>{pick(l, "Grupo", "Group")}</th>
                        <th class=TH_SM><span class="sr-only">{pick(l, "Guardada", "Saved")}</span></th>
                    </tr>
                </thead>
                <tbody class="bg-white divide-y divide-gray-200">
                    <For
                        each=move || rows.get()
                        key=|s| s.id
                        children={move |s: Arc<Species>| {
                            let row = s.clone();
                            view! {
                                <tr class="hover:bg-gray-50 cursor-pointer" on:click=move |_| ctx.selected.set(Some(row.clone()))>
                                    <td class="px-4 py-2 whitespace-nowrap font-medium text-gray-900">{s.common_name().unwrap_or("—").to_string()}</td>
                                    <td class="px-4 py-2 whitespace-nowrap italic text-gray-800">{s.scientific_name.clone()}</td>
                                    <td class="px-4 py-2 whitespace-nowrap text-sm text-gray-600">{s.family().to_string()}</td>
                                    <td class="px-4 py-2 whitespace-nowrap text-sm text-gray-600">{model::life_form_label(l, &s.life_form)}</td>
                                    <td class="px-4 py-2 whitespace-nowrap">{iucn_badge(l, &s.iucn_status)}</td>
                                    <td class="px-4 py-2 whitespace-nowrap">{group_tag(l, s.group())}</td>
                                    <td class="px-4 py-2 whitespace-nowrap text-right"><BookmarkButton id=s.id ctx /></td>
                                </tr>
                            }
                        }}
                    />
                </tbody>
            </table>
        </div>
    }
}
