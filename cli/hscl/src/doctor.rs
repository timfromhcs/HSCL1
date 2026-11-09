//! `hscl doctor` - truthful diagnostics. Output is redacted by default (AGENTS.md 8.3).

use crate::{redact::redact, security, security::State, sysinfo};
use serde::Serialize;

#[derive(Serialize, Clone, Copy, PartialEq, Eq, Debug)]
#[serde(rename_all = "lowercase")]
pub enum Level {
    Pass,
    Warn,
    Fail,
    Skip,
}

#[derive(Serialize)]
pub struct Check {
    pub id: &'static str,
    pub level: Level,
    pub detail: String,
}

#[derive(Serialize)]
pub struct Report {
    pub passed: usize,
    pub warned: usize,
    pub failed: usize,
    pub skipped: usize,
    pub checks: Vec<Check>,
}

fn c(id: &'static str, level: Level, detail: impl Into<String>) -> Check {
    Check {
        id,
        level,
        detail: detail.into(),
    }
}

/// Pure evaluation so it can be unit-tested with synthetic inputs.
pub fn evaluate(s: &sysinfo::SysInfo, sec: &security::Security) -> Vec<Check> {
    let mut v = vec![];
    v.push(if s.arch == "x86_64" {
        c("arch", Level::Pass, "x86_64")
    } else {
        c(
            "arch",
            Level::Warn,
            format!("{} is outside the v1 support scope (x86_64)", s.arch),
        )
    });
    v.push(if s.mem_total_mib >= 3500 {
        c("memory", Level::Pass, format!("{} MiB", s.mem_total_mib))
    } else {
        c(
            "memory",
            Level::Warn,
            format!("{} MiB is below the 4 GB minimum", s.mem_total_mib),
        )
    });
    v.push(match sec.apparmor {
        State::Yes => c("apparmor", Level::Pass, "enabled"),
        State::No => c("apparmor", Level::Fail, "disabled"),
        State::Unknown => c("apparmor", Level::Skip, "not readable on this system"),
    });
    v.push(match sec.firewall_ufw_enabled {
        State::Yes => c("firewall", Level::Pass, "ufw enabled"),
        State::No => c("firewall", Level::Fail, "ufw not enabled"),
        State::Unknown => c("firewall", Level::Skip, "ufw configuration not readable"),
    });
    v.push(if sec.forbidden_apt_sources.is_empty() {
        c(
            "apt-sources",
            Level::Pass,
            "no Kali/Debian/PPA repositories configured",
        )
    } else {
        c(
            "apt-sources",
            Level::Fail,
            format!(
                "forbidden repositories: {}",
                sec.forbidden_apt_sources.join("; ")
            ),
        )
    });
    v.push(match sec.secure_boot {
        State::Yes => c("secure-boot", Level::Pass, "enabled"),
        State::No => c("secure-boot", Level::Warn, "disabled (informational)"),
        State::Unknown => c("secure-boot", Level::Skip, secure_boot_skip_reason()),
    });
    v
}

/// Why Secure Boot could not be determined. Three very different situations used to share one message
/// ("non-UEFI or no efivars"), which was wrong in the installed UEFI VM measured on 2026-11-10: efivars
/// existed, the firmware simply exposed no `SecureBoot` variable because Secure Boot was off.
pub fn secure_boot_skip_reason() -> &'static str {
    secure_boot_skip_reason_at(std::path::Path::new("/sys/firmware"))
}

pub fn secure_boot_skip_reason_at(firmware_root: &std::path::Path) -> &'static str {
    if !firmware_root.join("efi").is_dir() {
        return "not determined: legacy BIOS boot (no /sys/firmware/efi)";
    }
    match std::fs::read_dir(firmware_root.join("efi/efivars")) {
        Ok(_) => {
            "not determined: UEFI without a SecureBoot variable (firmware has Secure Boot off)"
        }
        Err(_) => "not determined: /sys/firmware/efi/efivars is not readable",
    }
}

/// The active KDE colour scheme, read from a kdeglobals body. `hscl doctor` uses this to catch the
/// state visual QA found in the 2026-11-09 screenshots: a dark shell with light widget apps.
pub fn parse_color_scheme(text: &str) -> Option<String> {
    let mut in_general = false;
    for line in text.lines() {
        let l = line.trim();
        if l.starts_with('[') {
            in_general = l == "[General]";
            continue;
        }
        if in_general {
            if let Some(v) = l.strip_prefix("ColorScheme=") {
                let v = v.trim();
                if !v.is_empty() {
                    return Some(v.to_string());
                }
            }
        }
    }
    None
}

/// Pass when the session uses an HCS scheme, warn when it uses another one (the widget palette then
/// differs from the shell), skip when no kdeglobals is readable.
pub fn evaluate_color_scheme(scheme: Option<&str>) -> Check {
    match scheme {
        Some(s) if s.starts_with("HCS") => c("theme", Level::Pass, s.to_string()),
        Some(s) => c(
            "theme",
            Level::Warn,
            format!("{s} is not an HCS scheme; widget apps will not match the HCS palette"),
        ),
        None => c(
            "theme",
            Level::Skip,
            "no kdeglobals readable; colour scheme unknown",
        ),
    }
}

/// Candidate locations for the colour scheme, most specific first. The live session does not write
/// `~/.config/kdeglobals` until something is configured, so the system defaults and `/etc/skel`
/// (where new users come from) are legitimate evidence of what the session will use.
pub fn color_scheme_paths() -> Vec<std::path::PathBuf> {
    use std::path::PathBuf;
    let mut paths = Vec::new();
    if let Ok(xdg) = std::env::var("XDG_CONFIG_HOME") {
        if !xdg.is_empty() {
            paths.push(PathBuf::from(xdg).join("kdeglobals"));
        }
    }
    if let Ok(home) = std::env::var("HOME").or_else(|_| std::env::var("USERPROFILE")) {
        if !home.is_empty() {
            paths.push(PathBuf::from(home).join(".config/kdeglobals"));
        }
    }
    paths.push(PathBuf::from("/etc/xdg/kdeglobals"));
    paths.push(PathBuf::from("/etc/skel/.config/kdeglobals"));
    paths
}

/// Read the first readable candidate and report it together with its source.
pub fn color_scheme_check_in(paths: &[std::path::PathBuf]) -> Check {
    for p in paths {
        if let Ok(text) = std::fs::read_to_string(p) {
            if let Some(scheme) = parse_color_scheme(&text) {
                let mut check = evaluate_color_scheme(Some(&scheme));
                // Say where the value came from: a system default is still the palette the apps use.
                if check.level != Level::Fail {
                    check.detail = format!("{} (from {})", check.detail, p.display());
                }
                return check;
            }
        }
    }
    c(
        "theme",
        Level::Skip,
        "no kdeglobals with a ColorScheme yet; the session palette is unset",
    )
}

pub fn color_scheme_check() -> Check {
    color_scheme_check_in(&color_scheme_paths())
}

pub fn run(_full: bool) -> Report {
    let s = sysinfo::collect();
    let sec = security::collect();
    let user = std::env::var("USER")
        .or_else(|_| std::env::var("USERNAME"))
        .unwrap_or_default();
    let host = std::fs::read_to_string("/etc/hostname")
        .unwrap_or_default()
        .trim()
        .to_string();
    let mut checks = evaluate(&s, &sec);
    checks.push(color_scheme_check());
    for ch in &mut checks {
        ch.detail = redact(&ch.detail, &user, &host);
    }
    let n = |l: Level| checks.iter().filter(|x| x.level == l).count();
    Report {
        passed: n(Level::Pass),
        warned: n(Level::Warn),
        failed: n(Level::Fail),
        skipped: n(Level::Skip),
        checks,
    }
}

pub fn render(r: &Report) -> String {
    let mut out = String::new();
    for ch in &r.checks {
        let tag = match ch.level {
            Level::Pass => "PASS",
            Level::Warn => "WARN",
            Level::Fail => "FAIL",
            Level::Skip => "SKIP",
        };
        out.push_str(&format!("[{tag}] {:<12} {}\n", ch.id, ch.detail));
    }
    out.push_str(&format!(
        "{} passed, {} warnings, {} failed, {} skipped",
        r.passed, r.warned, r.failed, r.skipped
    ));
    out
}

#[cfg(test)]
mod tests {
    use super::*;

    fn sec(a: State, f: State, bad: Vec<String>) -> security::Security {
        security::Security {
            apparmor: a,
            firewall_ufw_enabled: f,
            secure_boot: State::Unknown,
            luks_mapped_devices: None,
            forbidden_apt_sources: bad,
        }
    }

    #[test]
    fn the_secure_boot_skip_reason_distinguishes_bios_uefi_and_unreadable() {
        use std::fs;
        let tmp = tempfile::tempdir().unwrap();
        assert!(secure_boot_skip_reason_at(tmp.path()).contains("legacy BIOS"));
        fs::create_dir_all(tmp.path().join("efi/efivars")).unwrap();
        assert!(secure_boot_skip_reason_at(tmp.path()).contains("without a SecureBoot variable"));
        fs::remove_dir_all(tmp.path().join("efi/efivars")).unwrap();
        assert!(secure_boot_skip_reason_at(tmp.path()).contains("not readable"));
    }

    #[test]
    fn colour_scheme_is_read_from_the_general_section_only() {
        let body = "[Colors:View]\nColorScheme=NotThis\n[General]\nColorScheme=HCSMidnight\nshadeSortColumn=true\n";
        assert_eq!(parse_color_scheme(body).as_deref(), Some("HCSMidnight"));
        assert_eq!(parse_color_scheme("[General]\nColorScheme=  \n"), None);
        assert_eq!(parse_color_scheme(""), None);
    }

    #[test]
    fn an_hcs_scheme_passes_and_another_scheme_warns() {
        assert_eq!(
            evaluate_color_scheme(Some("HCSMidnight")).level,
            Level::Pass
        );
        let warn = evaluate_color_scheme(Some("BreezeLight"));
        assert_eq!(warn.level, Level::Warn);
        assert!(warn.detail.contains("BreezeLight"));
        assert_eq!(evaluate_color_scheme(None).level, Level::Skip);
    }

    #[test]
    fn the_skel_default_is_used_when_the_session_has_no_kdeglobals() {
        // The live session in the 2026-11-09 candidate had no ~/.config/kdeglobals; the palette came
        // from /etc/skel. Reporting SKIP there was wrong because the apps clearly use HCSMidnight.
        let dir = tempfile::tempdir().unwrap();
        let missing = dir.path().join("absent-kdeglobals");
        let skel = dir.path().join("skel-kdeglobals");
        std::fs::write(&skel, "[General]\nColorScheme=HCSMidnight\n").unwrap();
        let check = color_scheme_check_in(&[missing, skel.clone()]);
        assert_eq!(check.level, Level::Pass);
        assert!(check.detail.contains("HCSMidnight"));
        assert!(check.detail.contains("skel-kdeglobals"), "{}", check.detail);
    }

    #[test]
    fn no_kdeglobals_at_all_still_skips() {
        let dir = tempfile::tempdir().unwrap();
        let check = color_scheme_check_in(&[dir.path().join("nope")]);
        assert_eq!(check.level, Level::Skip);
        assert!(check.detail.contains("unset"));
    }

    #[test]
    fn kali_source_fails() {
        let s = sysinfo::SysInfo {
            arch: "x86_64".into(),
            mem_total_mib: 8000,
            ..Default::default()
        };
        let r = evaluate(
            &s,
            &sec(
                State::Yes,
                State::Yes,
                vec!["deb http://http.kali.org/kali kali-rolling main".into()],
            ),
        );
        assert!(r
            .iter()
            .any(|c| c.id == "apt-sources" && c.level == Level::Fail));
    }

    #[test]
    fn unreadable_is_skip_not_pass() {
        let s = sysinfo::SysInfo {
            arch: "x86_64".into(),
            mem_total_mib: 8000,
            ..Default::default()
        };
        let r = evaluate(&s, &sec(State::Unknown, State::Unknown, vec![]));
        assert!(r
            .iter()
            .filter(|c| c.id == "apparmor" || c.id == "firewall")
            .all(|c| c.level == Level::Skip));
    }
}
