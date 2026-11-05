//! Security posture, read-only. Values that cannot be read without privilege are reported
//! as `unknown` - never guessed (AGENTS.md rule 0.3.1).

use serde::Serialize;
use std::fs;
use std::path::Path;

#[derive(Serialize, Clone, Copy, PartialEq, Eq, Debug)]
#[serde(rename_all = "lowercase")]
pub enum State {
    Yes,
    No,
    Unknown,
}

#[derive(Serialize)]
pub struct Security {
    pub apparmor: State,
    pub firewall_ufw_enabled: State,
    pub secure_boot: State,
    pub luks_mapped_devices: Option<usize>,
    /// APT source lines pointing at repositories HSCL1 forbids on the host.
    pub forbidden_apt_sources: Vec<String>,
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

fn apparmor() -> State {
    match fs::read_to_string("/sys/module/apparmor/parameters/enabled") {
        Ok(s) if s.trim() == "Y" => State::Yes,
        Ok(_) => State::No,
        Err(_) => State::Unknown,
    }
}

fn ufw() -> State {
    match fs::read_to_string("/etc/ufw/ufw.conf") {
        Ok(s) => {
            if s.lines()
                .any(|l| l.trim().eq_ignore_ascii_case("ENABLED=yes"))
            {
                State::Yes
            } else {
                State::No
            }
        }
        Err(_) => State::Unknown,
    }
}

fn secure_boot() -> State {
    let dir = Path::new("/sys/firmware/efi/efivars");
    let Ok(rd) = fs::read_dir(dir) else {
        return State::Unknown;
    };
    for e in rd.flatten() {
        if e.file_name().to_string_lossy().starts_with("SecureBoot-") {
            return match fs::read(e.path()) {
                // 4 attribute bytes, then the 1-byte value.
                Ok(b) if b.len() >= 5 => {
                    if b[4] == 1 {
                        State::Yes
                    } else {
                        State::No
                    }
                }
                _ => State::Unknown,
            };
        }
    }
    State::Unknown
}

fn luks_count() -> Option<usize> {
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
        if s.forbidden_apt_sources.is_empty() { "none".into() } else { s.forbidden_apt_sources.join("; ") }
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
}
