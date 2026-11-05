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
    pub packages: Vec<String>,
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
    fn render_mentions_reboot_state() {
        let mut u = parse_simulation(SOME).unwrap();
        assert!(render(&u).contains("Reboot required: no"));
        u.reboot_required = true;
        assert!(render(&u).contains("Reboot required: yes"));
    }
}
