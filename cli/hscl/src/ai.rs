//! Local AI hardware detection (AGENTS.md section 9.2). Read-only; never claims GPU
//! acceleration - only reports what is visible. Dedicated vs shared memory is not conflated.

use serde::Serialize;
use std::fs;
use std::path::Path;

#[derive(Serialize)]
pub struct Gpu {
    pub pci_vendor_id: String,
    pub pci_device_id: String,
    pub vendor: String,
    pub driver: Option<String>,
}

#[derive(Serialize)]
pub struct AiDetect {
    pub cpu_threads: usize,
    pub cpu_flags: Vec<String>,
    pub mem_total_mib: u64,
    pub mem_available_mib: u64,
    pub gpus: Vec<Gpu>,
    pub vulkan_icd_files: Vec<String>,
    pub render_nodes: Vec<String>,
    /// What `hscl ai setup --backend auto` would pick, with the reason. Not a verified result.
    pub recommended_backend: String,
    pub recommended_reason: String,
    pub gpu_acceleration_verified: bool,
    pub note: String,
}

pub fn vendor_name(id: &str) -> &'static str {
    match id.to_ascii_lowercase().trim_start_matches("0x") {
        "1002" => "AMD",
        "10de" => "NVIDIA",
        "8086" => "Intel",
        _ => "unknown",
    }
}

/// Keep only inference-relevant CPU flags.
pub fn interesting_flags(cpuinfo: &str) -> Vec<String> {
    const WANT: [&str; 7] = [
        "avx", "avx2", "avx512f", "fma", "f16c", "avx_vnni", "amx_tile",
    ];
    let line = cpuinfo
        .lines()
        .find(|l| l.starts_with("flags"))
        .unwrap_or("");
    let have: Vec<&str> = line.split_whitespace().collect();
    WANT.iter()
        .filter(|w| have.contains(w))
        .map(|w| w.to_string())
        .collect()
}

fn gpus() -> Vec<Gpu> {
    let mut out = vec![];
    let Ok(rd) = fs::read_dir("/sys/class/drm") else {
        return out;
    };
    let mut seen = std::collections::BTreeSet::new();
    for e in rd.flatten() {
        let name = e.file_name().to_string_lossy().into_owned();
        // cardN only (skip cardN-HDMI-A-1 connectors)
        if !name.starts_with("card") || name.contains('-') {
            continue;
        }
        let dev = e.path().join("device");
        let vendor = fs::read_to_string(dev.join("vendor"))
            .unwrap_or_default()
            .trim()
            .to_string();
        let device = fs::read_to_string(dev.join("device"))
            .unwrap_or_default()
            .trim()
            .to_string();
        if vendor.is_empty() || !seen.insert((vendor.clone(), device.clone())) {
            continue;
        }
        let driver = fs::read_link(dev.join("driver"))
            .ok()
            .and_then(|p| p.file_name().map(|f| f.to_string_lossy().into_owned()));
        out.push(Gpu {
            vendor: vendor_name(&vendor).into(),
            pci_vendor_id: vendor,
            pci_device_id: device,
            driver,
        });
    }
    out
}

fn list_dir(p: &str, filter: impl Fn(&str) -> bool) -> Vec<String> {
    let mut v: Vec<String> = fs::read_dir(p)
        .map(|rd| {
            rd.flatten()
                .map(|e| e.file_name().to_string_lossy().into_owned())
                .filter(|n| filter(n))
                .collect()
        })
        .unwrap_or_default();
    v.sort();
    v
}

pub fn detect() -> AiDetect {
    let cpuinfo = fs::read_to_string("/proc/cpuinfo").unwrap_or_default();
    let mem = fs::read_to_string("/proc/meminfo").unwrap_or_default();
    let icds = list_dir("/usr/share/vulkan/icd.d", |n| n.ends_with(".json"));
    let nodes = list_dir("/dev/dri", |n| n.starts_with("renderD"));
    let gpus = gpus();
    let (rec, reason) = if !icds.is_empty() && !nodes.is_empty() && !gpus.is_empty() {
        ("vulkan", "Vulkan ICD and a DRM render node are present; a real inference smoke test is still required before use")
    } else {
        (
            "cpu",
            "no usable Vulkan ICD / render node detected; CPU inference is the safe fallback",
        )
    };
    let _ = Path::new("/");
    AiDetect {
        cpu_threads: cpuinfo.lines().filter(|l| l.starts_with("processor")).count(),
        cpu_flags: interesting_flags(&cpuinfo),
        mem_total_mib: crate::sysinfo::meminfo_mib(&mem, "MemTotal:"),
        mem_available_mib: crate::sysinfo::meminfo_mib(&mem, "MemAvailable:"),
        gpus,
        vulkan_icd_files: icds,
        render_nodes: nodes,
        recommended_backend: rec.into(),
        recommended_reason: reason.into(),
        gpu_acceleration_verified: false,
        note: "Detection only. GPU acceleration is reported as verified only after a real inference smoke test.".into(),
    }
}

pub fn render(d: &AiDetect) -> String {
    let gpus = if d.gpus.is_empty() {
        "none detected".to_string()
    } else {
        d.gpus
            .iter()
            .map(|g| {
                format!(
                    "{} [{}:{}] driver={}",
                    g.vendor,
                    g.pci_vendor_id,
                    g.pci_device_id,
                    g.driver.as_deref().unwrap_or("?")
                )
            })
            .collect::<Vec<_>>()
            .join("; ")
    };
    format!(
        "CPU threads: {}\nCPU flags:   {}\nMemory:      {} MiB total / {} MiB available\nGPU(s):      {}\nVulkan ICDs: {}\nBackend:     {} ({})\nGPU acceleration verified: no\n{}",
        d.cpu_threads, d.cpu_flags.join(" "), d.mem_total_mib, d.mem_available_mib, gpus,
        if d.vulkan_icd_files.is_empty() { "none".into() } else { d.vulkan_icd_files.join(", ") },
        d.recommended_backend, d.recommended_reason, d.note
    )
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn vendors() {
        assert_eq!(vendor_name("0x1002"), "AMD");
        assert_eq!(vendor_name("0x10DE"), "NVIDIA");
        assert_eq!(vendor_name("0xffff"), "unknown");
    }

    #[test]
    fn flags_subset() {
        let f = interesting_flags("flags\t\t: fpu sse avx avx2 fma foo\n");
        assert_eq!(f, vec!["avx", "avx2", "fma"]);
    }
}
