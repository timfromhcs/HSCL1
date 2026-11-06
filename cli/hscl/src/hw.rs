//! `hscl hw detect`: read-only hardware inventory from sysfs/procfs. No root, no PCI port I/O, no external tool required.
//!
//! Everything takes a `root` directory (normally `/`) so the parsers are tested against fixture trees. Names come from the system's
//! `pci.ids` when present (the PCI ID Repository format is public and documented); without it the numeric IDs are still reported.
//! Idea credit: Ubuntu's `ubuntu-drivers-common` and `hwinfo` map hardware through sysfs `modalias`/class/vendor/device; this module
//! only reimplements the *reading* side, never package selection or installation.

use serde::Serialize;
use std::collections::HashMap;
use std::fs;
use std::path::{Path, PathBuf};

#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize)]
#[serde(rename_all = "snake_case")]
pub enum Kind {
    Gpu,
    Network,
    Storage,
    Audio,
    Usb,
    Bridge,
    Other,
}

#[derive(Debug, Clone, Serialize)]
pub struct Pci {
    pub slot: String,
    pub vendor_id: String,
    pub device_id: String,
    pub class: String,
    pub kind: Kind,
    pub vendor: Option<String>,
    pub device: Option<String>,
    pub driver: Option<String>,
}

#[derive(Debug, Clone, Serialize)]
pub struct Gpu {
    pub slot: String,
    pub vendor_id: String,
    pub device_id: String,
    pub vendor: Option<String>,
    pub device: Option<String>,
    pub driver: Option<String>,
    pub boot_vga: bool,
    pub render_nodes: Vec<String>,
    /// amdgpu only: dedicated VRAM and GTT (system RAM the GPU may map) as reported by the driver. Not combined or inferred.
    pub vram_total_mib: Option<u64>,
    pub gtt_total_mib: Option<u64>,
}

#[derive(Debug, Clone, Serialize, PartialEq, Eq)]
pub struct Firmware {
    /// `uefi` when /sys/firmware/efi exists, else `bios`.
    pub boot: String,
    /// `enabled`, `disabled` or `not_reported` (UEFI without a SecureBoot variable, or BIOS).
    pub secure_boot: String,
    pub setup_mode: Option<bool>,
}

#[derive(Debug, Clone, Serialize)]
pub struct Cpu {
    pub model: Option<String>,
    pub threads: usize,
    /// Subset of interesting feature flags that are present.
    pub features: Vec<String>,
}

#[derive(Debug, Clone, Serialize)]
pub struct Report {
    pub pci: Vec<Pci>,
    pub gpus: Vec<Gpu>,
    pub cpu: Cpu,
    pub memory_total_mib: Option<u64>,
    pub firmware: Firmware,
    pub names_from_pci_ids: bool,
}

const FEATURES: &[&str] = &[
    "sse4_2",
    "avx",
    "avx2",
    "fma",
    "avx512f",
    "avx512_vnni",
    "amx_tile",
];
const EFI_GLOBAL: &str = "8be4df61-93ca-11d2-aa0d-00e098032b8c";

pub fn classify(class: u32) -> Kind {
    match class >> 8 {
        0x0300 | 0x0302 | 0x0380 => Kind::Gpu,
        0x0200..=0x02ff => Kind::Network,
        0x0100..=0x01ff => Kind::Storage,
        0x0401 | 0x0403 => Kind::Audio,
        0x0c03 => Kind::Usb,
        0x0600..=0x06ff => Kind::Bridge,
        _ => Kind::Other,
    }
}

fn read_trim(p: &Path) -> Option<String> {
    fs::read_to_string(p).ok().map(|s| s.trim().to_string())
}

/// Parses `0x8086` style (or bare hex) text.
pub fn parse_hex(s: &str) -> Option<u32> {
    let t = s.trim();
    let t = t
        .strip_prefix("0x")
        .or_else(|| t.strip_prefix("0X"))
        .unwrap_or(t);
    if t.is_empty() || t.len() > 8 {
        return None;
    }
    u32::from_str_radix(t, 16).ok()
}

/// vendor id -> (vendor name, device id -> device name)
pub type PciIds = HashMap<u16, (String, HashMap<u16, String>)>;

/// Minimal parser of the pci.ids format: `vvvv  name` vendor lines, `\tdddd  name` device lines, deeper lines and the `C ` class section ignored.
pub fn parse_pci_ids(text: &str) -> PciIds {
    let mut out: PciIds = HashMap::new();
    let mut cur: Option<u16> = None;
    for line in text.lines() {
        if line.starts_with('#') || line.trim().is_empty() {
            continue;
        }
        if line.starts_with("C ") {
            break; // device class section follows the vendor section
        }
        if let Some(rest) = line.strip_prefix("\t\t") {
            let _ = rest; // subsystem lines: not used
            continue;
        }
        if let Some(rest) = line.strip_prefix('\t') {
            if let (Some(v), Some((id, name))) = (cur, rest.split_once("  ")) {
                if let Ok(d) = u16::from_str_radix(id.trim(), 16) {
                    if let Some(e) = out.get_mut(&v) {
                        e.1.insert(d, name.trim().to_string());
                    }
                }
            }
            continue;
        }
        if let Some((id, name)) = line.split_once("  ") {
            if id.len() == 4 {
                if let Ok(v) = u16::from_str_radix(id, 16) {
                    out.insert(v, (name.trim().to_string(), HashMap::new()));
                    cur = Some(v);
                    continue;
                }
            }
        }
        cur = None;
    }
    out
}

fn load_pci_ids(root: &Path) -> Option<PciIds> {
    for rel in [
        "usr/share/hwdata/pci.ids",
        "usr/share/misc/pci.ids",
        "usr/share/pci.ids",
    ] {
        if let Ok(t) = fs::read_to_string(root.join(rel)) {
            let ids = parse_pci_ids(&t);
            if !ids.is_empty() {
                return Some(ids);
            }
        }
    }
    None
}

fn driver_of(dev: &Path) -> Option<String> {
    fs::read_link(dev.join("driver"))
        .ok()
        .and_then(|p| p.file_name().map(|n| n.to_string_lossy().to_string()))
}

pub fn pci_devices(root: &Path, ids: Option<&PciIds>) -> Vec<Pci> {
    let dir = root.join("sys/bus/pci/devices");
    let mut v = Vec::new();
    let Ok(rd) = fs::read_dir(&dir) else { return v };
    for e in rd.flatten() {
        let p = e.path();
        let slot = e.file_name().to_string_lossy().to_string();
        let (Some(ven), Some(dev), Some(cls)) = (
            read_trim(&p.join("vendor")).and_then(|s| parse_hex(&s)),
            read_trim(&p.join("device")).and_then(|s| parse_hex(&s)),
            read_trim(&p.join("class")).and_then(|s| parse_hex(&s)),
        ) else {
            continue;
        };
        let (vendor, device) = match (ids, u16::try_from(ven).ok()) {
            (Some(ids), Some(vk)) => match ids.get(&vk) {
                Some((vn, devs)) => (
                    Some(vn.clone()),
                    u16::try_from(dev).ok().and_then(|d| devs.get(&d).cloned()),
                ),
                None => (None, None),
            },
            _ => (None, None),
        };
        v.push(Pci {
            slot,
            vendor_id: format!("{ven:04x}"),
            device_id: format!("{dev:04x}"),
            class: format!("{cls:06x}"),
            kind: classify(cls),
            vendor,
            device,
            driver: driver_of(&p),
        });
    }
    v.sort_by(|a, b| a.slot.cmp(&b.slot));
    v
}

fn mib(p: &Path) -> Option<u64> {
    read_trim(p)
        .and_then(|s| s.parse::<u64>().ok())
        .map(|b| b / (1024 * 1024))
}

pub fn gpus(root: &Path, pci: &[Pci]) -> Vec<Gpu> {
    pci.iter()
        .filter(|d| d.kind == Kind::Gpu)
        .map(|d| {
            let dev = root.join("sys/bus/pci/devices").join(&d.slot);
            let mut render_nodes: Vec<String> = fs::read_dir(dev.join("drm"))
                .map(|rd| {
                    rd.flatten()
                        .map(|e| e.file_name().to_string_lossy().to_string())
                        .filter(|n| n.starts_with("renderD"))
                        .collect()
                })
                .unwrap_or_default();
            render_nodes.sort();
            Gpu {
                slot: d.slot.clone(),
                vendor_id: d.vendor_id.clone(),
                device_id: d.device_id.clone(),
                vendor: d.vendor.clone(),
                device: d.device.clone(),
                driver: d.driver.clone(),
                boot_vga: read_trim(&dev.join("boot_vga")).as_deref() == Some("1"),
                render_nodes,
                vram_total_mib: mib(&dev.join("mem_info_vram_total")),
                gtt_total_mib: mib(&dev.join("mem_info_gtt_total")),
            }
        })
        .collect()
}

pub fn firmware(root: &Path) -> Firmware {
    let efi = root.join("sys/firmware/efi");
    if !efi.is_dir() {
        return Firmware {
            boot: "bios".into(),
            secure_boot: "not_reported".into(),
            setup_mode: None,
        };
    }
    let var = |name: &str| -> Option<bool> {
        let b = fs::read(efi.join("efivars").join(format!("{name}-{EFI_GLOBAL}"))).ok()?;
        (b.len() >= 5).then(|| b[b.len() - 1] != 0) // 4 attribute bytes, then the value
    };
    Firmware {
        boot: "uefi".into(),
        secure_boot: match var("SecureBoot") {
            Some(true) => "enabled",
            Some(false) => "disabled",
            None => "not_reported",
        }
        .into(),
        setup_mode: var("SetupMode"),
    }
}

pub fn cpu(cpuinfo: &str) -> Cpu {
    let mut model = None;
    let mut threads = 0;
    let mut flags: Vec<&str> = Vec::new();
    for l in cpuinfo.lines() {
        if let Some((k, v)) = l.split_once(':') {
            match k.trim() {
                "processor" => threads += 1,
                "model name" if model.is_none() => model = Some(v.trim().to_string()),
                "flags" if flags.is_empty() => flags = v.split_whitespace().collect(),
                _ => {}
            }
        }
    }
    Cpu {
        model,
        threads,
        features: FEATURES
            .iter()
            .filter(|f| flags.contains(f))
            .map(|f| f.to_string())
            .collect(),
    }
}

pub fn mem_total_mib(meminfo: &str) -> Option<u64> {
    meminfo
        .lines()
        .find_map(|l| l.strip_prefix("MemTotal:"))
        .and_then(|r| r.split_whitespace().next())
        .and_then(|n| n.parse::<u64>().ok())
        .map(|kb| kb / 1024)
}

pub fn detect(root: &Path) -> Report {
    let ids = load_pci_ids(root);
    let pci = pci_devices(root, ids.as_ref());
    let gpus = gpus(root, &pci);
    Report {
        gpus,
        pci,
        cpu: cpu(&fs::read_to_string(root.join("proc/cpuinfo")).unwrap_or_default()),
        memory_total_mib: mem_total_mib(
            &fs::read_to_string(root.join("proc/meminfo")).unwrap_or_default(),
        ),
        firmware: firmware(root),
        names_from_pci_ids: ids.is_some(),
    }
}

pub fn render(r: &Report) -> String {
    let mut s = String::new();
    s.push_str(&format!(
        "CPU: {} ({} threads; {})\n",
        r.cpu.model.as_deref().unwrap_or("unknown"),
        r.cpu.threads,
        if r.cpu.features.is_empty() {
            "no notable features".to_string()
        } else {
            r.cpu.features.join(" ")
        }
    ));
    s.push_str(&format!(
        "Memory: {}\n",
        r.memory_total_mib
            .map(|m| format!("{m} MiB"))
            .unwrap_or_else(|| "unknown".into())
    ));
    s.push_str(&format!(
        "Firmware: {}, Secure Boot {}\n",
        r.firmware.boot, r.firmware.secure_boot
    ));
    if r.gpus.is_empty() {
        s.push_str("GPU: none found on the PCI bus\n");
    }
    for g in &r.gpus {
        s.push_str(&format!(
            "GPU {}: {} {} [{}:{}] driver {}{}{}{}\n",
            g.slot,
            g.vendor.as_deref().unwrap_or("?"),
            g.device.as_deref().unwrap_or("?"),
            g.vendor_id,
            g.device_id,
            g.driver.as_deref().unwrap_or("none"),
            if g.boot_vga { ", boot display" } else { "" },
            g.vram_total_mib
                .map(|m| format!(", VRAM {m} MiB"))
                .unwrap_or_default(),
            g.gtt_total_mib
                .map(|m| format!(", GTT {m} MiB (system RAM the GPU may map)"))
                .unwrap_or_default()
        ));
    }
    let count = |k: Kind| r.pci.iter().filter(|d| d.kind == k).count();
    s.push_str(&format!(
        "PCI: {} devices ({} network, {} storage, {} audio, {} USB controllers)\n",
        r.pci.len(),
        count(Kind::Network),
        count(Kind::Storage),
        count(Kind::Audio),
        count(Kind::Usb)
    ));
    if !r.names_from_pci_ids {
        s.push_str("(pci.ids not found: devices are shown by numeric ID)\n");
    }
    s
}

#[allow(dead_code)]
pub fn default_root() -> PathBuf {
    PathBuf::from("/")
}

#[cfg(test)]
mod tests {
    use super::*;

    fn write(root: &Path, rel: &str, content: &str) {
        let p = root.join(rel);
        fs::create_dir_all(p.parent().unwrap()).unwrap();
        fs::write(p, content).unwrap();
    }

    /// Windows forbids ':' in directory names; the code under test does not care what the slot string looks like.
    fn s(slot: &str) -> String {
        if cfg!(windows) {
            slot.replace(':', "_")
        } else {
            slot.to_string()
        }
    }

    fn pci(root: &Path, slot: &str, ven: &str, dev: &str, class: &str) {
        let b = format!("sys/bus/pci/devices/{}", s(slot));
        write(root, &format!("{b}/vendor"), &format!("{ven}\n"));
        write(root, &format!("{b}/device"), &format!("{dev}\n"));
        write(root, &format!("{b}/class"), &format!("{class}\n"));
    }

    const IDS: &str = "# comment\n1002  Advanced Micro Devices, Inc. [AMD/ATI]\n\t1681  Rembrandt [Radeon 680M]\n\t\t17aa 3801  subsystem line\n10de  NVIDIA Corporation\n\t2684  AD102 [GeForce RTX 4090]\n8086  Intel Corporation\n\t46a6  Alder Lake-P GT2 [Iris Xe Graphics]\nC 03  Display controller\n\t00  VGA compatible controller\n";

    #[test]
    fn pci_ids_parser_reads_vendors_devices_and_stops_at_classes() {
        let ids = parse_pci_ids(IDS);
        assert_eq!(ids[&0x1002].0, "Advanced Micro Devices, Inc. [AMD/ATI]");
        assert_eq!(ids[&0x1002].1[&0x1681], "Rembrandt [Radeon 680M]");
        assert_eq!(ids[&0x10de].1[&0x2684], "AD102 [GeForce RTX 4090]");
        assert_eq!(ids.len(), 3, "the class section must not create vendors");
        assert!(
            parse_pci_ids("").is_empty() && parse_pci_ids("garbage\n\t\t\n\txx  y\n").is_empty()
        );
    }

    #[test]
    fn classes_map_to_kinds() {
        assert_eq!(classify(0x030000), Kind::Gpu);
        assert_eq!(classify(0x030200), Kind::Gpu);
        assert_eq!(classify(0x020000), Kind::Network);
        assert_eq!(classify(0x010802), Kind::Storage);
        assert_eq!(classify(0x040300), Kind::Audio);
        assert_eq!(classify(0x0c0330), Kind::Usb);
        assert_eq!(classify(0x060400), Kind::Bridge);
        assert_eq!(classify(0x118000), Kind::Other);
    }

    #[test]
    fn hex_parsing_is_strict() {
        assert_eq!(parse_hex("0x8086\n"), Some(0x8086));
        assert_eq!(parse_hex("8086"), Some(0x8086));
        for bad in ["", "0x", "zz", "0x123456789", " "] {
            assert_eq!(parse_hex(bad), None, "{bad:?}");
        }
    }

    #[test]
    fn amd_apu_fixture_reports_names_memory_and_render_node() {
        let td = tempfile::tempdir().unwrap();
        let r = td.path();
        write(r, "usr/share/misc/pci.ids", IDS);
        pci(r, "0000:06:00.0", "0x1002", "0x1681", "0x030000");
        let d = &format!("sys/bus/pci/devices/{}", s("0000:06:00.0"));
        write(r, &format!("{d}/boot_vga"), "1\n");
        write(
            r,
            &format!("{d}/mem_info_vram_total"),
            &format!("{}\n", 512u64 * 1024 * 1024),
        );
        write(
            r,
            &format!("{d}/mem_info_gtt_total"),
            &format!("{}\n", 16384u64 * 1024 * 1024),
        );
        fs::create_dir_all(r.join(d).join("drm/renderD128")).unwrap();
        fs::create_dir_all(r.join(d).join("drm/card0")).unwrap();
        pci(r, "0000:00:1f.3", "0x8086", "0x51c8", "0x040300");
        write(r, "proc/cpuinfo", "processor\t: 0\nmodel name\t: AMD Ryzen 7 7735HS\nflags\t: fpu sse4_2 avx avx2 fma\nprocessor\t: 1\nmodel name\t: AMD Ryzen 7 7735HS\n");
        write(
            r,
            "proc/meminfo",
            "MemTotal:       24576000 kB\nMemFree: 1 kB\n",
        );
        let rep = detect(r);
        assert!(rep.names_from_pci_ids);
        assert_eq!(rep.gpus.len(), 1);
        let g = &rep.gpus[0];
        assert_eq!(g.device.as_deref(), Some("Rembrandt [Radeon 680M]"));
        assert!(g.boot_vga);
        assert_eq!(g.render_nodes, ["renderD128"]);
        assert_eq!(
            (g.vram_total_mib, g.gtt_total_mib),
            (Some(512), Some(16384))
        );
        assert_eq!(rep.pci.iter().filter(|p| p.kind == Kind::Audio).count(), 1);
        assert_eq!(rep.cpu.threads, 2);
        assert_eq!(rep.cpu.features, ["sse4_2", "avx", "avx2", "fma"]);
        assert_eq!(rep.memory_total_mib, Some(24000));
        let text = render(&rep);
        assert!(
            text.contains("Radeon 680M")
                && text.contains("VRAM 512 MiB")
                && text.contains("GTT 16384 MiB")
        );
    }

    #[test]
    fn works_without_pci_ids_and_without_any_gpu() {
        let td = tempfile::tempdir().unwrap();
        pci(td.path(), "0000:00:02.0", "0x8086", "0x46a6", "0x030000");
        let rep = detect(td.path());
        assert!(!rep.names_from_pci_ids);
        assert_eq!(rep.gpus[0].vendor_id, "8086");
        assert!(rep.gpus[0].vendor.is_none() && rep.gpus[0].vram_total_mib.is_none());
        assert!(render(&rep).contains("numeric ID"));
        let empty = tempfile::tempdir().unwrap();
        let rep = detect(empty.path());
        assert!(
            rep.pci.is_empty()
                && rep.gpus.is_empty()
                && rep.cpu.threads == 0
                && rep.memory_total_mib.is_none()
        );
        assert!(render(&rep).contains("none found"));
    }

    #[test]
    fn secure_boot_states_from_efi_variables() {
        let td = tempfile::tempdir().unwrap();
        let r = td.path();
        assert_eq!(
            firmware(r),
            Firmware {
                boot: "bios".into(),
                secure_boot: "not_reported".into(),
                setup_mode: None
            }
        );
        fs::create_dir_all(r.join("sys/firmware/efi/efivars")).unwrap();
        assert_eq!(
            firmware(r).secure_boot,
            "not_reported",
            "UEFI without the variable (e.g. OVMF without Secure Boot)"
        );
        let var = |name: &str, v: u8| {
            fs::write(
                r.join(format!("sys/firmware/efi/efivars/{name}-{EFI_GLOBAL}")),
                [6u8, 0, 0, 0, v],
            )
            .unwrap()
        };
        var("SecureBoot", 1);
        var("SetupMode", 0);
        let f = firmware(r);
        assert_eq!(
            (f.boot.as_str(), f.secure_boot.as_str(), f.setup_mode),
            ("uefi", "enabled", Some(false))
        );
        var("SecureBoot", 0);
        assert_eq!(firmware(r).secure_boot, "disabled");
        fs::write(
            r.join(format!("sys/firmware/efi/efivars/SecureBoot-{EFI_GLOBAL}")),
            [1u8, 2],
        )
        .unwrap(); // truncated
        assert_eq!(firmware(r).secure_boot, "not_reported");
    }

    #[cfg(unix)]
    #[test]
    fn driver_is_the_symlink_target_name() {
        let td = tempfile::tempdir().unwrap();
        let r = td.path();
        pci(r, "0000:00:02.0", "0x1234", "0x1111", "0x030000");
        std::os::unix::fs::symlink(
            "../../../bus/pci/drivers/bochs-drm",
            r.join("sys/bus/pci/devices/0000:00:02.0/driver"),
        )
        .unwrap();
        assert_eq!(detect(r).gpus[0].driver.as_deref(), Some("bochs-drm"));
    }

    #[test]
    fn seeded_fuzz_parsers_never_panic() {
        let mut seed: u64 = 0xfeed_beef_1234_5678;
        let mut next = move || {
            seed ^= seed << 13;
            seed ^= seed >> 7;
            seed ^= seed << 17;
            seed
        };
        let alphabet: Vec<char> = "0123456789abcdefABCDEFxX \t\n#C:[]-_/zZ\u{e4}"
            .chars()
            .collect();
        for _ in 0..5000 {
            let n = (next() % 120) as usize;
            let s: String = (0..n)
                .map(|_| alphabet[(next() % alphabet.len() as u64) as usize])
                .collect();
            let _ = parse_pci_ids(&s);
            let _ = parse_hex(&s);
            let _ = cpu(&s);
            let _ = mem_total_mib(&s);
        }
    }
}
