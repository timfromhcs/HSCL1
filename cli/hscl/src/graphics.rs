//! Adaptive graphics: detect the machine, pick a profile (ultra..minimal), apply it to Qt Quick, KWin and the rain wallpaper.
//!
//! Pure classification and profile mapping (tested); applying goes through fixed `kwriteconfig6`/`qdbus6` argument vectors.
//! Software rendering (no GPU, virtual GPU) always gets the minimal profile: animations off, no blur or translucency.

use crate::appearance::Runner;
use anyhow::Result;
use serde::Serialize;
use std::path::Path;

#[derive(Debug, Clone, Copy, Serialize, PartialEq, Eq)]
pub enum GpuClass {
    Discrete,
    Integrated,
    /// Virtual or software-rendered (QEMU/VMware/virtio, llvmpipe-only): no real acceleration.
    Software,
    None,
}

#[derive(Debug, Clone, Serialize, PartialEq, Eq)]
pub struct Machine {
    pub gpu: GpuClass,
    pub driver: Option<String>,
    pub ram_total_mib: u64,
    pub cpu_threads: u32,
    /// Pixels of the largest connected display, if known.
    pub pixels: Option<u64>,
    pub on_battery_device: bool,
    pub low_vram_mode: bool,
}

#[derive(Debug, Clone, Copy, Serialize, PartialEq, Eq, PartialOrd, Ord)]
pub enum Level {
    Minimal,
    Low,
    Balanced,
    High,
    Ultra,
}

impl Level {
    pub fn name(&self) -> &'static str {
        match self {
            Level::Minimal => "minimal",
            Level::Low => "low",
            Level::Balanced => "balanced",
            Level::High => "high",
            Level::Ultra => "ultra",
        }
    }
}

#[derive(Debug, Clone, Serialize, PartialEq)]
pub struct Profile {
    pub level: Level,
    /// `QSG_RHI_BACKEND` value for Qt Quick apps ("software" -> QT_QUICK_BACKEND=software instead).
    pub qt_quick: String,
    /// KWin `AnimationDurationFactor` (0 = animations off; also stops the rain wallpaper).
    pub animation_factor: f32,
    pub blur: bool,
    pub translucency: bool,
    pub rain_density: u8,
    pub notes: Vec<String>,
}

const VIRTUAL_DRIVERS: &[&str] = &[
    "bochs-drm",
    "bochs",
    "vmwgfx",
    "virtio_gpu",
    "virtio-gpu",
    "qxl",
    "cirrus",
    "simpledrm",
    "vboxvideo",
    "hyperv_drm",
];

/// Classify the GPU from the DRM driver name and whether a render node exists.
pub fn classify(driver: Option<&str>, has_render_node: bool, discrete_hint: bool) -> GpuClass {
    match driver {
        None => GpuClass::None,
        Some(d) if VIRTUAL_DRIVERS.contains(&d) || !has_render_node => GpuClass::Software,
        Some(_) if discrete_hint => GpuClass::Discrete,
        Some(_) => GpuClass::Integrated,
    }
}

pub fn profile(m: &Machine) -> Profile {
    let mut notes = Vec::new();
    let mut level = match m.gpu {
        GpuClass::Software | GpuClass::None => Level::Minimal,
        GpuClass::Integrated if m.ram_total_mib < 6_000 => Level::Low,
        GpuClass::Integrated => Level::Balanced,
        GpuClass::Discrete if m.ram_total_mib < 8_000 => Level::Balanced,
        GpuClass::Discrete => Level::High,
    };
    if m.gpu == GpuClass::Discrete && m.ram_total_mib >= 16_000 && m.cpu_threads >= 8 {
        level = Level::Ultra;
    }
    if m.gpu == GpuClass::Integrated && m.pixels.is_some_and(|p| p > 3840 * 2160) {
        level = level.min(Level::Low);
        notes.push("very high resolution on an integrated GPU: reduced".into());
    }
    if m.on_battery_device && level > Level::Balanced {
        level = Level::Balanced;
        notes.push("battery-powered device: capped at balanced".into());
    }
    if m.low_vram_mode && level > Level::Low {
        level = Level::Low;
        notes.push("low-VRAM mode: capped at low".into());
    }
    if matches!(m.gpu, GpuClass::Software) {
        notes.push("software or virtual rendering: animations off, no blur".into());
    }
    let (qt, factor, blur, transl, rain) = match level {
        Level::Minimal => ("software", 0.0, false, false, 1),
        Level::Low => ("opengl", 0.5, false, false, 1),
        Level::Balanced => ("opengl", 1.0, false, true, 2),
        Level::High => ("vulkan", 1.0, true, true, 2),
        Level::Ultra => ("vulkan", 1.0, true, true, 3),
    };
    // software rendering must not ask Qt Quick for a GPU API
    let qt = if m.gpu == GpuClass::Software {
        "software"
    } else {
        qt
    };
    Profile {
        level,
        qt_quick: qt.into(),
        animation_factor: factor,
        blur,
        translucency: transl,
        rain_density: rain,
        notes,
    }
}

/// Stable hash of the hardware facts, so the profile is re-applied when the machine changes.
pub fn fingerprint(m: &Machine) -> String {
    use sha2::{Digest, Sha256};
    let s = format!(
        "{:?}|{:?}|{}|{}|{:?}|{}",
        m.gpu,
        m.driver,
        m.ram_total_mib / 512,
        m.cpu_threads,
        m.pixels,
        m.on_battery_device
    );
    Sha256::digest(s.as_bytes())
        .iter()
        .take(8)
        .map(|b| format!("{b:02x}"))
        .collect()
}

fn kw(file: &str, group: &str, key: &str, value: &str) -> Vec<String> {
    [
        "kwriteconfig6",
        "--file",
        file,
        "--group",
        group,
        "--key",
        key,
        value,
    ]
    .iter()
    .map(|s| s.to_string())
    .collect()
}

/// The exact commands that apply a profile (fixed programs, no shell).
pub fn commands(p: &Profile) -> Vec<Vec<String>> {
    let script = format!(
        "desktops().forEach(function(d){{ if (d.wallpaperPlugin == 'org.hcs.hscl1.rain') {{ d.currentConfigGroup = ['Wallpaper','org.hcs.hscl1.rain','General']; d.writeConfig('Density', {}); }} }});",
        p.rain_density
    );
    vec![
        kw(
            "kdeglobals",
            "KDE",
            "AnimationDurationFactor",
            &format!("{}", p.animation_factor),
        ),
        kw("kwinrc", "Plugins", "blurEnabled", &p.blur.to_string()),
        kw(
            "kwinrc",
            "Plugins",
            "translucencyEnabled",
            &p.translucency.to_string(),
        ),
        vec![
            "qdbus6".into(),
            "org.kde.plasmashell".into(),
            "/PlasmaShell".into(),
            "org.kde.PlasmaShell.evaluateScript".into(),
            script,
        ],
        vec![
            "qdbus6".into(),
            "org.kde.KWin".into(),
            "/KWin".into(),
            "reconfigure".into(),
        ],
    ]
}

/// Qt Quick environment for the session (`environment.d` format).
pub fn environment_file(p: &Profile) -> String {
    match p.qt_quick.as_str() {
        "software" => "QT_QUICK_BACKEND=software\n".into(),
        "opengl" => "QSG_RHI_BACKEND=opengl\n".into(),
        other => format!("QSG_RHI_BACKEND={other}\n"),
    }
}

#[derive(Serialize, serde::Deserialize, Default)]
pub struct State {
    pub fingerprint: String,
    pub level: String,
    /// User override: when set, autotune never changes the level.
    pub locked: bool,
}

pub fn load_state(cfg: &Path) -> State {
    std::fs::read_to_string(cfg.join("graphics.json"))
        .ok()
        .and_then(|t| serde_json::from_str(&t).ok())
        .unwrap_or_default()
}

/// Apply a profile unless the user locked it or nothing changed (`force` re-applies). Returns true when something ran.
pub fn apply(m: &Machine, cfg: &Path, runner: &mut dyn Runner, force: bool) -> Result<bool> {
    let st = load_state(cfg);
    let fp = fingerprint(m);
    if st.locked || (!force && st.fingerprint == fp) {
        return Ok(false);
    }
    let p = profile(m);
    std::fs::create_dir_all(cfg)?;
    for argv in commands(&p) {
        // a missing desktop session (e.g. over SSH) must not abort the whole tune: only the first failing step is reported
        runner.run(&argv)?;
    }
    std::fs::write(
        cfg.join("graphics.json"),
        serde_json::to_string_pretty(&State {
            fingerprint: fp,
            level: p.level.name().into(),
            locked: false,
        })?,
    )?;
    Ok(true)
}

#[cfg(test)]
mod tests {
    use super::*;

    fn m(gpu: GpuClass, ram: u64, threads: u32) -> Machine {
        Machine {
            gpu,
            driver: Some("x".into()),
            ram_total_mib: ram,
            cpu_threads: threads,
            pixels: Some(1920 * 1080),
            on_battery_device: false,
            low_vram_mode: false,
        }
    }

    #[test]
    fn classification_of_drivers() {
        assert_eq!(classify(None, false, false), GpuClass::None);
        assert_eq!(classify(Some("bochs-drm"), true, false), GpuClass::Software);
        assert_eq!(
            classify(Some("virtio_gpu"), true, false),
            GpuClass::Software
        );
        assert_eq!(
            classify(Some("amdgpu"), false, false),
            GpuClass::Software,
            "no render node: no acceleration"
        );
        assert_eq!(classify(Some("amdgpu"), true, false), GpuClass::Integrated);
        assert_eq!(classify(Some("nvidia"), true, true), GpuClass::Discrete);
    }

    #[test]
    fn software_rendering_always_gets_minimal_without_animation_or_blur() {
        for ram in [2_000, 8_000, 64_000] {
            let p = profile(&m(GpuClass::Software, ram, 32));
            assert_eq!(p.level, Level::Minimal);
            assert_eq!(p.animation_factor, 0.0);
            assert!(!p.blur && !p.translucency);
            assert_eq!(p.qt_quick, "software");
        }
    }

    #[test]
    fn integrated_scales_with_ram() {
        assert_eq!(
            profile(&m(GpuClass::Integrated, 4_000, 8)).level,
            Level::Low
        );
        assert_eq!(
            profile(&m(GpuClass::Integrated, 16_000, 16)).level,
            Level::Balanced
        );
        assert!(
            !profile(&m(GpuClass::Integrated, 16_000, 16)).blur,
            "no blur on integrated GPUs by default"
        );
    }

    #[test]
    fn discrete_is_high_and_ultra_needs_ram_and_threads() {
        assert_eq!(profile(&m(GpuClass::Discrete, 8_000, 8)).level, Level::High);
        assert_eq!(
            profile(&m(GpuClass::Discrete, 32_000, 16)).level,
            Level::Ultra
        );
        assert_eq!(
            profile(&m(GpuClass::Discrete, 6_000, 4)).level,
            Level::Balanced
        );
    }

    #[test]
    fn battery_low_vram_and_8k_caps() {
        let mut x = m(GpuClass::Discrete, 32_000, 16);
        x.on_battery_device = true;
        assert_eq!(profile(&x).level, Level::Balanced);
        let mut y = m(GpuClass::Discrete, 32_000, 16);
        y.low_vram_mode = true;
        assert_eq!(profile(&y).level, Level::Low);
        let mut z = m(GpuClass::Integrated, 32_000, 16);
        z.pixels = Some(7680 * 4320);
        assert_eq!(profile(&z).level, Level::Low);
    }

    #[test]
    fn commands_are_fixed_programs_without_shell_text() {
        let cmds = commands(&profile(&m(GpuClass::Integrated, 16_000, 16)));
        assert!(cmds
            .iter()
            .all(|c| matches!(c[0].as_str(), "kwriteconfig6" | "qdbus6")));
        assert!(cmds
            .iter()
            .flatten()
            .all(|a| !a.contains("&&") && !a.contains('|') && !a.contains('`')));
        assert!(cmds[0].contains(&"AnimationDurationFactor".to_string()));
    }

    #[test]
    fn environment_file_follows_the_backend() {
        assert_eq!(
            environment_file(&profile(&m(GpuClass::Software, 8_000, 8))),
            "QT_QUICK_BACKEND=software\n"
        );
        assert_eq!(
            environment_file(&profile(&m(GpuClass::Discrete, 16_000, 8))),
            "QSG_RHI_BACKEND=vulkan\n"
        );
    }

    #[derive(Default)]
    struct Rec(Vec<Vec<String>>);
    impl Runner for Rec {
        fn run(&mut self, a: &[String]) -> Result<()> {
            self.0.push(a.to_vec());
            Ok(())
        }
    }

    #[test]
    fn apply_runs_once_per_hardware_and_respects_the_lock() {
        let dir = tempfile::tempdir().unwrap();
        let machine = m(GpuClass::Integrated, 16_000, 16);
        let mut r = Rec::default();
        assert!(apply(&machine, dir.path(), &mut r, false).unwrap());
        let n = r.0.len();
        assert!(
            !apply(&machine, dir.path(), &mut r, false).unwrap(),
            "unchanged hardware: nothing to do"
        );
        assert_eq!(r.0.len(), n);
        let other = m(GpuClass::Discrete, 32_000, 16);
        assert!(
            apply(&other, dir.path(), &mut r, false).unwrap(),
            "hardware changed: re-tuned"
        );
        std::fs::write(
            dir.path().join("graphics.json"),
            r#"{"fingerprint":"","level":"low","locked":true}"#,
        )
        .unwrap();
        assert!(
            !apply(&machine, dir.path(), &mut r, true).unwrap(),
            "a user lock beats even force"
        );
    }

    #[test]
    fn fingerprint_changes_with_the_machine() {
        assert_ne!(
            fingerprint(&m(GpuClass::Integrated, 16_000, 16)),
            fingerprint(&m(GpuClass::Discrete, 16_000, 16))
        );
        assert_eq!(
            fingerprint(&m(GpuClass::Integrated, 16_000, 16)),
            fingerprint(&m(GpuClass::Integrated, 16_100, 16)),
            "tiny RAM differences do not retune"
        );
    }
}
