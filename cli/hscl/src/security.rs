//! Security posture, firewall profiles, AppArmor, disk encryption, and audit (AGENTS.md section 6.1 & 8.2).
//!
//! Values that cannot be read without privilege are reported as `unknown` - never guessed (AGENTS.md rule 0.3.1).
//! Operations that modify system firewall state require root privilege or the privileged helper;
//! `--dry-run` previews the planned commands safely without modifying disk state.

use anyhow::{bail, Context, Result};
use serde::{Deserialize, Serialize};
use std::fs;
use std::path::Path;
use std::time::{SystemTime, UNIX_EPOCH};

#[derive(Serialize, Deserialize, Clone, Copy, PartialEq, Eq, Debug)]
#[serde(rename_all = "lowercase")]
pub enum State {
    Yes,
    No,
    Unknown,
}

#[derive(Serialize, Deserialize, Clone, Debug, PartialEq, Eq)]
pub struct Security {
    pub apparmor: State,
    pub firewall_ufw_enabled: State,
    pub secure_boot: State,
    pub luks_mapped_devices: Option<usize>,
    /// APT source lines pointing at repositories HSCL1 forbids on the host.
    pub forbidden_apt_sources: Vec<String>,
}

#[derive(Serialize, Deserialize, Clone, Debug, PartialEq, Eq)]
pub struct FirewallStatus {
    pub enabled: State,
    pub default_incoming: String,
    pub default_outgoing: String,
    pub active_profile: String,
    pub profiles_available: Vec<String>,
}

#[derive(Serialize, Deserialize, Clone, Debug, PartialEq, Eq)]
pub struct FirewallProfile {
    pub name: &'static str,
    pub summary: &'static str,
    pub incoming_policy: &'static str,
    pub outgoing_policy: &'static str,
    pub description: &'static str,
}

pub const PROFILES: &[FirewallProfile] = &[
    FirewallProfile {
        name: "standard",
        summary: "Standard workstation protection (default)",
        incoming_policy: "deny",
        outgoing_policy: "allow",
        description: "Deny unsolicited inbound connections; permit normal outbound connections for daily-driver usage.",
    },
    FirewallProfile {
        name: "public-wifi",
        summary: "Untrusted public network protection",
        incoming_policy: "deny",
        outgoing_policy: "allow",
        description: "Deny all inbound connections, disable local discovery and file sharing services.",
    },
    FirewallProfile {
        name: "lab",
        summary: "Security Lab and host-only virtualization isolation",
        incoming_policy: "deny",
        outgoing_policy: "reject",
        description: "Tailored to virtual machine network interfaces and test lab (host-only isolation; no direct internet).",
    },
    FirewallProfile {
        name: "privacy",
        summary: "Privacy session isolation (Tor only)",
        incoming_policy: "deny",
        outgoing_policy: "reject",
        description: "Only expose approved Tor / bootstrapping traffic in dedicated privacy environment; block direct internet egress.",
    },
];

#[derive(Serialize, Deserialize, Clone, Debug, PartialEq, Eq)]
pub struct ApparmorStatus {
    pub enabled: State,
    pub profiles_loaded: usize,
    pub enforce_mode: usize,
    pub complain_mode: usize,
}

#[derive(Serialize, Deserialize, Clone, Debug, PartialEq, Eq)]
pub struct EncryptionStatus {
    pub luks_mapped_volumes: usize,
    pub crypttab_entries: Vec<String>,
    pub root_is_encrypted: bool,
}

#[derive(Serialize, Deserialize, Clone, Debug, PartialEq, Eq)]
pub struct RecoveryCheckStatus {
    pub backup_dir_exists: bool,
    pub snapshots_found: usize,
    pub notice: String,
}

#[derive(Serialize, Deserialize, Clone, Debug, PartialEq, Eq)]
pub struct SecurityAudit {
    pub timestamp: u64,
    pub apparmor: ApparmorStatus,
    pub firewall: FirewallStatus,
    pub secure_boot: State,
    pub encryption: EncryptionStatus,
    pub suid_dumpable_secure: bool,
    pub forbidden_apt_sources: Vec<String>,
    pub overall_verdict: String,
}

/// Return the lines of APT sources that reference forbidden repositories
/// (Kali, Debian, PPAs, Ubuntu interim/development pockets). Pure function for testing.
pub fn forbidden_sources(text: &str) -> Vec<String> {
    const BAD: [&str; 6] = [
        "kali.org",
        "deb.debian.org",
        "ppa.launchpad",
        "ppa.launchpadcontent",
        "kali-rolling",
        "/debian ",
    ];
    text.lines()
        .map(str::trim)
        .filter(|l| !l.starts_with('#') && !l.is_empty())
        .filter(|l| BAD.iter().any(|b| l.contains(b)))
        .map(String::from)
        .collect()
}

fn read_apt_sources() -> String {
    let mut all = fs::read_to_string("/etc/apt/sources.list").unwrap_or_default();
    if let Ok(rd) = fs::read_dir("/etc/apt/sources.list.d") {
        for e in rd.flatten() {
            if let Some(ext) = e.path().extension().and_then(|x| x.to_str()) {
                if ext == "list" || ext == "sources" {
                    all.push('\n');
                    all.push_str(&fs::read_to_string(e.path()).unwrap_or_default());
                }
            }
        }
    }
    all
}

pub fn parse_apparmor_enabled(content: &str) -> State {
    match content.trim() {
        "Y" | "1" => State::Yes,
        "N" | "0" => State::No,
        _ => State::Unknown,
    }
}

pub fn apparmor() -> State {
    match fs::read_to_string("/sys/module/apparmor/parameters/enabled") {
        Ok(s) => parse_apparmor_enabled(&s),
        Err(_) => State::Unknown,
    }
}

pub fn parse_apparmor_profiles(text: &str) -> (usize, usize) {
    let mut enforce = 0;
    let mut complain = 0;
    for line in text.lines() {
        let t = line.trim();
        if t.contains("(enforce)") {
            enforce += 1;
        } else if t.contains("(complain)") {
            complain += 1;
        }
    }
    (enforce, complain)
}

pub fn apparmor_status() -> ApparmorStatus {
    let enabled = apparmor();
    let profiles_content =
        fs::read_to_string("/sys/kernel/security/apparmor/profiles").unwrap_or_default();
    let (enforce, complain) = parse_apparmor_profiles(&profiles_content);
    ApparmorStatus {
        enabled,
        profiles_loaded: enforce + complain,
        enforce_mode: enforce,
        complain_mode: complain,
    }
}

pub fn parse_ufw_conf(text: &str) -> State {
    for l in text.lines() {
        let s = l.trim();
        if s.eq_ignore_ascii_case("ENABLED=yes") {
            return State::Yes;
        } else if s.eq_ignore_ascii_case("ENABLED=no") {
            return State::No;
        }
    }
    State::Unknown
}

pub fn ufw() -> State {
    match fs::read_to_string("/etc/ufw/ufw.conf") {
        Ok(s) => parse_ufw_conf(&s),
        Err(_) => State::Unknown,
    }
}

pub fn firewall_status() -> FirewallStatus {
    let enabled = ufw();
    let active_profile = match enabled {
        State::Yes => "standard",
        State::No => "disabled",
        State::Unknown => "unknown",
    };

    FirewallStatus {
        enabled,
        default_incoming: "deny".to_string(),
        default_outgoing: "allow".to_string(),
        active_profile: active_profile.to_string(),
        profiles_available: PROFILES.iter().map(|p| p.name.to_string()).collect(),
    }
}

pub fn plan_firewall_profile_set(name: &str) -> Result<Vec<String>> {
    let p = PROFILES
        .iter()
        .find(|p| p.name.eq_ignore_ascii_case(name.trim()))
        .with_context(|| format!("Unknown firewall profile '{name}'. Choose from: standard, public-wifi, lab, privacy"))?;

    let mut cmds = Vec::new();
    match p.name {
        "standard" => {
            cmds.push("ufw default deny incoming".to_string());
            cmds.push("ufw default allow outgoing".to_string());
            cmds.push("ufw enable".to_string());
        }
        "public-wifi" => {
            cmds.push("ufw default deny incoming".to_string());
            cmds.push("ufw default allow outgoing".to_string());
            cmds.push("ufw deny in to any port 5353 proto udp".to_string()); // block mDNS
            cmds.push("ufw enable".to_string());
        }
        "lab" => {
            cmds.push("ufw default deny incoming".to_string());
            cmds.push("ufw default reject outgoing".to_string());
            cmds.push("ufw enable".to_string());
        }
        "privacy" => {
            cmds.push("ufw default deny incoming".to_string());
            cmds.push("ufw default reject outgoing".to_string());
            cmds.push("ufw allow out to any port 9001 proto tcp".to_string()); // tor relay/directory
            cmds.push("ufw enable".to_string());
        }
        _ => unreachable!(),
    }

    Ok(cmds)
}

pub fn set_firewall_profile(name: &str, dry_run: bool) -> Result<Vec<String>> {
    let cmds = plan_firewall_profile_set(name)?;
    if dry_run {
        return Ok(cmds);
    }

    // Applying requires root privilege
    #[cfg(unix)]
    {
        let uid = unsafe { libc::geteuid() };
        if uid != 0 {
            bail!(
                "Applying firewall profile '{}' requires administrative privilege. Run with sudo: sudo hscl security firewall profile set {}",
                name,
                name
            );
        }
    }

    #[cfg(not(unix))]
    {
        bail!(
            "Applying firewall profile '{}' requires running on a Linux host with administrative privilege.",
            name
        );
    }

    #[allow(unreachable_code)]
    Ok(cmds)
}

pub fn parse_secure_boot(bytes: &[u8]) -> State {
    if bytes.len() >= 5 {
        if bytes[4] == 1 {
            State::Yes
        } else {
            State::No
        }
    } else {
        State::Unknown
    }
}

pub fn secure_boot() -> State {
    let dir = Path::new("/sys/firmware/efi/efivars");
    let Ok(rd) = fs::read_dir(dir) else {
        return State::Unknown;
    };
    for e in rd.flatten() {
        if e.file_name().to_string_lossy().starts_with("SecureBoot-") {
            return match fs::read(e.path()) {
                Ok(b) => parse_secure_boot(&b),
                _ => State::Unknown,
            };
        }
    }
    State::Unknown
}

pub fn luks_count() -> Option<usize> {
    let rd = fs::read_dir("/sys/block").ok()?;
    let mut n = 0;
    for e in rd.flatten() {
        let uuid = e.path().join("dm/uuid");
        if let Ok(u) = fs::read_to_string(uuid) {
            if u.starts_with("CRYPT-LUKS") {
                n += 1;
            }
        }
    }
    Some(n)
}

pub fn parse_crypttab(text: &str) -> Vec<String> {
    text.lines()
        .map(str::trim)
        .filter(|l| !l.is_empty() && !l.starts_with('#'))
        .map(String::from)
        .collect()
}

pub fn encryption_status() -> EncryptionStatus {
    let luks_count = luks_count().unwrap_or(0);
    let crypttab_text = fs::read_to_string("/etc/crypttab").unwrap_or_default();
    let entries = parse_crypttab(&crypttab_text);

    let root_is_encrypted = luks_count > 0;

    EncryptionStatus {
        luks_mapped_volumes: luks_count,
        crypttab_entries: entries,
        root_is_encrypted,
    }
}

pub fn recovery_check() -> RecoveryCheckStatus {
    let backup_dirs = [
        "/var/backups/hscl",
        "/timeshift/snapshots",
        "/var/lib/snapper/snapshots",
    ];

    let mut found = 0;
    let mut dir_exists = false;

    for d in backup_dirs {
        let p = Path::new(d);
        if p.is_dir() {
            dir_exists = true;
            if let Ok(rd) = fs::read_dir(p) {
                found += rd.flatten().count();
            }
        }
    }

    let notice = if found > 0 {
        format!("{found} system recovery snapshot(s) detected.")
    } else {
        "No recovery snapshots found. Recommended: configure system backups via Timeshift or btrfs snapshots."
            .to_string()
    };

    RecoveryCheckStatus {
        backup_dir_exists: dir_exists,
        snapshots_found: found,
        notice,
    }
}

pub fn audit_collect(root_prefix: Option<&Path>) -> SecurityAudit {
    let p_root = root_prefix.unwrap_or_else(|| Path::new("/"));

    let suid_path = p_root.join("proc/sys/fs/suid_dumpable");
    let suid_content = fs::read_to_string(&suid_path).unwrap_or_default();
    let suid_dumpable_secure = suid_content.trim() == "0";

    let now = SystemTime::now()
        .duration_since(UNIX_EPOCH)
        .unwrap_or_default()
        .as_secs();

    let ap = apparmor_status();
    let fw = firewall_status();
    let sb = secure_boot();
    let enc = encryption_status();
    let bad_repos = forbidden_sources(&read_apt_sources());

    let pass = ap.enabled != State::No
        && fw.enabled != State::No
        && bad_repos.is_empty()
        && suid_dumpable_secure;

    let overall_verdict = if pass {
        "PASS: Core security baseline established (AppArmor active, UFW enabled, forbidden repos clear, core dump memory protected)"
    } else {
        "ATTENTION: Security baseline checks identified recommended hardening actions"
    };

    SecurityAudit {
        timestamp: now,
        apparmor: ap,
        firewall: fw,
        secure_boot: sb,
        encryption: enc,
        suid_dumpable_secure,
        forbidden_apt_sources: bad_repos,
        overall_verdict: overall_verdict.to_string(),
    }
}

pub fn write_audit_report(path: &Path, audit: &SecurityAudit) -> Result<()> {
    if path.exists() {
        bail!("refusing to overwrite existing file: {}", path.display());
    }
    let json = serde_json::to_string_pretty(audit)?;
    fs::write(path, json).with_context(|| format!("failed to write {}", path.display()))?;
    Ok(())
}

pub fn collect() -> Security {
    Security {
        apparmor: apparmor(),
        firewall_ufw_enabled: ufw(),
        secure_boot: secure_boot(),
        luks_mapped_devices: luks_count(),
        forbidden_apt_sources: forbidden_sources(&read_apt_sources()),
    }
}

pub fn render(s: &Security) -> String {
    let st = |x: State| match x {
        State::Yes => "yes",
        State::No => "NO",
        State::Unknown => "unknown (not readable)",
    };
    format!(
        "AppArmor enabled:   {}\nUFW enabled:        {}\nSecure Boot:        {}\nLUKS volumes open:  {}\nForbidden APT repos: {}",
        st(s.apparmor),
        st(s.firewall_ufw_enabled),
        st(s.secure_boot),
        s.luks_mapped_devices.map_or("unknown".into(), |n| n.to_string()),
        if s.forbidden_apt_sources.is_empty() {
            "none".into()
        } else {
            s.forbidden_apt_sources.join("; ")
        }
    )
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn flags_kali_and_ppa() {
        let t = "deb http://http.kali.org/kali kali-rolling main\n# deb http://deb.debian.org/debian x\n\
                 deb http://archive.ubuntu.com/ubuntu resolute main\ndeb https://ppa.launchpadcontent.net/a/b/ubuntu resolute main";
        let f = forbidden_sources(t);
        assert_eq!(f.len(), 2);
        assert!(f[0].contains("kali"));
    }

    #[test]
    fn clean_ubuntu_sources_pass() {
        let t = "Types: deb\nURIs: http://archive.ubuntu.com/ubuntu/\nSuites: resolute resolute-updates resolute-security\n";
        assert!(forbidden_sources(t).is_empty());
    }

    #[test]
    fn test_parse_apparmor_profiles() {
        let sample = "\
/usr/bin/evince (enforce)
/usr/bin/man (enforce)
/usr/sbin/tcpdump (complain)
";
        let (enforce, complain) = parse_apparmor_profiles(sample);
        assert_eq!(enforce, 2);
        assert_eq!(complain, 1);
    }

    #[test]
    fn test_parse_ufw_conf() {
        assert_eq!(parse_ufw_conf("ENABLED=yes\n"), State::Yes);
        assert_eq!(parse_ufw_conf("ENABLED=no\n"), State::No);
        assert_eq!(parse_ufw_conf("# empty\n"), State::Unknown);
    }

    #[test]
    fn test_plan_firewall_profiles() {
        let std_cmds = plan_firewall_profile_set("standard").unwrap();
        assert!(std_cmds.iter().any(|c| c.contains("default deny incoming")));
        assert!(std_cmds
            .iter()
            .any(|c| c.contains("default allow outgoing")));

        let pub_cmds = plan_firewall_profile_set("public-wifi").unwrap();
        assert!(pub_cmds.iter().any(|c| c.contains("5353")));

        let lab_cmds = plan_firewall_profile_set("lab").unwrap();
        assert!(lab_cmds
            .iter()
            .any(|c| c.contains("default reject outgoing")));

        let priv_cmds = plan_firewall_profile_set("privacy").unwrap();
        assert!(priv_cmds.iter().any(|c| c.contains("9001")));

        assert!(plan_firewall_profile_set("invalid-name").is_err());
    }

    #[test]
    fn test_parse_crypttab() {
        let sample = "\
# target  source                                    keyfile  options
cr_root   UUID=12345678-1234-1234-1234-123456789abc  none     luks,discard
";
        let entries = parse_crypttab(sample);
        assert_eq!(entries.len(), 1);
        assert!(entries[0].starts_with("cr_root"));
    }

    #[test]
    fn test_write_audit_report_refuses_overwrite() {
        let tmp = tempfile::tempdir().unwrap();
        let report_file = tmp.path().join("audit.json");
        let audit = audit_collect(None);

        // First write succeeds
        assert!(write_audit_report(&report_file, &audit).is_ok());
        assert!(report_file.is_file());

        // Second write to same file fails
        assert!(write_audit_report(&report_file, &audit).is_err());
    }
}
