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
}
