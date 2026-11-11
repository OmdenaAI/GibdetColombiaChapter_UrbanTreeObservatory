//! Left filter panel: text searches, functional-group range and multi-select categories.

use leptos::prelude::*;

use super::Ctx;
use crate::i18n::I18n;
use super::model::{self, CANOPIES, Catalog, Category, Filters, GROUP_MAX, GROUP_MIN, IUCN, LIFE_FORMS, ORIGINS};

const INPUT: &str = "w-full border border-gray-300 rounded-lg py-1.5 px-3 text-sm focus:outline-none focus:ring-2 focus:ring-primary-500";

type Opt = (&'static str, &'static str, &'static str, Option<&'static str>);

/// Options of a category: (code, Spanish, English, optional color swatch classes).
fn options(cat: Category) -> Vec<Opt> {
    match cat {
        Category::FlowerColor => model::FLOWER_COLORS.iter().map(|(c, es, en, s)| (*c, *es, *en, Some(*s))).collect(),
        Category::LifeForm => LIFE_FORMS.iter().map(|(c, es, en)| (*c, *es, *en, None)).collect(),
        Category::Iucn => IUCN.iter().map(|c| (c.code, c.es, c.en, None)).collect(),
        Category::Origin => ORIGINS.iter().map(|(c, es, en)| (*c, *es, *en, None)).collect(),
        Category::Canopy => CANOPIES.iter().map(|(c, es, en)| (*c, *es, *en, None)).collect(),
    }
}

/// (category, Spanish title, English title, open by default)
const SECTIONS: [(Category, &str, &str, bool); 5] = [
    (Category::LifeForm, "Hábito", "Habit", true),
    (Category::Iucn, "Estado de conservación (UICN)", "Conservation status (IUCN)", true),
    (Category::Origin, "Origen", "Origin", true),
    (Category::FlowerColor, "Color de la flor", "Flower color", false),
    (Category::Canopy, "Forma de la copa", "Canopy shape", false),
];

#[component]
pub(super) fn FilterSidebar(catalog: Catalog, ctx: Ctx) -> impl IntoView {
    let f = ctx.filters;
    let i = I18n::use_ctx();
    let illustrated = catalog.iter().filter(|s| s.illustration().is_some()).count();

    let group_select = move |is_min: bool| {
        view! {
            <select
                class="flex-1 border border-gray-300 rounded-lg py-1.5 px-2 text-sm bg-white focus:outline-none focus:ring-2 focus:ring-primary-500"
                prop:value=move || f.with(|f| if is_min { f.group_min } else { f.group_max }.to_string())
                on:change=move |ev| {
                    let v: u8 = event_target_value(&ev).parse().unwrap_or(if is_min { GROUP_MIN } else { GROUP_MAX });
                    f.update(|f| {
                        if is_min {
                            f.group_min = v;
                            f.group_max = f.group_max.max(v);
                        } else {
                            f.group_max = v;
                            f.group_min = f.group_min.min(v);
                        }
                    });
                }
            >
                {(GROUP_MIN..=GROUP_MAX).map(|g| view! { <option value=g.to_string()>{g.to_string()}</option> }).collect_view()}
            </select>
        }
    };

    let sections = SECTIONS
        .into_iter()
        .map(|(cat, title_es, title_en, open)| {
            let items = options(cat)
                .into_iter()
                .map(|(code, es, en, swatch)| {
                    let count = catalog.iter().filter(|s| cat.value(s) == code).count();
                    view! {
                        <label class="flex items-center gap-2 py-0.5 text-sm text-gray-700 cursor-pointer hover:text-primary-700">
                            <input
                                type="checkbox"
                                class="rounded border-gray-300 accent-primary-600"
                                prop:checked=move || f.with(|f| f.is_selected(cat, code))
                                on:change=move |_| f.update(|f| f.toggle(cat, code))
                            />
                            {swatch.map(|s| view! { <span class=format!("h-3 w-3 rounded-full shrink-0 {s}")></span> })}
                            <span class="flex-1 truncate">{move || i.t(es, en)}</span>
                            <span class="text-xs text-gray-400">{count}</span>
                        </label>
                    }
                })
                .collect_view();
            view! {
                <details class="border-t border-gray-100 pt-3" open=open>
                    <summary class="text-xs font-semibold text-gray-500 uppercase tracking-wider cursor-pointer select-none mb-1">
                        {move || i.t(title_es, title_en)}
                    </summary>
                    <div class="mt-1">{items}</div>
                </details>
            }
        })
        .collect_view();

    view! {
        <aside class="w-64 shrink-0 bg-white rounded-lg shadow p-4 overflow-y-auto space-y-3">
            <h2 class="text-sm font-semibold text-gray-800">{move || i.t("Filtros", "Filters")}</h2>

            <TextFilter label=("Nombre común", "Common name") placeholder=("p. ej. Guayacán", "e.g. Guayacán") ctx get=|f| &f.common_name set=|f| &mut f.common_name />
            <TextFilter label=("Nombre científico", "Scientific name") placeholder=("Género o especie, p. ej. Ficus", "Genus or species, e.g. Ficus") ctx get=|f| &f.scientific_name set=|f| &mut f.scientific_name />
            <TextFilter label=("Familia", "Family") placeholder=("p. ej. Fabaceae", "e.g. Fabaceae") ctx get=|f| &f.family set=|f| &mut f.family />

            <label class="flex items-center gap-2 text-sm text-gray-700 cursor-pointer hover:text-primary-700">
                <input
                    type="checkbox"
                    class="rounded border-gray-300 accent-primary-600"
                    prop:checked=move || f.with(|f| f.illustrated_only)
                    on:change=move |_| f.update(|f| f.illustrated_only = !f.illustrated_only)
                />
                <span class="flex-1">{move || i.t("Solo con ilustración", "With illustration only")}</span>
                <span class="text-xs text-gray-400">{illustrated}</span>
            </label>

            <div class="space-y-1 border-t border-gray-100 pt-3">
                <label class="text-xs font-semibold text-gray-500 uppercase tracking-wider">{move || i.t("Grupo funcional", "Functional group")}</label>
                <div class="flex items-center gap-2">
                    {group_select(true)}
                    <span class="text-gray-400">"–"</span>
                    {group_select(false)}
                </div>
                <p class="text-xs text-gray-400">{move || i.t("Al acotar el rango se ocultan las especies sin grupo.", "Narrowing the range hides species without a group.")}</p>
            </div>

            {sections}
        </aside>
    }
}

/// Text box bound to one `Filters` string field.
#[component]
fn TextFilter(
    /// (Spanish, English)
    label: (&'static str, &'static str),
    /// (Spanish, English)
    placeholder: (&'static str, &'static str),
    ctx: Ctx,
    get: fn(&Filters) -> &String,
    set: fn(&mut Filters) -> &mut String,
) -> impl IntoView {
    let f = ctx.filters;
    let i = I18n::use_ctx();
    view! {
        <label class="block space-y-1">
            <span class="text-xs font-semibold text-gray-500 uppercase tracking-wider">{move || i.t(label.0, label.1)}</span>
            <input
                type="text"
                class=INPUT
                placeholder=move || i.t(placeholder.0, placeholder.1)
                prop:value=move || f.with(|x| get(x).clone())
                on:input=move |ev| f.update(|x| *set(x) = event_target_value(&ev))
            />
        </label>
    }
}
