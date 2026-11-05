//! `hscl system updates --check` - read-only view of pending APT updates.
//!
//! Runs `apt-get -s dist-upgrade` (simulation: nothing is installed or downloaded) and parses the result.
//! A broken or unusable apt is an error, never "0 updates".

use anyhow::{bail, Context, Result};
use serde::Serialize;
use std::path::Path;

#[derive(Debug, Serialize, PartialEq, Eq)]
pub struct Updates {
    pub upgradable: usize,
    pub security: usize,
    pub new_packages: usize,
    pub to_remove: usize,
    pub reboot_required: bool,
    /// Age of the newest APT package list in days; `None` when there are no lists at all.
    pub lists_age_days: Option<u64>,
    /// True when the lists are missing or older than `STALE_DAYS`: the counts then say nothing about what is available upstream.
    pub lists_stale: bool,
    pub packages: Vec<String>,
}

pub const STALE_DAYS: u64 = 7;

/// Pure staleness rule: no lists or lists older than `STALE_DAYS` days.
pub fn lists_state(newest_age_secs: Option<u64>) -> (Option<u64>, bool) {
    match newest_age_secs {
        None => (None, true),
        Some(s) => (Some(s / 86_400), s / 86_400 >= STALE_DAYS),
    }
}

/// Age in seconds of the newest regular file in /var/lib/apt/lists (ignoring `lock` and `partial`).
fn newest_list_age_secs() -> Option<u64> {
    let now = std::time::SystemTime::now();
    std::fs::read_dir("/var/lib/apt/lists")
        .ok()?
        .filter_map(|e| e.ok())
        .filter(|e| e.file_name() != "lock" && e.file_type().map(|t| t.is_file()).unwrap_or(false))
        .filter_map(|e| e.metadata().ok()?.modified().ok())
        .filter_map(|m| now.duration_since(m).ok())
        .map(|d| d.as_secs())
        .min()
}

/// Parse `apt-get -s dist-upgrade` output (LC_ALL=C).
pub fn parse_simulation(text: &str) -> Result<Updates> {
    let summary = text
        .lines()
        .find(|l| l.contains(" upgraded, ") && l.contains(" newly installed, "))
        .context("apt output has no summary line (apt unusable or output not recognised)")?;
    let num = |label: &str| -> usize {
        summary
            .split(',')
            .find(|p| p.contains(label))
            .and_then(|p| p.split_whitespace().next())
            .and_then(|n| n.parse().ok())
            .unwrap_or(0)
    };
    let mut packages = Vec::new();
    let mut security = 0;
    for line in text.lines().filter(|l| l.starts_with("Inst ")) {
        let name = line.split_whitespace().nth(1).unwrap_or_default();
        packages.push(name.to_string());
        if line.contains("-security") {
            security += 1;
        }
    }
    packages.sort();
    Ok(Updates {
        upgradable: num("upgraded"),
        security,
        new_packages: num("newly installed"),
        to_remove: num("to remove"),
        reboot_required: false,
        lists_age_days: None,
        lists_stale: true,
        packages,
    })
}

pub fn check() -> Result<Updates> {
    let out = std::process::Command::new("apt-get")
        .args(["-s", "dist-upgrade"])
        .env("LC_ALL", "C")
        .output()
        .context("cannot run apt-get")?;
    if !out.status.success() {
        bail!(
            "apt-get simulation failed ({}): {}",
            out.status,
            String::from_utf8_lossy(&out.stderr).trim()
        );
    }
    let mut u = parse_simulation(&String::from_utf8_lossy(&out.stdout))?;
    u.reboot_required = Path::new("/var/run/reboot-required").exists();
    let (age, stale) = lists_state(newest_list_age_secs());
    u.lists_age_days = age;
    u.lists_stale = stale;
    Ok(u)
}

pub fn render(u: &Updates) -> String {
    let mut s = format!(
        "{} package(s) can be upgraded ({} from the security pocket), {} new, {} to remove.\nReboot required: {}",
        u.upgradable,
        u.security,
        u.new_packages,
        u.to_remove,
        if u.reboot_required { "yes" } else { "no" }
    );
    if u.lists_stale {
        s.push_str(&match u.lists_age_days {
            Some(d) => format!("\nWARNING: package lists are {d} days old - this result is unknown, not 'up to date'. Run: sudo apt update"),
            None => "\nWARNING: no package lists - this result is unknown, not 'up to date'. Run: sudo apt update".to_string(),
        });
    }
    if !u.packages.is_empty() {
        s.push_str("\nPackages: ");
        s.push_str(&u.packages.join(", "));
    }
    s
}

#[cfg(test)]
mod tests {
    use super::*;

    const NONE: &str = "NOTE: This is only a simulation!\nReading package lists...\n0 upgraded, 0 newly installed, 0 to remove and 0 not upgraded.\n";
    const SOME: &str = "NOTE: This is only a simulation!\n\
Inst libfoo1 [1.0] (1.1 Ubuntu:26.04/resolute-security [amd64])\n\
Inst bar [2.0] (2.1 Ubuntu:26.04/resolute-updates [amd64])\n\
Inst newdep (1.0 Ubuntu:26.04/resolute-updates [amd64])\n\
Conf libfoo1 (1.1 Ubuntu:26.04/resolute-security [amd64])\n\
2 upgraded, 1 newly installed, 0 to remove and 0 not upgraded.\n";

    #[test]
    fn no_updates() {
        let u = parse_simulation(NONE).unwrap();
        assert_eq!((u.upgradable, u.security, u.new_packages), (0, 0, 0));
        assert!(u.packages.is_empty());
    }

    #[test]
    fn counts_security_and_names() {
        let u = parse_simulation(SOME).unwrap();
        assert_eq!(u.upgradable, 2);
        assert_eq!(u.security, 1);
        assert_eq!(u.new_packages, 1);
        assert_eq!(u.packages, ["bar", "libfoo1", "newdep"]);
    }

    #[test]
    fn unrecognised_or_empty_output_is_an_error_not_zero_updates() {
        assert!(parse_simulation("").is_err());
        assert!(parse_simulation("E: Could not open lock file\n").is_err());
        assert!(parse_simulation("Reading package lists...\n").is_err());
    }

    #[test]
    fn stale_rule() {
        assert_eq!(lists_state(None), (None, true));
        assert_eq!(lists_state(Some(86_400 * 6 + 10)), (Some(6), false));
        assert_eq!(lists_state(Some(86_400 * 7)), (Some(7), true));
    }

    #[test]
    fn stale_lists_are_never_rendered_as_up_to_date() {
        let u = parse_simulation(NONE).unwrap(); // defaults to stale
        assert!(render(&u).contains("unknown, not 'up to date'"));
        let mut fresh = u;
        fresh.lists_stale = false;
        fresh.lists_age_days = Some(0);
        assert!(!render(&fresh).contains("WARNING"));
    }

    #[test]
    fn render_mentions_reboot_state() {
        let mut u = parse_simulation(SOME).unwrap();
        assert!(render(&u).contains("Reboot required: no"));
        u.reboot_required = true;
        assert!(render(&u).contains("Reboot required: yes"));
    }
}
