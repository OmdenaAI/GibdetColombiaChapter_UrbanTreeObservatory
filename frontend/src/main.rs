#![recursion_limit = "512"]

mod api;
mod app;
mod i18n;
mod interop;
mod layout;
mod pages;

fn main() {
    console_error_panic_hook::set_once();
    leptos::mount::mount_to_body(app::App);
}
