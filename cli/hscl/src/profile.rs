//! Hardware profile engine: detected hardware + catalog model + backend capabilities -> a runnable plan.
//!
//! Pure functions. Unknown values stay unknown (never guessed); speed is never claimed (measure with `hscl ai bench`).
//! KV-cache policy: TurboQuant types only when the backend advertises them, otherwise upstream `q8_0` (and `q4_0` only when
//! memory would otherwise force a context below 4096). "No loss" is verified by `hscl ai quality-check`, not asserted here.

use crate::catalog::Model;
use serde::Serialize;

#[derive(Debug, Clone, Serialize, PartialEq, Eq)]
pub struct HwGpu {
    pub vendor: String,
    /// Dedicated VRAM, only when the kernel reports it (amdgpu `mem_info_vram_total`, NVIDIA). `None` = unknown.
    pub vram_mib: Option<u64>,
    /// True for integrated GPUs that use system memory.
    pub unified_memory: bool,
}

#[derive(Debug, Clone, Serialize, PartialEq, Eq)]
pub struct Hw {
    pub ram_total_mib: u64,
    pub ram_available_mib: u64,
    pub cpu_threads: u32,
    pub gpu: Option<HwGpu>,
    pub vulkan: bool,
    pub free_disk_mib: Option<u64>,
}

#[derive(Debug, Clone, Default, Serialize, PartialEq, Eq)]
pub struct BackendCaps {
    /// Accepted TurboQuant cache type names found in `llama-server --help` (e.g. `turbo4`, `turbo3`).
    pub turboquant: Vec<String>,
    /// Accepted value for the speculative-decoding MTP option (e.g. `mtp` or `draft-mtp`), if the build has it.
    pub mtp_flag: Option<String>,
    /// Newer builds take `-fa on|off|auto`, older ones a bare `-fa`.
    pub fa_takes_value: bool,
}

#[derive(Debug, Clone, Serialize, PartialEq, Eq, PartialOrd, Ord)]
pub enum Tier {
    Minimal,
    Tiny,
    Small,
    Medium,
    Large,
    Xl,
}

impl Tier {
    pub fn name(&self) -> &'static str {
        match self {
            Tier::Minimal => "minimal",
            Tier::Tiny => "tiny",
            Tier::Small => "small",
            Tier::Medium => "medium",
            Tier::Large => "large",
            Tier::Xl => "xl",
        }
    }
}

/// RAM bands (MiB, total): below 3.5 GB minimal, then tiny/small/medium/large, xl from 30 GB.
pub fn tier_for(ram_total_mib: u64) -> Tier {
    match ram_total_mib {
        0..=3_499 => Tier::Minimal,
        3_500..=5_999 => Tier::Tiny,
        6_000..=9_999 => Tier::Small,
        10_000..=14_999 => Tier::Medium,
        15_000..=29_999 => Tier::Large,
        _ => Tier::Xl,
    }
}

#[derive(Debug, Clone, Serialize, PartialEq, Eq)]
pub struct Plan {
    pub model_id: String,
    pub tier: Tier,
    pub backend: String,
    pub ngl: i32,
    pub ctx: u32,
    pub kv_type: String,
    pub flash_attn: bool,
    pub threads: u32,
    pub mmap: bool,
    pub low_vram: bool,
    pub mtp: Option<String>,
    pub feasible: bool,
    pub notes: Vec<String>,
}

fn mib(bytes: u64) -> u64 {
    bytes.div_ceil(1024 * 1024)
}

/// Rough f16 KV-cache cost in MiB per token by model size class (documented estimate, not a measurement).
fn kv_mib_per_token_f16(size_mib: u64) -> f64 {
    match size_mib {
        0..=2_000 => 0.03,
        2_001..=4_000 => 0.06,
        4_001..=9_000 => 0.10,
        9_001..=22_000 => 0.12,
        _ => 0.16,
    }
}

fn kv_factor(kv: &str) -> f64 {
    match kv {
        "f16" => 1.0,
        "q8_0" => 0.53,
        "q4_0" => 0.28,
        "turbo4" => 0.27,
        "turbo3" => 0.20,
        _ => 1.0,
    }
}

/// Does the model fit the memory that is actually available? Weights + 15 % overhead + 2048 tokens of a q4_0 KV cache must
/// stay within 90 % of the available RAM, so every "fitting" model also gets a usable context in `plan`.
pub fn fits(hw: &Hw, m: &Model) -> bool {
    let size = mib(m.size_bytes);
    let need = size as f64 * 1.15 + kv_mib_per_token_f16(size) * 2048.0 * kv_factor("q4_0");
    need <= hw.ram_available_mib as f64 * 0.90 && hw.free_disk_mib.map_or(true, |d| d > size + 512)
}

pub fn plan(hw: &Hw, m: &Model, caps: &BackendCaps, low_vram_forced: bool) -> Plan {
    let size = mib(m.size_bytes);
    let mut notes = Vec::new();
    let tier = tier_for(hw.ram_total_mib);
    let gpu_usable = hw.vulkan && hw.gpu.is_some();
    let mut low_vram = low_vram_forced;
    let mut ngl: i32 = 0;
    let backend = if gpu_usable { "vulkan" } else { "cpu" };

    if gpu_usable {
        let g = hw.gpu.as_ref().unwrap();
        match (g.unified_memory, g.vram_mib) {
            (true, _) => {
                ngl = 99;
                notes.push("integrated GPU with shared memory: all layers are offloaded; shared memory counts against RAM".into());
            }
            (false, Some(v)) if v >= size + size / 10 + 512 => ngl = 99,
            (false, Some(v)) => {
                low_vram = true;
                let budget = v.saturating_sub(512) as f64;
                ngl = ((40.0 * budget / size as f64).floor() as i32).clamp(0, 99);
                notes.push(format!("dedicated VRAM {v} MiB < model {size} MiB: partial offload with an assumed 40 layers (tune with llama-bench)"));
            }
            (false, None) => {
                ngl = 0;
                notes.push(
                    "dedicated VRAM is unknown: no layers are offloaded until it is measured"
                        .into(),
                );
            }
        }
    } else {
        notes.push("no usable Vulkan GPU detected: CPU inference".into());
    }
    if low_vram_forced {
        notes.push("low-VRAM mode requested".into());
        if ngl > 0 {
            ngl = ngl.min(((size as f64 / 1024.0) * 6.0) as i32).max(8);
        }
    }

    // KV cache type: TurboQuant only when the backend offers it; otherwise q8_0; q4_0 only when memory forces it.
    let turbo = |name: &str| caps.turboquant.iter().any(|t| t == name);
    let mem_for_kv = (hw.ram_available_mib as f64 * 0.90 - size as f64 * 1.15).max(0.0);
    let ctx_for = |kv: &str| -> u32 {
        let per = kv_mib_per_token_f16(size) * kv_factor(kv);
        (((mem_for_kv / per).floor() as u64).min(32_768) / 1024 * 1024) as u32
    };
    let mut kv = if turbo("turbo4") { "turbo4" } else { "q8_0" }.to_string();
    if low_vram && turbo("turbo3") {
        kv = "turbo3".into();
    }
    if ctx_for(&kv) < 4096 && !turbo("turbo3") {
        kv = "q4_0".into();
        notes.push("memory is tight: KV cache quantised to q4_0 (check quality with `hscl ai quality-check`)".into());
    }
    let ctx = ctx_for(&kv).clamp(0, 32_768);
    let feasible = fits(hw, m) && ctx >= 2048;
    if !feasible {
        notes.push("this model does not fit the available memory with a usable context".into());
    }
    let threads = (hw.cpu_threads / 2).clamp(2, 16);
    let mtp = if m.mtp { caps.mtp_flag.clone() } else { None };
    if m.mtp && mtp.is_none() {
        notes.push("model has MTP heads but this llama.cpp build does not advertise MTP: running without speculative decoding".into());
    }
    if kv != "f16" {
        notes.push("quantised KV cache needs flash attention: enabled".into());
    }
    Plan {
        model_id: m.id.clone(),
        tier,
        backend: backend.into(),
        ngl,
        ctx: ctx.max(if feasible { 2048 } else { 0 }),
        kv_type: kv,
        flash_attn: true,
        threads,
        mmap: !low_vram_forced || size < 8_000,
        low_vram,
        mtp,
        feasible,
        notes,
    }
}

/// `llama-server` arguments for a plan (loopback only; no flag takes a shell string).
pub fn server_args(
    p: &Plan,
    model_path: &str,
    caps: &BackendCaps,
    port: u16,
    mmproj: Option<&str>,
) -> Vec<String> {
    let mut a: Vec<String> = vec![
        "-m".into(),
        model_path.into(),
        "--host".into(),
        "127.0.0.1".into(),
        "--port".into(),
        port.to_string(),
        "-c".into(),
        p.ctx.to_string(),
        "-ngl".into(),
        p.ngl.to_string(),
        "-t".into(),
        p.threads.to_string(),
    ];
    if p.flash_attn {
        a.push("-fa".into());
        if caps.fa_takes_value {
            a.push("on".into());
        }
    }
    if p.kv_type != "f16" {
        a.extend([
            "-ctk".into(),
            p.kv_type.clone(),
            "-ctv".into(),
            p.kv_type.clone(),
        ]);
    }
    if !p.mmap {
        a.push("--no-mmap".into());
    }
    if let Some(flag) = &p.mtp {
        a.extend(["--spec-type".into(), flag.clone()]);
    }
    if let Some(mm) = mmproj {
        a.extend(["--mmproj".into(), mm.into()]);
    }
    a
}

/// Parse `llama-server --help` text into backend capabilities (TurboQuant cache types, MTP value, `-fa` style).
pub fn probe_caps(help: &str) -> BackendCaps {
    let mut turbo: Vec<String> = Vec::new();
    for w in help.split(|c: char| !(c.is_ascii_alphanumeric() || c == '_')) {
        if (w == "turbo2" || w == "turbo3" || w == "turbo4") && !turbo.iter().any(|t| t == w) {
            turbo.push(w.to_string());
        }
    }
    turbo.sort();
    turbo.reverse();
    let words_have_mtp = help
        .split(|c: char| !c.is_ascii_alphanumeric())
        .any(|w| w == "mtp");
    let mtp_flag = if help.contains("draft-mtp") {
        Some("draft-mtp".to_string())
    } else if help.contains("spec-type") && words_have_mtp {
        Some("mtp".to_string())
    } else {
        None
    };
    let fa_takes_value = help.lines().any(|l| {
        (l.contains("-fa,") || l.contains("--flash-attn"))
            && (l.contains("[on|off|auto]") || l.contains("on|off"))
    });
    BackendCaps {
        turboquant: turbo,
        mtp_flag,
        fa_takes_value,
    }
}

/// Catalog entries that fit, best first: requested role, then largest that fits, abliterated variants first (as requested).
pub fn recommend<'a>(hw: &Hw, models: &'a [Model], role: Option<&str>) -> Vec<&'a Model> {
    let mut v: Vec<&Model> = models
        .iter()
        .filter(|m| fits(hw, m))
        .filter(|m| role.map_or(true, |r| m.role == r || m.role == "chat"))
        .collect();
    v.sort_by(|a, b| {
        let ra = (role.is_some_and(|r| a.role == r)) as u8;
        let rb = (role.is_some_and(|r| b.role == r)) as u8;
        rb.cmp(&ra)
            .then((b.variant == "abliterated").cmp(&(a.variant == "abliterated")))
            .then(b.size_bytes.cmp(&a.size_bytes))
    });
    v
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::catalog;

    fn hw(ram_total: u64, avail: u64, gpu: Option<HwGpu>) -> Hw {
        Hw {
            ram_total_mib: ram_total,
            ram_available_mib: avail,
            cpu_threads: 16,
            vulkan: gpu.is_some(),
            gpu,
            free_disk_mib: Some(500_000),
        }
    }
    fn igpu() -> Option<HwGpu> {
        Some(HwGpu {
            vendor: "AMD".into(),
            vram_mib: Some(512),
            unified_memory: true,
        })
    }
    fn dgpu(v: Option<u64>) -> Option<HwGpu> {
        Some(HwGpu {
            vendor: "NVIDIA".into(),
            vram_mib: v,
            unified_memory: false,
        })
    }
    fn models() -> Vec<Model> {
        catalog::load().unwrap()
    }
    fn caps() -> BackendCaps {
        BackendCaps::default()
    }

    #[test]
    fn tier_boundaries() {
        for (ram, t) in [
            (2_000, Tier::Minimal),
            (3_499, Tier::Minimal),
            (3_500, Tier::Tiny),
            (5_999, Tier::Tiny),
            (6_000, Tier::Small),
            (9_999, Tier::Small),
            (10_000, Tier::Medium),
            (14_999, Tier::Medium),
            (15_000, Tier::Large),
            (29_999, Tier::Large),
            (30_000, Tier::Xl),
        ] {
            assert_eq!(tier_for(ram), t, "{ram}");
        }
    }

    #[test]
    fn recommendations_never_exceed_available_memory() {
        let ms = models();
        for avail in [
            2_000u64, 4_000, 6_000, 8_000, 12_000, 16_000, 24_000, 64_000,
        ] {
            let h = hw(avail + 2_000, avail, None);
            for m in recommend(&h, &ms, None) {
                assert!(
                    mib(m.size_bytes) * 115 / 100 <= avail,
                    "{} does not fit {avail} MiB",
                    m.id
                );
            }
        }
    }

    #[test]
    fn eight_gb_gets_the_4b_not_the_9b_and_abliterated_first() {
        let ms = models();
        let r = recommend(&hw(8_192, 6_500, None), &ms, None);
        assert!(!r.is_empty());
        assert!(r.iter().all(|m| m.id != "qwen3.5-9b-abliterated"));
        assert!(r[0].variant == "abliterated");
    }

    #[test]
    fn nothing_fits_below_the_smallest_model() {
        assert!(recommend(&hw(2_048, 1_200, None), &models(), None).is_empty());
    }

    #[test]
    fn coder_role_prefers_the_coder_when_it_fits() {
        let ms = models();
        let r = recommend(&hw(32_000, 28_000, None), &ms, Some("coder"));
        assert_eq!(r[0].role, "coder");
    }

    #[test]
    fn cpu_only_has_no_offload_and_unknown_vram_is_not_guessed() {
        let m = models()
            .into_iter()
            .find(|m| m.id == "qwen3.5-4b-abliterated")
            .unwrap();
        assert_eq!(plan(&hw(16_000, 12_000, None), &m, &caps(), false).ngl, 0);
        let p = plan(&hw(16_000, 12_000, dgpu(None)), &m, &caps(), false);
        assert_eq!(p.ngl, 0);
        assert!(p.notes.iter().any(|n| n.contains("unknown")));
    }

    #[test]
    fn igpu_offloads_everything_and_dgpu_with_enough_vram_too() {
        let m = models()
            .into_iter()
            .find(|m| m.id == "qwen3.5-4b-abliterated")
            .unwrap();
        assert_eq!(
            plan(&hw(16_000, 12_000, igpu()), &m, &caps(), false).ngl,
            99
        );
        assert_eq!(
            plan(&hw(16_000, 12_000, dgpu(Some(8_192))), &m, &caps(), false).ngl,
            99
        );
    }

    #[test]
    fn small_vram_triggers_low_vram_with_partial_offload() {
        let m = models()
            .into_iter()
            .find(|m| m.id == "qwen3.5-9b-abliterated")
            .unwrap();
        let p = plan(&hw(24_000, 20_000, dgpu(Some(2_048))), &m, &caps(), false);
        assert!(p.low_vram);
        assert!(p.ngl > 0 && p.ngl < 99, "partial offload, got {}", p.ngl);
    }

    #[test]
    fn kv_cache_is_q8_0_by_default_and_turboquant_only_when_the_backend_has_it() {
        let m = models()
            .into_iter()
            .find(|m| m.id == "qwen3.5-4b-abliterated")
            .unwrap();
        let h = hw(32_000, 28_000, None);
        assert_eq!(plan(&h, &m, &caps(), false).kv_type, "q8_0");
        let tq = BackendCaps {
            turboquant: vec!["turbo4".into(), "turbo3".into()],
            ..Default::default()
        };
        assert_eq!(plan(&h, &m, &tq, false).kv_type, "turbo4");
        assert_eq!(
            plan(&h, &m, &tq, true).kv_type,
            "turbo3",
            "low-VRAM prefers the denser TurboQuant type"
        );
    }

    #[test]
    fn mtp_only_for_mtp_models_on_capable_backends() {
        let mut m = models().remove(0);
        let c = BackendCaps {
            mtp_flag: Some("mtp".into()),
            ..Default::default()
        };
        assert!(plan(&hw(16_000, 12_000, None), &m, &c, false).mtp.is_none());
        m.mtp = true;
        assert_eq!(
            plan(&hw(16_000, 12_000, None), &m, &c, false)
                .mtp
                .as_deref(),
            Some("mtp")
        );
        let p = plan(&hw(16_000, 12_000, None), &m, &caps(), false);
        assert!(p.mtp.is_none() && p.notes.iter().any(|n| n.contains("MTP")));
    }

    #[test]
    fn context_is_bounded_and_infeasible_models_are_flagged() {
        let ms = models();
        let big = ms
            .iter()
            .find(|m| m.id == "qwen3-coder-30b-a3b-abliterated")
            .unwrap();
        let p = plan(&hw(16_000, 12_000, None), big, &caps(), false);
        assert!(!p.feasible);
        let small = ms
            .iter()
            .find(|m| m.id == "qwen3.5-2b-abliterated")
            .unwrap();
        let q = plan(&hw(64_000, 60_000, None), small, &caps(), false);
        assert!(q.feasible && q.ctx <= 32_768 && q.ctx >= 2048);
    }

    #[test]
    fn probe_caps_parses_help_text() {
        let upstream = "-fa,  --flash-attn [on|off|auto]  set Flash Attention use\n-ctk, --cache-type-k TYPE  f32, f16, bf16, q8_0, q4_0";
        let c = probe_caps(upstream);
        assert!(c.turboquant.is_empty() && c.mtp_flag.is_none() && c.fa_takes_value);
        let fork = "-ctk TYPE  f16, q8_0, q4_0, turbo3, turbo4\n--spec-type [none|draft-mtp|ngram]\n-fa, --flash-attn";
        let c = probe_caps(fork);
        assert_eq!(c.turboquant, vec!["turbo4", "turbo3"]);
        assert_eq!(c.mtp_flag.as_deref(), Some("draft-mtp"));
        assert!(!c.fa_takes_value);
        assert_eq!(
            probe_caps("--spec-type [none|mtp]").mtp_flag.as_deref(),
            Some("mtp")
        );
        assert_eq!(probe_caps("").turboquant.len(), 0);
    }

    #[test]
    fn server_args_bind_loopback_and_follow_the_plan() {
        let m = models()
            .into_iter()
            .find(|m| m.id == "qwen3.5-4b-abliterated")
            .unwrap();
        let c = BackendCaps {
            fa_takes_value: true,
            mtp_flag: Some("mtp".into()),
            ..Default::default()
        };
        let p = plan(&hw(16_000, 12_000, igpu()), &m, &c, false);
        let a = server_args(&p, "/models/x.gguf", &c, 8080, Some("/models/mm.gguf"));
        let s = a.join(" ");
        assert!(
            s.contains("--host 127.0.0.1")
                && s.contains("-ngl 99")
                && s.contains("-fa on")
                && s.contains("-ctk q8_0 -ctv q8_0")
        );
        assert!(s.contains("--mmproj /models/mm.gguf"));
        assert!(!s.contains("0.0.0.0"));
        assert!(
            !s.contains("--spec-type"),
            "the 4B entry is not MTP-trained"
        );
    }
}
