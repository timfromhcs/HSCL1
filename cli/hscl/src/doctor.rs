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
        State::Unknown => c(
            "secure-boot",
            Level::Skip,
            "not readable (non-UEFI or no efivars)",
        ),
    });
    v
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
