//! Species catalog data: API types, code → label tables and filtering.
//!
//! Filters work on the backend *codes* (`TR`, `NT`, `GL`, …), never on the localized
//! `*_display` strings, which the API returns in Spanish.

use std::collections::HashSet;
use std::sync::Arc;

use futures::future::try_join_all;
use serde::Deserialize;

use crate::api::{API_BASE, get_json};
use crate::i18n::{Lang, pick};

// ---------------------------------------------------------------------------
// API types (subset of /api/v1/taxonomy/species/)
// ---------------------------------------------------------------------------

#[derive(Clone, Debug, PartialEq, Deserialize)]
pub struct Species {
    pub id: i64,
    pub scientific_name: String,
    #[serde(default)]
    pub accepted_scientific_name: Option<String>,
    /// Most frequent common name in the species' biodiversity records (annotated by the API).
    #[serde(default)]
    pub common_name: Option<String>,
    pub genus: Genus,
    #[serde(default)]
    pub functional_group: Option<FunctionalGroup>,
    pub origin: String,
    pub iucn_status: String,
    pub life_form: String,
    pub canopy_shape: String,
    pub flower_color: String,
    #[serde(default)]
    pub gbif_url: Option<String>,
    #[serde(default)]
    pub tropical_plants_url: Option<String>,
    #[serde(default)]
    pub identified_by: Option<String>,
    #[serde(default)]
    pub date: Option<String>,
}

#[derive(Clone, Debug, PartialEq, Deserialize)]
pub struct Genus {
    pub name: String,
    pub family: Family,
}

#[derive(Clone, Debug, PartialEq, Deserialize)]
pub struct Family {
    pub name: String,
}

#[derive(Clone, Debug, PartialEq, Deserialize)]
pub struct FunctionalGroup {
    pub group_id: u8,
    #[serde(default)]
    pub trait_values: Vec<TraitValue>,
}

#[derive(Clone, Debug, PartialEq, Deserialize)]
pub struct TraitValue {
    #[serde(rename = "trait")]
    pub trait_: Trait,
    pub min_value: Option<f64>,
    pub max_value: Option<f64>,
}

#[derive(Clone, Debug, PartialEq, Deserialize)]
pub struct Trait {
    #[serde(rename = "type")]
    pub ty: String,
}

#[derive(Deserialize)]
struct Page {
    count: usize,
    results: Vec<Species>,
}

pub type Catalog = Arc<Vec<Arc<Species>>>;

/// Download every page of the species endpoint (page 1 first, the rest in parallel).
pub async fn fetch_all_species() -> Result<Catalog, String> {
    let base = format!("{API_BASE}/api/v1/taxonomy/species/");
    let first: Page = parse(get_json(&base).await?)?;
    let page_size = first.results.len().max(1);
    let pages = first.count.div_ceil(page_size);

    let rest = try_join_all((2..=pages).map(|p| {
        let url = format!("{base}?page={p}");
        async move { parse::<Page>(get_json(&url).await?) }
    }))
    .await?;

    let mut all: Vec<Arc<Species>> = first.results.into_iter().map(Arc::new).collect();
    for page in rest {
        all.extend(page.results.into_iter().map(Arc::new));
    }
    Ok(Arc::new(all))
}

fn parse<T: for<'de> Deserialize<'de>>(v: serde_json::Value) -> Result<T, String> {
    serde_json::from_value(v).map_err(|e| format!("Unexpected API response: {e}"))
}

// ---------------------------------------------------------------------------
// Derived values
// ---------------------------------------------------------------------------

/// Species with a cover illustration in `public/assets/species/<genus-epithet>.webp`
/// (640×640 WebP). Matched against the scientific name or the accepted name, because some
/// records differ (e.g. "Aiouea Cinnamomum triplinerve", accepted "Cinnamomum triplinerve …").
pub const ILLUSTRATIONS: [&str; 17] = [
    "Amyris balsamifera",
    "Anacardium excelsum",
    "Bursera graveolens",
    "Cedrela odorata",
    "Cinnamomum triplinerve",
    "Cordia alliodora",
    "Cupania cinerea",
    "Erythroxylum amazonicum",
    "Euphorbia cotinifolia",
    "Hura crepitans",
    "Lacistema aggregatum",
    "Myrcia cucullata",
    "Pachira insignis",
    "Pithecellobium dulce",
    "Senna reticulata",
    "Thevetia ahouai",
    "Xylosma intermedia",
];

/// Functional-group traits shown on cards: carbon sequestration, shade, canopy, height.
/// (code, Spanish, English)
pub const TRAITS: [(&str, &str, &str); 4] = [
    ("CS", "Secuestro de carbono (%)", "Carbon sequestration (%)"),
    ("SH", "Índice de sombra", "Shade index"),
    ("CY", "Diámetro de copa (m)", "Canopy diameter (m)"),
    ("HX", "Altura máxima (m)", "Maximum height (m)"),
];

impl Species {
    pub fn common_name(&self) -> Option<&str> {
        self.common_name.as_deref().map(str::trim).filter(|n| !n.is_empty())
    }

    /// URL of the cover illustration, if there is one.
    pub fn illustration(&self) -> Option<String> {
        let accepted = self.accepted_scientific_name.as_deref().unwrap_or("");
        ILLUSTRATIONS
            .iter()
            .find(|n| {
                self.scientific_name == **n
                    || accepted == **n
                    || accepted.strip_prefix(**n).is_some_and(|rest| rest.starts_with(' '))
            })
            .map(|n| format!("/assets/species/{}.webp", n.to_lowercase().replace(' ', "-")))
    }

    pub fn family(&self) -> &str {
        &self.genus.family.name
    }

    pub fn group(&self) -> Option<u8> {
        self.functional_group.as_ref().map(|g| g.group_id)
    }

    /// Formatted trait range ("51.6 – 77.4"), single value, or "—" when unknown.
    pub fn trait_value(&self, ty: &str) -> String {
        let Some(tv) = self
            .functional_group
            .as_ref()
            .and_then(|g| g.trait_values.iter().find(|t| t.trait_.ty == ty))
        else {
            return "—".into();
        };
        match (tv.min_value, tv.max_value) {
            (Some(a), Some(b)) => {
                let (lo, hi) = if a <= b { (a, b) } else { (b, a) };
                if lo == hi { fmt_num(lo) } else { format!("{} – {}", fmt_num(lo), fmt_num(hi)) }
            }
            (Some(v), None) | (None, Some(v)) => fmt_num(v),
            (None, None) => "—".into(),
        }
    }
}

pub fn fmt_num(v: f64) -> String {
    let s = format!("{v:.2}");
    s.trim_end_matches('0').trim_end_matches('.').to_string()
}

// ---------------------------------------------------------------------------
// Code tables (backend codes → Spanish / English labels), in sidebar display order
// ---------------------------------------------------------------------------

/// (code, Spanish, English, swatch classes)
pub const FLOWER_COLORS: [(&str, &str, &str, &str); 10] = [
    ("NI", "Sin información", "No information", "border border-gray-400 bg-transparent"),
    ("WH", "Blanco", "White", "border border-gray-300 bg-white"),
    ("YE", "Amarillo", "Yellow", "bg-yellow-400"),
    ("PI", "Rosado", "Pink", "bg-pink-400"),
    ("RE", "Rojo", "Red", "bg-red-500"),
    ("VI", "Violeta", "Violet", "bg-purple-500"),
    ("OR", "Naranja", "Orange", "bg-orange-500"),
    ("FU", "Fucsia", "Fuchsia", "bg-fuchsia-600"),
    ("BR", "Café", "Brown", "bg-amber-800"),
    ("GR", "Verde", "Green", "bg-green-500"),
];

/// (code, Spanish, English)
pub type Label = (&'static str, &'static str, &'static str);

pub const LIFE_FORMS: [Label; 4] = [
    ("TR", "Árbol", "Tree"),
    ("SH", "Arbusto", "Shrub"),
    ("PT", "Palma", "Palm"),
    ("OT", "Otro", "Other"),
];

/// IUCN category: code, labels, badge classes and descriptions.
pub struct IucnCategory {
    pub code: &'static str,
    pub es: &'static str,
    pub en: &'static str,
    pub badge: &'static str,
    pub desc_es: &'static str,
    pub desc_en: &'static str,
}

const fn iucn(
    code: &'static str,
    es: &'static str,
    en: &'static str,
    badge: &'static str,
    desc_es: &'static str,
    desc_en: &'static str,
) -> IucnCategory {
    IucnCategory { code, es, en, badge, desc_es, desc_en }
}

pub const IUCN: [IucnCategory; 9] = [
    iucn("LC", "Preocupación menor", "Least concern", "bg-green-600",
        "Taxones extendidos y abundantes, con bajo riesgo de extinción.",
        "Widespread and abundant taxa with a low risk of extinction."),
    iucn("NT", "Casi amenazada", "Near threatened", "bg-teal-700",
        "Cerca de calificar para una categoría de amenaza en el futuro cercano.",
        "Close to qualifying for a threatened category in the near future."),
    iucn("VU", "Vulnerable", "Vulnerable", "bg-amber-500",
        "Enfrenta un riesgo alto de extinción en estado silvestre.",
        "Facing a high risk of extinction in the wild."),
    iucn("EN", "En peligro", "Endangered", "bg-orange-600",
        "Enfrenta un riesgo muy alto de extinción en estado silvestre.",
        "Facing a very high risk of extinction in the wild."),
    iucn("CR", "En peligro crítico", "Critically endangered", "bg-red-700",
        "Enfrenta un riesgo extremadamente alto de extinción en estado silvestre.",
        "Facing an extremely high risk of extinction in the wild."),
    iucn("EW", "Extinta en estado silvestre", "Extinct in the wild", "bg-gray-900",
        "Solo sobrevive en cultivo o fuera de su área de distribución natural.",
        "Known only to survive in cultivation or outside its natural range."),
    iucn("CD", "Dependiente de conservación", "Conservation dependent", "bg-lime-600",
        "Riesgo menor, pero depende de medidas de conservación (categoría antigua de la UICN).",
        "Lower risk, but dependent on conservation measures (older IUCN category)."),
    iucn("DD", "Datos insuficientes", "Data deficient", "bg-gray-500",
        "No hay información suficiente para evaluar su riesgo de extinción.",
        "Not enough information to assess its risk of extinction."),
    iucn("NE", "No evaluada", "Not evaluated", "bg-gray-400",
        "Aún no evaluada con los criterios de la Lista Roja de la UICN.",
        "Not yet assessed against the IUCN Red List criteria."),
];

pub const ORIGINS: [Label; 7] = [
    ("NT", "Nativa", "Native"),
    ("CU", "Cultivada", "Cultivated"),
    ("NC", "Nativa-cultivada", "Native-cultivated"),
    ("EN", "Endémica", "Endemic"),
    ("NU", "Naturalizada", "Naturalized"),
    ("NL", "Naturalizada-cultivada", "Naturalized-cultivated"),
    ("NI", "Sin identificar", "Unidentified"),
];

pub const CANOPIES: [Label; 12] = [
    ("GL", "Globosa", "Globose"),
    ("SG", "Semiglobosa", "Semiglobose"),
    ("OV", "Ovalada", "Oval"),
    ("IR", "Irregular", "Irregular"),
    ("SP", "Extendida", "Spreading"),
    ("PY", "Piramidal", "Pyramidal"),
    ("CO", "Columnar", "Columnar"),
    ("BD", "Amplia", "Broad"),
    ("CF", "Caulirrósula en abanico", "Fan-shaped caulirosula"),
    ("CR", "Caulirrósula plumosa", "Feather-shaped caulirosula"),
    ("CS", "Caulirrósula cespitosa", "Cespitose caulirosula"),
    ("NI", "Sin información", "No information"),
];

/// "Unknown" in the given language.
pub fn unknown(l: Lang) -> &'static str {
    pick(l, "Desconocido", "Unknown")
}

fn lookup(table: &[Label], l: Lang, code: &str) -> &'static str {
    table.iter().find(|(c, ..)| *c == code).map(|(_, es, en)| pick(l, *es, *en)).unwrap_or(unknown(l))
}

pub fn life_form_label(l: Lang, code: &str) -> &'static str { lookup(&LIFE_FORMS, l, code) }
pub fn origin_label(l: Lang, code: &str) -> &'static str { lookup(&ORIGINS, l, code) }
pub fn canopy_label(l: Lang, code: &str) -> &'static str { lookup(&CANOPIES, l, code) }

pub fn flower_label(l: Lang, code: &str) -> &'static str {
    FLOWER_COLORS
        .iter()
        .find(|(c, ..)| *c == code)
        .map(|(_, es, en, _)| pick(l, *es, *en))
        .unwrap_or(unknown(l))
}

/// Card icon colors (fill, text) per flower color code.
pub fn flower_fill(code: &str) -> (&'static str, &'static str) {
    match code {
        "WH" => ("#FFFFFF", "#14532D"),
        "YE" => ("#FACC15", "#14532D"),
        "PI" => ("#F9A8D4", "#14532D"),
        "RE" => ("#EF4444", "#FFFFFF"),
        "VI" => ("#8B5CF6", "#FFFFFF"),
        "OR" => ("#FB923C", "#14532D"),
        "FU" => ("#C026D3", "#FFFFFF"),
        "BR" => ("#92400E", "#FFFFFF"),
        "GR" => ("#4ADE80", "#14532D"),
        _ => ("#E5E7EB", "#374151"),
    }
}

/// IUCN Red List category colors (background, text).
pub fn iucn_colors(code: &str) -> (&'static str, &'static str) {
    match code {
        "LC" => ("#11706B", "#FFFFFF"),
        "NT" => ("#CCE226", "#111827"),
        "CD" => ("#9BBF45", "#111827"),
        "VU" => ("#F9E814", "#111827"),
        "EN" => ("#FC7F3F", "#111827"),
        "CR" => ("#D81E05", "#FFFFFF"),
        "EW" => ("#542344", "#FFFFFF"),
        "DD" => ("#D1D1C6", "#111827"),
        _ => ("#FFFFFF", "#111827"),
    }
}

/// (label, badge classes, description) of an IUCN category.
pub fn iucn_info(l: Lang, code: &str) -> (&'static str, &'static str, &'static str) {
    IUCN.iter()
        .find(|c| c.code == code)
        .map(|c| (pick(l, c.es, c.en), c.badge, pick(l, c.desc_es, c.desc_en)))
        .unwrap_or((unknown(l), "bg-gray-400", ""))
}

// ---------------------------------------------------------------------------
// Filters
// ---------------------------------------------------------------------------

pub const GROUP_MIN: u8 = 1;
pub const GROUP_MAX: u8 = 18;

/// Multi-select filter categories (each selects backend codes).
#[derive(Clone, Copy, PartialEq, Eq)]
pub enum Category {
    FlowerColor,
    LifeForm,
    Iucn,
    Origin,
    Canopy,
}

impl Category {
    pub fn chip_prefix(self, l: Lang) -> &'static str {
        match self {
            Category::FlowerColor => pick(l, "Flor", "Flower"),
            Category::LifeForm => pick(l, "Hábito", "Habit"),
            Category::Iucn => pick(l, "UICN", "IUCN"),
            Category::Origin => pick(l, "Origen", "Origin"),
            Category::Canopy => pick(l, "Copa", "Canopy"),
        }
    }

    pub fn value(self, s: &Species) -> &str {
        match self {
            Category::FlowerColor => &s.flower_color,
            Category::LifeForm => &s.life_form,
            Category::Iucn => &s.iucn_status,
            Category::Origin => &s.origin,
            Category::Canopy => &s.canopy_shape,
        }
    }

    pub fn label(self, l: Lang, code: &str) -> &'static str {
        match self {
            Category::FlowerColor => flower_label(l, code),
            Category::LifeForm => life_form_label(l, code),
            Category::Iucn => iucn_info(l, code).0,
            Category::Origin => origin_label(l, code),
            Category::Canopy => canopy_label(l, code),
        }
    }
}

#[derive(Clone, PartialEq)]
pub struct Filters {
    pub common_name: String,
    pub scientific_name: String,
    pub family: String,
    pub selected: Vec<(Category, &'static str)>,
    pub group_min: u8,
    pub group_max: u8,
    pub saved_only: bool,
    pub illustrated_only: bool,
}

impl Default for Filters {
    fn default() -> Self {
        Self {
            common_name: String::new(),
            scientific_name: String::new(),
            family: String::new(),
            selected: Vec::new(),
            group_min: GROUP_MIN,
            group_max: GROUP_MAX,
            saved_only: false,
            illustrated_only: false,
        }
    }
}

impl Filters {
    pub fn is_selected(&self, cat: Category, code: &str) -> bool {
        self.selected.iter().any(|(c, v)| *c == cat && *v == code)
    }

    pub fn toggle(&mut self, cat: Category, code: &'static str) {
        if let Some(i) = self.selected.iter().position(|(c, v)| *c == cat && *v == code) {
            self.selected.remove(i);
        } else {
            self.selected.push((cat, code));
        }
    }

    pub fn group_range_active(&self) -> bool {
        self.group_min != GROUP_MIN || self.group_max != GROUP_MAX
    }

    pub fn is_active(&self) -> bool {
        *self != Filters::default()
    }

    /// Within a category the selected codes are OR-ed; categories are AND-ed.
    pub fn matches(&self, s: &Species, saved: &HashSet<i64>) -> bool {
        // Each text box searches only its own field (case-insensitive substring).
        // The scientific name starts with the genus, so typing a genus lists all its species.
        let common = self.common_name.trim().to_lowercase();
        if !common.is_empty() && !s.common_name().is_some_and(|c| c.to_lowercase().contains(&common)) {
            return false;
        }

        let sci = self.scientific_name.trim().to_lowercase();
        if !sci.is_empty() && !s.scientific_name.to_lowercase().contains(&sci) {
            return false;
        }

        let fam = self.family.trim().to_lowercase();
        if !fam.is_empty() && !s.family().to_lowercase().contains(&fam) {
            return false;
        }

        for cat in [Category::FlowerColor, Category::LifeForm, Category::Iucn, Category::Origin, Category::Canopy] {
            let mut chosen = self.selected.iter().filter(|(c, _)| *c == cat).peekable();
            if chosen.peek().is_some() && !chosen.any(|(_, code)| *code == cat.value(s)) {
                return false;
            }
        }

        // Species without a functional group only pass while the full range is selected.
        if self.group_range_active() {
            match s.group() {
                Some(g) if g >= self.group_min && g <= self.group_max => {}
                _ => return false,
            }
        }

        if self.illustrated_only && s.illustration().is_none() {
            return false;
        }

        !self.saved_only || saved.contains(&s.id)
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    fn species(json: serde_json::Value) -> Species {
        let mut base = serde_json::json!({
            "id": 1, "scientific_name": "Ficus benjamina", "accepted_scientific_name": null,
            "genus": {"name": "Ficus", "family": {"name": "Moraceae"}},
            "functional_group": null, "origin": "CU", "iucn_status": "LC",
            "life_form": "TR", "canopy_shape": "GL", "flower_color": "NI"
        });
        base.as_object_mut().unwrap().extend(json.as_object().unwrap().clone());
        serde_json::from_value(base).unwrap()
    }

    #[test]
    fn trait_ranges_are_sorted_and_formatted() {
        let s = species(serde_json::json!({"functional_group": {"group_id": 6, "trait_values": [
            {"trait": {"type": "CS"}, "min_value": 100.0, "max_value": 63.64},
            {"trait": {"type": "HX"}, "min_value": 15.0, "max_value": 15.0},
            {"trait": {"type": "SH"}, "min_value": null, "max_value": 51.6}
        ]}}));
        assert_eq!(s.trait_value("CS"), "63.64 – 100");
        assert_eq!(s.trait_value("HX"), "15");
        assert_eq!(s.trait_value("SH"), "51.6");
        assert_eq!(s.trait_value("CY"), "—");
    }

    #[test]
    fn filters_or_within_category_and_across() {
        let palm = species(serde_json::json!({"id": 2, "life_form": "PT"}));
        let tree = species(serde_json::json!({"id": 3}));
        let saved = HashSet::from([3]);
        let mut f = Filters::default();
        f.toggle(Category::LifeForm, "PT");
        assert!(f.matches(&palm, &saved) && !f.matches(&tree, &saved));
        f.toggle(Category::LifeForm, "TR");
        assert!(f.matches(&palm, &saved) && f.matches(&tree, &saved));
        f.saved_only = true;
        assert!(!f.matches(&palm, &saved) && f.matches(&tree, &saved));
    }

    #[test]
    fn text_filters_search_only_their_own_field() {
        let mut s = species(serde_json::json!({"common_name": "Caucho"}));
        let none = HashSet::new();
        let only = |f: fn(&mut Filters)| {
            let mut x = Filters::default();
            f(&mut x);
            x
        };
        // Common name box: common name only.
        assert!(only(|f| f.common_name = "cauch".into()).matches(&s, &none));
        assert!(!only(|f| f.common_name = "ficus".into()).matches(&s, &none));
        // Scientific name box: genus prefix lists the genus, never the common name.
        assert!(only(|f| f.scientific_name = "Ficus".into()).matches(&s, &none));
        assert!(!only(|f| f.scientific_name = "caucho".into()).matches(&s, &none));
        // Family box: family only, not the genus.
        assert!(only(|f| f.family = "morac".into()).matches(&s, &none));
        assert!(!only(|f| f.family = "ficus".into()).matches(&s, &none));
        s.common_name = None;
        assert!(!only(|f| f.common_name = "cauch".into()).matches(&s, &none));
    }

    #[test]
    fn illustration_matches_scientific_or_accepted_name() {
        let direct = species(serde_json::json!({"scientific_name": "Hura crepitans"}));
        assert_eq!(direct.illustration().as_deref(), Some("/assets/species/hura-crepitans.webp"));
        let accepted = species(serde_json::json!({
            "scientific_name": "Aiouea Cinnamomum triplinerve",
            "accepted_scientific_name": "Cinnamomum triplinerve (Ruiz & Pav.) Kosterm."
        }));
        assert_eq!(accepted.illustration().as_deref(), Some("/assets/species/cinnamomum-triplinerve.webp"));
        let prefix_only = species(serde_json::json!({"accepted_scientific_name": "Hura crepitansoides"}));
        assert_eq!(prefix_only.illustration(), None);
    }

    #[test]
    fn narrowing_groups_hides_species_without_group() {
        let none = species(serde_json::json!({}));
        let mut f = Filters::default();
        assert!(f.matches(&none, &HashSet::new()));
        f.group_max = 17;
        assert!(!f.matches(&none, &HashSet::new()));
    }
}
