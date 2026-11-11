//! Privacy mode, ephemeral sessions, Tor workflows, and Tails verification (AGENTS.md section 6.5 & 8.2).
//!
//! HSCL1 provides ephemeral live session properties, memory-only scratch overlays, and
//! isolated Tor workflows.
//!
//! HONEST THREAT MODEL BOUNDARIES:
//! HSCL1 is NOT Tails and makes no claim of absolute anonymity, forensic invisibility, or
//! anti-surveillance guarantees. For threat models requiring strict anonymity, users must
//! run the authentic, signature-verified Tails OS.

use anyhow::{bail, Context, Result};
use serde::{Deserialize, Serialize};
use sha2::{Digest, Sha256};
use std::fs;
use std::io::Read;
use std::net::TcpStream;
use std::path::{Path, PathBuf};
use std::time::Duration;

pub const TAILS_DOWNLOAD_URL: &str = "https://tails.net/install/download/";
pub const MANDATORY_DISCLAIMER: &str =
    "HSCL1 Privacy Mode is NOT Tails and makes no claim of absolute anonymity or forensic invisibility. It provides ephemeral session properties (volatile RAM overlayfs, memory-backed zram swap, fs.suid_dumpable=0, unmounted host disks) and isolated Tor workflows.";

pub const SESSION_EXPLANATION: &str = r#"HSCL1 Privacy Mode: Architecture, Session Isolation & Threat Model
========================================================================

1. Ephemeral Overlay Filesystem
   The operating system root runs on a volatile, RAM-backed overlayfs (e.g. /cow or tmpfs).
   All filesystem writes, application temporary files, user home modifications, and caches
   are held strictly in volatile RAM. They are completely discarded upon shutdown or reboot.

2. Volatile Memory & Swap Security
   No persistent swap partitions or swap files on physical storage disks are enabled in the
   ephemeral privacy session. Memory expansion is provided by compressed zram with swap
   priority 100, ensuring all paging remains in volatile system RAM and is cleared on power-off.

3. Dumpability and Core Dump Protection
   Kernel dumpability is disabled via sysctl:
     fs.suid_dumpable = 0
   This prevents process memory or sensitive cryptographic keys from being written to disk
   in the event of an unhandled crash or fault.

4. Host Storage Isolation
   Internal physical drives (SATA, NVMe, eMMC, USB storage partitions) are NOT automatically
   mounted in the ephemeral privacy session. Host storage remains isolated unless the user
   explicitly chooses to mount a specific filesystem.

5. Tor Launcher, and What Is NOT Enforced
   Privacy web workflows use Tor Browser with upstream safe defaults.
   `hscl privacy tor launch` starts Tor Browser and nothing else: if Tor Browser is not
   installed it refuses with an error instead of substituting Firefox or Chromium. That is a
   launcher rule, not a network rule - HSCL1 does NOT filter egress, does NOT block a browser
   the user starts normally, and does NOT verify that traffic reached Tor. There is no
   killswitch and no packet-capture evidence for a Tor-routed session.

6. Clear Boundaries vs Authentic Tails
   HSCL1 is a unified multi-mode Linux workstation, NOT Tails:
   - HSCL1 does NOT guarantee kernel-level amnesic RAM sanitization on every hardware platform.
   - HSCL1 does NOT enforce a system-wide transparent Tor firewall killswitch for all host packets.
   - HSCL1 does NOT spoof network MAC addresses by default on every network interface.
   For adversarial, anti-surveillance, or high-risk threat models, use the authentic Tails OS.
   HSCL1 provides verified launchers for official Tails ISOs via:
     $ hscl privacy tails verify <IMAGE> [--expected-sha256 <HASH>]
     $ hscl privacy tails launch <IMAGE>
"#;

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Eq)]
pub struct PrivacyStatus {
    /// True when root filesystem is backed by a volatile RAM overlay (/cow or overlayfs).
    pub ephemeral_overlay: bool,
    /// Root mount filesystem type.
    pub root_fstype: String,
    /// True if any persistent swap partition/file is active on physical disk.
    pub persistent_swap_active: bool,
    /// True if zram compressed memory swap is active.
    pub zram_swap_active: bool,
    /// True if kernel dumpability is disabled (fs.suid_dumpable == 0).
    pub suid_dumpable_disabled: bool,
    /// Internal disks automounted under /media or /mnt.
    pub internal_disks_automounted: Vec<String>,
    /// True if local Tor daemon/SOCKS proxy is responsive.
    pub tor_service_active: bool,
    /// True if Tor Browser launcher or executable is present.
    pub tor_browser_installed: bool,
    /// Detected path to Tor Browser or launcher.
    pub tor_browser_path: Option<String>,
    /// Mandatory honest threat model disclaimer.
    pub disclaimer: String,
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Eq)]
pub struct TorStatus {
    pub service_active: bool,
    pub browser_installed: bool,
    pub browser_path: Option<String>,
    /// True because `tor_launch` refuses to start anything but Tor Browser. It is NOT a network policy:
    /// nothing filters egress. The old name (`fail_closed_policy`) claimed more than the code does.
    pub tor_launch_requires_browser: bool,
    pub notice: String,
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Eq)]
pub struct TailsVerifyReport {
    pub image: PathBuf,
    pub size_bytes: u64,
    pub calculated_sha256: String,
    pub expected_sha256: Option<String>,
    pub verified: bool,
    pub tails_doc_url: String,
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Eq)]
pub struct TailsLaunchReport {
    pub image: PathBuf,
    pub ram_mb: u32,
    pub command: String,
    pub dry_run: bool,
    pub safety_notice: String,
}

/// Parse `/proc/mounts` content and extract overlay status, root fstype, and mounted host disks.
pub fn parse_mounts(content: &str) -> (bool, String, Vec<String>) {
    let mut ephemeral_overlay = false;
    let mut root_fstype = String::from("unknown");
    let mut internal_disks_automounted = Vec::new();

    for line in content.lines() {
        let parts: Vec<&str> = line.split_whitespace().collect();
        if parts.len() < 3 {
            continue;
        }
        let src = parts[0];
        let target = parts[1];
        let fstype = parts[2];

        if target == "/" {
            root_fstype = fstype.to_string();
            if fstype == "overlay" || src == "/cow" || src.contains("overlay") {
                ephemeral_overlay = true;
            }
        }

        if src == "/cow" || fstype == "overlay" {
            ephemeral_overlay = true;
        }

        // Check for internal physical disk partitions mounted under /media or /mnt
        let is_disk_dev = src.starts_with("/dev/sd")
            || src.starts_with("/dev/nvme")
            || src.starts_with("/dev/vd")
            || src.starts_with("/dev/mapper/");
        let is_automount_dir = target.starts_with("/media") || target.starts_with("/mnt");

        if is_disk_dev && is_automount_dir {
            internal_disks_automounted.push(format!("{src} on {target} ({fstype})"));
        }
    }

    internal_disks_automounted.sort();
    (ephemeral_overlay, root_fstype, internal_disks_automounted)
}

/// Parse `/proc/swaps` content and extract zram vs persistent swap status.
pub fn parse_swaps(content: &str) -> (bool, bool) {
    let mut zram_active = false;
    let mut persistent_active = false;

    for line in content.lines().skip(1) {
        let parts: Vec<&str> = line.split_whitespace().collect();
        if parts.is_empty() {
            continue;
        }
        let dev = parts[0];
        if dev.starts_with("/dev/zram") {
            zram_active = true;
        } else if !dev.is_empty() {
            persistent_active = true;
        }
    }

    (zram_active, persistent_active)
}

/// Parse `/proc/sys/fs/suid_dumpable`.
pub fn parse_suid_dumpable(content: &str) -> bool {
    content.trim() == "0"
}

/// Check if Tor proxy is listening on standard local ports (9050 or 9150).
pub fn is_tor_port_open() -> bool {
    for port in [9050, 9150] {
        if let Ok(stream) = TcpStream::connect_timeout(
            &format!("127.0.0.1:{port}").parse().unwrap(),
            Duration::from_millis(50),
        ) {
            drop(stream);
            return true;
        }
    }
    false
}

/// Locate Tor Browser launcher or standalone executable.
pub fn find_tor_browser(path_override: Option<&str>) -> Option<String> {
    let standard_paths = [
        "/usr/bin/torbrowser-launcher",
        "/usr/bin/tor-browser",
        "/opt/tor-browser/start-tor-browser",
        "/opt/tor-browser/Browser/start-tor-browser",
    ];

    for p in standard_paths {
        if Path::new(p).exists() {
            return Some(p.to_string());
        }
    }

    // Check system PATH
    let paths_str = path_override
        .map(String::from)
        .or_else(|| std::env::var("PATH").ok());

    if let Some(paths) = paths_str {
        for dir in std::env::split_paths(&paths) {
            for bin in ["torbrowser-launcher", "tor-browser"] {
                let candidate = dir.join(bin);
                if candidate.is_file() {
                    return Some(candidate.to_string_lossy().to_string());
                }
            }
        }
    }

    None
}

/// Calculate SHA256 of any file via streaming 1MB buffer.
pub fn sha256_file(path: &Path) -> Result<String> {
    let mut file =
        fs::File::open(path).with_context(|| format!("failed to open {}", path.display()))?;
    let mut hasher = Sha256::new();
    let mut buf = vec![0u8; 1024 * 1024];

    loop {
        let n = file.read(&mut buf)?;
        if n == 0 {
            break;
        }
        hasher.update(&buf[..n]);
    }

    Ok(hasher
        .finalize()
        .iter()
        .map(|b| format!("{b:02x}"))
        .collect())
}

/// Retrieve live privacy status. Reads from optional `root_prefix` (for fixture tests).
pub fn get_privacy_status(root_prefix: Option<&Path>) -> PrivacyStatus {
    let p_root = root_prefix.unwrap_or_else(|| Path::new("/"));

    let mounts_path = p_root.join("proc/mounts");
    let mounts_content = fs::read_to_string(&mounts_path).unwrap_or_default();
    let (ephemeral_overlay, root_fstype, internal_disks_automounted) =
        parse_mounts(&mounts_content);

    let swaps_path = p_root.join("proc/swaps");
    let swaps_content = fs::read_to_string(&swaps_path).unwrap_or_default();
    let (zram_swap_active, persistent_swap_active) = parse_swaps(&swaps_content);

    let suid_path = p_root.join("proc/sys/fs/suid_dumpable");
    let suid_content = fs::read_to_string(&suid_path).unwrap_or_default();
    let suid_dumpable_disabled = parse_suid_dumpable(&suid_content);

    let tor_service_active = is_tor_port_open();
    let tor_browser_path = find_tor_browser(None);
    let tor_browser_installed = tor_browser_path.is_some();

    PrivacyStatus {
        ephemeral_overlay,
        root_fstype,
        persistent_swap_active,
        zram_swap_active,
        suid_dumpable_disabled,
        internal_disks_automounted,
        tor_service_active,
        tor_browser_installed,
        tor_browser_path,
        disclaimer: MANDATORY_DISCLAIMER.to_string(),
    }
}

/// Retrieve Tor subsystem status.
pub fn get_tor_status() -> TorStatus {
    let service_active = is_tor_port_open();
    let tor_browser_path = find_tor_browser(None);
    let browser_installed = tor_browser_path.is_some();

    let notice = if !browser_installed {
        "Tor Browser is not installed. `hscl privacy tor launch` will refuse to start anything else; HSCL1 does NOT block direct browsing or filter egress."
    } else if !service_active {
        "Tor service/proxy is not detected on ports 9050/9150. Tor Browser will start its own embedded tor process upon launch."
    } else {
        "Tor service is active and Tor Browser is available."
    };

    TorStatus {
        service_active,
        browser_installed,
        browser_path: tor_browser_path,
        tor_launch_requires_browser: true,
        notice: notice.to_string(),
    }
}

/// Launch Tor Browser only. Without Tor Browser this refuses instead of substituting another browser; it does
/// not and cannot stop the user from browsing directly, because no egress filtering exists.
pub fn tor_launch(dry_run: bool) -> Result<String> {
    let browser_bin = find_tor_browser(None).ok_or_else(|| {
        anyhow::anyhow!(
            "Tor Browser is not installed. `hscl privacy tor launch` refuses to start a different browser; this is a launcher rule, not a network policy - HSCL1 does not block direct browsing or filter egress. Install torbrowser-launcher or configure Tor Browser."
        )
    })?;

    if dry_run {
        return Ok(format!("[dry-run] Would execute: {browser_bin}"));
    }

    std::process::Command::new(&browser_bin)
        .spawn()
        .with_context(|| format!("failed to launch {browser_bin}"))?;

    Ok(format!("Launched {browser_bin}"))
}

/// Verify an official Tails ISO image file.
pub fn verify_tails_iso(image: &Path, expected_sha256: Option<&str>) -> Result<TailsVerifyReport> {
    if !image.is_file() {
        bail!("Tails image file does not exist: {}", image.display());
    }

    let metadata =
        fs::metadata(image).with_context(|| format!("failed to inspect {}", image.display()))?;
    let size_bytes = metadata.len();
    if size_bytes < 1024 * 1024 * 100 {
        bail!(
            "File {} is too small for a Tails ISO ({size_bytes} bytes)",
            image.display()
        );
    }

    let calculated_sha256 = sha256_file(image)?;
    let verified = match expected_sha256 {
        Some(exp) => calculated_sha256.eq_ignore_ascii_case(exp.trim()),
        None => true,
    };

    if let Some(exp) = expected_sha256 {
        if !verified {
            bail!(
                "SHA256 checksum mismatch for {}\n  calculated: {calculated_sha256}\n  expected:   {exp}",
                image.display()
            );
        }
    }

    Ok(TailsVerifyReport {
        image: image.to_path_buf(),
        size_bytes,
        calculated_sha256,
        expected_sha256: expected_sha256.map(str::to_string),
        verified,
        tails_doc_url: TAILS_DOWNLOAD_URL.to_string(),
    })
}

/// Build an isolated QEMU/KVM launch command for an official Tails ISO.
/// Ensures no host drives are attached and volatile guest snapshot mode is used.
pub fn build_tails_qemu_cmd(image: &Path, ram_mb: u32) -> String {
    format!(
        "qemu-system-x86_64 -enable-kvm -m {ram_mb} -cpu host -smp 2 -cdrom \"{}\" -net nic,model=virtio -net user -boot d -snapshot",
        image.display()
    )
}

/// Launch official Tails ISO inside an isolated QEMU VM.
pub fn launch_tails_vm(image: &Path, ram_mb: u32, dry_run: bool) -> Result<TailsLaunchReport> {
    if !image.is_file() {
        bail!("Tails image file does not exist: {}", image.display());
    }

    let cmd_str = build_tails_qemu_cmd(image, ram_mb);
    let notice = "Isolated QEMU virtual machine instance. No host storage partitions or home directories are attached.";

    if dry_run {
        return Ok(TailsLaunchReport {
            image: image.to_path_buf(),
            ram_mb,
            command: cmd_str,
            dry_run: true,
            safety_notice: notice.to_string(),
        });
    }

    let qemu_bin = which_qemu()?;
    let status = std::process::Command::new(qemu_bin)
        .arg("-enable-kvm")
        .arg("-m")
        .arg(ram_mb.to_string())
        .arg("-cpu")
        .arg("host")
        .arg("-smp")
        .arg("2")
        .arg("-cdrom")
        .arg(image)
        .arg("-net")
        .arg("nic,model=virtio")
        .arg("-net")
        .arg("user")
        .arg("-boot")
        .arg("d")
        .arg("-snapshot")
        .status()
        .with_context(|| "failed to execute qemu-system-x86_64")?;

    if !status.success() {
        bail!("QEMU exited with error: {:?}", status.code());
    }

    Ok(TailsLaunchReport {
        image: image.to_path_buf(),
        ram_mb,
        command: cmd_str,
        dry_run: false,
        safety_notice: notice.to_string(),
    })
}

fn which_qemu() -> Result<String> {
    for candidate in ["qemu-system-x86_64", "qemu-system-x86_64.exe"] {
        if let Ok(paths) = std::env::var("PATH") {
            for dir in std::env::split_paths(&paths) {
                let bin = dir.join(candidate);
                if bin.is_file() {
                    return Ok(bin.to_string_lossy().to_string());
                }
            }
        }
    }
    bail!(
        "qemu-system-x86_64 not found in PATH. Install qemu-system-x86 to launch virtual machines."
    )
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::io::Write;

    #[test]
    fn test_parse_mounts_ephemeral_overlay() {
        let sample = "\
/cow / overlay rw,relatime,lowerdir=/rofs,upperdir=/cow/upper,workdir=/cow/work 0 0
proc /proc proc rw,nosuid,nodev,noexec,relatime 0 0
sysfs /sys sysfs rw,nosuid,nodev,noexec,relatime 0 0
";
        let (ephemeral, root_fs, disks) = parse_mounts(sample);
        assert!(ephemeral);
        assert_eq!(root_fs, "overlay");
        assert!(disks.is_empty());
    }

    #[test]
    fn test_parse_mounts_persistent_ext4_with_automount() {
        let sample = "\
/dev/nvme0n1p2 / ext4 rw,relatime,errors=remount-ro 0 0
/dev/sda1 /media/user/Backup ext4 rw,nosuid,nodev,relatime 0 0
";
        let (ephemeral, root_fs, disks) = parse_mounts(sample);
        assert!(!ephemeral);
        assert_eq!(root_fs, "ext4");
        assert_eq!(disks.len(), 1);
        assert!(disks[0].contains("/dev/sda1 on /media/user/Backup"));
    }

    #[test]
    fn test_parse_swaps_zram_vs_disk() {
        let zram_only = "\
Filename				Type		Size		Used		Priority
/dev/zram0                              partition	4194300		0		100
";
        let (zram, persistent) = parse_swaps(zram_only);
        assert!(zram);
        assert!(!persistent);

        let with_disk = "\
Filename				Type		Size		Used		Priority
/dev/zram0                              partition	4194300		0		100
/dev/nvme0n1p3                          partition	8388604		0		-2
";
        let (zram2, persistent2) = parse_swaps(with_disk);
        assert!(zram2);
        assert!(persistent2);
    }

    #[test]
    fn test_parse_suid_dumpable() {
        assert!(parse_suid_dumpable("0\n"));
        assert!(parse_suid_dumpable("0"));
        assert!(!parse_suid_dumpable("1\n"));
        assert!(!parse_suid_dumpable("2\n"));
    }

    #[test]
    fn test_disclaimer_honesty() {
        assert!(MANDATORY_DISCLAIMER.contains("NOT Tails"));
        assert!(MANDATORY_DISCLAIMER.contains("no claim of absolute anonymity"));
        assert!(MANDATORY_DISCLAIMER.contains("forensic invisibility"));
    }

    #[test]
    fn test_sha256_file_and_tails_verify() {
        let dir = tempfile::tempdir().unwrap();
        let file_path = dir.path().join("tails-test.iso");

        // Write 101 MB dummy file so it exceeds the min-size check
        let mut file = fs::File::create(&file_path).unwrap();
        let chunk = vec![0x42u8; 1024 * 1024];
        for _ in 0..101 {
            file.write_all(&chunk).unwrap();
        }
        drop(file);

        let sha = sha256_file(&file_path).unwrap();
        assert_eq!(sha.len(), 64);

        // Verification with matching hash
        let report = verify_tails_iso(&file_path, Some(&sha)).unwrap();
        assert!(report.verified);
        assert_eq!(report.calculated_sha256, sha);

        // Verification with wrong hash must fail
        assert!(verify_tails_iso(
            &file_path,
            Some("0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef")
        )
        .is_err());
    }

    #[test]
    fn test_build_tails_qemu_cmd() {
        let p = Path::new("/tmp/tails.iso");
        let cmd = build_tails_qemu_cmd(p, 4096);
        assert!(cmd.contains("qemu-system-x86_64"));
        assert!(cmd.contains("-m 4096"));
        assert!(cmd.contains("-snapshot"));
        assert!(cmd.contains("/tmp/tails.iso"));
        assert!(!cmd.contains("-hda"));
    }

    #[test]
    fn test_tor_launch_refuses_without_a_browser() {
        let res = tor_launch(true);
        // Without torbrowser-launcher the launcher must refuse rather than substitute another browser
        if find_tor_browser(None).is_none() {
            assert!(res.is_err());
            let err_msg = format!("{:#}", res.unwrap_err());
            assert!(err_msg.contains("refuses to start a different browser"));
            assert!(err_msg.contains("does not block direct browsing"), "the error must not imply egress filtering");
        }
    }
}
