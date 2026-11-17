//! Spanish / English UI. Spanish is the default; the choice is kept in `localStorage`.
//!
//! Texts live next to the markup as `(es, en)` pairs, not in a key catalog:
//! `let i = I18n::use_ctx();` then `{move || i.t("Árboles", "Trees")}` in a view. Reading
//! the language subscribes the closure, so the text updates when the user switches.
//! For formatted text use `i.is_es()` / `i.lang()` inside a reactive closure.

use leptos::prelude::*;

const STORAGE_KEY: &str = "uto.lang";

#[derive(Clone, Copy, PartialEq, Eq, Debug, Default)]
pub enum Lang {
    #[default]
    Es,
    En,
}

impl Lang {
    pub fn code(self) -> &'static str {
        match self {
            Lang::Es => "es",
            Lang::En => "en",
        }
    }

    fn from_code(code: &str) -> Option<Self> {
        match code {
            "es" => Some(Lang::Es),
            "en" => Some(Lang::En),
            _ => None,
        }
    }
}

/// The current language, shared through the Leptos context (see `provide`).
#[derive(Clone, Copy)]
pub struct I18n(RwSignal<Lang>);

impl I18n {
    /// Create the language signal (from `localStorage`, Spanish by default), keep
    /// `<html lang>` and `localStorage` in sync, and put it in the context.
    pub fn provide() -> Self {
        let saved = storage()
            .and_then(|s| s.get_item(STORAGE_KEY).ok().flatten())
            .and_then(|c| Lang::from_code(&c));
        let i = I18n(RwSignal::new(saved.unwrap_or_default()));
        Effect::new(move |_| {
            let lang = i.lang();
            if let Some(s) = storage() {
                let _ = s.set_item(STORAGE_KEY, lang.code());
            }
            if let Some(html) = web_sys::window()
                .and_then(|w| w.document())
                .and_then(|d| d.document_element())
            {
                let _ = html.set_attribute("lang", lang.code());
            }
        });
        provide_context(i);
        i
    }

    pub fn use_ctx() -> Self {
        expect_context::<I18n>()
    }

    /// Current language (tracked).
    pub fn lang(self) -> Lang {
        self.0.get()
    }

    /// Current language without subscribing (event handlers, one-off code).
    pub fn lang_untracked(self) -> Lang {
        self.0.get_untracked()
    }

    pub fn set(self, lang: Lang) {
        self.0.set(lang);
    }

    pub fn is_es(self) -> bool {
        self.lang() == Lang::Es
    }

    /// The text for the current language (tracked).
    pub fn t(self, es: &'static str, en: &'static str) -> &'static str {
        pick(self.lang(), es, en)
    }
}

/// `es` or `en` for a given language (for code that already has the `Lang`).
pub fn pick<T>(lang: Lang, es: T, en: T) -> T {
    match lang {
        Lang::Es => es,
        Lang::En => en,
    }
}

fn storage() -> Option<web_sys::Storage> {
    web_sys::window()?.local_storage().ok().flatten()
}

/// "ES | EN" switch for the navbar.
#[component]
pub fn LanguageSwitch() -> impl IntoView {
    let i = I18n::use_ctx();
    let button = move |lang: Lang, label: &'static str, title: &'static str| {
        view! {
            <button
                type="button"
                class=move || {
                    if i.lang() == lang {
                        "px-2.5 py-1 text-xs font-bold rounded-md bg-white text-primary-700"
                    } else {
                        "px-2.5 py-1 text-xs font-semibold rounded-md text-white hover:bg-primary-700"
                    }
                }
                aria-pressed=move || (i.lang() == lang).to_string()
                title=title
                on:click=move |_| i.set(lang)
            >
                {label}
            </button>
        }
    };
    view! {
        <div
            class="flex items-center gap-0.5 rounded-lg border border-white/40 p-0.5"
            role="group"
            aria-label=move || i.t("Idioma", "Language")
        >
            {button(Lang::Es, "ES", "Español")}
            {button(Lang::En, "EN", "English")}
        </div>
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn spanish_is_default() {
        assert_eq!(Lang::default(), Lang::Es);
        assert_eq!(pick(Lang::En, "árbol", "tree"), "tree");
        assert_eq!(Lang::from_code("en"), Some(Lang::En));
        assert_eq!(Lang::from_code("fr"), None);
    }
}
