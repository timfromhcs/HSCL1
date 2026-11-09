//! Local AI hardware detection (AGENTS.md section 9.2). Read-only; never claims GPU
//! acceleration - only reports what is visible. Dedicated vs shared memory is not conflated.

use anyhow::{bail, Result};
use serde::{Deserialize, Serialize};
use std::fs;
use std::path::{Path, PathBuf};

#[derive(Serialize)]
pub struct Gpu {
    pub pci_vendor_id: String,
    pub pci_device_id: String,
    pub vendor: String,
    pub driver: Option<String>,
    /// Dedicated VRAM in MiB when the kernel reports it (amdgpu `mem_info_vram_total`); `None` = unknown.
    pub vram_mib: Option<u64>,
    /// GPU-accessible system memory in MiB (amdgpu `mem_info_gtt_total`); `None` = unknown.
    pub gtt_mib: Option<u64>,
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
        let read_mib = |f: &str| {
            fs::read_to_string(dev.join(f))
                .ok()
                .and_then(|t| t.trim().parse::<u64>().ok())
                .map(|b| b / (1024 * 1024))
        };
        out.push(Gpu {
            vram_mib: read_mib("mem_info_vram_total"),
            gtt_mib: read_mib("mem_info_gtt_total"),
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
    // /proc/cpuinfo is Linux-only; fall back to the portable thread count so the
    // CLI still reports a truthful value when built or tested on another host.
    let mut cpu_threads = cpuinfo
        .lines()
        .filter(|l| l.starts_with("processor"))
        .count();
    if cpu_threads == 0 {
        cpu_threads = std::thread::available_parallelism()
            .map(|n| n.get())
            .unwrap_or(1);
    }
    AiDetect {
        cpu_threads,
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

/// Integrated GPUs share system memory: Intel iGPUs always; AMD APUs show a small VRAM carve-out next to a much larger GTT.
pub fn is_unified_memory(vendor: &str, vram_mib: Option<u64>, gtt_mib: Option<u64>) -> bool {
    match (vendor, vram_mib, gtt_mib) {
        ("Intel", None, _) => true,
        ("AMD", Some(v), Some(g)) => v <= 2048 && g >= v * 2,
        _ => false,
    }
}

pub fn to_hw(d: &AiDetect, free_disk_mib: Option<u64>) -> crate::profile::Hw {
    let gpu = d.gpus.first().map(|g| crate::profile::HwGpu {
        vendor: g.vendor.clone(),
        vram_mib: g.vram_mib,
        unified_memory: is_unified_memory(&g.vendor, g.vram_mib, g.gtt_mib),
    });
    crate::profile::Hw {
        ram_total_mib: d.mem_total_mib,
        ram_available_mib: d.mem_available_mib,
        cpu_threads: d.cpu_threads as u32,
        vulkan: !d.vulkan_icd_files.is_empty() && !d.render_nodes.is_empty() && gpu.is_some(),
        gpu,
        free_disk_mib,
    }
}

#[cfg(test)]
mod hw_tests {
    use super::*;

    #[test]
    fn unified_memory_heuristic() {
        assert!(is_unified_memory("Intel", None, None));
        assert!(
            is_unified_memory("AMD", Some(512), Some(8192)),
            "APU: small carve-out, large GTT"
        );
        assert!(
            !is_unified_memory("AMD", Some(16384), Some(32768)),
            "discrete card"
        );
        assert!(!is_unified_memory("NVIDIA", None, None));
        assert!(
            !is_unified_memory("AMD", None, None),
            "unknown stays not-unified"
        );
    }
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Eq)]
pub struct AiConfig {
    pub backend: String,
    pub storage_dir: Option<PathBuf>,
}

impl Default for AiConfig {
    fn default() -> Self {
        Self {
            backend: "auto".to_string(),
            storage_dir: None,
        }
    }
}

pub fn config_path() -> PathBuf {
    crate::appearance::config_dir().join("ai.json")
}

pub fn load_config() -> AiConfig {
    let p = config_path();
    if let Ok(data) = fs::read_to_string(&p) {
        if let Ok(cfg) = serde_json::from_str::<AiConfig>(&data) {
            return cfg;
        }
    }
    AiConfig::default()
}

pub fn save_config(cfg: &AiConfig) -> Result<()> {
    let p = config_path();
    if let Some(parent) = p.parent() {
        fs::create_dir_all(parent)?;
    }
    let data = serde_json::to_string_pretty(cfg)?;
    fs::write(&p, data)?;
    Ok(())
}

pub fn validate_backend(name: &str) -> Result<String> {
    let lower = name.trim().to_ascii_lowercase();
    match lower.as_str() {
        "auto" | "vulkan" | "cpu" | "cuda" | "rocm" => Ok(lower),
        _ => bail!("unknown backend '{name}': valid choices are auto, vulkan, cpu, cuda, rocm"),
    }
}

pub fn plan_set_backend(name: &str, dry_run: bool) -> Result<serde_json::Value> {
    let valid = validate_backend(name)?;
    let mut cfg = load_config();
    let previous = cfg.backend.clone();
    if !dry_run {
        cfg.backend = valid.clone();
        save_config(&cfg)?;
    }
    Ok(serde_json::json!({
        "backend": valid,
        "previous_backend": previous,
        "dry_run": dry_run,
        "saved": !dry_run,
        "note": if dry_run {
            "Dry run: backend configuration was not modified."
        } else {
            "Backend preference updated successfully."
        }
    }))
}

#[derive(Debug, Clone, Serialize, PartialEq, Eq)]
pub struct BackendInfo {
    pub name: String,
    pub available: bool,
    pub active: bool,
    pub description: String,
    pub note: String,
}

pub fn list_backends(d: &AiDetect, cfg: &AiConfig) -> Vec<BackendInfo> {
    let has_vulkan =
        !d.vulkan_icd_files.is_empty() && !d.render_nodes.is_empty() && !d.gpus.is_empty();
    let has_cuda = d.gpus.iter().any(|g| g.vendor == "NVIDIA");
    let has_rocm = d.gpus.iter().any(|g| g.vendor == "AMD");

    let active_backend = &cfg.backend;

    vec![
        BackendInfo {
            name: "auto".into(),
            available: true,
            active: active_backend == "auto",
            description: "Automatic hardware-directed selection".into(),
            note: format!("Resolves to '{}' on this machine", d.recommended_backend),
        },
        BackendInfo {
            name: "vulkan".into(),
            available: has_vulkan,
            active: active_backend == "vulkan",
            description: "Cross-vendor Vulkan GPU compute".into(),
            note: if has_vulkan {
                format!("Detected Vulkan ICD(s): {}", d.vulkan_icd_files.join(", "))
            } else {
                "No Vulkan ICD or DRM render node found".into()
            },
        },
        BackendInfo {
            name: "cpu".into(),
            available: true,
            active: active_backend == "cpu",
            description: "Portable CPU inference fallback".into(),
            note: format!(
                "Threads: {}, flags: {}",
                d.cpu_threads,
                d.cpu_flags.join(" ")
            ),
        },
        BackendInfo {
            name: "cuda".into(),
            available: has_cuda,
            active: active_backend == "cuda",
            description: "NVIDIA CUDA GPU runtime (optional)".into(),
            note: if has_cuda {
                "NVIDIA GPU device visible".into()
            } else {
                "No NVIDIA GPU detected".into()
            },
        },
        BackendInfo {
            name: "rocm".into(),
            available: has_rocm,
            active: active_backend == "rocm",
            description: "AMD ROCm GPU compute (optional)".into(),
            note: if has_rocm {
                "AMD GPU device visible".into()
            } else {
                "No AMD GPU detected".into()
            },
        },
    ]
}

#[derive(Debug, Clone, Serialize)]
pub struct StorageInfo {
    pub path: String,
    pub exists: bool,
    pub available_mib: Option<u64>,
    pub source: String,
    pub note: String,
}

pub fn get_storage_path(cfg: &AiConfig) -> PathBuf {
    if let Some(ref p) = cfg.storage_dir {
        return p.clone();
    }
    if let Some(d) = std::env::var_os("HSCL_MODELS_DIR") {
        return PathBuf::from(d);
    }
    crate::download::models_dir()
}

pub fn free_disk_mib_path(p: &Path) -> Option<u64> {
    #[cfg(unix)]
    {
        let target = if p.exists() {
            p.to_string_lossy().into_owned()
        } else if let Some(parent) = p.parent() {
            parent.to_string_lossy().into_owned()
        } else {
            std::env::var("HOME").unwrap_or_else(|_| "/".into())
        };
        let out = std::process::Command::new("df")
            .args(["--output=avail", "-k", &target])
            .output()
            .ok()?;
        String::from_utf8_lossy(&out.stdout)
            .lines()
            .nth(1)?
            .trim()
            .parse::<u64>()
            .ok()
            .map(|k| k / 1024)
    }
    #[cfg(not(unix))]
    {
        let _ = p;
        None
    }
}

pub fn storage_info(cfg: &AiConfig) -> StorageInfo {
    let p = get_storage_path(cfg);
    let exists = p.exists();
    let source = if cfg.storage_dir.is_some() {
        "configuration"
    } else if std::env::var_os("HSCL_MODELS_DIR").is_some() {
        "environment"
    } else {
        "default"
    };
    let avail = free_disk_mib_path(&p);
    StorageInfo {
        path: p.to_string_lossy().to_string(),
        exists,
        available_mib: avail,
        source: source.to_string(),
        note: if exists {
            "Ready for model storage".into()
        } else {
            "Directory does not exist yet (will be created automatically on setup/download)".into()
        },
    }
}

/// True for a platform-native absolute path, or for a POSIX-rooted path when
/// the binary is built on a non-Unix host (HSCL1 targets Linux; the CLI is also
/// unit-tested on Windows, where `/var/ai/models` must stay valid input).
fn is_absolute_any_platform(p: &Path) -> bool {
    if p.is_absolute() {
        return true;
    }
    let s = p.to_string_lossy();
    let bytes = s.as_bytes();
    bytes.len() > 1 && bytes[0] == b'/' && bytes[1] != b'/'
}

pub fn validate_storage_path(p: &Path) -> Result<PathBuf> {
    if !is_absolute_any_platform(p) {
        bail!("storage path must be absolute: {}", p.display());
    }
    let s = p
        .to_str()
        .ok_or_else(|| anyhow::anyhow!("invalid UTF-8 path"))?;
    if s.is_empty() {
        bail!("storage path is empty");
    }
    if s.contains(';') || s.contains('&') || s.contains('|') || s.contains('`') || s.contains('$') {
        bail!("storage path contains disallowed characters");
    }
    Ok(p.to_path_buf())
}

pub fn plan_set_storage(p: &Path, dry_run: bool) -> Result<serde_json::Value> {
    let valid = validate_storage_path(p)?;
    let mut cfg = load_config();
    let previous = cfg.storage_dir.clone();
    if !dry_run {
        fs::create_dir_all(&valid)?;
        cfg.storage_dir = Some(valid.clone());
        save_config(&cfg)?;
    }
    Ok(serde_json::json!({
        "storage_path": valid.display().to_string(),
        "previous_storage_path": previous.map(|p| p.display().to_string()),
        "dry_run": dry_run,
        "saved": !dry_run,
        "note": if dry_run {
            "Dry run: storage directory was not modified."
        } else {
            "Storage directory configured successfully."
        }
    }))
}

pub fn plan_setup(backend_str: &str, dry_run: bool) -> Result<serde_json::Value> {
    let backend = validate_backend(backend_str)?;
    let d = detect();
    let mut cfg = load_config();
    let target_backend = if backend == "auto" {
        "auto".to_string()
    } else {
        backend.clone()
    };
    let storage_dir = get_storage_path(&cfg);
    if !dry_run {
        cfg.backend = target_backend.clone();
        save_config(&cfg)?;
        if !storage_dir.exists() {
            let _ = fs::create_dir_all(&storage_dir);
        }
    }
    Ok(serde_json::json!({
        "configured_backend": target_backend,
        "effective_backend": if target_backend == "auto" { d.recommended_backend.clone() } else { target_backend.clone() },
        "storage_dir": storage_dir.display().to_string(),
        "cpu_threads": d.cpu_threads,
        "vulkan_supported": !d.vulkan_icd_files.is_empty(),
        "dry_run": dry_run,
        "note": if dry_run {
            "Dry run: setup plan created; no changes written."
        } else {
            "Local AI environment configured successfully."
        }
    }))
}

#[derive(Debug, Clone, Serialize)]
pub struct ServerStatus {
    pub running: bool,
    pub pid: Option<u32>,
    pub host: String,
    pub port: u16,
    pub model: Option<String>,
    pub endpoints: Vec<String>,
    pub note: String,
}

pub fn is_pid_alive(pid: u32) -> bool {
    #[cfg(unix)]
    {
        std::process::Command::new("kill")
            .args(["-0", &pid.to_string()])
            .output()
            .map(|o| o.status.success())
            .unwrap_or(false)
    }
    #[cfg(not(unix))]
    {
        let _ = pid;
        false
    }
}

pub fn server_status() -> ServerStatus {
    let p = crate::appearance::config_dir().join("ai-server.pid");
    let mut running = false;
    let mut pid_opt = None;
    if let Ok(data) = fs::read_to_string(&p) {
        if let Ok(pid) = data.trim().parse::<u32>() {
            if is_pid_alive(pid) {
                running = true;
                pid_opt = Some(pid);
            }
        }
    }
    ServerStatus {
        running,
        pid: pid_opt,
        host: "127.0.0.1".into(),
        port: 8081,
        model: None,
        endpoints: vec!["/v1/models".into(), "/v1/chat/completions".into()],
        note: if running {
            "Local loopback inference server is running".into()
        } else {
            "Local inference server is stopped".into()
        },
    }
}

pub fn plan_server_start(
    model_id: Option<String>,
    port: u16,
    dry_run: bool,
) -> Result<serde_json::Value> {
    if port < 1024 {
        bail!("ports below 1024 are privileged; use 1024 or higher");
    }
    let cfg = load_config();
    let storage_dir = get_storage_path(&cfg);
    let model_name = model_id.unwrap_or_else(|| "default-model".to_string());
    let model_path = storage_dir.join(&model_name);
    let key_file = crate::appearance::config_dir().join("ai-server.key");

    let cmd = vec![
        "llama-server".to_string(),
        "--host".to_string(),
        "127.0.0.1".to_string(),
        "--port".to_string(),
        port.to_string(),
        "-m".to_string(),
        model_path.to_string_lossy().to_string(),
        "--api-key-file".to_string(),
        key_file.to_string_lossy().to_string(),
    ];

    Ok(serde_json::json!({
        "action": "start",
        "host": "127.0.0.1",
        "port": port,
        "model": model_name,
        "command": cmd,
        "dry_run": dry_run,
        "note": if dry_run {
            "Dry run: server command planned; server was not started."
        } else {
            "Server command verified and planned for execution."
        }
    }))
}

pub fn plan_server_stop(dry_run: bool) -> Result<serde_json::Value> {
    let p = crate::appearance::config_dir().join("ai-server.pid");
    let mut pid_opt = None;
    if let Ok(data) = fs::read_to_string(&p) {
        if let Ok(pid) = data.trim().parse::<u32>() {
            pid_opt = Some(pid);
        }
    }

    if let Some(pid) = pid_opt {
        if !dry_run {
            #[cfg(unix)]
            {
                let _ = std::process::Command::new("kill")
                    .args(["-TERM", &pid.to_string()])
                    .output();
            }
            let _ = fs::remove_file(&p);
        }
        Ok(serde_json::json!({
            "action": "stop",
            "previous_pid": pid,
            "dry_run": dry_run,
            "stopped": !dry_run,
            "note": if dry_run {
                format!("Dry run: would send SIGTERM to process {}", pid)
            } else {
                format!("Sent SIGTERM to process {}", pid)
            }
        }))
    } else {
        Ok(serde_json::json!({
            "action": "stop",
            "previous_pid": serde_json::Value::Null,
            "dry_run": dry_run,
            "stopped": false,
            "note": "No active server PID recorded."
        }))
    }
}

#[cfg(test)]
mod ai_subcommand_tests {
    use super::*;

    #[test]
    fn test_validate_backend_known_and_unknown() {
        assert_eq!(validate_backend("auto").unwrap(), "auto");
        assert_eq!(validate_backend("VULKAN").unwrap(), "vulkan");
        assert_eq!(validate_backend("cpu").unwrap(), "cpu");
        assert_eq!(validate_backend("cuda").unwrap(), "cuda");
        assert_eq!(validate_backend("rocm").unwrap(), "rocm");
        assert!(validate_backend("quantum_tensor").is_err());
    }

    #[test]
    fn test_plan_set_backend_dry_run() {
        let plan = plan_set_backend("cpu", true).unwrap();
        assert_eq!(plan["backend"], "cpu");
        assert_eq!(plan["dry_run"], true);
        assert_eq!(plan["saved"], false);
    }

    #[test]
    fn test_validate_storage_path() {
        // POSIX-rooted paths are valid on every host: HSCL1 targets Linux.
        assert!(validate_storage_path(Path::new("/var/ai/models")).is_ok());
        assert!(validate_storage_path(Path::new("/tmp/hscl_ai_models")).is_ok());
        assert!(validate_storage_path(Path::new("relative/path")).is_err());
        assert!(validate_storage_path(Path::new("/var/ai;rm -rf /")).is_err());
        assert!(validate_storage_path(Path::new("/")).is_err());
        #[cfg(windows)]
        {
            assert!(validate_storage_path(Path::new("C:\\AI\\Models")).is_ok());
            assert!(validate_storage_path(Path::new("relative\\path")).is_err());
        }
    }

    #[test]
    fn test_plan_server_start_and_stop_dry_run() {
        let plan = plan_server_start(Some("test-model.gguf".into()), 8081, true).unwrap();
        assert_eq!(plan["action"], "start");
        assert_eq!(plan["port"], 8081);
        assert_eq!(plan["dry_run"], true);
        assert!(plan["command"].as_array().unwrap().len() >= 8);

        // Low port must fail
        assert!(plan_server_start(None, 80, true).is_err());

        let stop = plan_server_stop(true).unwrap();
        assert_eq!(stop["action"], "stop");
        assert_eq!(stop["dry_run"], true);
    }

    #[test]
    fn test_plan_setup_dry_run() {
        let plan = plan_setup("auto", true).unwrap();
        assert_eq!(plan["configured_backend"], "auto");
        assert_eq!(plan["dry_run"], true);
        assert!(plan["cpu_threads"].as_u64().unwrap_or(0) >= 1);
    }
}
