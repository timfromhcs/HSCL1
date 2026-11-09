//! Diagnostic log inspection and collection with automatic redaction (AGENTS.md section 8.2, 8.3 & rule 0.3.8).
//!
//! Log commands redact usernames, hostnames, MAC addresses, private IPv4 addresses,
//! and sensitive credential patterns (passwords, tokens, recovery keys) by default.
//! Exporting collected bundles with `--output PATH` never overwrites existing files.

use crate::redact;
use anyhow::{bail, Context, Result};
use serde::{Deserialize, Serialize};
use std::fs;
use std::path::Path;
use std::process::Command;
use std::time::{SystemTime, UNIX_EPOCH};

#[derive(Serialize, Deserialize, Clone, Debug, PartialEq, Eq)]
pub struct LogResult {
    pub target: String,
    pub lines_requested: usize,
    pub lines_returned: usize,
    pub content: String,
    pub redacted: bool,
}

#[derive(Serialize, Deserialize, Clone, Debug, PartialEq, Eq)]
pub struct LogEntry {
    pub source: String,
    pub lines: usize,
    pub bytes: usize,
    pub content: String,
}

#[derive(Serialize, Deserialize, Clone, Debug, PartialEq, Eq)]
pub struct LogBundle {
    pub timestamp: u64,
    pub redacted: bool,
    pub entries: Vec<LogEntry>,
    pub total_bytes: usize,
}

fn get_identity() -> (String, String) {
    let user = ["USER", "USERNAME", "LOGNAME"]
        .iter()
        .find_map(|k| std::env::var(k).ok())
        .unwrap_or_default();
    let host = std::fs::read_to_string("/etc/hostname")
        .ok()
        .map(|s| s.trim().to_string())
        .or_else(|| std::env::var("HOSTNAME").ok())
        .or_else(|| std::env::var("COMPUTERNAME").ok())
        .unwrap_or_default();
    (user, host)
}

/// Redact credentials, passphrases, tokens, or keys that must never appear in logs (AGENTS.md rule 0.3.8).
pub fn sanitize_credentials(text: &str) -> String {
    let bad_keys = [
        "password=",
        "password:",
        "passphrase=",
        "passphrase:",
        "secret=",
        "secret:",
        "token=",
        "token:",
        "recovery_key=",
        "recovery-key=",
    ];

    let mut out = Vec::new();
    for line in text.lines() {
        let mut clean = line.to_string();
        for key in bad_keys {
            if let Some(pos) = clean.to_ascii_lowercase().find(key) {
                let val_start = pos + key.len();
                let val_end = clean[val_start..]
                    .find(|c: char| {
                        c.is_whitespace() || c == ',' || c == ';' || c == '"' || c == '\''
                    })
                    .map(|i| val_start + i)
                    .unwrap_or(clean.len());
                clean.replace_range(val_start..val_end, "[redacted-credential]");
            }
        }
        out.push(clean);
    }
    out.join("\n")
}

/// Fully redact log text (credentials, user, host, MAC, private IPv4).
pub fn redact_log_text(text: &str) -> String {
    let (user, host) = get_identity();
    let pass1 = sanitize_credentials(text);
    redact::redact(&pass1, &user, &host)
}

fn read_last_lines(path: &Path, max_lines: usize) -> Option<String> {
    let content = fs::read_to_string(path).ok()?;
    let lines: Vec<&str> = content.lines().collect();
    if lines.is_empty() {
        return Some(String::new());
    }
    let start = lines.len().saturating_sub(max_lines);
    Some(lines[start..].join("\n"))
}

fn run_journalctl(service: Option<&str>, lines: usize) -> Option<String> {
    let mut cmd = Command::new("journalctl");
    cmd.arg("-n").arg(lines.to_string()).arg("--no-pager");
    if let Some(s) = service {
        cmd.arg("-u").arg(s);
    }
    let out = cmd.output().ok()?;
    if out.status.success() {
        Some(String::from_utf8_lossy(&out.stdout).to_string())
    } else {
        None
    }
}

/// Inspect logs for a specific service or system log.
pub fn show_log(service: Option<&str>, lines: usize, root_prefix: Option<&Path>) -> LogResult {
    let p_root = root_prefix.unwrap_or_else(|| Path::new("/"));
    let target = service.unwrap_or("system").to_string();

    let raw = match target.as_str() {
        "calamares" | "installer" => read_last_lines(&p_root.join("var/log/calamares.log"), lines)
            .or_else(|| read_last_lines(&p_root.join("var/log/installer/syslog"), lines))
            .or_else(|| read_last_lines(&p_root.join("var/log/installer/version"), lines)),
        "xorg" => read_last_lines(&p_root.join("var/log/Xorg.0.log"), lines),
        "sddm" => read_last_lines(&p_root.join("var/log/sddm.log"), lines)
            .or_else(|| run_journalctl(Some("sddm"), lines)),
        "dmesg" | "kernel" => read_last_lines(&p_root.join("var/log/dmesg"), lines).or_else(|| {
            Command::new("dmesg")
                .output()
                .ok()
                .map(|o| String::from_utf8_lossy(&o.stdout).to_string())
                .map(|s| {
                    let l: Vec<&str> = s.lines().collect();
                    let start = l.len().saturating_sub(lines);
                    l[start..].join("\n")
                })
        }),
        "system" | "journal" => run_journalctl(None, lines)
            .or_else(|| read_last_lines(&p_root.join("var/log/syslog"), lines)),
        other => run_journalctl(Some(other), lines),
    };

    let content = match raw {
        Some(s) if !s.trim().is_empty() => redact_log_text(&s),
        _ => format!("No log entries available for service '{target}'"),
    };

    let lines_returned = content.lines().count();

    LogResult {
        target,
        lines_requested: lines,
        lines_returned,
        content,
        redacted: true,
    }
}

/// Collect a redacted diagnostic log bundle.
pub fn collect_logs(root_prefix: Option<&Path>) -> LogBundle {
    let p_root = root_prefix.unwrap_or_else(|| Path::new("/"));
    let mut entries = Vec::new();

    // 1. System / Journal
    let sys = show_log(Some("system"), 100, Some(p_root));
    entries.push(LogEntry {
        source: "system_journal".to_string(),
        lines: sys.lines_returned,
        bytes: sys.content.len(),
        content: sys.content,
    });

    // 2. Kernel / Dmesg
    let kern = show_log(Some("kernel"), 50, Some(p_root));
    entries.push(LogEntry {
        source: "kernel_dmesg".to_string(),
        lines: kern.lines_returned,
        bytes: kern.content.len(),
        content: kern.content,
    });

    // 3. Calamares / Installer
    let inst = show_log(Some("calamares"), 50, Some(p_root));
    if !inst.content.starts_with("No log entries") {
        entries.push(LogEntry {
            source: "calamares_installer".to_string(),
            lines: inst.lines_returned,
            bytes: inst.content.len(),
            content: inst.content,
        });
    }

    // 4. Display Manager (SDDM)
    let sddm = show_log(Some("sddm"), 50, Some(p_root));
    if !sddm.content.starts_with("No log entries") {
        entries.push(LogEntry {
            source: "sddm_display".to_string(),
            lines: sddm.lines_returned,
            bytes: sddm.content.len(),
            content: sddm.content,
        });
    }

    let total_bytes = entries.iter().map(|e| e.bytes).sum();
    let now = SystemTime::now()
        .duration_since(UNIX_EPOCH)
        .unwrap_or_default()
        .as_secs();

    LogBundle {
        timestamp: now,
        redacted: true,
        entries,
        total_bytes,
    }
}

/// Write a log bundle as pretty JSON; refuses to overwrite existing files.
pub fn write_bundle(path: &Path, bundle: &LogBundle) -> Result<()> {
    if path.exists() {
        bail!("refusing to overwrite existing file: {}", path.display());
    }
    let json = serde_json::to_string_pretty(bundle)?;
    fs::write(path, json).with_context(|| format!("failed to write {}", path.display()))?;
    Ok(())
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_sanitize_credentials() {
        let input = "kernel: auth failed user=alice password=SuperSecret123, ip=1.2.3.4\nservice token=ghp_ABC1234567890 valid";
        let clean = sanitize_credentials(input);
        assert!(!clean.contains("SuperSecret123"));
        assert!(!clean.contains("ghp_ABC1234567890"));
        assert!(clean.contains("[redacted-credential]"));
    }

    #[test]
    fn test_redact_log_text_scrubs_mac_and_private_ip() {
        let text = "eth0: link up, mac aa:bb:cc:dd:ee:ff local 192.168.1.100 connected";
        let redacted = redact_log_text(text);
        assert!(!redacted.contains("aa:bb:cc:dd:ee:ff"));
        assert!(!redacted.contains("192.168.1.100"));
        assert!(redacted.contains("[redacted]"));
    }

    #[test]
    fn test_show_log_from_fixture_file() {
        let tmp = tempfile::tempdir().unwrap();
        let log_dir = tmp.path().join("var/log");
        fs::create_dir_all(&log_dir).unwrap();

        let calamares_log = log_dir.join("calamares.log");
        fs::write(
            &calamares_log,
            "10:00:00 [6]: START CALAMARES\n10:00:01 [6]: Partition module done\n10:00:02 [6]: FINISH\n",
        )
        .unwrap();

        let res = show_log(Some("calamares"), 2, Some(tmp.path()));
        assert_eq!(res.lines_requested, 2);
        assert_eq!(res.lines_returned, 2);
        assert!(res.content.contains("FINISH"));
        assert!(!res.content.contains("START CALAMARES"));
    }

    #[test]
    fn test_write_bundle_refuses_overwrite() {
        let tmp = tempfile::tempdir().unwrap();
        let bundle_file = tmp.path().join("logs.json");
        let bundle = collect_logs(Some(tmp.path()));

        assert!(write_bundle(&bundle_file, &bundle).is_ok());
        assert!(bundle_file.is_file());

        // Second write fails
        assert!(write_bundle(&bundle_file, &bundle).is_err());
    }
}
