//! Root component and routes.

use leptos::prelude::*;
use leptos_router::components::{Redirect, Route, Router, Routes};
use leptos_router::path;

use crate::layout::Layout;
use crate::pages::{
    about::About, alerts::Alerts, analytics::Analytics, dashboard::Dashboard, map::MapPage,
    reports::Reports, species::SpeciesCatalog, trees::Trees,
};

/// Reports and Alerts are for administrators and partner institutions (public and private
/// entities that manage urban trees). The demo has no login yet, so they are hidden: not in
/// the sidebar, and their URLs redirect to the dashboard.
/// TODO(restricted-pages): show them to logged-in, privileged users once the platform's
/// login and roles are defined with those institutions. See README "Future work".
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
                    <Route path=path!("/reports") view=|| restricted(|| view! { <Reports /> }.into_any()) />
                    <Route path=path!("/alerts") view=|| restricted(|| view! { <Alerts /> }.into_any()) />
                    <Route path=path!("/analytics") view=Analytics />
                    <Route path=path!("/about") view=About />
                </Routes>
            </Layout>
        </Router>
    }
}
