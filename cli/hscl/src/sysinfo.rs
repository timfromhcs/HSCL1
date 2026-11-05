//! Read-only system information from /etc, /proc and /sys. No command execution.

use serde::Serialize;
use std::fs;

#[derive(Serialize, Default)]
pub struct SysInfo {
    pub os_pretty: String,
    pub os_version_id: String,
    pub os_codename: String,
    pub kernel: String,
    pub arch: String,
    pub cpu_model: String,
    pub cpu_threads: usize,
    pub mem_total_mib: u64,
    pub mem_available_mib: u64,
    pub uefi: bool,
}

/// Parse `KEY="value"` lines (os-release format).
pub fn parse_kv(text: &str) -> Vec<(String, String)> {
    text.lines()
        .filter_map(|l| {
            let (k, v) = l.split_once('=')?;
            Some((k.trim().to_string(), v.trim().trim_matches('"').to_string()))
        })
        .collect()
}

fn get<'a>(kv: &'a [(String, String)], k: &str) -> &'a str {
    kv.iter()
        .find(|(a, _)| a == k)
        .map(|(_, v)| v.as_str())
        .unwrap_or("")
}

/// Parse a `/proc/meminfo` value in kB as MiB.
pub fn meminfo_mib(text: &str, key: &str) -> u64 {
    text.lines()
        .find(|l| l.starts_with(key))
        .and_then(|l| l.split_whitespace().nth(1))
        .and_then(|n| n.parse::<u64>().ok())
        .map(|kb| kb / 1024)
        .unwrap_or(0)
}

pub fn collect() -> SysInfo {
    let osr = parse_kv(&fs::read_to_string("/etc/os-release").unwrap_or_default());
    let cpuinfo = fs::read_to_string("/proc/cpuinfo").unwrap_or_default();
    let mem = fs::read_to_string("/proc/meminfo").unwrap_or_default();
    SysInfo {
        os_pretty: get(&osr, "PRETTY_NAME").to_string(),
        os_version_id: get(&osr, "VERSION_ID").to_string(),
        os_codename: get(&osr, "VERSION_CODENAME").to_string(),
        kernel: fs::read_to_string("/proc/sys/kernel/osrelease")
            .unwrap_or_default()
            .trim()
            .to_string(),
        arch: std::env::consts::ARCH.to_string(),
        cpu_model: cpuinfo
            .lines()
            .find(|l| l.starts_with("model name"))
            .and_then(|l| l.split_once(':'))
            .map(|(_, v)| v.trim().to_string())
            .unwrap_or_default(),
        cpu_threads: cpuinfo
            .lines()
            .filter(|l| l.starts_with("processor"))
            .count(),
        mem_total_mib: meminfo_mib(&mem, "MemTotal:"),
        mem_available_mib: meminfo_mib(&mem, "MemAvailable:"),
        uefi: std::path::Path::new("/sys/firmware/efi").exists(),
    }
}

pub fn render(s: &SysInfo) -> String {
    format!(
        "OS:      {}\nKernel:  {}\nArch:    {}\nCPU:     {} ({} threads)\nMemory:  {} MiB total, {} MiB available\nFirmware: {}",
        s.os_pretty, s.kernel, s.arch, s.cpu_model, s.cpu_threads, s.mem_total_mib, s.mem_available_mib,
        if s.uefi { "UEFI" } else { "BIOS/unknown" }
    )
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn parses_os_release() {
        let kv = parse_kv("NAME=\"Ubuntu\"\nVERSION_ID=\"26.04\"\n# c\n");
        assert_eq!(get(&kv, "VERSION_ID"), "26.04");
        assert_eq!(get(&kv, "MISSING"), "");
    }

    #[test]
    fn parses_meminfo() {
        assert_eq!(
            meminfo_mib("MemTotal:       2048000 kB\n", "MemTotal:"),
            2000
        );
        assert_eq!(meminfo_mib("", "MemTotal:"), 0);
    }
}
