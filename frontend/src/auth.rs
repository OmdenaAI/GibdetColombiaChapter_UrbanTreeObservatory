//! Login with the Django admin's username and password (JWT, `api/v1/auth/`).
//!
//! The tokens are kept in `localStorage`: the access token (30 minutes) is renewed with the
//! refresh token (7 days) when the API answers 401, so the session lasts a week of use.
//! `Auth::user` is `None` while logged out; staff users see the Reports page.

use gloo_net::http::{Request, RequestBuilder, Response};
use leptos::prelude::*;
use leptos::task::spawn_local;
use serde_json::{Value, json};

use crate::api::API_BASE;
use crate::i18n::I18n;

const ACCESS_KEY: &str = "uto.access";
const REFRESH_KEY: &str = "uto.refresh";

#[derive(Clone, Debug, PartialEq)]
pub struct User {
    pub username: String,
    pub name: String,
    pub is_staff: bool,
}

impl User {
    pub fn display_name(&self) -> String {
        if self.name.is_empty() { self.username.clone() } else { self.name.clone() }
    }
}

/// Session state, shared through the Leptos context (see `provide`).
#[derive(Clone, Copy)]
pub struct Auth {
    pub user: RwSignal<Option<User>>,
    /// `false` until a saved session has been checked (avoids flashing the login form).
    pub ready: RwSignal<bool>,
}

impl Auth {
    /// Put the session in the context and restore a saved one.
    pub fn provide() -> Self {
        let auth = Auth { user: RwSignal::new(None), ready: RwSignal::new(false) };
        provide_context(auth);
        spawn_local(async move {
            if token(ACCESS_KEY).is_some() || token(REFRESH_KEY).is_some() {
                match fetch_me().await {
                    Ok(user) => auth.user.set(Some(user)),
                    Err(_) => clear_tokens(),
                }
            }
            auth.ready.set(true);
        });
        auth
    }

    pub fn use_ctx() -> Self {
        expect_context::<Auth>()
    }

    /// Staff user logged in (tracked).
    pub fn is_staff(self) -> bool {
        self.user.with(|u| u.as_ref().is_some_and(|u| u.is_staff))
    }

    pub async fn login(self, username: &str, password: &str) -> Result<(), LoginError> {
        let resp = Request::post(&format!("{API_BASE}/api/v1/auth/token/"))
            .json(&json!({"username": username, "password": password}))
            .map_err(|_| LoginError::Network)?
            .send()
            .await
            .map_err(|_| LoginError::Network)?;
        if resp.status() == 401 || resp.status() == 400 {
            return Err(LoginError::Credentials);
        }
        if !resp.ok() {
            return Err(LoginError::Network);
        }
        let tokens: Value = resp.json().await.map_err(|_| LoginError::Network)?;
        set_token(ACCESS_KEY, tokens["access"].as_str());
        set_token(REFRESH_KEY, tokens["refresh"].as_str());
        let user = fetch_me().await.map_err(|_| LoginError::Network)?;
        self.user.set(Some(user));
        Ok(())
    }

    pub fn logout(self) {
        clear_tokens();
        self.user.set(None);
    }

    /// Send an authenticated request (`make` builds it). On 401 the access token is renewed
    /// once and the request sent again; if that fails, the session is closed.
    pub async fn send(
        self,
        make: impl Fn(RequestBuilder) -> Result<Request, String>,
        url: &str,
        method: &str,
    ) -> Result<Response, String> {
        let resp = send_with_token(&make, url, method).await?;
        if resp.status() != 401 {
            return Ok(resp);
        }
        if refresh().await.is_ok() {
            let resp = send_with_token(&make, url, method).await?;
            if resp.status() != 401 {
                return Ok(resp);
            }
        }
        self.logout();
        Err("401".into())
    }

    /// Authenticated GET + JSON; a non-2xx status is an error (the server's message).
    pub async fn get_json(self, url: &str) -> Result<Value, String> {
        let resp = self.send(|b| b.build().map_err(|e| e.to_string()), url, "GET").await?;
        json_or_error(resp).await
    }

    /// Authenticated POST; `body` is a JSON value or `None`.
    pub async fn post_json(self, url: &str, body: Option<Value>) -> Result<(u16, Value), String> {
        let resp = self
            .send(
                |b| match &body {
                    Some(v) => b.json(v).map_err(|e| e.to_string()),
                    None => b.build().map_err(|e| e.to_string()),
                },
                url,
                "POST",
            )
            .await?;
        let status = resp.status();
        let value = resp.json::<Value>().await.unwrap_or(Value::Null);
        Ok((status, value))
    }
}

#[derive(Clone, Copy, Debug, PartialEq)]
pub enum LoginError {
    Credentials,
    Network,
}

async fn send_with_token(
    make: &impl Fn(RequestBuilder) -> Result<Request, String>,
    url: &str,
    method: &str,
) -> Result<Response, String> {
    let builder = match method {
        "POST" => Request::post(url),
        _ => Request::get(url),
    };
    let builder = match token(ACCESS_KEY) {
        Some(t) => builder.header("Authorization", &format!("Bearer {t}")),
        None => builder,
    };
    make(builder)?.send().await.map_err(|e| e.to_string())
}

async fn json_or_error(resp: Response) -> Result<Value, String> {
    if !resp.ok() {
        let detail = resp.json::<Value>().await.ok().and_then(|v| v["error"].as_str().map(str::to_string));
        return Err(detail.unwrap_or_else(|| format!("{} {}", resp.status(), resp.status_text())));
    }
    resp.json::<Value>().await.map_err(|e| e.to_string())
}

async fn refresh() -> Result<(), ()> {
    let refresh = token(REFRESH_KEY).ok_or(())?;
    let resp = Request::post(&format!("{API_BASE}/api/v1/auth/token/refresh/"))
        .json(&json!({"refresh": refresh}))
        .map_err(|_| ())?
        .send()
        .await
        .map_err(|_| ())?;
    if !resp.ok() {
        return Err(());
    }
    let tokens: Value = resp.json().await.map_err(|_| ())?;
    set_token(ACCESS_KEY, tokens["access"].as_str());
    Ok(())
}

async fn fetch_me() -> Result<User, String> {
    let url = format!("{API_BASE}/api/v1/auth/me/");
    let mut resp = send_with_token(&|b: RequestBuilder| b.build().map_err(|e| e.to_string()), &url, "GET").await?;
    if resp.status() == 401 {
        refresh().await.map_err(|_| "401".to_string())?;
        resp = send_with_token(&|b: RequestBuilder| b.build().map_err(|e| e.to_string()), &url, "GET").await?;
    }
    let v = json_or_error(resp).await?;
    Ok(User {
        username: v["username"].as_str().unwrap_or_default().to_string(),
        name: v["name"].as_str().unwrap_or_default().to_string(),
        is_staff: v["is_staff"].as_bool().unwrap_or(false),
    })
}

fn storage() -> Option<web_sys::Storage> {
    web_sys::window()?.local_storage().ok().flatten()
}

fn token(key: &str) -> Option<String> {
    storage()?.get_item(key).ok().flatten().filter(|t| !t.is_empty())
}

fn set_token(key: &str, value: Option<&str>) {
    if let (Some(s), Some(v)) = (storage(), value) {
        let _ = s.set_item(key, v);
    }
}

fn clear_tokens() {
    if let Some(s) = storage() {
        let _ = s.remove_item(ACCESS_KEY);
        let _ = s.remove_item(REFRESH_KEY);
    }
}

const INPUT: &str = "w-full rounded-md border border-gray-300 px-2.5 py-1.5 text-sm text-gray-900 focus:border-primary-600 focus:outline-none focus:ring-1 focus:ring-primary-600";
const LABEL: &str = "block text-xs font-medium text-gray-600 mb-1";

/// Username + password form; `on_done` runs after a successful login.
#[component]
pub fn LoginForm(#[prop(optional)] on_done: Option<Callback<()>>) -> impl IntoView {
    let i = I18n::use_ctx();
    let auth = Auth::use_ctx();
    let username = RwSignal::new(String::new());
    let password = RwSignal::new(String::new());
    let error = RwSignal::new(None::<LoginError>);
    let busy = RwSignal::new(false);

    let submit = move |ev: leptos::ev::SubmitEvent| {
        ev.prevent_default();
        if busy.get_untracked() {
            return;
        }
        busy.set(true);
        error.set(None);
        spawn_local(async move {
            let result = auth.login(&username.get_untracked(), &password.get_untracked()).await;
            busy.try_set(false);
            match result {
                Ok(()) => {
                    password.try_set(String::new());
                    if let Some(cb) = on_done {
                        cb.run(());
                    }
                }
                Err(e) => {
                    error.try_set(Some(e));
                }
            }
        });
    };

    view! {
        <form class="space-y-3" on:submit=submit>
            <div>
                <label class=LABEL for="login-username">{move || i.t("Usuario", "Username")}</label>
                <input id="login-username" class=INPUT type="text" autocomplete="username" required
                    prop:value=move || username.get()
                    on:input=move |ev| username.set(event_target_value(&ev)) />
            </div>
            <div>
                <label class=LABEL for="login-password">{move || i.t("Contraseña", "Password")}</label>
                <input id="login-password" class=INPUT type="password" autocomplete="current-password" required
                    prop:value=move || password.get()
                    on:input=move |ev| password.set(event_target_value(&ev)) />
            </div>
            {move || error.get().map(|e| view! {
                <p class="text-sm text-red-700" role="alert">
                    {match e {
                        LoginError::Credentials => i.t("Usuario o contraseña incorrectos.", "Wrong username or password."),
                        LoginError::Network => i.t("No se pudo conectar con el servidor.", "Could not reach the server."),
                    }}
                </p>
            })}
            <button type="submit"
                class="w-full inline-flex justify-center rounded-md bg-primary-700 px-3 py-2 text-sm font-medium text-white hover:bg-primary-800 disabled:opacity-50"
                disabled=move || busy.get()>
                {move || if busy.get() { i.t("Ingresando…", "Signing in…") } else { i.t("Iniciar sesión", "Sign in") }}
            </button>
            <p class="text-xs text-gray-500">
                {move || i.t(
                    "Use el mismo usuario y contraseña del administrador de Django.",
                    "Use the same username and password as the Django admin.",
                )}
            </p>
        </form>
    }
}

const ICON_USER: &str = "M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z";

/// Navbar user button: a login form when logged out, the user and "sign out" when in.
#[component]
pub fn UserMenu(button_class: &'static str) -> impl IntoView {
    let i = I18n::use_ctx();
    let auth = Auth::use_ctx();
    let open = RwSignal::new(false);
    let logged_in = move || auth.user.with(Option::is_some);

    view! {
        <div class="relative">
            <button type="button" class=button_class
                aria-haspopup="true"
                aria-expanded=move || open.get().to_string()
                title=move || match auth.user.get() {
                    Some(u) => u.display_name(),
                    None => i.t("Iniciar sesión", "Sign in").to_string(),
                }
                on:click=move |_| open.update(|o| *o = !*o)>
                <span class="flex items-center gap-2">
                    <svg xmlns="http://www.w3.org/2000/svg" class="h-6 w-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d=ICON_USER />
                    </svg>
                    {move || auth.user.get().map(|u| view! {
                        <span class="hidden sm:inline text-sm font-medium">{u.display_name()}</span>
                    })}
                </span>
            </button>
            <Show when=move || open.get()>
                <div class="absolute right-0 z-[1100] mt-2 w-72 rounded-lg bg-white p-4 shadow-xl ring-1 ring-black/5">
                    <Show
                        when=logged_in
                        fallback=move || view! {
                            <p class="mb-3 text-sm font-semibold text-gray-900">{move || i.t("Iniciar sesión", "Sign in")}</p>
                            <LoginForm on_done=Callback::new(move |_| open.set(false)) />
                        }
                    >
                        <p class="text-sm font-semibold text-gray-900">{move || auth.user.get().map(|u| u.display_name())}</p>
                        <p class="text-xs text-gray-500 mb-3">
                            {move || if auth.is_staff() { i.t("Administrador", "Administrator") } else { i.t("Usuario", "User") }}
                        </p>
                        <Show when=move || auth.is_staff()>
                            <a href="/reports" class="block rounded-md px-2 py-1.5 text-sm text-gray-700 hover:bg-primary-50"
                                on:click=move |_| open.set(false)>
                                {move || i.t("Reportes: actualizar datos", "Reports: update data")}
                            </a>
                        </Show>
                        <button type="button" class="mt-1 block w-full rounded-md px-2 py-1.5 text-left text-sm text-red-700 hover:bg-red-50"
                            on:click=move |_| { auth.logout(); open.set(false); }>
                            {move || i.t("Cerrar sesión", "Sign out")}
                        </button>
                    </Show>
                </div>
            </Show>
        </div>
    }
}
