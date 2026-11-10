//! Root component and routes.

use leptos::prelude::*;
use leptos_router::components::{Redirect, Route, Router, Routes};
use leptos_router::path;

use crate::layout::Layout;
use crate::pages::{
    about::About, alerts::Alerts, analytics::Analytics, dashboard::Dashboard, map::MapPage,
    reports::Reports, trees::Trees,
};

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
                    <Route path=path!("/reports") view=Reports />
                    <Route path=path!("/alerts") view=Alerts />
                    <Route path=path!("/analytics") view=Analytics />
                    <Route path=path!("/about") view=About />
                </Routes>
            </Layout>
        </Router>
    }
}
