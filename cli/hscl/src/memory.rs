//! `hscl memory` - memory status and the AI RAM budget.
//!
//! The AI budget is a percentage of total RAM that local AI may use (default 60 %); `ai profile`/`ai model` use
//! min(available, budget) instead of raw available memory, so a model is never planned into the desktop's share.

use crate::profile::Hw;
use anyhow::{bail, Result};
use serde::Serialize;
use std::path::Path;

pub const DEFAULT_PERCENT: u8 = 60;

#[derive(Debug, Serialize, PartialEq, Eq)]
pub struct MemStatus {
    pub total_mib: u64,
    pub available_mib: u64,
    pub swap_total_mib: u64,
    pub swap_free_mib: u64,
    pub zram_devices: Vec<String>,
    pub ai_budget_percent: u8,
    pub ai_budget_mib: u64,
}

fn field(text: &str, key: &str) -> u64 {
    text.lines()
        .find(|l| l.starts_with(key))
        .and_then(|l| l.split_whitespace().nth(1))
        .and_then(|v| v.parse::<u64>().ok())
        .map(|kb| kb / 1024)
        .unwrap_or(0)
}

/// (total, available, swap total, swap free) in MiB from /proc/meminfo text.
pub fn parse_meminfo(text: &str) -> (u64, u64, u64, u64) {
    (
        field(text, "MemTotal:"),
        field(text, "MemAvailable:"),
        field(text, "SwapTotal:"),
        field(text, "SwapFree:"),
    )
}

pub fn budget_mib(total_mib: u64, percent: u8) -> u64 {
    total_mib * percent.clamp(10, 90) as u64 / 100
}

/// Limit what the AI planner may count on.
pub fn cap_hw(hw: &mut Hw, percent: u8) {
    hw.ram_available_mib = hw
        .ram_available_mib
        .min(budget_mib(hw.ram_total_mib, percent));
}

pub fn read_percent(cfg: &Path) -> u8 {
    std::fs::read_to_string(cfg.join("ai-ram-percent"))
        .ok()
        .and_then(|t| t.trim().parse::<u8>().ok())
        .filter(|p| (10..=90).contains(p))
        .unwrap_or(DEFAULT_PERCENT)
}

pub fn write_percent(cfg: &Path, percent: u8) -> Result<()> {
    if !(10..=90).contains(&percent) {
        bail!("the AI RAM budget must be between 10 and 90 percent");
    }
    std::fs::create_dir_all(cfg)?;
    std::fs::write(cfg.join("ai-ram-percent"), format!("{percent}\n"))?;
    Ok(())
}

pub fn zram_devices() -> Vec<String> {
    let mut v: Vec<String> = std::fs::read_dir("/sys/block")
        .map(|r| {
            r.flatten()
                .map(|e| e.file_name().to_string_lossy().into_owned())
                .filter(|n| n.starts_with("zram"))
                .collect()
        })
        .unwrap_or_default();
    v.sort();
    v
}

pub fn status(cfg: &Path) -> MemStatus {
    let (t, a, st, sf) =
        parse_meminfo(&std::fs::read_to_string("/proc/meminfo").unwrap_or_default());
    let pct = read_percent(cfg);
    MemStatus {
        total_mib: t,
        available_mib: a,
        swap_total_mib: st,
        swap_free_mib: sf,
        zram_devices: zram_devices(),
        ai_budget_percent: pct,
        ai_budget_mib: budget_mib(t, pct),
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    const INFO: &str = "MemTotal:       16384000 kB\nMemFree:         1000000 kB\nMemAvailable:   12288000 kB\nSwapTotal:       4194304 kB\nSwapFree:        4000000 kB\n";

    fn hw(total: u64, avail: u64) -> Hw {
        Hw {
            ram_total_mib: total,
            ram_available_mib: avail,
            cpu_threads: 8,
            gpu: None,
            vulkan: false,
            free_disk_mib: None,
        }
    }

    #[test]
    fn meminfo_parsing() {
        assert_eq!(parse_meminfo(INFO), (16000, 12000, 4096, 3906));
        assert_eq!(parse_meminfo(""), (0, 0, 0, 0));
    }

    #[test]
    fn budget_is_a_clamped_share_of_total() {
        assert_eq!(budget_mib(16000, 60), 9600);
        assert_eq!(
            budget_mib(16000, 5),
            1600,
            "below 10 percent is raised to 10"
        );
        assert_eq!(
            budget_mib(16000, 99),
            14400,
            "above 90 percent is lowered to 90"
        );
    }

    #[test]
    fn the_planner_never_counts_on_more_than_the_budget() {
        let mut h = hw(16000, 15000);
        cap_hw(&mut h, 60);
        assert_eq!(h.ram_available_mib, 9600);
        let mut busy = hw(16000, 2000);
        cap_hw(&mut busy, 60);
        assert_eq!(
            busy.ram_available_mib, 2000,
            "less memory than the budget stays as it is"
        );
    }

    #[test]
    fn percent_persists_and_rejects_bad_values() {
        let d = tempfile::tempdir().unwrap();
        assert_eq!(read_percent(d.path()), DEFAULT_PERCENT);
        write_percent(d.path(), 40).unwrap();
        assert_eq!(read_percent(d.path()), 40);
        assert!(write_percent(d.path(), 5).is_err() && write_percent(d.path(), 95).is_err());
        std::fs::write(d.path().join("ai-ram-percent"), "garbage").unwrap();
        assert_eq!(read_percent(d.path()), DEFAULT_PERCENT);
    }

    #[test]
    fn a_smaller_budget_changes_the_recommendation() {
        let models = crate::catalog::load().unwrap();
        let full = crate::profile::recommend(&hw(16000, 14000), &models, None);
        let mut capped = hw(16000, 14000);
        cap_hw(&mut capped, 30);
        let small = crate::profile::recommend(&capped, &models, None);
        assert!(
            small.len() < full.len(),
            "{} vs {}",
            small.len(),
            full.len()
        );
    }
}
