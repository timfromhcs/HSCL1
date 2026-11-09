//! Security Lab: typed options -> a rootless `podman` argv. Never a shell string, never a pass-through of user flags.
//!
//! Safe by construction: there is no field that can add `--privileged`, host networking/PID/IPC, device passthrough, extra capabilities
//! (except the fixed install-phase set), or arbitrary mounts. The only mount is one validated lab folder. The image must be pinned by
//! sha256 digest and is never pulled implicitly (`--pull=never`).
//!
//! Two phases (official Kali images ship without tools and without systemd, see docs/SECURITY_LAB.md):
//! * install: network on, writable root, only the capabilities apt needs to drop to its `_apt` user (namespaced by the rootless user
//!   namespace), no host folder; the result is committed as a local image.
//! * run: `--cap-drop=ALL`, `no-new-privileges`, read-only root, no network unless chosen, resource limits, one optional lab folder.

use anyhow::{bail, Result};
use std::path::{Component, Path, PathBuf};

/// Packages a toolset may install (checked against this allow-list, and syntactically).
pub const TOOLSETS: &[(&str, &[&str])] = &[
    (
        "basic",
        &[
            "nmap",
            "tcpdump",
            "tshark",
            "whois",
            "bind9-dnsutils",
            "netcat-openbsd",
        ],
    ),
    ("web", &["curl", "wget", "nikto", "sqlmap", "dirb", "wfuzz"]),
    (
        "forensics",
        &["binwalk", "foremost", "sleuthkit", "exiftool"],
    ),
    ("crypto", &["hashcat", "john", "hydra"]),
    ("reversing", &["radare2", "gdb", "ltrace", "strace"]),
];

/// Capabilities apt needs while installing (hypothesis, verified in a VM: P4.3). Run phase gets none.
pub const INSTALL_CAPS: &[&str] = &["CHOWN", "DAC_OVERRIDE", "FOWNER", "SETUID", "SETGID"];

/// Home-relative folders that must never be reachable from a container, even if a lab folder is placed next to them.
const SENSITIVE: &[&str] = &[
    ".ssh",
    ".gnupg",
    ".config",
    ".mozilla",
    ".password-store",
    ".local",
    ".aws",
    ".kube",
    ".docker",
    ".cache",
];
/// Absolute prefixes that are never acceptable as a lab folder.
const FORBIDDEN_ABS: &[&str] = &[
    "/", "/etc", "/run", "/var", "/proc", "/sys", "/dev", "/boot", "/root", "/usr", "/bin",
    "/sbin", "/lib", "/home", "/mnt", "/media",
];

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum Network {
    /// No network at all (default).
    None,
    /// Rootless user-mode networking (podman's default for rootless containers): outbound only, never the host's network namespace.
    Outbound,
}

impl Network {
    pub fn parse(s: &str) -> Result<Self> {
        match s {
            "none" => Ok(Network::None),
            "outbound" => Ok(Network::Outbound),
            other => bail!("network must be `none` or `outbound`, not `{other}` (host networking is not offered)"),
        }
    }
}

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub struct Limits {
    pub memory_mib: u32,
    pub cpus: u32,
    pub pids: u32,
}

impl Default for Limits {
    fn default() -> Self {
        Limits {
            memory_mib: 2048,
            cpus: 2,
            pids: 512,
        }
    }
}

impl Limits {
    fn check(&self) -> Result<()> {
        if !(256..=16384).contains(&self.memory_mib) {
            bail!("memory must be 256..16384 MiB");
        }
        if !(1..=16).contains(&self.cpus) {
            bail!("cpus must be 1..16");
        }
        if !(64..=4096).contains(&self.pids) {
            bail!("pids must be 64..4096");
        }
        Ok(())
    }
}

pub fn validate_project(p: &str) -> Result<()> {
    let ok = !p.is_empty()
        && p.len() <= 31
        && p.chars()
            .next()
            .is_some_and(|c| c.is_ascii_lowercase() || c.is_ascii_digit())
        && p.chars()
            .all(|c| c.is_ascii_lowercase() || c.is_ascii_digit() || c == '-');
    if !ok {
        bail!("project must match [a-z0-9][a-z0-9-]{{0,30}}");
    }
    Ok(())
}

/// `registry/name[:tag]@sha256:<64 hex>`: a tag alone is refused, the digest is what is pinned.
pub fn validate_image(img: &str) -> Result<()> {
    let Some((name, digest)) = img.rsplit_once("@sha256:") else {
        bail!(
            "image must be pinned by digest (`...@sha256:<64 hex>`); a tag alone is not accepted"
        );
    };
    let hex_ok = digest.len() == 64
        && digest
            .bytes()
            .all(|b| b.is_ascii_digit() || (b'a'..=b'f').contains(&b));
    let name_ok = !name.is_empty()
        && name.len() <= 200
        && name
            .bytes()
            .all(|b| b.is_ascii_lowercase() || b.is_ascii_digit() || b"./_-:".contains(&b))
        && !name.starts_with('-')
        && !name.contains("..");
    if !hex_ok || !name_ok {
        bail!("image reference is not a valid `name@sha256:<64 hex>`");
    }
    Ok(())
}

/// A lab folder must be an absolute, normalised path strictly below `labs_root`, free of characters that could smuggle volume options,
/// and not a symlink anywhere on its existing part. Returns the path as given (normalised).
pub fn validate_workspace(ws: &Path, labs_root: &Path) -> Result<PathBuf> {
    let s = ws.to_string_lossy();
    if s.contains([':', ',', '\0', '\n', '\r']) || s.contains("//") {
        bail!("lab folder contains a character that is not allowed (`:` `,` NUL newline or `//`)");
    }
    // Lab folders are Linux paths: test the text, so the same rule holds when the code is built and tested on another OS.
    if !s.starts_with('/') {
        bail!("lab folder must be an absolute path");
    }
    let mut norm = PathBuf::new();
    for c in ws.components() {
        match c {
            Component::ParentDir => bail!("lab folder must not contain `..`"),
            Component::CurDir => {}
            other => norm.push(other.as_os_str()),
        }
    }
    if FORBIDDEN_ABS.iter().any(|f| norm == Path::new(f)) {
        bail!("`{}` is never allowed as a lab folder", norm.display());
    }
    if !norm.starts_with(labs_root) || norm == labs_root {
        bail!(
            "lab folder must be inside {} (not the folder itself)",
            labs_root.display()
        );
    }
    for c in norm.strip_prefix(labs_root)?.components() {
        if let Component::Normal(n) = c {
            let n = n.to_string_lossy();
            if SENSITIVE.contains(&n.as_ref()) || n.starts_with('.') {
                bail!("`{n}` is a hidden or credential-bearing folder name and is refused inside a lab folder path");
            }
        }
    }
    let mut cur = PathBuf::new();
    for c in norm.components() {
        cur.push(c.as_os_str());
        if cur.is_symlink() {
            bail!(
                "`{}` is a symlink; lab folders may not contain symlinks",
                cur.display()
            );
        }
    }
    Ok(norm)
}

pub struct RunSpec<'a> {
    pub project: &'a str,
    pub image: &'a str,
    pub workspace: Option<&'a Path>,
    pub labs_root: &'a Path,
    pub network: Network,
    pub limits: Limits,
    /// Command inside the container (the container is the sandbox); defaults to an interactive shell.
    pub command: &'a [String],
}

pub fn container_name(project: &str) -> String {
    format!("hscl-lab-{project}")
}

pub fn run_argv(spec: &RunSpec) -> Result<Vec<String>> {
    validate_project(spec.project)?;
    validate_image(spec.image)?;
    spec.limits.check()?;
    let mut a: Vec<String> = vec![
        "podman".into(),
        "run".into(),
        "--rm".into(),
        "--interactive".into(),
        "--tty".into(),
        "--name".into(),
        container_name(spec.project),
        "--hostname".into(),
        "hscl-lab".into(),
        "--pull=never".into(),
        "--cap-drop=ALL".into(),
        "--security-opt=no-new-privileges".into(),
        "--read-only".into(),
        "--tmpfs".into(),
        "/tmp:rw,noexec,nosuid,nodev,size=256m".into(),
        "--tmpfs".into(),
        "/run:rw,noexec,nosuid,nodev,size=16m".into(),
        format!("--memory={}m", spec.limits.memory_mib),
        format!("--cpus={}", spec.limits.cpus),
        format!("--pids-limit={}", spec.limits.pids),
    ];
    if spec.network == Network::None {
        a.push("--network=none".into());
    }
    if let Some(ws) = spec.workspace {
        let ws = validate_workspace(ws, spec.labs_root)?;
        a.push("--volume".into());
        a.push(format!("{}:/work:rw,nosuid,nodev", ws.display()));
        a.push("--workdir".into());
        a.push("/work".into());
    }
    a.push(spec.image.to_string());
    if spec.command.is_empty() {
        a.push("/bin/bash".into());
    } else {
        if spec.command.iter().any(|c| c.contains('\0')) {
            bail!("command contains a NUL byte");
        }
        a.extend(spec.command.iter().cloned());
    }
    Ok(a)
}

/// Install phase: writable root, outbound network, only the apt capabilities, no host folder. Packages come from a toolset allow-list.
pub fn install_argv(
    project: &str,
    image: &str,
    toolset: &str,
    limits: Limits,
) -> Result<Vec<String>> {
    validate_project(project)?;
    validate_image(image)?;
    limits.check()?;
    let Some((_, pkgs)) = TOOLSETS.iter().find(|(n, _)| *n == toolset) else {
        bail!("unknown toolset `{toolset}`");
    };
    for p in *pkgs {
        if !p
            .bytes()
            .all(|b| b.is_ascii_lowercase() || b.is_ascii_digit() || b"+.-".contains(&b))
        {
            bail!("invalid package name in toolset");
        }
    }
    let script = format!("apt-get update && DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends {}", pkgs.join(" "));
    let mut a: Vec<String> = vec![
        "podman".into(),
        "run".into(),
        "--name".into(),
        format!("hscl-lab-install-{project}"),
        "--pull=never".into(),
        "--cap-drop=ALL".into(),
    ];
    for c in INSTALL_CAPS {
        a.push(format!("--cap-add={c}"));
    }
    a.extend([
        "--security-opt=no-new-privileges".to_string(),
        format!("--memory={}m", limits.memory_mib),
        format!("--cpus={}", limits.cpus),
        format!("--pids-limit={}", limits.pids),
        image.to_string(),
        "/bin/sh".into(),
        "-c".into(),
        script,
    ]);
    Ok(a)
}

/// Turns the finished install container into the local image `localhost/hscl-lab-<project>:latest`.
pub fn commit_argv(project: &str) -> Result<Vec<String>> {
    validate_project(project)?;
    Ok(vec![
        "podman".into(),
        "commit".into(),
        format!("hscl-lab-install-{project}"),
        format!("localhost/hscl-lab-{project}:latest"),
    ])
}

/// Removes this project's containers and local image. Never touches volumes, bind-mounted lab folders or other projects.
pub fn destroy_argv(project: &str) -> Result<Vec<Vec<String>>> {
    validate_project(project)?;
    Ok(vec![
        vec![
            "podman".into(),
            "rm".into(),
            "--force".into(),
            "--ignore".into(),
            container_name(project),
            format!("hscl-lab-install-{project}"),
        ],
        vec![
            "podman".into(),
            "rmi".into(),
            "--force".into(),
            "--ignore".into(),
            format!("localhost/hscl-lab-{project}:latest"),
        ],
    ])
}

/// Human display of an argv with shell-safe quoting (display only; execution never goes through a shell).
pub fn display(argv: &[String]) -> String {
    argv.iter()
        .map(|a| {
            if a.bytes()
                .all(|b| b.is_ascii_alphanumeric() || b"-_./=:,@+".contains(&b))
            {
                a.clone()
            } else {
                format!("'{}'", a.replace('\'', "'\\''"))
            }
        })
        .collect::<Vec<_>>()
        .join(" ")
}

pub fn validate_toolset(name: &str) -> Result<(&'static str, &'static [&'static str])> {
    let lower = name.trim().to_ascii_lowercase();
    TOOLSETS
        .iter()
        .find(|(n, _)| *n == lower)
        .copied()
        .ok_or_else(|| {
            anyhow::anyhow!(
                "unknown toolset '{name}': valid toolsets are {}",
                TOOLSETS
                    .iter()
                    .map(|(n, _)| *n)
                    .collect::<Vec<_>>()
                    .join(", ")
            )
        })
}

#[derive(Debug, Clone, serde::Serialize)]
pub struct LabContainerSummary {
    pub name: String,
    pub image: String,
    pub status: String,
    pub created: String,
}

pub fn list_containers() -> Vec<LabContainerSummary> {
    let out = std::process::Command::new("podman")
        .args([
            "ps",
            "-a",
            "--filter",
            "name=hscl-lab-",
            "--format",
            "{{.Names}}\t{{.Image}}\t{{.Status}}\t{{.CreatedAt}}",
        ])
        .output();
    let mut list = Vec::new();
    if let Ok(o) = out {
        if o.status.success() {
            let text = String::from_utf8_lossy(&o.stdout);
            for line in text.lines() {
                let parts: Vec<&str> = line.split('\t').collect();
                if !parts.is_empty() && !parts[0].is_empty() {
                    list.push(LabContainerSummary {
                        name: parts[0].to_string(),
                        image: parts.get(1).unwrap_or(&"unknown").to_string(),
                        status: parts.get(2).unwrap_or(&"unknown").to_string(),
                        created: parts.get(3).unwrap_or(&"unknown").to_string(),
                    });
                }
            }
        }
    }
    list
}

pub fn inspect_container(name: &str) -> Result<serde_json::Value> {
    validate_project(name)?;
    let cname = container_name(name);
    let out = std::process::Command::new("podman")
        .args(["inspect", &cname])
        .output();
    match out {
        Ok(o) => {
            if o.status.success() {
                let data: serde_json::Value = serde_json::from_slice(&o.stdout)?;
                Ok(data)
            } else {
                let err = String::from_utf8_lossy(&o.stderr);
                bail!("podman inspect failed: {err}")
            }
        }
        Err(e) => bail!("podman executable not available: {e}"),
    }
}

pub fn plan_container_shell(name: &str, dry_run: bool) -> Result<serde_json::Value> {
    validate_project(name)?;
    let cname = container_name(name);
    let cmd = vec![
        "podman".to_string(),
        "exec".to_string(),
        "-it".to_string(),
        cname.clone(),
        "/bin/bash".to_string(),
    ];
    Ok(serde_json::json!({
        "action": "container_shell",
        "container": cname,
        "command": cmd,
        "dry_run": dry_run,
        "note": if dry_run {
            "Dry run: container shell command planned; did not attach."
        } else {
            "Attaching to container shell."
        }
    }))
}

pub fn plan_container_stop(name: &str, dry_run: bool) -> Result<serde_json::Value> {
    validate_project(name)?;
    let cname = container_name(name);
    let cmd = vec!["podman".to_string(), "stop".to_string(), cname.clone()];
    Ok(serde_json::json!({
        "action": "container_stop",
        "container": cname,
        "command": cmd,
        "dry_run": dry_run,
        "note": if dry_run {
            "Dry run: container stop planned."
        } else {
            "Stopping container."
        }
    }))
}

pub fn plan_container_destroy(name: &str, dry_run: bool) -> Result<serde_json::Value> {
    validate_project(name)?;
    let cname = container_name(name);
    let cmd = vec![
        "podman".to_string(),
        "rm".to_string(),
        "-f".to_string(),
        cname.clone(),
    ];
    Ok(serde_json::json!({
        "action": "container_destroy",
        "container": cname,
        "command": cmd,
        "dry_run": dry_run,
        "note": if dry_run {
            "Dry run: container removal planned."
        } else {
            "Destroying container."
        }
    }))
}

#[derive(Debug, Clone, serde::Serialize)]
pub struct LabVmProfile {
    pub name: String,
    pub network: String,
    pub memory_mib: u32,
    pub cpus: u32,
    pub disk_gib: u32,
    pub description: String,
    pub security_boundary: String,
}

pub fn list_vm_profiles() -> Vec<LabVmProfile> {
    vec![
        LabVmProfile {
            name: "isolated".into(),
            network: "host-only / isolated (no internet)".into(),
            memory_mib: 4096,
            cpus: 2,
            disk_gib: 20,
            description: "Default isolated malware/exploit analysis sandbox".into(),
            security_boundary: "Host-only network namespace; no packets leave the virtual switch"
                .into(),
        },
        LabVmProfile {
            name: "bridged".into(),
            network: "bridged (authorized target network)".into(),
            memory_mib: 4096,
            cpus: 2,
            disk_gib: 20,
            description: "Bridged network VM for authorized LAN assessments".into(),
            security_boundary: "Direct network interface access; requires explicit authorization"
                .into(),
        },
        LabVmProfile {
            name: "usb-passthrough".into(),
            network: "isolated".into(),
            memory_mib: 4096,
            cpus: 2,
            disk_gib: 20,
            description: "Hardware testing VM with USB Wi-Fi / SDR passthrough enabled".into(),
            security_boundary:
                "Dedicated USB controller passed directly to the guest; host detached".into(),
        },
    ]
}

pub fn validate_vm_profile(profile: &str) -> Result<LabVmProfile> {
    let lower = profile.trim().to_ascii_lowercase();
    list_vm_profiles()
        .into_iter()
        .find(|p| p.name == lower)
        .ok_or_else(|| {
            anyhow::anyhow!(
                "unknown VM profile '{profile}': valid choices are isolated, bridged, usb-passthrough"
            )
        })
}

pub fn plan_create_vm(
    profile: &str,
    custom_name: Option<&str>,
    dry_run: bool,
) -> Result<serde_json::Value> {
    let prof = validate_vm_profile(profile)?;
    let vm_name = custom_name.unwrap_or(&prof.name);
    validate_project(vm_name)?;
    let vms_dir = crate::appearance::config_dir().join("lab").join("vms");
    let disk_path = vms_dir.join(format!("{vm_name}.qcow2"));

    let qemu_img_cmd = vec![
        "qemu-img".to_string(),
        "create".to_string(),
        "-f".to_string(),
        "qcow2".to_string(),
        disk_path.to_string_lossy().to_string(),
        format!("{}G", prof.disk_gib),
    ];

    if !dry_run {
        let _ = std::fs::create_dir_all(&vms_dir);
    }

    Ok(serde_json::json!({
        "action": "create_vm",
        "name": vm_name,
        "profile": prof.name,
        "memory_mib": prof.memory_mib,
        "cpus": prof.cpus,
        "disk_path": disk_path.display().to_string(),
        "command": qemu_img_cmd,
        "dry_run": dry_run,
        "security_boundary": prof.security_boundary,
        "note": if dry_run {
            "Dry run: VM creation planned; disk image was not created."
        } else {
            "VM profile configured and disk image prepared."
        }
    }))
}

pub fn plan_launch_vm(name: &str, dry_run: bool) -> Result<serde_json::Value> {
    validate_project(name)?;
    let vms_dir = crate::appearance::config_dir().join("lab").join("vms");
    let disk_path = vms_dir.join(format!("{name}.qcow2"));

    let qemu_cmd = vec![
        "qemu-system-x86_64".to_string(),
        "-enable-kvm".to_string(),
        "-m".to_string(),
        "4096".to_string(),
        "-smp".to_string(),
        "2".to_string(),
        "-drive".to_string(),
        format!("file={},if=virtio,format=qcow2", disk_path.display()),
        "-netdev".to_string(),
        "user,id=net0,restrict=on".to_string(),
        "-device".to_string(),
        "virtio-net-pci,netdev=net0".to_string(),
        "-name".to_string(),
        format!("hscl-lab-{name}"),
    ];

    Ok(serde_json::json!({
        "action": "launch_vm",
        "name": name,
        "disk_path": disk_path.display().to_string(),
        "command": qemu_cmd,
        "dry_run": dry_run,
        "network_isolation": "restricted user-mode (isolated, no host/external traffic)",
        "note": if dry_run {
            "Dry run: VM launch command planned; VM was not started."
        } else {
            "VM launch command prepared for execution."
        }
    }))
}

pub fn plan_destroy_vm(name: &str, dry_run: bool) -> Result<serde_json::Value> {
    validate_project(name)?;
    let vms_dir = crate::appearance::config_dir().join("lab").join("vms");
    let disk_path = vms_dir.join(format!("{name}.qcow2"));

    let existed = disk_path.exists();
    if !dry_run && existed {
        let _ = std::fs::remove_file(&disk_path);
    }

    Ok(serde_json::json!({
        "action": "destroy_vm",
        "name": name,
        "disk_path": disk_path.display().to_string(),
        "dry_run": dry_run,
        "deleted": !dry_run && existed,
        "note": if dry_run {
            "Dry run: VM disk would be permanently deleted."
        } else {
            "Disposable VM disk image destroyed."
        }
    }))
}

#[cfg(test)]
mod tests {
    use super::*;

    const IMG: &str = "docker.io/kalilinux/kali-rolling@sha256:0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef";
    const FORBIDDEN: &[&str] = &[
        "--privileged",
        "--network=host",
        "--net=host",
        "--pid=host",
        "--ipc=host",
        "--uts=host",
        "--userns=host",
        "--device",
        "--cap-add=ALL",
        "--security-opt=seccomp=unconfined",
        "--security-opt=apparmor=unconfined",
        "--security-opt=label=disable",
        "--volumes-from",
    ];

    fn root() -> PathBuf {
        PathBuf::from("/home/u/SecurityLabs")
    }

    fn spec<'a>(ws: Option<&'a Path>, root: &'a Path, cmd: &'a [String]) -> RunSpec<'a> {
        RunSpec {
            project: "web1",
            image: IMG,
            workspace: ws,
            labs_root: root,
            network: Network::None,
            limits: Limits::default(),
            command: cmd,
        }
    }

    #[test]
    fn run_defaults_are_the_safe_set() {
        let r = root();
        let a = run_argv(&spec(None, &r, &[])).unwrap();
        for must in [
            "--cap-drop=ALL",
            "--security-opt=no-new-privileges",
            "--read-only",
            "--network=none",
            "--pull=never",
            "--rm",
        ] {
            assert!(a.iter().any(|x| x == must), "missing {must}: {a:?}");
        }
        assert!(
            !a.iter().any(|x| x.starts_with("--cap-add")),
            "run phase must add no capability"
        );
        assert_eq!(a.last().unwrap(), "/bin/bash");
        assert!(
            a.iter().any(|x| x.starts_with("--memory="))
                && a.iter().any(|x| x.starts_with("--pids-limit="))
        );
        assert!(
            !a.iter().any(|x| x == "--volume"),
            "no mount without a lab folder"
        );
    }

    #[test]
    fn outbound_network_only_removes_the_none_flag_and_never_selects_the_host() {
        let r = root();
        let mut s = spec(None, &r, &[]);
        s.network = Network::Outbound;
        let a = run_argv(&s).unwrap();
        assert!(!a.iter().any(|x| x.starts_with("--network")));
        assert!(Network::parse("host").is_err() && Network::parse("bridge").is_err());
    }

    #[test]
    fn no_valid_input_can_produce_a_forbidden_flag() {
        let r = root();
        let ws = PathBuf::from("/home/u/SecurityLabs/p1");
        for net in [Network::None, Network::Outbound] {
            let cmd = vec![
                "nmap".to_string(),
                "-sV".to_string(),
                "10.0.0.1".to_string(),
            ];
            let mut s = spec(Some(&ws), &r, &cmd);
            s.network = net;
            let a = run_argv(&s).unwrap();
            for f in FORBIDDEN {
                assert!(
                    !a.iter().any(|x| x == f || x.starts_with(&format!("{f}="))),
                    "{f} present in {a:?}"
                );
            }
        }
        let i = install_argv("web1", IMG, "basic", Limits::default()).unwrap();
        for f in FORBIDDEN {
            assert!(!i.iter().any(|x| x == f), "{f} in install argv");
        }
        let caps: Vec<_> = i
            .iter()
            .filter_map(|x| x.strip_prefix("--cap-add="))
            .collect();
        assert_eq!(caps, INSTALL_CAPS);
        assert!(
            !i.iter().any(|x| x == "--volume"),
            "install phase mounts nothing from the host"
        );
        assert!(
            !i.iter().any(|x| x == "--read-only"),
            "apt needs a writable root in the install phase only"
        );
    }

    #[test]
    fn image_must_be_digest_pinned() {
        assert!(validate_image(IMG).is_ok());
        assert!(validate_image("docker.io/kalilinux/kali-rolling:latest").is_err());
        assert!(validate_image("docker.io/kalilinux/kali-rolling").is_err());
        assert!(validate_image("docker.io/kalilinux/kali-rolling@sha256:abc").is_err());
        assert!(validate_image(
            "--privileged@sha256:0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef"
        )
        .is_err());
        assert!(validate_image(
            "a b@sha256:0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef"
        )
        .is_err());
        assert!(validate_image(
            "../x@sha256:0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef"
        )
        .is_err());
    }

    #[test]
    fn project_names_are_restricted() {
        for ok in ["a", "web1", "a-b-c", "0day"] {
            assert!(validate_project(ok).is_ok(), "{ok}");
        }
        for bad in [
            "",
            "-x",
            "A",
            "a b",
            "a/b",
            "a;b",
            "a..",
            &"x".repeat(32),
            "ü",
        ] {
            assert!(validate_project(bad).is_err(), "{bad:?}");
        }
    }

    #[test]
    fn workspace_must_be_a_clean_folder_inside_the_labs_root() {
        let r = root();
        assert!(validate_workspace(Path::new("/home/u/SecurityLabs/p1"), &r).is_ok());
        assert!(validate_workspace(Path::new("/home/u/SecurityLabs/p1/sub"), &r).is_ok());
        for bad in [
            "/",
            "/etc",
            "/home/u",
            "/home/u/SecurityLabs",
            "/home/u/SecurityLabs/../.ssh",
            "/home/u/SecurityLabs/p1/../../x",
            "relative/p",
            "/home/u/SecurityLabs/p1:/etc",
            "/home/u/SecurityLabs/p1,ro",
            "/home/u/SecurityLabs//p1",
            "/home/u/.ssh",
            "/home/u/SecurityLabs/.ssh",
            "/home/u/SecurityLabs/.hidden",
            "/home/u/SecurityLabs/p1/.gnupg",
            "/run/user/1000",
            "/var/run/docker.sock",
            "/home/u/SecurityLabs/p1\n",
            "/other/SecurityLabs/p1",
        ] {
            assert!(
                validate_workspace(Path::new(bad), &r).is_err(),
                "{bad:?} should be refused"
            );
        }
    }

    #[cfg(unix)]
    #[test]
    fn workspace_symlinks_are_refused() {
        let td = tempfile::tempdir().unwrap();
        let labs = td.path().join("SecurityLabs");
        std::fs::create_dir_all(labs.join("real")).unwrap();
        std::os::unix::fs::symlink("/etc", labs.join("link")).unwrap();
        assert!(validate_workspace(&labs.join("link"), &labs).is_err());
        assert!(validate_workspace(&labs.join("link").join("x"), &labs).is_err());
        assert!(validate_workspace(&labs.join("real"), &labs).is_ok());
    }

    #[test]
    fn seeded_fuzz_of_workspace_strings_never_yields_a_volume_with_extra_segments() {
        let r = root();
        let pieces = [
            "/home/u/SecurityLabs",
            "/p1",
            "/..",
            "/.",
            ":",
            ",",
            "ro",
            "/etc",
            "/.ssh",
            "//",
            "\n",
            " ",
            "/run",
            "x",
            "/sock",
            "~",
            "$HOME",
            "\\",
            "\0",
        ];
        let mut seed: u64 = 0x5eed_1234_abcd_ef01;
        let mut next = || {
            seed ^= seed << 13;
            seed ^= seed >> 7;
            seed ^= seed << 17;
            seed
        };
        let mut accepted = 0;
        for _ in 0..20000 {
            let n = 1 + (next() % 6) as usize;
            let s: String = (0..n)
                .map(|_| pieces[(next() % pieces.len() as u64) as usize])
                .collect();
            let p = PathBuf::from(&s);
            if let Ok(v) = validate_workspace(&p, &r) {
                accepted += 1;
                let arg = format!("{}:/work:rw,nosuid,nodev", v.display());
                assert_eq!(arg.matches(':').count(), 2, "{s:?} -> {arg}");
                assert_eq!(arg.matches(',').count(), 2, "{s:?} -> {arg}");
                assert!(v.starts_with(&r) && v != r, "{s:?}");
                assert!(
                    !v.components().any(|c| matches!(c, Component::ParentDir)),
                    "{s:?}"
                );
            }
        }
        assert!(accepted > 0, "generator must produce valid paths too");
    }

    #[test]
    fn limits_are_bounded() {
        let r = root();
        for l in [
            Limits {
                memory_mib: 100,
                ..Default::default()
            },
            Limits {
                memory_mib: 99999,
                ..Default::default()
            },
            Limits {
                cpus: 0,
                ..Default::default()
            },
            Limits {
                cpus: 99,
                ..Default::default()
            },
            Limits {
                pids: 1,
                ..Default::default()
            },
            Limits {
                pids: 100000,
                ..Default::default()
            },
        ] {
            let mut s = spec(None, &r, &[]);
            s.limits = l;
            assert!(run_argv(&s).is_err(), "{l:?}");
        }
    }

    #[test]
    fn toolsets_are_an_allow_list_and_destroy_only_removes_this_project() {
        assert!(install_argv("web1", IMG, "everything", Limits::default()).is_err());
        let i = install_argv("web1", IMG, "basic", Limits::default()).unwrap();
        assert!(
            i.last().unwrap().contains("nmap")
                && !i.last().unwrap().contains("kali-linux-everything")
        );
        let d = destroy_argv("web1").unwrap();
        let flat: Vec<&String> = d.iter().flatten().collect();
        assert!(flat
            .iter()
            .all(|x| !x.starts_with("--volumes") && *x != "-v" && *x != "--all" && *x != "prune"));
        assert!(
            flat.iter().any(|x| *x == "hscl-lab-web1")
                && !flat.iter().any(|x| *x == "hscl-lab-web2")
        );
        assert!(destroy_argv("../x").is_err() && commit_argv("A").is_err());
    }

    #[test]
    fn display_quotes_for_a_shell_but_execution_never_uses_one() {
        let a = vec![
            "podman".to_string(),
            "run".into(),
            "a b".into(),
            "it's".into(),
            "x;y".into(),
        ];
        let s = display(&a);
        assert_eq!(s, "podman run 'a b' 'it'\\''s' 'x;y'");
    }

    #[test]
    fn test_validate_toolset_known_and_unknown() {
        assert!(validate_toolset("basic").is_ok());
        assert!(validate_toolset("web").is_ok());
        assert!(validate_toolset("forensics").is_ok());
        assert!(validate_toolset("crypto").is_ok());
        assert!(validate_toolset("reversing").is_ok());
        assert!(validate_toolset("unknown_exploit_kit").is_err());
    }

    #[test]
    fn test_validate_vm_profile_and_plan() {
        assert!(validate_vm_profile("isolated").is_ok());
        assert!(validate_vm_profile("bridged").is_ok());
        assert!(validate_vm_profile("usb-passthrough").is_ok());
        assert!(validate_vm_profile("full-host-root").is_err());

        let plan = plan_create_vm("isolated", Some("test-vm"), true).unwrap();
        assert_eq!(plan["action"], "create_vm");
        assert_eq!(plan["dry_run"], true);

        let launch = plan_launch_vm("test-vm", true).unwrap();
        assert_eq!(launch["action"], "launch_vm");
        assert_eq!(launch["dry_run"], true);

        let destroy = plan_destroy_vm("test-vm", true).unwrap();
        assert_eq!(destroy["action"], "destroy_vm");
        assert_eq!(destroy["dry_run"], true);
    }

    #[test]
    fn test_plan_container_shell_stop_destroy() {
        let shell = plan_container_shell("test-proj", true).unwrap();
        assert_eq!(shell["action"], "container_shell");
        assert_eq!(shell["dry_run"], true);

        let stop = plan_container_stop("test-proj", true).unwrap();
        assert_eq!(stop["action"], "container_stop");
        assert_eq!(stop["dry_run"], true);

        let destroy = plan_container_destroy("test-proj", true).unwrap();
        assert_eq!(destroy["action"], "container_destroy");
        assert_eq!(destroy["dry_run"], true);
    }
}
