use personal_os_desktop::{
    desktop_context, health_payload, sanitize_deep_link, tray_menu_items, DesktopContext,
    DesktopHealth, QUICK_CAPTURE_WINDOW,
};
use tauri::{
    menu::{Menu, MenuItem},
    tray::TrayIconBuilder,
    Manager, WebviewUrl, WebviewWindowBuilder,
};
use tauri_plugin_global_shortcut::{Code, Modifiers, Shortcut, ShortcutState};

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

/// Toggle the frameless quick-capture window: create-and-show on first use,
/// then focus/hide on subsequent presses.
fn toggle_quick_capture(app: &tauri::AppHandle) {
    if let Some(win) = app.get_webview_window(QUICK_CAPTURE_WINDOW) {
        let visible = win.is_visible().unwrap_or(false);
        if visible {
            let _ = win.hide();
        } else {
            let _ = win.show();
            let _ = win.set_focus();
        }
        return;
    }
    let _ = WebviewWindowBuilder::new(
        app,
        QUICK_CAPTURE_WINDOW,
        WebviewUrl::App("index.html#/capture".into()),
    )
    .title("Quick Capture")
    .inner_size(640.0, 360.0)
    .decorations(false)
    .always_on_top(true)
    .center()
    .skip_taskbar(true)
    .build();
}

fn main() {
    let quick_capture = Shortcut::new(Some(Modifiers::SHIFT | Modifiers::SUPER), Code::Space);

    tauri::Builder::default()
        // Single-instance: focus the running window instead of launching a second.
        .plugin(tauri_plugin_single_instance::init(|app, _argv, _cwd| {
            if let Some(main) = app.get_webview_window("main") {
                let _ = main.show();
                let _ = main.set_focus();
            }
        }))
        // Global shortcut: Ctrl/Cmd+Shift+Space → quick-capture window.
        .plugin(
            tauri_plugin_global_shortcut::Builder::new()
                .with_shortcut(quick_capture)
                .expect("register quick-capture shortcut")
                .with_handler(move |app, shortcut, event| {
                    if event.state() == ShortcutState::Pressed && shortcut == &quick_capture {
                        toggle_quick_capture(app);
                    }
                })
                .build(),
        )
        .setup(|app| {
            // Tray icon: menu items from the shared, tested config. The badge/
            // tooltip is refreshed from the frontend via the desktop commands.
            let handle = app.handle();
            let menu_items: Vec<MenuItem<_>> = tray_menu_items()
                .into_iter()
                .map(|label| MenuItem::with_id(handle, label, label, true, None::<&str>))
                .collect::<Result<_, _>>()?;
            let item_refs: Vec<&dyn tauri::menu::IsMenuItem<_>> =
                menu_items.iter().map(|i| i as &dyn tauri::menu::IsMenuItem<_>).collect();
            let menu = Menu::with_items(handle, &item_refs)?;
            let mut tray = TrayIconBuilder::new().tooltip("Nexus Core · Personal OS").menu(&menu);
            if let Some(icon) = app.default_window_icon() {
                tray = tray.icon(icon.clone());
            }
            tray
                .on_menu_event(|app, event| match event.id().as_ref() {
                    "Capture" => toggle_quick_capture(app),
                    "Quit" => app.exit(0),
                    _ => {}
                })
                .build(app)?;
            Ok(())
        })
        .invoke_handler(tauri::generate_handler![
            desktop_health,
            desktop_runtime_context,
            validate_deep_link
        ])
        .run(tauri::generate_context!())
        .expect("failed to run Personal OS desktop shell");
}
