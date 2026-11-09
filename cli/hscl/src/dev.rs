//! Developer environment inspection, setup bundles, Git hygiene, containers, and virtualization (AGENTS.md section 7.1, 7.2, and 8.2).
//!
//! All operations run unprivileged by default.
//! Package setup produces safe, inspectable argument vectors and refuses shell execution.

use anyhow::Result;
use serde::{Deserialize, Serialize};
use std::fs;
use std::path::Path;
use std::process::Command;

/// Tool category for developer environment classification.
#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Eq)]
#[serde(rename_all = "lowercase")]
pub enum ToolCategory {
    Compiler,
    Vcs,
    Language,
    Container,
    Virtualization,
    Monitor,
}

/// Information about a single probed developer tool.
#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Eq)]
pub struct ToolInfo {
    pub name: String,
    pub category: ToolCategory,
    pub present: bool,
    pub details: Option<String>,
}

/// Developer workstation readiness status.
#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Eq)]
pub struct DevStatus {
    pub readiness: String,
    pub compilers_ready: bool,
    pub git_ready: bool,
    pub python_ready: bool,
    pub rust_ready: bool,
    pub node_ready: bool,
    pub containers_ready: bool,
    pub virt_ready: bool,
    pub monitors_ready: bool,
    pub installed_tools: Vec<ToolInfo>,
    pub missing_recommended: Vec<String>,
}

/// Curated developer bundle definition.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct DevBundle {
    pub name: &'static str,
    pub summary: &'static str,
    pub packages: &'static [&'static str],
}

pub const BUNDLES: &[DevBundle] = &[
    DevBundle {
        name: "base",
        summary: "Core build tools, Git, SSH client, curl, and btop resource monitor",
        packages: &[
            "build-essential",
            "pkg-config",
            "git",
            "curl",
            "openssh-client",
            "btop",
        ],
    },
    DevBundle {
        name: "python",
        summary: "Python 3 environment, venv, and pipx package isolation",
        packages: &["python3", "python3-venv", "python3-pip", "pipx"],
    },
    DevBundle {
        name: "rust",
        summary: "Rust compiler and Cargo package manager from distribution archive",
        packages: &["rustc", "cargo"],
    },
    DevBundle {
        name: "containers",
        summary: "Rootless container toolchain: Podman, Buildah, and Skopeo",
        packages: &["podman", "buildah", "skopeo"],
    },
    DevBundle {
        name: "virt",
        summary: "QEMU/KVM virtualization stack, libvirt daemon, and Virt-Manager",
        packages: &["qemu-system-x86", "libvirt-daemon-system", "virt-manager"],
    },
    DevBundle {
        name: "all",
        summary: "Complete HSCL1 developer workstation suite (all bundles)",
        packages: &[
            "build-essential",
            "pkg-config",
            "git",
            "curl",
            "openssh-client",
            "btop",
            "python3",
            "python3-venv",
            "python3-pip",
            "pipx",
            "rustc",
            "cargo",
            "podman",
            "buildah",
            "skopeo",
            "qemu-system-x86",
            "libvirt-daemon-system",
            "virt-manager",
        ],
    },
];

/// Setup execution plan for developer bundles.
#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Eq)]
pub struct DevSetupPlan {
    pub bundle: String,
    pub packages: Vec<String>,
    pub command: Vec<String>,
    pub dry_run: bool,
    pub message: String,
}

/// Git hygiene and signing diagnostic report.
#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Eq)]
pub struct GitDoctorReport {
    pub user_name: Option<String>,
    pub user_email: Option<String>,
    pub default_branch: Option<String>,
    pub gpg_sign: bool,
    pub editor: Option<String>,
    pub healthy: bool,
    pub issues: Vec<String>,
    pub recommendations: Vec<String>,
}

/// Rootless container subsystem status.
#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Eq)]
pub struct ContainerStatus {
    pub podman_installed: bool,
    pub podman_version: Option<String>,
    pub subuid_configured: bool,
    pub subgid_configured: bool,
    pub cgroups_v2: bool,
    pub rootless_ready: bool,
    pub notice: String,
}

/// Virtualization and KVM acceleration status.
#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Eq)]
pub struct VmStatus {
    pub kvm_device_present: bool,
    pub kvm_accessible: bool,
    pub cpu_virtualization_supported: bool,
    pub qemu_installed: bool,
    pub libvirt_running: bool,
    pub readiness: String,
    pub guidance: String,
}

fn check_bin(name: &str) -> bool {
    if let Some(path) = std::env::var_os("PATH") {
        std::env::split_paths(&path).any(|dir| {
            let p = dir.join(name);
            p.is_file() || p.with_extension("exe").is_file()
        })
    } else {
        false
    }
}

/// Gather developer environment status across compilers, languages, and virtualization.
pub fn get_dev_status() -> DevStatus {
    let mut tools = Vec::new();
    let mut missing = Vec::new();

    let check_tool = |tools: &mut Vec<ToolInfo>,
                      missing: &mut Vec<String>,
                      name: &str,
                      cat: ToolCategory,
                      essential: bool|
     -> bool {
        let present = check_bin(name);
        if present {
            tools.push(ToolInfo {
                name: name.to_string(),
                category: cat,
                present: true,
                details: None,
            });
        } else if essential {
            missing.push(name.to_string());
        }
        present
    };

    let git_ready = check_tool(&mut tools, &mut missing, "git", ToolCategory::Vcs, true);
    let make_ready = check_tool(
        &mut tools,
        &mut missing,
        "make",
        ToolCategory::Compiler,
        true,
    );
    let gcc_ready = check_tool(
        &mut tools,
        &mut missing,
        "gcc",
        ToolCategory::Compiler,
        false,
    );
    let clang_ready = check_tool(
        &mut tools,
        &mut missing,
        "clang",
        ToolCategory::Compiler,
        false,
    );
    let pkg_ready = check_tool(
        &mut tools,
        &mut missing,
        "pkg-config",
        ToolCategory::Compiler,
        false,
    );
    let python_ready = check_tool(
        &mut tools,
        &mut missing,
        "python3",
        ToolCategory::Language,
        true,
    );
    let rustc_ready = check_tool(
        &mut tools,
        &mut missing,
        "rustc",
        ToolCategory::Language,
        false,
    );
    let cargo_ready = check_tool(
        &mut tools,
        &mut missing,
        "cargo",
        ToolCategory::Language,
        false,
    );
    let node_ready = check_tool(
        &mut tools,
        &mut missing,
        "node",
        ToolCategory::Language,
        false,
    );
    let podman_ready = check_tool(
        &mut tools,
        &mut missing,
        "podman",
        ToolCategory::Container,
        false,
    );
    let qemu_ready = check_tool(
        &mut tools,
        &mut missing,
        "qemu-system-x86_64",
        ToolCategory::Virtualization,
        false,
    );
    let btop_ready = check_tool(
        &mut tools,
        &mut missing,
        "btop",
        ToolCategory::Monitor,
        false,
    );

    let compilers_ready = make_ready && (gcc_ready || clang_ready || pkg_ready);
    let rust_ready = rustc_ready && cargo_ready;

    let readiness = if git_ready && python_ready && compilers_ready && podman_ready {
        "ready".to_string()
    } else if git_ready || python_ready || compilers_ready {
        "partial".to_string()
    } else {
        "minimal".to_string()
    };

    DevStatus {
        readiness,
        compilers_ready,
        git_ready,
        python_ready,
        rust_ready,
        node_ready,
        containers_ready: podman_ready,
        virt_ready: qemu_ready,
        monitors_ready: btop_ready,
        installed_tools: tools,
        missing_recommended: missing,
    }
}

/// Create an install plan for a curated developer bundle.
pub fn plan_dev_setup(bundle_name: Option<&str>, dry_run: bool) -> Result<DevSetupPlan> {
    let name = bundle_name.unwrap_or("base");
    let bundle = BUNDLES.iter().find(|b| b.name == name).ok_or_else(|| {
        anyhow::anyhow!(
            "unknown bundle '{name}'; valid bundles: base, python, rust, containers, virt, all"
        )
    })?;

    let mut cmd = vec![
        "sudo".to_string(),
        "apt-get".to_string(),
        "install".to_string(),
        "-y".to_string(),
    ];
    for pkg in bundle.packages {
        cmd.push(pkg.to_string());
    }

    let message = if dry_run {
        format!(
            "Dry run: planned installation of {} package(s) for bundle '{}' ({}):\n  Command: {}",
            bundle.packages.len(),
            bundle.name,
            bundle.summary,
            cmd.join(" ")
        )
    } else {
        format!(
            "To install the '{}' bundle ({}), run the following command:\n  {}",
            bundle.name,
            bundle.summary,
            cmd.join(" ")
        )
    };

    Ok(DevSetupPlan {
        bundle: bundle.name.to_string(),
        packages: bundle.packages.iter().map(|&s| s.to_string()).collect(),
        command: cmd,
        dry_run,
        message,
    })
}

/// Parse git config contents and perform hygiene checks.
pub fn parse_gitconfig(content: &str) -> GitDoctorReport {
    let mut user_name = None;
    let mut user_email = None;
    let mut default_branch = None;
    let mut gpg_sign = false;
    let mut editor = None;

    let mut current_section = "";

    for line in content.lines() {
        let trimmed = line.trim();
        if trimmed.is_empty() || trimmed.starts_with('#') || trimmed.starts_with(';') {
            continue;
        }

        if trimmed.starts_with('[') && trimmed.ends_with(']') {
            current_section = &trimmed[1..trimmed.len() - 1];
            continue;
        }

        if let Some((k, v)) = trimmed.split_once('=') {
            let key = k.trim();
            let val = v.trim().trim_matches('"');
            match (current_section, key) {
                ("user", "name") => user_name = Some(val.to_string()),
                ("user", "email") => user_email = Some(val.to_string()),
                ("init", "defaultBranch") => default_branch = Some(val.to_string()),
                ("commit", "gpgsign") => gpg_sign = val.eq_ignore_ascii_case("true"),
                ("core", "editor") => editor = Some(val.to_string()),
                _ => {}
            }
        }
    }

    let mut issues = Vec::new();
    let mut recommendations = Vec::new();

    if user_name.is_none() {
        issues.push("Git user.name is not configured.".to_string());
        recommendations
            .push("Set user.name: git config --global user.name \"Your Name\"".to_string());
    }
    if user_email.is_none() {
        issues.push("Git user.email is not configured.".to_string());
        recommendations
            .push("Set user.email: git config --global user.email \"you@example.com\"".to_string());
    }
    if default_branch.as_deref() != Some("main") {
        recommendations.push(
            "Adopt modern standard default branch: git config --global init.defaultBranch main"
                .to_string(),
        );
    }

    let healthy = issues.is_empty();

    GitDoctorReport {
        user_name,
        user_email,
        default_branch,
        gpg_sign,
        editor,
        healthy,
        issues,
        recommendations,
    }
}

/// Run git doctor against current environment.
pub fn get_git_doctor() -> GitDoctorReport {
    let mut config_text = String::new();

    if let Ok(home) = std::env::var("HOME").or_else(|_| std::env::var("USERPROFILE")) {
        let gitconfig_path = Path::new(&home).join(".gitconfig");
        if let Ok(s) = fs::read_to_string(&gitconfig_path) {
            config_text = s;
        }
    }

    if config_text.is_empty() {
        // Fall back to running git config --list if available
        if let Ok(out) = Command::new("git").args(["config", "--list"]).output() {
            if out.status.success() {
                let mut pseudo = String::new();
                for line in String::from_utf8_lossy(&out.stdout).lines() {
                    if let Some((k, v)) = line.split_once('=') {
                        if let Some((sec, subk)) = k.split_once('.') {
                            pseudo.push_str(&format!("[{sec}]\n  {subk} = {v}\n"));
                        }
                    }
                }
                config_text = pseudo;
            }
        }
    }

    parse_gitconfig(&config_text)
}

/// Check rootless container environment readiness.
pub fn get_container_status() -> ContainerStatus {
    let podman_installed = check_bin("podman");
    let mut podman_version = None;

    if podman_installed {
        if let Ok(out) = Command::new("podman").arg("--version").output() {
            if out.status.success() {
                podman_version = Some(String::from_utf8_lossy(&out.stdout).trim().to_string());
            }
        }
    }

    let user = std::env::var("USER").unwrap_or_default();
    let subuid_configured = check_sub_id("/etc/subuid", &user);
    let subgid_configured = check_sub_id("/etc/subgid", &user);
    let cgroups_v2 = Path::new("/sys/fs/cgroup/cgroup.controllers").exists();

    let rootless_ready = podman_installed && (subuid_configured || user.is_empty()) && cgroups_v2;

    let notice = if !podman_installed {
        "Podman is not installed. Install via `hscl dev setup containers`.".to_string()
    } else if !cgroups_v2 {
        "cgroups v2 not detected; container resource delegation may be limited.".to_string()
    } else if !subuid_configured && !user.is_empty() {
        format!("User '{user}' not found in /etc/subuid. Run `sudo usermod --add-subuids 100000-165535 {user}`.")
    } else {
        "Rootless container environment is configured and ready.".to_string()
    };

    ContainerStatus {
        podman_installed,
        podman_version,
        subuid_configured,
        subgid_configured,
        cgroups_v2,
        rootless_ready,
        notice,
    }
}

fn check_sub_id(path: &str, user: &str) -> bool {
    if user.is_empty() {
        return false;
    }
    if let Ok(content) = fs::read_to_string(path) {
        for line in content.lines() {
            let line = line.trim();
            if line.starts_with('#') || line.is_empty() {
                continue;
            }
            if let Some(entry_user) = line.split(':').next() {
                if entry_user == user {
                    return true;
                }
            }
        }
    }
    false
}

/// Check hardware virtualization and KVM acceleration.
pub fn get_vm_status() -> VmStatus {
    let kvm_device_present = Path::new("/dev/kvm").exists();
    let kvm_accessible = if kvm_device_present {
        fs::OpenOptions::new()
            .read(true)
            .write(true)
            .open("/dev/kvm")
            .is_ok()
    } else {
        false
    };

    let cpu_virtualization_supported = if let Ok(cpuinfo) = fs::read_to_string("/proc/cpuinfo") {
        cpuinfo.contains("vmx") || cpuinfo.contains("svm")
    } else {
        false
    };

    let qemu_installed = check_bin("qemu-system-x86_64");
    let libvirt_running = Path::new("/var/run/libvirt/libvirt-sock").exists();

    let readiness = if kvm_device_present && kvm_accessible {
        "hardware-accelerated".to_string()
    } else if cpu_virtualization_supported {
        "cpu-supported-unconfigured".to_string()
    } else {
        "emulation-only".to_string()
    };

    let guidance = if readiness == "hardware-accelerated" {
        "KVM hardware acceleration is active and accessible.".to_string()
    } else if !kvm_device_present && cpu_virtualization_supported {
        "Virtualization is supported by CPU but /dev/kvm was not found. Enable Intel VT-x or AMD-V in UEFI/BIOS settings.".to_string()
    } else if kvm_device_present && !kvm_accessible {
        "KVM device exists but is not writable. Add user to kvm group: sudo usermod -aG kvm $USER"
            .to_string()
    } else {
        "Hardware virtualization acceleration not detected; VMs will run in slow emulation mode."
            .to_string()
    };

    VmStatus {
        kvm_device_present,
        kvm_accessible,
        cpu_virtualization_supported,
        qemu_installed,
        libvirt_running,
        readiness,
        guidance,
    }
}

#[cfg(test)]
pub mod tests {
    use super::*;

    #[test]
    fn test_bundles_valid_and_non_empty() {
        assert!(!BUNDLES.is_empty());
        for b in BUNDLES {
            assert!(!b.name.is_empty());
            assert!(!b.summary.is_empty());
            assert!(!b.packages.is_empty());
            for pkg in b.packages {
                assert!(!pkg.is_empty());
            }
        }
    }

    #[test]
    fn test_plan_dev_setup_known_and_unknown() {
        let plan = plan_dev_setup(Some("python"), true).unwrap();
        assert_eq!(plan.bundle, "python");
        assert!(plan.dry_run);
        assert!(plan.packages.contains(&"python3-venv".to_string()));
        assert!(plan.command.contains(&"apt-get".to_string()));

        let err = plan_dev_setup(Some("nonexistent_bundle"), false).unwrap_err();
        assert!(err.to_string().contains("unknown bundle"));
    }

    #[test]
    fn test_parse_gitconfig_healthy_and_unhealthy() {
        let healthy_cfg = r#"
[user]
    name = Jane Doe
    email = jane@example.com
[init]
    defaultBranch = main
[commit]
    gpgsign = true
[core]
    editor = nano
"#;
        let rep = parse_gitconfig(healthy_cfg);
        assert!(rep.healthy);
        assert_eq!(rep.user_name.as_deref(), Some("Jane Doe"));
        assert_eq!(rep.user_email.as_deref(), Some("jane@example.com"));
        assert_eq!(rep.default_branch.as_deref(), Some("main"));
        assert!(rep.gpg_sign);
        assert_eq!(rep.editor.as_deref(), Some("nano"));
        assert!(rep.issues.is_empty());

        let empty_cfg = "";
        let rep_empty = parse_gitconfig(empty_cfg);
        assert!(!rep_empty.healthy);
        assert!(rep_empty.user_name.is_none());
        assert_eq!(rep_empty.issues.len(), 2); // missing name and email
    }

    #[test]
    fn test_check_sub_id() {
        let temp_dir = tempfile::tempdir().unwrap();
        let subuid_path = temp_dir.path().join("subuid");
        fs::write(
            &subuid_path,
            "# subuid file\nalice:100000:65536\nbob:165536:65536\n",
        )
        .unwrap();

        assert!(check_sub_id(subuid_path.to_str().unwrap(), "alice"));
        assert!(check_sub_id(subuid_path.to_str().unwrap(), "bob"));
        assert!(!check_sub_id(subuid_path.to_str().unwrap(), "charlie"));
        assert!(!check_sub_id(subuid_path.to_str().unwrap(), ""));
    }

    #[test]
    fn test_dev_status_structure() {
        let st = get_dev_status();
        assert!(["ready", "partial", "minimal"].contains(&st.readiness.as_str()));
    }
}
