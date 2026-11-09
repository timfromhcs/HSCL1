//! System recovery posture, snapshot inspection/creation, and non-destructive configuration reset (AGENTS.md section 8.2 & 8.4).

use anyhow::{bail, Context, Result};
use serde::{Deserialize, Serialize};
use std::fs;
use std::path::Path;
use std::time::{SystemTime, UNIX_EPOCH};

#[derive(Serialize, Deserialize, Clone, Debug, PartialEq, Eq)]
pub struct RecoveryStatus {
    pub backup_dir: String,
    pub backup_dir_exists: bool,
    pub snapshots_found: usize,
    pub timeshift_detected: bool,
    pub snapper_detected: bool,
    pub readiness: String,
    pub notice: String,
}

#[derive(Serialize, Deserialize, Clone, Debug, PartialEq, Eq)]
pub struct SnapshotInfo {
    pub id: String,
    pub label: String,
    pub timestamp: u64,
    pub path: String,
    pub provider: String,
}

#[derive(Serialize, Deserialize, Clone, Debug, PartialEq, Eq)]
pub struct SnapshotCreatePlan {
    pub label: String,
    pub target_dir: String,
    pub timestamp: u64,
    pub dry_run: bool,
    pub executed: bool,
    pub message: String,
}

#[derive(Serialize, Deserialize, Clone, Debug, PartialEq, Eq)]
pub struct ConfigResetItem {
    pub target_path: String,
    pub default_source: String,
    pub backup_path: Option<String>,
    pub status: String,
}

#[derive(Serialize, Deserialize, Clone, Debug, PartialEq, Eq)]
pub struct ConfigResetPlan {
    pub component: String,
    pub dry_run: bool,
    pub executed: bool,
    pub items: Vec<ConfigResetItem>,
    pub message: String,
}

/// Validate snapshot label: alphanumeric, underscores, hyphens only, 1-32 chars.
pub fn validate_label(label: &str) -> Result<()> {
    if label.is_empty() {
        bail!("snapshot label cannot be empty");
    }
    if label.len() > 32 {
        bail!("snapshot label too long (max 32 characters)");
    }
    if !label
        .chars()
        .all(|c| c.is_ascii_alphanumeric() || c == '_' || c == '-')
    {
        bail!("snapshot label may only contain letters, numbers, hyphens, and underscores");
    }
    Ok(())
}

/// Inspect system recovery posture and backup provider readiness.
pub fn get_recovery_status(root_prefix: Option<&Path>) -> RecoveryStatus {
    let p_root = root_prefix.unwrap_or_else(|| Path::new("/"));
    let hscl_backup = p_root.join("var/backups/hscl");
    let timeshift_dir = p_root.join("timeshift/snapshots");
    let snapper_dir = p_root.join("var/lib/snapper/snapshots");

    let mut snapshots_found = 0;
    let backup_dir_exists = hscl_backup.is_dir();

    if backup_dir_exists {
        if let Ok(entries) = fs::read_dir(&hscl_backup) {
            snapshots_found += entries.flatten().filter(|e| e.path().is_dir()).count();
        }
    }

    let timeshift_detected = timeshift_dir.is_dir();
    if timeshift_detected {
        if let Ok(entries) = fs::read_dir(&timeshift_dir) {
            snapshots_found += entries.flatten().filter(|e| e.path().is_dir()).count();
        }
    }

    let snapper_detected = snapper_dir.is_dir();
    if snapper_detected {
        if let Ok(entries) = fs::read_dir(&snapper_dir) {
            snapshots_found += entries.flatten().filter(|e| e.path().is_dir()).count();
        }
    }

    let (readiness, notice) = if snapshots_found > 0 {
        (
            "ready".to_string(),
            format!("{snapshots_found} recovery snapshot(s) available across active providers."),
        )
    } else if backup_dir_exists {
        (
            "configured".to_string(),
            "Backup directory /var/backups/hscl exists, but no snapshots have been taken yet."
                .to_string(),
        )
    } else {
        (
            "not_configured".to_string(),
            "No recovery snapshots found. Recommended: run 'hscl recovery snapshots create <LABEL>' or configure Timeshift/Btrfs.".to_string(),
        )
    };

    RecoveryStatus {
        backup_dir: hscl_backup.display().to_string(),
        backup_dir_exists,
        snapshots_found,
        timeshift_detected,
        snapper_detected,
        readiness,
        notice,
    }
}

/// List all detected recovery snapshots sorted newest first.
pub fn list_snapshots(root_prefix: Option<&Path>) -> Vec<SnapshotInfo> {
    let p_root = root_prefix.unwrap_or_else(|| Path::new("/"));
    let mut list = Vec::new();

    // 1. HSCL snapshots
    let hscl_dir = p_root.join("var/backups/hscl");
    if let Ok(rd) = fs::read_dir(&hscl_dir) {
        for entry in rd.flatten() {
            let path = entry.path();
            if path.is_dir() {
                let name = entry.file_name().to_string_lossy().to_string();
                let (ts, label) = if let Some((ts_str, lbl)) = name.split_once('_') {
                    (ts_str.parse::<u64>().unwrap_or_default(), lbl.to_string())
                } else {
                    (0, name.clone())
                };
                list.push(SnapshotInfo {
                    id: name,
                    label,
                    timestamp: ts,
                    path: path.display().to_string(),
                    provider: "hscl".to_string(),
                });
            }
        }
    }

    // 2. Timeshift snapshots
    let ts_dir = p_root.join("timeshift/snapshots");
    if let Ok(rd) = fs::read_dir(&ts_dir) {
        for entry in rd.flatten() {
            let path = entry.path();
            if path.is_dir() {
                let name = entry.file_name().to_string_lossy().to_string();
                list.push(SnapshotInfo {
                    id: name.clone(),
                    label: name,
                    timestamp: 0,
                    path: path.display().to_string(),
                    provider: "timeshift".to_string(),
                });
            }
        }
    }

    list.sort_by_key(|a| std::cmp::Reverse(a.timestamp));
    list
}

/// Create a timestamped recovery point with system configuration manifest.
pub fn create_snapshot(
    label: &str,
    dry_run: bool,
    root_prefix: Option<&Path>,
) -> Result<SnapshotCreatePlan> {
    validate_label(label)?;
    let p_root = root_prefix.unwrap_or_else(|| Path::new("/"));
    let now = SystemTime::now()
        .duration_since(UNIX_EPOCH)
        .unwrap_or_default()
        .as_secs();

    let target_dirname = format!("{now}_{label}");
    let target_dir = p_root.join("var/backups/hscl").join(&target_dirname);

    if target_dir.exists() {
        bail!(
            "refusing to overwrite existing snapshot directory: {}",
            target_dir.display()
        );
    }

    if dry_run {
        return Ok(SnapshotCreatePlan {
            label: label.to_string(),
            target_dir: target_dir.display().to_string(),
            timestamp: now,
            dry_run: true,
            executed: false,
            message: format!(
                "[dry-run] Would create snapshot directory '{}' with system manifest",
                target_dir.display()
            ),
        });
    }

    fs::create_dir_all(&target_dir)
        .with_context(|| format!("failed to create snapshot dir: {}", target_dir.display()))?;

    let manifest = serde_json::json!({
        "timestamp": now,
        "label": label,
        "created_by": "hscl recovery",
        "version": env!("CARGO_PKG_VERSION"),
    });

    fs::write(
        target_dir.join("manifest.json"),
        serde_json::to_string_pretty(&manifest)?,
    )?;

    // Back up critical system configuration files if readable
    let configs = ["etc/fstab", "etc/crypttab", "etc/hostname"];
    for cfg in configs {
        let src = p_root.join(cfg);
        if src.is_file() {
            let dest_name = cfg.replace('/', "_");
            let _ = fs::copy(&src, target_dir.join(dest_name));
        }
    }

    Ok(SnapshotCreatePlan {
        label: label.to_string(),
        target_dir: target_dir.display().to_string(),
        timestamp: now,
        dry_run: false,
        executed: true,
        message: format!(
            "Snapshot '{label}' successfully created at {}",
            target_dir.display()
        ),
    })
}

/// Plan and execute non-destructive configuration reset with safety backup creation.
pub fn plan_config_reset(
    component: Option<&str>,
    dry_run: bool,
    home_dir: &Path,
    sys_dir: &Path,
) -> Result<ConfigResetPlan> {
    let comp = component.unwrap_or("shortcuts").to_lowercase();
    let now = SystemTime::now()
        .duration_since(UNIX_EPOCH)
        .unwrap_or_default()
        .as_secs();

    let mut items = Vec::new();
    let cfg_dir = home_dir.join(".config");

    match comp.as_str() {
        "shortcuts" => {
            let target = cfg_dir.join("kglobalshortcutsrc");
            let default_src = sys_dir.join("etc/xdg/kglobalshortcutsrc");
            let backup = if target.exists() {
                Some(format!("{}.bak.{now}", target.display()))
            } else {
                None
            };
            items.push(ConfigResetItem {
                target_path: target.display().to_string(),
                default_source: default_src.display().to_string(),
                backup_path: backup,
                status: if dry_run { "preview" } else { "pending" }.to_string(),
            });
        }
        "theme" => {
            let target = cfg_dir.join("plasma-localerc");
            let default_src = sys_dir.join("etc/xdg/plasma-localerc");
            let backup = if target.exists() {
                Some(format!("{}.bak.{now}", target.display()))
            } else {
                None
            };
            items.push(ConfigResetItem {
                target_path: target.display().to_string(),
                default_source: default_src.display().to_string(),
                backup_path: backup,
                status: if dry_run { "preview" } else { "pending" }.to_string(),
            });
        }
        "all" => {
            let sub_s = plan_config_reset(Some("shortcuts"), dry_run, home_dir, sys_dir)?;
            items.extend(sub_s.items);
            let sub_t = plan_config_reset(Some("theme"), dry_run, home_dir, sys_dir)?;
            items.extend(sub_t.items);
        }
        other => bail!("unknown component: '{other}'. Supported: shortcuts, theme, all"),
    }

    if dry_run {
        return Ok(ConfigResetPlan {
            component: comp,
            dry_run: true,
            executed: false,
            items,
            message: "[dry-run] Configuration reset preview generated (no changes made)"
                .to_string(),
        });
    }

    // Execute non-destructively: back up existing files before replacing
    fs::create_dir_all(&cfg_dir)?;
    for item in &mut items {
        let target_path = Path::new(&item.target_path);
        let default_source = Path::new(&item.default_source);

        if let Some(bak_str) = &item.backup_path {
            let bak_path = Path::new(bak_str);
            fs::copy(target_path, bak_path)
                .with_context(|| format!("failed to create backup {}", bak_str))?;
        }

        if default_source.exists() {
            fs::copy(default_source, target_path).with_context(|| {
                format!(
                    "failed to restore from default {}",
                    default_source.display()
                )
            })?;
            item.status = "restored_from_default".to_string();
        } else {
            fs::write(target_path, "# HSCL1 Default Configuration Restored\n")?;
            item.status = "restored_fallback_default".to_string();
        }
    }

    Ok(ConfigResetPlan {
        component: comp,
        dry_run: false,
        executed: true,
        items,
        message: "Configuration successfully reset to defaults with safety backups created"
            .to_string(),
    })
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_validate_label() {
        assert!(validate_label("pre_update_1").is_ok());
        assert!(validate_label("test-snap").is_ok());
        assert!(validate_label("").is_err());
        assert!(validate_label("bad label with spaces").is_err());
        assert!(validate_label("bad/traversal").is_err());
        assert!(validate_label(&"a".repeat(33)).is_err());
    }

    #[test]
    fn test_recovery_status_fixture() {
        let tmp = tempfile::tempdir().unwrap();
        let st1 = get_recovery_status(Some(tmp.path()));
        assert_eq!(st1.readiness, "not_configured");
        assert_eq!(st1.snapshots_found, 0);

        // Create backup directory
        let bdir = tmp.path().join("var/backups/hscl");
        fs::create_dir_all(&bdir).unwrap();
        let st2 = get_recovery_status(Some(tmp.path()));
        assert_eq!(st2.readiness, "configured");

        // Add a snapshot dir
        fs::create_dir_all(bdir.join("1700000000_init")).unwrap();
        let st3 = get_recovery_status(Some(tmp.path()));
        assert_eq!(st3.readiness, "ready");
        assert_eq!(st3.snapshots_found, 1);
    }

    #[test]
    fn test_list_snapshots_sorted() {
        let tmp = tempfile::tempdir().unwrap();
        let bdir = tmp.path().join("var/backups/hscl");
        fs::create_dir_all(bdir.join("100_first")).unwrap();
        fs::create_dir_all(bdir.join("200_second")).unwrap();

        let snaps = list_snapshots(Some(tmp.path()));
        assert_eq!(snaps.len(), 2);
        assert_eq!(snaps[0].label, "second");
        assert_eq!(snaps[1].label, "first");
    }

    #[test]
    fn test_create_snapshot_real_and_dry_run() {
        let tmp = tempfile::tempdir().unwrap();

        // Dry run
        let p_dry = create_snapshot("baseline", true, Some(tmp.path())).unwrap();
        assert!(p_dry.dry_run);
        assert!(!p_dry.executed);

        // Real run
        let p_real = create_snapshot("baseline", false, Some(tmp.path())).unwrap();
        assert!(!p_real.dry_run);
        assert!(p_real.executed);

        let snap_dir = Path::new(&p_real.target_dir);
        assert!(snap_dir.is_dir());
        assert!(snap_dir.join("manifest.json").is_file());

        // Re-creating the exact same snapshot in the same second fails with overwrite refusal
        let err = create_snapshot("baseline", false, Some(tmp.path()));
        assert!(err.is_err());
    }

    #[test]
    fn test_plan_config_reset_preserves_backup() {
        let tmp = tempfile::tempdir().unwrap();
        let home = tmp.path().join("home/user");
        let sys = tmp.path().join("sys");
        let cfg = home.join(".config");
        fs::create_dir_all(&cfg).unwrap();

        let shortcut_file = cfg.join("kglobalshortcutsrc");
        fs::write(&shortcut_file, "custom=shortcut\n").unwrap();

        // Default template
        let sys_xdg = sys.join("etc/xdg");
        fs::create_dir_all(&sys_xdg).unwrap();
        fs::write(sys_xdg.join("kglobalshortcutsrc"), "default=shortcut\n").unwrap();

        // Execute reset
        let plan = plan_config_reset(Some("shortcuts"), false, &home, &sys).unwrap();
        assert!(plan.executed);
        assert_eq!(plan.items.len(), 1);
        assert!(plan.items[0].backup_path.is_some());

        // Target has been reset to default
        let new_content = fs::read_to_string(&shortcut_file).unwrap();
        assert_eq!(new_content, "default=shortcut\n");

        // Backup file exists and has old content
        let bak = Path::new(plan.items[0].backup_path.as_ref().unwrap());
        assert!(bak.is_file());
        assert_eq!(fs::read_to_string(bak).unwrap(), "custom=shortcut\n");
    }
}
