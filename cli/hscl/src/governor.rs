//! Wallpaper / GPU-pressure governor decision logic (plan P31.2 + P31.3).
//!
//! Why a governor at all: the animated wallpaper renders inside the Plasma shell all day, and on a
//! shared-memory iGPU every megabyte it holds is a megabyte the CPU side cannot use. The desktop
//! has no adaptive animation quality of its own, and PowerDevil can only switch effects off on
//! battery. So HSCL1 decides in one small, testable place:
//!
//! * nothing runs while a window covers the desktop, the session is locked/idle or the machine is
//!   on battery (the user asked for "less VRAM, less power, same look"),
//! * the animation drops to a cheaper scale when the GPU is busy,
//! * a resident local model wins over the wallpaper: the still frame is used while it is loaded
//!   (the owner's "low-VRAM switch"),
//! * every decision is a named reason, so the service can log *why* and the Control Center can show
//!   it, and a steady state produces no transition at all (no log spam, no repaint churn).
//!
//! This module is pure: it takes a [`Sample`] that the service harvested from sysfs/procfs and
//! returns the next state. Nothing here touches the filesystem or a display, which is what makes it
//! unit-testable on a machine without HSCL1. The sysfs reader for the memory/busy numbers lives at
//! the bottom (`read_gpu`) and is fixture-tested; desktop/lock/battery/model state is supplied by
//! the caller (KWin, logind, UPower, the AI server) because each needs a different source.

// The governor service (plan P31.3, sprint S5) calls `decide`/`read_gpu`; until that service is
// packaged the module is exercised only by its tests, so keep the dead-code lint quiet here
// instead of shipping an unused command that would have to guess half of its inputs.
#![allow(dead_code)]

use std::path::Path;

/// One observation. Everything is optional because a machine may lack an amdgpu sysfs node, a
/// battery or a GPU at all - "unknown" must never be read as "fine" or as "in trouble".
#[derive(Debug, Clone, Copy, Default, PartialEq, Eq)]
pub struct Sample {
    pub vram_used_mib: Option<u64>,
    pub vram_total_mib: Option<u64>,
    pub gtt_used_mib: Option<u64>,
    pub gtt_total_mib: Option<u64>,
    /// `/sys/class/drm/card*/device/gpu_busy_percent`, 0..=100.
    pub gpu_busy_pct: Option<u8>,
    /// True when every window is maximised or fullscreen (the wallpaper is not visible).
    pub desktop_covered: bool,
    /// True when the session is locked or the display is idle.
    pub locked_or_idle: bool,
    pub on_battery: bool,
    /// True while `hscl ai` has a model resident on this machine.
    pub ai_model_resident: bool,
}

impl Sample {
    /// Smallest free headroom across the memory pools we can read, in MiB.
    ///
    /// VRAM and GTT are separate pools: on an APU almost everything lives in GTT, on a discrete GPU
    /// in VRAM. Taking the minimum means a full pool blocks the animation even if the other one is
    /// empty, and an unknown pool simply does not vote.
    pub fn free_mib(&self) -> Option<u64> {
        let pools = [
            (self.vram_used_mib, self.vram_total_mib),
            (self.gtt_used_mib, self.gtt_total_mib),
        ];
        pools
            .iter()
            .filter_map(|(used, total)| match (used, total) {
                (Some(u), Some(t)) if t > u => Some(t - u),
                (Some(_), Some(_)) => Some(0),
                _ => None,
            })
            .min()
    }
}

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum Wallpaper {
    /// Animated, with the frame rate and the render scale the governor allows.
    Animating {
        fps: u8,
        scale_pct: u8,
    },
    Still,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum Reason {
    UserDisabled,
    LockedOrIdle,
    DesktopCovered,
    LowMemory,
    AiModelResident,
    GpuBusy,
    OnBattery,
    Normal,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub struct Config {
    /// Master switch. `false` keeps the animation at full quality; the governor then only reports.
    pub enabled: bool,
    /// Requested frame rate; never applied above [`MAX_FPS`].
    pub anim_fps: u8,
    /// Render scale used when the GPU is busy or the machine is on battery.
    pub reduced_scale_pct: u8,
    /// Free-memory floor in MiB below which the still frame takes over.
    pub memory_margin_mib: u64,
    /// GPU busy percentage at which the reduced profile starts.
    pub busy_enter_pct: u8,
    /// Busy percentage below which the reduced profile ends (hysteresis, must be <= enter).
    pub busy_exit_pct: u8,
}

/// Hard cap from the plan: a wallpaper above 30 fps buys nothing visible on a desktop and costs
/// power all day.
pub const MAX_FPS: u8 = 30;

impl Default for Config {
    fn default() -> Self {
        Self {
            enabled: true,
            anim_fps: 30,
            reduced_scale_pct: 50,
            memory_margin_mib: 512,
            busy_enter_pct: 80,
            busy_exit_pct: 70,
        }
    }
}

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub struct State {
    pub wallpaper: Wallpaper,
    pub reason: Reason,
}

impl Default for State {
    fn default() -> Self {
        Self {
            wallpaper: Wallpaper::Animating {
                fps: MAX_FPS,
                scale_pct: 100,
            },
            reason: Reason::Normal,
        }
    }
}

/// A state change worth logging. A steady state returns `None` from [`decide`].
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub struct Transition {
    pub from: Wallpaper,
    pub to: Wallpaper,
    pub reason: Reason,
    pub free_mib: Option<u64>,
}

/// The whole governor: pure function of (config, sample, previous state).
pub fn decide(cfg: &Config, s: &Sample, prev: &State) -> (State, Option<Transition>) {
    let fps = cfg.anim_fps.min(MAX_FPS);
    let full = Wallpaper::Animating {
        fps,
        scale_pct: 100,
    };
    let reduced = Wallpaper::Animating {
        fps,
        scale_pct: cfg.reduced_scale_pct.clamp(10, 100),
    };
    let free_mib = s.free_mib();

    let (next, reason) = if !cfg.enabled {
        (full, Reason::UserDisabled)
    } else if s.locked_or_idle {
        (Wallpaper::Still, Reason::LockedOrIdle)
    } else if s.desktop_covered {
        (Wallpaper::Still, Reason::DesktopCovered)
    } else if free_mib.is_some_and(|free| free < cfg.memory_margin_mib) {
        (Wallpaper::Still, Reason::LowMemory)
    } else if s.ai_model_resident {
        (Wallpaper::Still, Reason::AiModelResident)
    } else if busy_calls_for_reduced(cfg, s, prev) {
        (reduced, Reason::GpuBusy)
    } else if s.on_battery {
        (reduced, Reason::OnBattery)
    } else {
        (full, Reason::Normal)
    };

    let next = State {
        wallpaper: next,
        reason,
    };
    if next.wallpaper == prev.wallpaper {
        // Same look, possibly a new reason (covered -> locked). Keep the newest reason without
        // logging a transition: only a visible change is worth a line.
        return (next, None);
    }
    let t = Transition {
        from: prev.wallpaper,
        to: next.wallpaper,
        reason,
        free_mib,
    };
    (next, Some(t))
}

/// Busy threshold with hysteresis: the reduced profile starts at `busy_enter_pct` and only ends
/// below `busy_exit_pct`, so a value hovering at the threshold does not flip the wallpaper every
/// second.
fn busy_calls_for_reduced(cfg: &Config, s: &Sample, prev: &State) -> bool {
    let Some(busy) = s.gpu_busy_pct else {
        return false;
    };
    let already_reduced = match prev.wallpaper {
        Wallpaper::Animating { scale_pct, .. } => scale_pct < 100,
        Wallpaper::Still => false,
    };
    let exit = cfg.busy_exit_pct.min(cfg.busy_enter_pct);
    if already_reduced {
        busy >= exit
    } else {
        busy >= cfg.busy_enter_pct
    }
}

/// Memory and GPU-busy numbers from the kernel's amdgpu (or any driver that exports the same files)
/// sysfs nodes. Missing files are `None`, never an error: a machine without them simply has no
/// memory input for the governor.
pub fn read_gpu(root: &Path) -> Sample {
    let mut sample = Sample::default();
    let drm = root.join("sys/class/drm");
    let Ok(entries) = std::fs::read_dir(&drm) else {
        return sample;
    };
    let mut cards: Vec<std::path::PathBuf> = entries
        .flatten()
        .map(|e| e.path())
        .filter(|p| {
            p.file_name()
                .and_then(|n| n.to_str())
                .is_some_and(|n| n.starts_with("card") && !n.contains('-'))
        })
        .collect();
    cards.sort();
    for card in cards {
        let dev = card.join("device");
        sample.vram_used_mib = sample
            .vram_used_mib
            .or_else(|| mib(&dev.join("mem_info_vram_used")));
        sample.vram_total_mib = sample
            .vram_total_mib
            .or_else(|| mib(&dev.join("mem_info_vram_total")));
        sample.gtt_used_mib = sample
            .gtt_used_mib
            .or_else(|| mib(&dev.join("mem_info_gtt_used")));
        sample.gtt_total_mib = sample
            .gtt_total_mib
            .or_else(|| mib(&dev.join("mem_info_gtt_total")));
        if sample.gpu_busy_pct.is_none() {
            sample.gpu_busy_pct = read_u64(&dev.join("gpu_busy_percent")).map(|v| v.min(100) as u8);
        }
    }
    sample
}

fn read_u64(path: &Path) -> Option<u64> {
    let text = std::fs::read_to_string(path).ok()?;
    text.trim().parse::<u64>().ok()
}

fn mib(path: &Path) -> Option<u64> {
    read_u64(path).map(|bytes| bytes / 1_048_576)
}

#[cfg(test)]
mod tests {
    use super::*;

    fn cfg() -> Config {
        Config::default()
    }

    fn sample() -> Sample {
        Sample {
            vram_used_mib: Some(200),
            vram_total_mib: Some(4096),
            gtt_used_mib: Some(300),
            gtt_total_mib: Some(8000),
            gpu_busy_pct: Some(5),
            ..Sample::default()
        }
    }

    fn full() -> Wallpaper {
        Wallpaper::Animating {
            fps: 30,
            scale_pct: 100,
        }
    }

    fn reduced() -> Wallpaper {
        Wallpaper::Animating {
            fps: 30,
            scale_pct: 50,
        }
    }

    #[test]
    fn a_normal_machine_animates_at_full_quality_with_no_transition_from_the_same_state() {
        let s = sample();
        let prev = State {
            wallpaper: full(),
            reason: Reason::Normal,
        };
        let (next, t) = decide(&cfg(), &s, &prev);
        assert_eq!(next.wallpaper, full());
        assert_eq!(next.reason, Reason::Normal);
        assert_eq!(t, None);
    }

    #[test]
    fn a_covered_desktop_stops_the_animation_and_says_why() {
        let s = Sample {
            desktop_covered: true,
            ..sample()
        };
        let (next, t) = decide(&cfg(), &s, &State::default());
        assert_eq!(next.wallpaper, Wallpaper::Still);
        assert_eq!(next.reason, Reason::DesktopCovered);
        let t = t.expect("a visible change must be reported");
        assert_eq!(t.from, full());
        assert_eq!(t.to, Wallpaper::Still);
    }

    #[test]
    fn a_locked_session_wins_over_a_covered_desktop() {
        let s = Sample {
            desktop_covered: true,
            locked_or_idle: true,
            ..sample()
        };
        let (next, _) = decide(&cfg(), &s, &State::default());
        assert_eq!(next.reason, Reason::LockedOrIdle);
    }

    #[test]
    fn low_free_memory_stops_the_animation_and_records_the_headroom() {
        let s = Sample {
            gtt_used_mib: Some(7900),
            gtt_total_mib: Some(8000),
            ..sample()
        };
        let (next, t) = decide(&cfg(), &s, &State::default());
        assert_eq!(next.reason, Reason::LowMemory);
        assert_eq!(t.unwrap().free_mib, Some(100));
    }

    #[test]
    fn an_unknown_memory_pool_never_triggers_low_memory() {
        let s = Sample {
            vram_used_mib: None,
            vram_total_mib: None,
            gtt_used_mib: None,
            gtt_total_mib: None,
            ..Sample::default()
        };
        let (next, _) = decide(&cfg(), &s, &State::default());
        assert_eq!(next.wallpaper, full());
        assert_eq!(next.reason, Reason::Normal);
    }

    #[test]
    fn a_resident_model_gives_the_memory_back_to_the_model() {
        let s = Sample {
            ai_model_resident: true,
            ..sample()
        };
        let (next, _) = decide(&cfg(), &s, &State::default());
        assert_eq!(next.wallpaper, Wallpaper::Still);
        assert_eq!(next.reason, Reason::AiModelResident);
    }

    #[test]
    fn low_memory_outranks_a_resident_model() {
        let s = Sample {
            ai_model_resident: true,
            gtt_used_mib: Some(7990),
            ..sample()
        };
        let (next, _) = decide(&cfg(), &s, &State::default());
        assert_eq!(next.reason, Reason::LowMemory);
    }

    #[test]
    fn a_busy_gpu_reduces_the_scale_and_hysteresis_keeps_it_there() {
        let c = cfg();
        let busy = Sample {
            gpu_busy_pct: Some(85),
            ..sample()
        };
        let (next, _) = decide(&c, &busy, &State::default());
        assert_eq!(next.wallpaper, reduced());
        assert_eq!(next.reason, Reason::GpuBusy);

        // 75 is below the enter threshold but above the exit threshold: stay reduced.
        let hovering = Sample {
            gpu_busy_pct: Some(75),
            ..sample()
        };
        let (stays, t) = decide(&c, &hovering, &next);
        assert_eq!(stays.wallpaper, reduced());
        assert_eq!(t, None, "a hovering value must not repaint the desktop");

        // Below 70 the full animation comes back.
        let calm = Sample {
            gpu_busy_pct: Some(69),
            ..sample()
        };
        let (back, t) = decide(&c, &calm, &stays);
        assert_eq!(back.wallpaper, full());
        assert_eq!(t.unwrap().reason, Reason::Normal);
    }

    #[test]
    fn a_battery_reduces_the_scale_but_never_below_the_hard_cap() {
        let s = Sample {
            on_battery: true,
            ..sample()
        };
        let mut c = cfg();
        c.anim_fps = 120;
        let (next, _) = decide(&c, &s, &State::default());
        assert_eq!(
            next.wallpaper,
            Wallpaper::Animating {
                fps: MAX_FPS,
                scale_pct: 50
            }
        );
        assert_eq!(next.reason, Reason::OnBattery);
    }

    #[test]
    fn the_master_switch_keeps_full_quality_even_when_covered() {
        let mut c = cfg();
        c.enabled = false;
        let s = Sample {
            desktop_covered: true,
            on_battery: true,
            ..sample()
        };
        let (next, _) = decide(&c, &s, &State::default());
        assert_eq!(next.wallpaper, full());
        assert_eq!(next.reason, Reason::UserDisabled);
    }

    #[test]
    fn a_configured_scale_of_zero_is_clamped_to_something_renderable() {
        let mut c = cfg();
        c.reduced_scale_pct = 0;
        let s = Sample {
            on_battery: true,
            ..sample()
        };
        let (next, _) = decide(&c, &s, &State::default());
        assert_eq!(
            next.wallpaper,
            Wallpaper::Animating {
                fps: 30,
                scale_pct: 10
            }
        );
    }

    fn write(path: &Path, text: &str) {
        std::fs::create_dir_all(path.parent().unwrap()).unwrap();
        std::fs::write(path, text).unwrap();
    }

    #[test]
    fn the_sysfs_reader_takes_memory_and_busy_percent_from_the_first_card() {
        let dir = tempfile::tempdir().unwrap();
        let root = dir.path();
        let dev = root.join("sys/class/drm/card1/device");
        write(&dev.join("mem_info_vram_used"), "209715200\n");
        write(&dev.join("mem_info_vram_total"), "536870912\n");
        write(&dev.join("mem_info_gtt_used"), "1073741824\n");
        write(&dev.join("mem_info_gtt_total"), "8589934592\n");
        write(&dev.join("gpu_busy_percent"), "37\n");
        // A connector directory (`card1-DP-1`) must not be mistaken for a card.
        write(&root.join("sys/class/drm/card1-DP-1/status"), "connected\n");
        let s = read_gpu(root);
        assert_eq!(s.vram_used_mib, Some(200));
        assert_eq!(s.vram_total_mib, Some(512));
        assert_eq!(s.gtt_used_mib, Some(1024));
        assert_eq!(s.gtt_total_mib, Some(8192));
        assert_eq!(s.gpu_busy_pct, Some(37));
        assert_eq!(s.free_mib(), Some(312));
    }

    #[test]
    fn the_sysfs_reader_is_quiet_when_there_is_nothing_to_read() {
        let dir = tempfile::tempdir().unwrap();
        let s = read_gpu(dir.path());
        assert_eq!(s, Sample::default());
        assert_eq!(s.free_mib(), None);
    }

    #[test]
    fn a_nonsense_busy_value_is_clamped_instead_of_wrapping() {
        let dir = tempfile::tempdir().unwrap();
        write(
            &dir.path()
                .join("sys/class/drm/card0/device/gpu_busy_percent"),
            "250\n",
        );
        assert_eq!(read_gpu(dir.path()).gpu_busy_pct, Some(100));
    }
}
