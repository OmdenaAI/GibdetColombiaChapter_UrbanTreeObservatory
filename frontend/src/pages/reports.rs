//! Reports page (staff users): update the tree database from a file.
//!
//! The file (Excel, CSV, zipped Shapefile or GeoJSON, with the columns of the map's
//! downloads) is first checked by the server, which answers what would change and the
//! errors of each row (`POST reports/uploads/`); nothing is written until the user applies
//! it (`POST reports/uploads/{id}/apply/`). Below, the files sent before.

use leptos::prelude::*;
use leptos::task::spawn_local;
use serde_json::Value;

use crate::api::{API_BASE, fmt_thousands};
use crate::auth::{Auth, LoginForm};
use crate::i18n::{I18n, Lang, pick};
use crate::pages::trees::export::save_bytes;

const ACCEPT: &str = ".xlsx,.csv,.zip,.geojson,.json";
const MAX_BYTES: f64 = 20.0 * 1024.0 * 1024.0;

const CARD: &str = "bg-white shadow rounded-lg p-6";
const BTN: &str = "inline-flex items-center justify-center gap-1.5 rounded-md px-3 py-2 text-sm font-medium transition-colors disabled:opacity-50 disabled:cursor-not-allowed";
const BTN_PRIMARY: &str = "bg-primary-700 text-white hover:bg-primary-800";
const BTN_SECONDARY: &str = "border border-gray-300 bg-white text-gray-700 hover:bg-gray-50";
const TH: &str = "px-3 py-2 text-left text-xs font-medium text-gray-500 uppercase tracking-wider";
const TD: &str = "px-3 py-2 text-sm text-gray-700 align-top";
const ICON_UPLOAD: &str = "M3 16.5v2.25A2.25 2.25 0 0 0 5.25 21h13.5A2.25 2.25 0 0 0 21 18.75V16.5m-13.5-9L12 3m0 0 4.5 4.5M12 3v13.5";

/// (column, Spanish help, English help), in template order.
const COLUMNS: [(&str, &str, &str); 23] = [
    ("id", "Código del árbol (obligatorio). Si no existe en la base, se crea un árbol nuevo con ese código.", "Tree code (required). If it is not in the database, a new tree is created with that code."),
    ("common_name", "Nombre común.", "Common name."),
    ("scientific_name", "Nombre científico; debe estar en el catálogo de especies. Obligatorio para árboles nuevos.", "Scientific name; it must be in the species catalog. Required for new trees."),
    ("neighborhood", "Barrio. En árboles nuevos sin barrio se toma el de su ubicación.", "Barrio. New trees without one get the barrio of their location."),
    ("comuna", "Solo para distinguir barrios con el mismo nombre.", "Only to tell apart barrios with the same name."),
    ("site", "Sitio.", "Site."),
    ("latitude", "Latitud (WGS 84). En GeoJSON y Shapefile se usa la geometría del punto.", "Latitude (WGS 84). GeoJSON and Shapefile use the point geometry."),
    ("longitude", "Longitud (WGS 84).", "Longitude (WGS 84)."),
    ("record_date", "Fecha de registro del árbol.", "Date the tree was recorded."),
    ("recorded_by", "Quién registró el árbol (por defecto, su usuario en árboles nuevos).", "Who recorded the tree (your user by default for new trees)."),
    ("elevation_m", "Altitud en metros.", "Elevation in meters."),
    ("total_height_m", "Altura total (m): se agrega como medición nueva.", "Total height (m): added as a new measurement."),
    ("dbh_cm", "Diámetro a la altura del pecho (cm).", "Diameter at breast height (cm)."),
    ("trunk_height_m", "Altura del fuste (m).", "Trunk height (m)."),
    ("crown_diameter_m", "Diámetro de copa (m).", "Crown diameter (m)."),
    ("volume_m3", "Volumen (m³).", "Volume (m³)."),
    ("wood_density_g_cm3", "Densidad de la madera (g/cm³).", "Wood density (g/cm³)."),
    ("measurement_date", "Fecha de las mediciones y observaciones nuevas (obligatoria si las hay). En las descargas se llama last_measurement_date.", "Date of the new measurements and observations (required when there are any). Downloads call it last_measurement_date."),
    ("phytosanitary_status", "Estado fitosanitario: saludable, enfermo, crítico, muerto.", "Phytosanitary status: healthy, sick, critical, dead."),
    ("physical_condition", "Condición física: buena, regular, mala.", "Physical condition: good, fair, poor."),
    ("foliage_density", "Densidad del follaje: densa, media, escasa.", "Foliage density: dense, medium, sparse."),
    ("growth_phase", "Fase de crecimiento: plántula, juvenil, adulto.", "Growth phase: seedling, juvenile, adult."),
    ("photo_url", "Enlace a la foto.", "Link to the photo."),
];

#[derive(Clone, Copy, PartialEq)]
enum Busy {
    Checking,
    Applying,
}

#[component]
pub fn Reports() -> impl IntoView {
    let auth = Auth::use_ctx();
    let i = I18n::use_ctx();
    view! {
        <Show
            when=move || auth.ready.get()
            fallback=move || view! { <div class=CARD><p class="text-sm text-gray-500">{move || i.t("Cargando…", "Loading…")}</p></div> }
        >
            <Show when=move || auth.is_staff() fallback=SignInCard>
                <Uploads />
            </Show>
        </Show>
    }
}

#[component]
fn SignInCard() -> impl IntoView {
    let auth = Auth::use_ctx();
    let i = I18n::use_ctx();
    view! {
        <div class="mx-auto mt-8 max-w-sm bg-white shadow rounded-lg p-6">
            <h1 class="text-xl font-bold text-primary-700 mb-1">{move || i.t("Reportes", "Reports")}</h1>
            <Show
                when=move || auth.user.with(Option::is_none)
                fallback=move || view! {
                    <p class="text-sm text-gray-600">
                        {move || i.t(
                            "Su usuario no tiene permiso para actualizar la base de datos. Pida a un administrador que le dé acceso de staff.",
                            "Your user may not update the database. Ask an administrator for staff access.",
                        )}
                    </p>
                }
            >
                <p class="text-sm text-gray-600 mb-4">
                    {move || i.t(
                        "Inicie sesión para actualizar la base de datos de árboles.",
                        "Sign in to update the tree database.",
                    )}
                </p>
                <LoginForm />
            </Show>
        </div>
    }
}

#[component]
fn Uploads() -> impl IntoView {
    let auth = Auth::use_ctx();
    let i = I18n::use_ctx();
    let current = RwSignal::new(None::<Value>); // checked file waiting to be applied
    let applied = RwSignal::new(None::<Value>);
    let error = RwSignal::new(None::<String>);
    let busy = RwSignal::new(None::<Busy>);
    let history = RwSignal::new(Vec::<Value>::new());
    let dragging = RwSignal::new(false);
    let file_ref = NodeRef::<leptos::html::Input>::new();

    let load_history = move || {
        spawn_local(async move {
            let url = format!("{API_BASE}/api/v1/reports/uploads/");
            if let Ok(v) = auth.get_json(&url).await {
                history.try_set(v["results"].as_array().cloned().unwrap_or_default());
            }
        });
    };
    load_history();

    let lang = move || i.lang_untracked().code();

    let send_file = move |file: web_sys::File| {
        if busy.get_untracked().is_some() {
            return;
        }
        applied.set(None);
        current.set(None);
        if file.size() > MAX_BYTES {
            error.set(Some(i.t("El archivo pesa más de 20 MB.", "The file is larger than 20 MB.").into()));
            return;
        }
        error.set(None);
        busy.set(Some(Busy::Checking));
        spawn_local(async move {
            let url = format!("{API_BASE}/api/v1/reports/uploads/?lang={}", lang());
            let result = auth
                .send(
                    |b| {
                        let form = web_sys::FormData::new().map_err(|_| "FormData".to_string())?;
                        form.append_with_blob_and_filename("file", &file, &file.name())
                            .map_err(|_| "FormData".to_string())?;
                        b.body(form).map_err(|e| e.to_string())
                    },
                    &url,
                    "POST",
                )
                .await;
            busy.try_set(None);
            match result {
                Ok(resp) => {
                    let status = resp.status();
                    let v = resp.json::<Value>().await.unwrap_or(Value::Null);
                    if status == 201 {
                        current.try_set(Some(v));
                        load_history();
                    } else {
                        error.try_set(Some(server_error(&v, status)));
                    }
                }
                Err(e) if e == "401" => {} // session closed: the page shows the login
                Err(_) => {
                    error.try_set(Some(i.t("No se pudo conectar con el servidor.", "Could not reach the server.").into()));
                }
            }
        });
    };

    let on_file = move |ev: leptos::ev::Event| {
        let input = event_target::<web_sys::HtmlInputElement>(&ev);
        let Some(file) = input.files().and_then(|f| f.get(0)) else { return };
        input.set_value(""); // choosing the same file again fires `change` again
        send_file(file);
    };
    let on_drop = move |ev: leptos::ev::DragEvent| {
        ev.prevent_default();
        dragging.set(false);
        if let Some(file) = ev.data_transfer().and_then(|d| d.files()).and_then(|f| f.get(0)) {
            send_file(file);
        }
    };

    let apply = move |_| {
        let Some(id) = current.with_untracked(|c| c.as_ref().and_then(|c| c["id"].as_i64())) else { return };
        busy.set(Some(Busy::Applying));
        error.set(None);
        spawn_local(async move {
            let url = format!("{API_BASE}/api/v1/reports/uploads/{id}/apply/?lang={}", lang());
            let result = auth.post_json(&url, None).await;
            busy.try_set(None);
            match result {
                Ok((200, v)) => {
                    current.try_set(None);
                    applied.try_set(Some(v));
                    load_history();
                }
                // Checked again on apply: the database changed and some rows are wrong now.
                Ok((400, v)) if v.get("summary").is_some() => {
                    current.try_set(Some(v));
                }
                Ok((status, v)) => {
                    error.try_set(Some(server_error(&v, status)));
                }
                Err(e) if e == "401" => {}
                Err(_) => {
                    error.try_set(Some(i.t("No se pudo conectar con el servidor.", "Could not reach the server.").into()));
                }
            }
        });
    };

    let template = move |_| {
        let header = COLUMNS.iter().map(|c| c.0).collect::<Vec<_>>().join(",");
        let csv = format!("\u{feff}{header}\r\n");
        let _ = save_bytes(csv.as_bytes(), "plantilla-arboles.csv", "text/csv;charset=utf-8");
    };

    view! {
        <div class="space-y-6">
            <div class=CARD>
                <h1 class="text-2xl font-bold text-primary-600">{move || i.t("Reportes", "Reports")}</h1>
                <p class="mt-1 text-sm text-gray-600">
                    {move || i.t(
                        "Actualice la base de datos desde un archivo: modifique los datos de árboles existentes, agregue árboles nuevos o mediciones nuevas. Primero verá qué cambiaría; nada se escribe hasta que lo aplique.",
                        "Update the database from a file: edit existing trees, add new trees or new measurements. You first see what would change; nothing is written until you apply it.",
                    )}
                </p>

                <div
                    class=move || format!(
                        "mt-5 flex flex-col items-center justify-center rounded-lg border-2 border-dashed px-6 py-8 text-center transition-colors {}",
                        if dragging.get() { "border-primary-600 bg-primary-50" } else { "border-gray-300" },
                    )
                    on:dragover=move |ev: leptos::ev::DragEvent| { ev.prevent_default(); dragging.set(true); }
                    on:dragleave=move |_| dragging.set(false)
                    on:drop=on_drop
                >
                    <svg xmlns="http://www.w3.org/2000/svg" class="h-10 w-10 text-primary-700" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor" aria-hidden="true">
                        <path stroke-linecap="round" stroke-linejoin="round" d=ICON_UPLOAD />
                    </svg>
                    <p class="mt-2 text-sm text-gray-700">
                        {move || i.t("Arrastre un archivo aquí o", "Drop a file here or")}
                    </p>
                    <button type="button" class=format!("{BTN} {BTN_PRIMARY} mt-2")
                        disabled=move || busy.get().is_some()
                        on:click=move |_| { if let Some(input) = file_ref.get() { input.click(); } }>
                        {move || match busy.get() {
                            Some(Busy::Checking) => i.t("Verificando archivo…", "Checking file…"),
                            _ => i.t("Elegir archivo", "Choose file"),
                        }}
                    </button>
                    <p class="mt-2 text-xs text-gray-500">
                        {move || i.t(
                            "Excel (.xlsx), CSV, Shapefile comprimido (.zip) o GeoJSON · hasta 20 MB y 20.000 filas",
                            "Excel (.xlsx), CSV, zipped Shapefile (.zip) or GeoJSON · up to 20 MB and 20,000 rows",
                        )}
                    </p>
                    <input node_ref=file_ref type="file" class="hidden" accept=ACCEPT on:change=on_file />
                </div>

                {move || error.get().map(|e| view! {
                    <p class="mt-4 rounded-md bg-red-50 px-3 py-2 text-sm text-red-800" role="alert">{e}</p>
                })}
                {move || applied.get().map(|v| view! { <AppliedBanner upload=v /> })}

                <FormatHelp on_template=template />
            </div>

            {move || current.get().map(|v| view! {
                <Preview upload=v busy=busy on_apply=Callback::new(apply) on_cancel=Callback::new(move |_| current.set(None)) />
            })}

            <History history=history />
        </div>
    }
}

fn server_error(v: &Value, status: u16) -> String {
    v["error"].as_str().map(str::to_string).unwrap_or_else(|| format!("Error {status}"))
}

#[component]
fn FormatHelp(on_template: impl Fn(leptos::ev::MouseEvent) + 'static) -> impl IntoView {
    let i = I18n::use_ctx();
    view! {
        <details class="mt-5 rounded-lg border border-gray-200">
            <summary class="cursor-pointer select-none px-4 py-2 text-sm font-medium text-gray-800">
                {move || i.t("Formato del archivo", "File format")}
            </summary>
            <div class="border-t border-gray-200 px-4 py-3 text-sm text-gray-700 space-y-3">
                <p>
                    {move || i.t(
                        "Una fila por árbol, con las mismas columnas de las descargas del Mapa: puede descargar una consulta, editarla y subirla. Solo id es obligatoria; las celdas vacías no cambian nada. Las mediciones y observaciones se agregan con su fecha y las anteriores quedan como historial.",
                        "One row per tree, with the columns of the map's downloads: you can download a query, edit it and upload it. Only id is required; empty cells change nothing. Measurements and observations are added with their date and the previous ones stay as history.",
                    )}
                </p>
                <button type="button" class=format!("{BTN} {BTN_SECONDARY}") on:click=on_template>
                    {move || i.t("Descargar plantilla CSV", "Download CSV template")}
                </button>
                <div class="overflow-x-auto">
                    <table class="min-w-full divide-y divide-gray-200">
                        <tbody class="divide-y divide-gray-100">
                            {COLUMNS.iter().map(|(name, es, en)| view! {
                                <tr>
                                    <td class="py-1.5 pr-4 font-mono text-xs text-gray-900 whitespace-nowrap align-top">{*name}</td>
                                    <td class="py-1.5 text-xs text-gray-600">{move || i.t(es, en)}</td>
                                </tr>
                            }).collect_view()}
                        </tbody>
                    </table>
                </div>
            </div>
        </details>
    }
}

fn count(summary: &Value, key: &str) -> i64 {
    summary["counts"][key].as_i64().unwrap_or(0)
}

/// "3 nuevos · 12 modificados · ..." for a summary.
fn counts_text(lang: Lang, summary: &Value) -> String {
    let parts = [
        ("created", "árboles nuevos", "new trees"),
        ("updated", "árboles modificados", "trees edited"),
        ("measurements", "mediciones", "measurements"),
        ("observations", "observaciones", "observations"),
    ];
    let mut out: Vec<String> = parts
        .iter()
        .filter(|(k, ..)| count(summary, k) > 0)
        .map(|(k, es, en)| format!("{} {}", fmt_thousands(count(summary, k)), pick(lang, *es, *en)))
        .collect();
    let errors = summary["error_count"].as_i64().unwrap_or(0);
    if errors > 0 {
        out.push(format!("{} {}", fmt_thousands(errors), pick(lang, "errores", "errors")));
    }
    if out.is_empty() {
        pick(lang, "sin cambios", "no changes").to_string()
    } else {
        out.join(" · ")
    }
}

#[component]
fn AppliedBanner(upload: Value) -> impl IntoView {
    let i = I18n::use_ctx();
    view! {
        <p class="mt-4 rounded-md bg-green-50 px-3 py-2 text-sm text-green-800" role="status">
            {move || format!(
                "{} {}: {}.",
                i.t("Se aplicó", "Applied"),
                upload["name"].as_str().unwrap_or_default(),
                counts_text(i.lang(), &upload["summary"]),
            )}
        </p>
    }
}

#[component]
fn Preview(
    upload: Value,
    busy: RwSignal<Option<Busy>>,
    on_apply: Callback<()>,
    on_cancel: Callback<()>,
) -> impl IntoView {
    let i = I18n::use_ctx();
    let summary = upload["summary"].clone();
    let name = upload["name"].as_str().unwrap_or_default().to_string();
    let errors = summary["errors"].as_array().cloned().unwrap_or_default();
    let error_count = summary["error_count"].as_i64().unwrap_or(0);
    let changes = summary["changes"].as_array().cloned().unwrap_or_default();
    let changed = count(&summary, "created") + count(&summary, "updated")
        + count(&summary, "measurements") + count(&summary, "observations");
    let can_apply = error_count == 0 && changed > 0;
    let by_feature = summary["numbered_by"].as_str() == Some("feature");
    let ignored = summary["ignored_columns"].as_array().cloned().unwrap_or_default();
    let listed_changes = changes.len() as i64;
    let total_changed = summary["rows"].as_i64().unwrap_or(0) - count(&summary, "unchanged") - error_count;

    let tiles = [
        ("created", "Árboles nuevos", "New trees"),
        ("updated", "Árboles modificados", "Trees edited"),
        ("measurements", "Mediciones nuevas", "New measurements"),
        ("observations", "Observaciones nuevas", "New observations"),
        ("unchanged", "Sin cambios", "Unchanged"),
    ];
    let row_label = move || if by_feature { i.t("Elemento", "Feature") } else { i.t("Fila", "Row") };

    view! {
        <div class=CARD>
            <p class="text-xs font-semibold uppercase tracking-wide text-primary-700">{move || i.t("Vista previa", "Preview")}</p>
            <h2 class="text-lg font-semibold text-gray-900 break-all">{name}</h2>
            <p class="text-sm text-gray-500">
                {move || format!("{} {}", fmt_thousands(summary["rows"].as_i64().unwrap_or(0)), i.t("filas leídas", "rows read"))}
            </p>

            <div class="mt-4 grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-6">
                {tiles.into_iter().map(|(key, es, en)| {
                    let n = count(&upload["summary"], key);
                    view! {
                        <div class="rounded-lg border border-gray-200 px-3 py-2">
                            <p class="text-xs text-gray-500">{move || i.t(es, en)}</p>
                            <p class="text-xl font-semibold text-gray-900">{fmt_thousands(n)}</p>
                        </div>
                    }
                }).collect_view()}
                <div class={if error_count > 0 { "rounded-lg border border-red-300 bg-red-50 px-3 py-2" } else { "rounded-lg border border-gray-200 px-3 py-2" }}>
                    <p class={if error_count > 0 { "text-xs text-red-700" } else { "text-xs text-gray-500" }}>{move || i.t("Errores", "Errors")}</p>
                    <p class={if error_count > 0 { "text-xl font-semibold text-red-800" } else { "text-xl font-semibold text-gray-900" }}>{fmt_thousands(error_count)}</p>
                </div>
            </div>

            {(!ignored.is_empty()).then(|| {
                let names = ignored.iter().filter_map(|v| v.as_str()).collect::<Vec<_>>().join(", ");
                view! {
                    <p class="mt-3 text-sm text-gray-600">
                        {move || i.t("Columnas ignoradas (no se reconocen): ", "Ignored columns (not recognized): ")}
                        <span class="font-mono text-xs">{names.clone()}</span>
                    </p>
                }
            })}

            {(error_count > 0).then(|| view! {
                <div class="mt-5">
                    <h3 class="text-sm font-semibold text-red-800">
                        {move || i.t(
                            "Corrija estos errores en el archivo y vuelva a subirlo: no se aplica nada mientras haya errores.",
                            "Fix these errors in the file and upload it again: nothing is applied while there are errors.",
                        )}
                    </h3>
                    <div class="mt-2 max-h-80 overflow-auto rounded-lg border border-red-200">
                        <table class="min-w-full divide-y divide-red-100">
                            <thead class="bg-red-50 sticky top-0">
                                <tr>
                                    <th class=TH>{row_label}</th>
                                    <th class=TH>{move || i.t("Columna", "Column")}</th>
                                    <th class=TH>{move || i.t("Problema", "Problem")}</th>
                                </tr>
                            </thead>
                            <tbody class="bg-white divide-y divide-gray-100">
                                {errors.iter().map(|e| view! {
                                    <tr>
                                        <td class=TD>{e["row"].as_i64().unwrap_or(0)}</td>
                                        <td class=format!("{TD} font-mono text-xs")>{e["column"].as_str().unwrap_or_default().to_string()}</td>
                                        <td class=TD>{e["message"].as_str().unwrap_or_default().to_string()}</td>
                                    </tr>
                                }).collect_view()}
                            </tbody>
                        </table>
                    </div>
                    {(error_count > errors.len() as i64).then(|| view! {
                        <p class="mt-1 text-xs text-gray-500">
                            {move || format!("{} {} {}", i.t("Se muestran los primeros", "Showing the first"), errors.len(), i.t("errores.", "errors."))}
                        </p>
                    })}
                </div>
            })}

            {(!changes.is_empty()).then(|| view! {
                <div class="mt-5">
                    <h3 class="text-sm font-semibold text-gray-900">{move || i.t("Cambios", "Changes")}</h3>
                    <div class="mt-2 max-h-[28rem] overflow-auto rounded-lg border border-gray-200">
                        <table class="min-w-full divide-y divide-gray-200">
                            <thead class="bg-gray-50 sticky top-0">
                                <tr>
                                    <th class=TH>{row_label}</th>
                                    <th class=TH>{move || i.t("Código", "Code")}</th>
                                    <th class=TH>{move || i.t("Acción", "Action")}</th>
                                    <th class=TH>{move || i.t("Fecha medición", "Measurement date")}</th>
                                    <th class=TH>{move || i.t("Cambios", "Changes")}</th>
                                </tr>
                            </thead>
                            <tbody class="bg-white divide-y divide-gray-100">
                                {changes.iter().map(|c| {
                                    let create = c["action"].as_str() == Some("create");
                                    let fields = c["fields"].as_array().cloned().unwrap_or_default();
                                    view! {
                                        <tr>
                                            <td class=TD>{c["row"].as_i64().unwrap_or(0)}</td>
                                            <td class=format!("{TD} font-medium text-gray-900")>{c["id"].as_i64().unwrap_or(0)}</td>
                                            <td class=TD>
                                                <span class={if create {
                                                    "inline-flex rounded-full bg-green-100 px-2 text-xs font-semibold leading-5 text-green-800"
                                                } else {
                                                    "inline-flex rounded-full bg-blue-100 px-2 text-xs font-semibold leading-5 text-blue-800"
                                                }}>
                                                    {move || if create { i.t("Nuevo", "New") } else { i.t("Modificado", "Edited") }}
                                                </span>
                                            </td>
                                            <td class=format!("{TD} whitespace-nowrap")>{c["date"].as_str().unwrap_or("—").to_string()}</td>
                                            <td class=TD>
                                                <ul class="space-y-0.5">
                                                    {fields.iter().map(|f| {
                                                        let old = f["old"].as_str().unwrap_or_default().to_string();
                                                        let new = f["new"].as_str().unwrap_or_default().to_string();
                                                        view! {
                                                            <li class="text-xs">
                                                                <span class="font-mono text-gray-500">{f["field"].as_str().unwrap_or_default().to_string()}</span>": "
                                                                {(!old.is_empty()).then(|| view! { <span class="text-gray-400 line-through">{old}</span>" → " })}
                                                                <span class="text-gray-900">{new}</span>
                                                            </li>
                                                        }
                                                    }).collect_view()}
                                                </ul>
                                            </td>
                                        </tr>
                                    }
                                }).collect_view()}
                            </tbody>
                        </table>
                    </div>
                    {(total_changed > listed_changes).then(|| view! {
                        <p class="mt-1 text-xs text-gray-500">
                            {move || format!("{} {} {} {}.", i.t("Se muestran", "Showing"), listed_changes, i.t("de", "of"), fmt_thousands(total_changed))}
                        </p>
                    })}
                </div>
            })}

            <div class="mt-5 flex flex-wrap items-center gap-3">
                <button type="button" class=format!("{BTN} {BTN_PRIMARY}")
                    disabled=move || !can_apply || busy.get().is_some()
                    on:click=move |_| on_apply.run(())>
                    {move || match busy.get() {
                        Some(Busy::Applying) => i.t("Aplicando…", "Applying…"),
                        _ => i.t("Aplicar cambios", "Apply changes"),
                    }}
                </button>
                <button type="button" class=format!("{BTN} {BTN_SECONDARY}")
                    disabled=move || busy.get().is_some()
                    on:click=move |_| on_cancel.run(())>
                    {move || i.t("Descartar", "Discard")}
                </button>
                {(error_count == 0 && changed == 0).then(|| view! {
                    <p class="text-sm text-gray-600">{move || i.t("El archivo no cambia nada.", "The file changes nothing.")}</p>
                })}
            </div>
        </div>
    }
}

#[component]
fn History(history: RwSignal<Vec<Value>>) -> impl IntoView {
    let i = I18n::use_ctx();
    view! {
        <div class=CARD>
            <h2 class="text-lg font-semibold text-gray-900">{move || i.t("Archivos enviados", "Files sent")}</h2>
            {move || {
                let rows = history.get();
                if rows.is_empty() {
                    return view! {
                        <p class="mt-2 text-sm text-gray-500">{move || i.t("Aún no se ha enviado ningún archivo.", "No file has been sent yet.")}</p>
                    }.into_any();
                }
                view! {
                    <div class="mt-3 overflow-x-auto">
                        <table class="min-w-full divide-y divide-gray-200">
                            <thead class="bg-gray-50">
                                <tr>
                                    <th class=TH>{move || i.t("Fecha", "Date")}</th>
                                    <th class=TH>{move || i.t("Archivo", "File")}</th>
                                    <th class=TH>{move || i.t("Usuario", "User")}</th>
                                    <th class=TH>{move || i.t("Estado", "Status")}</th>
                                    <th class=TH>{move || i.t("Resultado", "Result")}</th>
                                </tr>
                            </thead>
                            <tbody class="bg-white divide-y divide-gray-100">
                                {rows.into_iter().map(|u| {
                                    let applied = u["status"].as_str() == Some("AP");
                                    let when = u["applied_at"].as_str().or(u["created_at"].as_str()).map(short_datetime).unwrap_or_default();
                                    let summary = u["summary"].clone();
                                    view! {
                                        <tr>
                                            <td class=format!("{TD} whitespace-nowrap")>{when}</td>
                                            <td class=format!("{TD} break-all")>{u["name"].as_str().unwrap_or_default().to_string()}</td>
                                            <td class=TD>{u["user"].as_str().unwrap_or_default().to_string()}</td>
                                            <td class=TD>
                                                <span class={if applied {
                                                    "inline-flex rounded-full bg-green-100 px-2 text-xs font-semibold leading-5 text-green-800"
                                                } else {
                                                    "inline-flex rounded-full bg-gray-100 px-2 text-xs font-semibold leading-5 text-gray-700"
                                                }}>
                                                    {move || if applied { i.t("Aplicado", "Applied") } else { i.t("No aplicado", "Not applied") }}
                                                </span>
                                            </td>
                                            <td class=TD>{move || counts_text(i.lang(), &summary)}</td>
                                        </tr>
                                    }
                                }).collect_view()}
                            </tbody>
                        </table>
                    </div>
                }.into_any()
            }}
        </div>
    }
}

/// `2026-11-18T19:52:01.123Z` -> `2026-11-18 14:52` in the browser's time zone.
fn short_datetime(iso: &str) -> String {
    let date = js_sys::Date::new(&wasm_bindgen::JsValue::from_str(iso));
    if date.get_time().is_nan() {
        return iso.chars().take(16).collect::<String>().replace('T', " ");
    }
    format!(
        "{:04}-{:02}-{:02} {:02}:{:02}",
        date.get_full_year(),
        date.get_month() + 1,
        date.get_date(),
        date.get_hours(),
        date.get_minutes(),
    )
}
