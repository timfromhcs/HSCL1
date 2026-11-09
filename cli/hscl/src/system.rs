//! System operations, services inventory, and power management (AGENTS.md section 8.2 & rule 0.3.7).
//!
//! Privileged actions use systemd/logind APIs and refuse shell execution.
//! Dry-run allows previewing power commands safely without disrupting active sessions.

use anyhow::{bail, Result};
use serde::{Deserialize, Serialize};
use std::process::Command;

/// Service status representation.
#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Eq)]
pub struct ServiceInfo {
    pub name: String,
    pub state: String,
    pub enabled: bool,
}

/// Power action execution plan.
#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Eq)]
pub struct PowerPlan {
    pub action: String,
    pub command: Vec<String>,
    pub dry_run: bool,
    pub message: String,
}

/// Parse lines from `systemctl list-unit-files --type=service`.
pub fn parse_systemd_services(text: &str, enabled_only: bool) -> Vec<ServiceInfo> {
    let mut list = Vec::new();
    for line in text.lines() {
        let trimmed = line.trim();
        if trimmed.is_empty() || trimmed.starts_with('#') {
            continue;
        }
        let parts: Vec<&str> = trimmed.split_whitespace().collect();
        if parts.is_empty() {
            continue;
        }
        let name = parts[0].to_string();
        if !name.ends_with(".service") {
            continue;
        }
        let state = parts.get(1).copied().unwrap_or("unknown").to_string();
        let enabled = state == "enabled" || state == "enabled-runtime";

        if enabled_only && !enabled {
            continue;
        }

        list.push(ServiceInfo {
            name,
            state,
            enabled,
        });
    }
    list
}

/// List systemd services, optionally filtering to enabled services.
pub fn list_services(enabled_only: bool) -> Vec<ServiceInfo> {
    if let Ok(out) = Command::new("systemctl")
        .args([
            "list-unit-files",
            "--type=service",
            "--no-pager",
            "--no-legend",
        ])
        .output()
    {
        if out.status.success() {
            let text = String::from_utf8_lossy(&out.stdout);
            return parse_systemd_services(&text, enabled_only);
        }
    }
    Vec::new()
}

/// Plan a power action (reboot, shutdown, lock).
pub fn plan_power(action: &str, dry_run: bool) -> Result<PowerPlan> {
    let (cmd, msg_action) = match action {
        "reboot" => (
            vec!["systemctl".to_string(), "reboot".to_string()],
            "reboot",
        ),
        "shutdown" | "poweroff" => (
            vec!["systemctl".to_string(), "poweroff".to_string()],
            "system shutdown",
        ),
        "lock" => (
            vec!["loginctl".to_string(), "lock-session".to_string()],
            "session lock",
        ),
        other => bail!("unsupported power action '{other}'; valid actions: reboot, shutdown, lock"),
    };

    let message = if dry_run {
        format!(
            "Dry run: planned {} with command: {}",
            msg_action,
            cmd.join(" ")
        )
    } else {
        format!("Executing {} via: {}", msg_action, cmd.join(" "))
    };

    Ok(PowerPlan {
        action: action.to_string(),
        command: cmd,
        dry_run,
        message,
    })
}

/// Execute a prepared power plan.
pub fn execute_power(plan: &PowerPlan) -> Result<()> {
    if plan.dry_run {
        return Ok(());
    }
    if plan.command.is_empty() {
        bail!("empty command in power plan");
    }
    let mut cmd = Command::new(&plan.command[0]);
    if plan.command.len() > 1 {
        cmd.args(&plan.command[1..]);
    }
    let status = cmd.status()?;
    if !status.success() {
        bail!("power command failed with exit code: {:?}", status.code());
    }
    Ok(())
}

#[cfg(test)]
pub mod tests {
    use super::*;

    #[test]
    fn test_parse_systemd_services_all_and_enabled() {
        let sample = r#"
apparmor.service                           enabled         enabled
cups.service                               disabled        enabled
earlyoom.service                           enabled         enabled
sddm.service                               enabled         enabled
ufw.service                                enabled         enabled
snapd.service                              masked          disabled
"#;
        let all = parse_systemd_services(sample, false);
        assert_eq!(all.len(), 6);
        assert_eq!(all[0].name, "apparmor.service");
        assert_eq!(all[0].state, "enabled");
        assert!(all[0].enabled);

        let enabled = parse_systemd_services(sample, true);
        assert_eq!(enabled.len(), 4);
        assert!(enabled.iter().all(|s| s.enabled));
        assert!(enabled.iter().any(|s| s.name == "sddm.service"));
        assert!(!enabled.iter().any(|s| s.name == "cups.service"));
    }

    #[test]
    fn test_plan_power_actions() {
        let reboot = plan_power("reboot", true).unwrap();
        assert_eq!(reboot.command, vec!["systemctl", "reboot"]);
        assert!(reboot.dry_run);
        assert!(reboot.message.contains("Dry run"));

        let shutdown = plan_power("shutdown", false).unwrap();
        assert_eq!(shutdown.command, vec!["systemctl", "poweroff"]);
        assert!(!shutdown.dry_run);

        let lock = plan_power("lock", true).unwrap();
        assert_eq!(lock.command, vec!["loginctl", "lock-session"]);

        let err = plan_power("hibernate_unsupported", true).unwrap_err();
        assert!(err.to_string().contains("unsupported power action"));
    }
}
