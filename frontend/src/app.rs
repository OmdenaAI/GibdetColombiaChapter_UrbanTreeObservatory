//! Root component and routes.

use leptos::prelude::*;
use leptos_router::components::{Redirect, Route, Router, Routes};
use leptos_router::path;

use crate::auth::Auth;
use crate::i18n::I18n;
use crate::layout::Layout;
use crate::pages::{
    about::About, alerts::Alerts, analytics::Analytics, dashboard::Dashboard, map::MapPage,
    reports::Reports, species::SpeciesCatalog, trees::Trees,
};

/// Alerts is for administrators and partner institutions (public and private entities that
/// manage urban trees) and has no content yet, so it is hidden: not in the sidebar, and its
/// URL redirects to the dashboard. Reports is shown to logged-in staff users (see `auth`).
/// TODO(restricted-pages): define Alerts with those institutions. See ROADMAP.md.
pub const RESTRICTED_PAGES: bool = cfg!(feature = "restricted-pages");

fn restricted(page: fn() -> AnyView) -> AnyView {
    if RESTRICTED_PAGES {
        page()
    } else {
        view! { <Redirect path="/dashboard" /> }.into_any()
    }
}

#[component]
pub fn App() -> impl IntoView {
    I18n::provide();
    Auth::provide();
    view! {
        <Router>
            <Layout>
                // No wildcard route: an unknown URL renders an empty content area.
                <Routes fallback=|| ()>
                    <Route path=path!("/") view=|| view! { <Redirect path="/dashboard" /> } />
                    <Route path=path!("/dashboard") view=Dashboard />
                    <Route path=path!("/map") view=MapPage />
                    <Route path=path!("/trees") view=Trees />
                    <Route path=path!("/species") view=SpeciesCatalog />
                    <Route path=path!("/reports") view=Reports />
                    <Route path=path!("/alerts") view=|| restricted(|| view! { <Alerts /> }.into_any()) />
                    <Route path=path!("/analytics") view=Analytics />
                    <Route path=path!("/about") view=About />
                </Routes>
            </Layout>
        </Router>
    }
}
