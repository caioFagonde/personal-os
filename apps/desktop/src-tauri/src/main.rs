use personal_os_desktop::{desktop_context, health_payload, sanitize_deep_link, DesktopContext, DesktopHealth};

#[tauri::command]
fn desktop_health() -> DesktopHealth {
    health_payload()
}

#[tauri::command]
fn desktop_runtime_context() -> DesktopContext {
    desktop_context()
}

#[tauri::command]
fn validate_deep_link(url: String) -> Result<String, String> {
    sanitize_deep_link(&url)
}

fn main() {
    tauri::Builder::default()
        .invoke_handler(tauri::generate_handler![desktop_health, desktop_runtime_context, validate_deep_link])
        .run(tauri::generate_context!())
        .expect("failed to run Personal OS desktop shell");
}
