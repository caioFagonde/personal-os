use serde::Serialize;

#[derive(Debug, Serialize, PartialEq, Eq)]
pub struct DesktopHealth {
    pub service: &'static str,
    pub status: &'static str,
    pub shell: &'static str,
    pub capabilities: Vec<&'static str>,
}

#[derive(Debug, Serialize, PartialEq, Eq)]
pub struct DesktopContext {
    pub os: &'static str,
    pub arch: &'static str,
    pub channel: String,
    pub api_url: String,
}

pub fn health_payload() -> DesktopHealth {
    DesktopHealth {
        service: "personal-os-desktop",
        status: "ok",
        shell: "tauri",
        capabilities: vec!["deep-link", "system-tray-ready", "local-file-open", "mesh-url"],
    }
}

pub fn desktop_context() -> DesktopContext {
    DesktopContext {
        os: std::env::consts::OS,
        arch: std::env::consts::ARCH,
        channel: std::env::var("PERSONAL_OS_RELEASE_CHANNEL").unwrap_or_else(|_| "dev".to_string()),
        api_url: std::env::var("PERSONAL_OS_API_URL").unwrap_or_else(|_| "http://localhost:8080".to_string()),
    }
}

// --- Phase E3: global hotkey + tray + quick-capture window (pure config) ------
// These are side-effect-free so `cargo test --lib` covers them without a display
// server; the Builder in main.rs consumes them at runtime.

/// Global shortcut that summons the frameless quick-capture window.
pub const QUICK_CAPTURE_SHORTCUT: &str = "CmdOrCtrl+Shift+Space";

/// Label of the secondary quick-capture window (frameless, always-on-top).
pub const QUICK_CAPTURE_WINDOW: &str = "quick-capture";

/// Deep link the quick-capture window loads.
pub fn quick_capture_url() -> String {
    "personal-os://capture".to_string()
}

/// Tray context-menu items, in order. The last is always Quit.
pub fn tray_menu_items() -> Vec<&'static str> {
    vec!["Capture", "Approvals", "Sync now", "Open vault", "Quit"]
}

/// Tray badge/tooltip text from live counts. `None` when nothing needs the user
/// (an empty badge is honest: no attention required).
pub fn tray_badge_label(approvals: u32, conflicts: u32) -> Option<String> {
    match (approvals, conflicts) {
        (0, 0) => None,
        (a, 0) => Some(format!("{a} approval{}", if a == 1 { "" } else { "s" })),
        (0, c) => Some(format!("{c} conflict{}", if c == 1 { "" } else { "s" })),
        (a, c) => Some(format!("{a} approval{} · {c} conflict{}", if a == 1 { "" } else { "s" }, if c == 1 { "" } else { "s" })),
    }
}

pub fn sanitize_deep_link(raw: &str) -> Result<String, String> {
    let trimmed = raw.trim();
    if trimmed.len() > 2048 {
        return Err("deep link too long".to_string());
    }
    if trimmed.starts_with("personal-os://") || trimmed.starts_with("http://localhost") || trimmed.starts_with("https://") {
        Ok(trimmed.to_string())
    } else {
        Err("unsupported deep link scheme".to_string())
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn health_payload_is_stable() {
        let payload = health_payload();
        assert_eq!(payload.service, "personal-os-desktop");
        assert_eq!(payload.status, "ok");
        assert!(payload.capabilities.contains(&"mesh-url"));
    }

    #[test]
    fn desktop_context_has_defaults() {
        let ctx = desktop_context();
        assert!(!ctx.os.is_empty());
        assert!(!ctx.arch.is_empty());
        assert!(ctx.api_url.starts_with("http://localhost"));
    }

    #[test]
    fn deep_link_validation_allows_expected_schemes() {
        assert!(sanitize_deep_link("personal-os://open/study").is_ok());
        assert!(sanitize_deep_link("http://localhost:8080/health").is_ok());
        assert!(sanitize_deep_link("https://tailnet-name.ts.net").is_ok());
    }

    #[test]
    fn deep_link_validation_rejects_unsafe_schemes() {
        assert!(sanitize_deep_link("file:///etc/passwd").is_err());
        assert!(sanitize_deep_link("javascript:alert(1)").is_err());
        assert!(sanitize_deep_link(&"a".repeat(3000)).is_err());
    }

    #[test]
    fn quick_capture_shortcut_and_window_are_stable() {
        assert_eq!(QUICK_CAPTURE_SHORTCUT, "CmdOrCtrl+Shift+Space");
        assert_eq!(QUICK_CAPTURE_WINDOW, "quick-capture");
        assert!(sanitize_deep_link(&quick_capture_url()).is_ok());
    }

    #[test]
    fn tray_menu_has_core_actions_and_quit_last() {
        let items = tray_menu_items();
        assert!(items.contains(&"Capture"));
        assert!(items.contains(&"Approvals"));
        assert_eq!(*items.last().unwrap(), "Quit");
    }

    #[test]
    fn tray_badge_reflects_attention() {
        assert_eq!(tray_badge_label(0, 0), None);
        assert_eq!(tray_badge_label(1, 0), Some("1 approval".to_string()));
        assert_eq!(tray_badge_label(2, 0), Some("2 approvals".to_string()));
        assert_eq!(tray_badge_label(0, 3), Some("3 conflicts".to_string()));
        assert_eq!(tray_badge_label(1, 1), Some("1 approval · 1 conflict".to_string()));
    }
}
