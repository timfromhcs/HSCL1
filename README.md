<div align="center">

# HSCL1

**HSCL1 = Hypercharged Supreme Computing Layout 1**

### *One system. Three modes. Your machine, your rules.*

*Made with love by hcsmedia* · Publisher: HCSMEDIA

[![CI](https://github.com/timfromhcs/HSCL1/actions/workflows/ci.yml/badge.svg)](https://github.com/timfromhcs/HSCL1/actions/workflows/ci.yml)
[![Release](https://img.shields.io/badge/release-0.1.4--alpha.0-blue.svg)](https://github.com/timfromhcs/HSCL1/releases/tag/v0.1.4-alpha.0)
![status](https://img.shields.io/badge/status-pre--alpha-orange)
![licence](https://img.shields.io/badge/licence-GPL--3.0--or--later-blue)
![base](https://img.shields.io/badge/base-Ubuntu%2026.04%20LTS-E95420)
![desktop](https://img.shields.io/badge/desktop-KDE%20Plasma%206.6%20LTS-1D99F3)
![architecture](https://img.shields.io/badge/arch-x86__64%20%2F%20amd64-lightgrey)

<br>

[✨ Features](#-key-features) • [🚀 Quick Start](#-quickstart-try-it-in-qemu) • [📸 Live Showcase](#-live-application-showcase) • [💻 3 Modes](#-three-operating-modes) • [⚡ CLI Reference](#-command-line-interface-hscl) • [🔧 Troubleshooting](#-troubleshooting--vm-tips) • [📦 Download](#-download--verification) • [🛠️ Build From Source](#-build-from-source)

<br>

<img src="docs/img/showcase/01_desktop_clean.png" alt="HSCL1 v0.1.4-alpha.0 Live Desktop (KDE Plasma 6.6 LTS, Top Bar, Dock, Midnight Theme) — real capture from QEMU 9.2.0 with WHPX" width="940">

*HSCL1 v0.1.4-alpha.0 running live in QEMU/WHPX — clean first boot with HCS top status bar, centered floating dock, and Midnight theme.*

</div>

---

## ✨ Why HSCL1?

1. **Cohesive Keyboard-First Ergonomics:** A unified workstation experience combining the speed and aesthetics of Omarchy with the rock-solid hardware stability of Ubuntu 26.04 LTS and KDE Plasma 6.6 LTS. Slim top status bar, centered floating dock, and dynamic GPU/CPU shader-driven wallpapers.
2. **Three Structurally Isolated Modes:** Seamless switching between everyday **Workstation**, isolated **Security Lab** (rootless Podman + official Kali Linux OCI containers), and an ephemeral **Privacy Session** (RAM overlay, unmounted host storage, isolated network routing).
3. **Zero Telemetry & Rigorous Attestation:** Zero analytics, 100% offline documentation in 3 languages (English, German, French), Argon2id full-disk encryption, and an unbending evidence-based contract—every feature is verified by automated VM tests and cryptographic proof.

> [!IMPORTANT]
> **Status: Pre-Alpha (`0.1.4-alpha.0`).**
> HSCL1 is currently verified **in virtual machines only** (UEFI, BIOS, and Secure-Boot firmware via QEMU 9.2.0 with WHPX / KVM acceleration). It has **not** yet been tested on bare-metal physical hardware, and releases are **unsigned** (SHA-256 integrity checksums provided). Read [Known limitations](docs/KNOWN_LIMITATIONS.md) and the [evidence ledger](docs/CLAIMS.md) before installing. Do not use HSCL1 on systems requiring security certifications.

> [!NOTE]
> HSCL1 is **not Tails**, **not an official Kali release**, and is not affiliated with or endorsed by the Tails project, Canonical, the KDE/Kubuntu projects, or Offensive Security. It makes **no anonymity claim**.
> KALI LINUX™ is a trademark of OffSec. Where strong anonymity matters, use the official Tails release. See [Trademarks](docs/TRADEMARKS.md).

---

## 🚀 Quickstart: Try It in QEMU

Test the verified pre-alpha live ISO in a hardware-accelerated disposable virtual machine with a single command:

### Windows (WHPX Acceleration)
```powershell
# Run with 4 GB RAM and dismiss first-run dialogs automatically:
python scripts/qemu_boot_test.py `
  --iso "path\to\HSCL1-0.1.4-alpha.0-amd64.iso" `
  --mem 4096 `
  --dismiss-welcome
```

### Linux (KVM Acceleration)
```bash
# Run with hardware KVM acceleration and UEFI firmware:
qemu-system-x86_64 -enable-kvm -m 4096 -smp 4 \
  -bios /usr/share/ovmf/OVMF.fd \
  -cdrom HSCL1-0.1.4-alpha.0-amd64.iso \
  -vga std -device virtio-net-pci,netdev=net0 \
  -netdev user,id=net0
```

---

## 📸 Live Application Showcase

*Every screenshot below is an authentic, unedited capture taken live inside the booted QEMU virtual machine session using the hypervisor QMP interface and guest Workshop daemon.*

### 1. Modern Desktop & Dynamic Shaders

The HCS desktop features a fluid, shader-driven wallpaper engine switchable on the fly via `hscl wallpaper apply <preset>` or the Control Center.

| Clean Live Desktop & Floating Dock | Kickoff Application Launcher |
|:---:|:---:|
| ![Clean Desktop](docs/img/showcase/01_desktop_clean.png) | ![Kickoff Launcher](docs/img/showcase/03_app_launcher_kickoff.png) |
| **Aurora Glow Shader** | **Grid Pulse Cyber Lattice** |
| ![Aurora Wallpaper](docs/img/showcase/02_wallpaper_aurora.png) | ![Grid Pulse Wallpaper](docs/img/showcase/02_wallpaper_grid.png) |
| **Midnight Rain Shader** | **Starfield Deep Space Drift** |
| ![Midnight Rain Wallpaper](docs/img/showcase/02_wallpaper_rain.png) | ![Starfield Wallpaper](docs/img/showcase/02_wallpaper_starfield.png) |

---

### 2. Native HCS Control Center (Qt 6 / QML)

A zero-telemetry control center providing instant hardware diagnostics, security policy auditing, theme customization, and system identity verification.

| System Overview & Hardware Profiling | Security Baseline & Firewall Policy |
|:---:|:---:|
| ![Control Center Overview](docs/img/showcase/04_control_center_overview.png) | ![Control Center Security](docs/img/showcase/06_control_center_security.png) |
| **Appearance & Desktop Design Tokens** | **System Attestation & Versioning** |
| ![Control Center Appearance](docs/img/showcase/05_control_center_appearance.png) | ![Control Center About](docs/img/showcase/07_control_center_about.png) |

---

### 3. Interactive Terminal & CLI Diagnostics (`hscl`)

Built-in developer terminal with full hardware diagnostic output, redacting health checks, and containerized security lab controls.

| System Status & Diagnostic Doctor (`hscl`) | Isolated Security Lab Suite (`hscl lab`) |
|:---:|:---:|
| ![Terminal Status and Doctor](docs/img/showcase/08_terminal_hscl_status_doctor.png) | ![Terminal Security Lab](docs/img/showcase/09_terminal_hscl_lab.png) |
| **Privacy Posture & Security Baseline (`hscl privacy/security`)** | **Diagnostic Log Redaction & Language (`hscl logs/language`)** |
| ![Privacy and Security](docs/img/showcase/16_terminal_privacy_security.png) | ![Logs and Language](docs/img/showcase/17_terminal_logs_and_diag.png) |

---

### 4. Core Productivity Applications

Familiar window ergonomics, Dolphin file manager with HCS styling, Kate text editor with syntax highlighting, and an offline trilingual documentation handbook.

| Dolphin File Manager (HCS Theme) | Kate Text Editor (`/etc/os-release`) |
|:---:|:---:|
| ![Dolphin File Manager](docs/img/showcase/10_app_dolphin.png) | ![Kate Text Editor](docs/img/showcase/14_app_kate.png) |
| **Trilingual Offline Handbook** | **Post-Session Desktop State** |
| ![Offline Handbook](docs/img/showcase/13_offline_handbook.png) | ![Final Desktop](docs/img/showcase/15_desktop_final.png) |

---

### 5. Verified Encrypted Installation Flow (Calamares + LUKS2)

Automated full-disk encryption with Argon2id key derivation, unencrypted `/boot`, and encrypted root volume, verified end-to-end on disposable virtual disks.

| Calamares Welcome & Language Selection | Timezone & Geographic Location |
|:---:|:---:|
| ![Calamares Welcome](docs/img/showcase/11_installer_welcome.png) | ![Calamares Location](docs/img/showcase/12_installer_location.png) |
| **Full-Disk Encryption Selection** | **Argon2id Boot Passphrase Unlock** |
| ![Calamares Encryption Options](docs/img/install-encrypt.png) | ![Argon2id Disk Unlock Prompt](docs/img/boot-unlock.png) |

---

## 💻 Three Operating Modes

```mermaid
flowchart LR
    subgraph HSCL1["HSCL1 Operating System"]
        direction TB
        A["💻 Workstation Mode<br>Ubuntu 26.04 + KDE 6.6<br>Daily Driver & Coding"]
        B["🛡️ Security Lab<br>Rootless Podman + Kali OCI<br>Curated Tooling & CTF"]
        C["🔒 Privacy Mode<br>Tor Routing + Ephemeral RAM<br>Zero Host Persistence"]
    end
    style HSCL1 fill:#0f172a,stroke:#38bdf8,stroke-width:2px,color:#fff
    style A fill:#1e293b,stroke:#0ea5e9,color:#fff
    style B fill:#1e293b,stroke:#ef4444,color:#fff
    style C fill:#1e293b,stroke:#10b981,color:#fff
```

### A. Workstation (Everyday Daily Driver)
- **Modern Desktop:** KDE Plasma 6.6 LTS with custom HCS top bar and dock.
- **Hardware Autotune:** Dynamic GPU detection and automatic compositing adjustments (`hscl autotune`).
- **Memory Protection:** Automated `earlyoom`, compressed `/dev/zram0` swap, and AI workload RAM budgets.
- **Offline Handbook:** Complete trilingual reference manual accessible directly offline in English, German, and French.

### B. Security Lab (Authorized Testing Only)
- **Isolation by Architecture:** Security and penetration testing tools run strictly in rootless OCI containers (Podman) or disposable VMs—**never** mixed into the host APT repositories.
- **Official Kali Digest:** Image pinned to official Kali Linux rolling digest with verified SHA-256 digests.
- **Mandatory Authorization:** CLI execution requires explicit attestation:
  ```console
  $ hscl lab run --yes="I am authorized to test this target" -- nmap -sV 127.0.0.1
  ```
- **Fail-Closed:** Containers mount no host home directories, credentials, or SSH agents by default.

### C. Privacy (Disposable Sessions)
- **Ephemeral RAM Overlay:** Read-only root filesystem backed by a RAM overlay; all state discarded on shutdown.
- **Disk Isolation:** Host internal drives are unmounted and ignored by default.
- **Tor Integration:** Isolated network routing preventing direct clearnet leaks when privacy mode is engaged.
- **Honest Limitations:** HSCL1 is not Tails. For life-critical anonymity, launch the official signature-verified Tails ISO.

---

## ⚡ Command Line Interface (`hscl`)

The `hscl` tool provides unified control over the workstation, security tooling, memory policies, and local AI workflows:

```console
# System status & diagnostics
$ hscl status                                                      # Hardware, kernel, and memory summary
$ hscl doctor                                                      # Diagnostic health checks (redacted by default)

# Hardware & graphics profiling
$ hscl graphics detect                                             # Identify GPU and recommended visual profile
$ hscl memory status                                               # Inspect RAM, zram, and AI inference headroom

# Dynamic desktop styling
$ hscl wallpaper list                                              # Available wallpaper shader presets
$ hscl wallpaper apply rain                                        # Switch desktop wallpaper immediately

# Security Lab container execution
$ hscl lab run --yes="I am authorized to test this target" -- nmap 127.0.0.1
$ hscl lab install --yes="I am authorized to test this target" --toolset=web

# Local AI profiling
$ hscl ai model recommend                                          # Models fitting the available RAM/VRAM budget

# Model Context Protocol (MCP) server
$ hscl mcp                                                         # Stdio MCP JSON-RPC server (read-only by default)
```

Detailed CLI documentation is available in [`docs/CLI.md`](docs/CLI.md).

---

## 🔧 Troubleshooting & VM Tips

| Issue | Cause | Solution |
|---|---|---|
| **Black screen or sluggish boot** | Hardware acceleration disabled in QEMU | Ensure `-accel whpx,kernel-irqchip=off` (Windows) or `-enable-kvm` (Linux) is active. |
| **Out-of-memory / kernel panic** | Allocating < 3 GB RAM to the VM | The live ISO unpacks a zstd squashfs into RAM overlay; allocate at least **3072 MB** (recommended: **4096 MB**). |
| **Welcome screen doesn't dismiss** | Plasma first-run dialog modal grab | Press `Esc` or click the bottom-left "Skip" button (`(0.288, 0.848)` screen coordinates). |
| **Secure Boot verification failure** | Unsigned test image on third-party UEFI | Use the signed Ubuntu shim/GRUB bootchain or run with standard OVMF firmware (`--firmware uefi`). |
| **Installer cannot find disk** | No virtual disk attached to VM | Pass `--disk <path.qcow2>` to `qemu_boot_test.py` or `-drive file=<disk>,if=virtio` in QEMU. |

---

## 📊 Verification & Showoff Evidence

HSCL1 adheres to a strict evidence-driven development contract: **nothing is claimed as working without recorded cryptographic and automated test proof.**

| Area | Status | Evidence / Verification Metric |
|---|:---:|---|
| **Remastered Live/Installer ISO** | `VM-VERIFIED` | Boots to live desktop in 130 s under UEFI (QEMU+WHPX); Welcome dismissed; [`docs/img/showcase/01_desktop_clean.png`](docs/img/showcase/01_desktop_clean.png) |
| **Secure Boot Firmware Boot** | `VM-VERIFIED` | Boots under OVMF Secure Boot code + Microsoft-key vars; signed shim/GRUB/kernel bootchain preserved |
| **LUKS2 Full-Disk Installation** | `VM-VERIFIED` | 40 GB virtual disk; Argon2id key derivation, `/` = `0:0 755`, no passphrase leak in logs; [`docs/img/desktop-installed.png`](docs/img/desktop-installed.png) |
| **Rust `hscl` CLI Workspace** | `TESTED` | 202 unit tests (Windows) + 209 unit tests (Linux/WSL); 0 failures; `cargo clippy -D warnings` clean |
| **Security Lab CLI** | `TESTED` | `run`, `install`, `commit`, `destroy` subcommands with mandatory `--yes` gate; builder probe verified |
| **MCP Stdio Server Protocol** | `TESTED` | 7/7 protocol tests passed via `scripts/dev/mcp_selftest.py` (JSON-RPC handshake, 14 tools listed) |
| **Memory Manager Baseline** | `VM-VERIFIED` | `/dev/zram0` (1.9 GB zstd, priority 100), `earlyoom` active, `hscl-ai.slice` memory capped at 60% |
| **HCSEASYMATH Symbolic Engine** | `TESTED` | 244 math test cases green; differentiate, integrate, evaluate, simplify, solve, plot |
| **NPBENCH Algorithmic Suite** | `TESTED` | 134 tests green; DIMACS parser, DRAT checker, RUP refutations, WalkSAT, CDCL baseline |
| **Split & Rejoin Integrity** | `TESTED` | 3 parts (<1900 MiB) join byte-identically to whole ISO; verified via `release-join.sh --verify-only` |

*Full evidence log available at [`docs/CLAIMS.md`](docs/CLAIMS.md) and [`docs/BUILD_LOG.md`](docs/BUILD_LOG.md).*

---

## 📦 Download & Verification

Pre-release assets are hosted on [GitHub Releases](https://github.com/timfromhcs/HSCL1/releases). Because the ISO exceeds GitHub's 2 GiB per-file limit, it is distributed in numbered split parts with full cryptographic checksums.

```console
# 1. Download release assets (parts + SHA256SUMS)
$ mkdir hscl1-release && cd hscl1-release
$ gh release download v0.1.4-alpha.0 --repo timfromhcs/HSCL1

# 2. Clone repository to obtain verified join script
$ git clone https://github.com/timfromhcs/HSCL1 ../HSCL1-src

# 3. Verify integrity of all parts against SHA256SUMS (dry-run, writes nothing)
$ bash ../HSCL1-src/scripts/release-join.sh . --verify-only

# 4. Join parts into single bootable ISO
$ bash ../HSCL1-src/scripts/release-join.sh .
```

### Release Checksums (v0.1.4-alpha.0)
```text
bb47493b4191b62cb35cec0b29080ff69fcf41b1f199f20e756cf3fd006cff86  HSCL1-0.1.4-alpha.0-amd64.iso.part000
7c9de4008b55001706661744ce60c2125461c81c18b6b09599be9a982b5a2e35  HSCL1-0.1.4-alpha.0-amd64.iso.part001
e6effefff63bfc0211ddcf64172d255a85405c647360d9c155ed681e1f0ab5f6  HSCL1-0.1.4-alpha.0-amd64.iso.part002
a7e055a7e9192b6007e4295a396bc5d771e3676877943de67fc313e4254d1f6f  HSCL1-0.1.4-alpha.0-amd64.iso
```

> [!TIP]
> A single joined `.iso` file is also created automatically by the GitHub Actions Cloud Verification workflow (`.github/workflows/release.yml`) and retained as an Actions artifact for 90 days.

---

## 🛠️ Build From Source

HSCL1 uses a reproducible remastering and package build pipeline. Detailed requirements and setup guides are in [`docs/BUILDING.md`](docs/BUILDING.md).

```console
# 1. Run local rust test suite
$ cargo fmt --all -- --check
$ cargo clippy --all-targets -- -D warnings
$ cargo test --all

# 2. Run Python & shell validation gates
$ python scripts/forge.py check

# 3. High-performance developer cycle (WSL2 bridge)
$ scripts/dev/wsl-cycle.sh status
$ scripts/dev/wsl-cycle.sh iso --fast
```

---

## 📂 Repository Structure

| Path | Purpose |
|---|---|
| [`cli/hscl`](cli/hscl) | Rust CLI workspace, MCP server, security lab, memory manager, and system diagnostics |
| [`apps/control-center`](apps/control-center) | Qt 6 / QML Control Center with modular diagnostics, security, and appearance pages |
| [`apps/hcseasymath`](apps/hcseasymath) | Isolated symbolic mathematics engine and educational user interface |
| [`packages/debian`](packages/debian) | HSCL1 Debian packages (`base`, `branding`, `desktop`, `security`, `handbook`, `control-center`, `workshop`) |
| [`distro`](distro) | Live image hooks, Calamares installer configuration, initrd customization, and security sysctl |
| [`themes`](themes) | Design tokens (Midnight, Light, Nord, Aurora) and asset generation scripts |
| [`scripts`](scripts) | Remaster pipeline, release split/join, QEMU boot test harness, and developer cycle tools |
| [`handbook`](handbook) | Trilingual offline documentation handbook (English, Deutsch, Français) |
| [`docs`](docs) | Architecture specifications, threat models, claims ledger, and roadmap plans |

---

## 📚 Project Documentation

- [Claims & Evidence Ledger](docs/CLAIMS.md) — Exact status and proof targets for every feature.
- [Known Limitations](docs/KNOWN_LIMITATIONS.md) — Honest disclosure of pre-alpha boundaries and gaps.
- [Architecture Overview](docs/ARCHITECTURE.md) — System layers, packaging, and interaction model.
- [Threat Model & Security](docs/THREAT_MODEL.md) — Security assumptions and container isolation rules.
- [Build Log](docs/BUILD_LOG.md) — Chronological engineering execution and test logs.
- [Roadmap to v1.0.0](docs/superpowers/plans/2026-11-08-selfheal-masterplan.md) — Active self-healing research masterplan.
- [Licenses & Attributions](docs/LICENSES.md) — Upstream component licenses and intellectual property terms.

---

<details>
<summary><b>Deutsch (German)</b></summary>
<br>

**HSCL1 (Hypercharged Supreme Computing Layout 1)** ist eine moderne Linux-Workstation auf Basis von Ubuntu 26.04 LTS (Kubuntu) und KDE Plasma 6.6 LTS mit eigenem Oberflächendesign (schlanke Top-Bar, schwebendes App-Dock, shader-basierte animierte Wallpaper), dem Kommandozeilenwerkzeug `hscl`, einem nativen Qt6/QML Control Center, einem vollständigen Offline-Handbuch (EN/DE/FR), integrierter Speicherverwaltung, lokalen KI- und Coding-Werkzeugen sowie isolierten Security-Lab-Workflows.

**Status: Pre-Alpha (`0.1.4-alpha.0`).** Bislang ausschließlich in virtuellen Maschinen (QEMU mit WHPX/KVM) getestet, nicht auf physischer Hardware. Die Releases sind unverschlüsselt/unsigniert (Integritätssicherung über SHA-256-Prüfsummen). HSCL1 ist weder Tails noch ein offizielles Kali Linux und erhebt keinen universellen Anonymitätsanspruch. Alle verifizierten Fakten und Grenzen sind transparent in [`docs/CLAIMS.md`](docs/CLAIMS.md) und [`docs/KNOWN_LIMITATIONS.md`](docs/KNOWN_LIMITATIONS.md) dokumentiert.

Das ISO-Abbild überschreitet das GitHub-Größenlimit und wird in 3 Split-Parts bereitgestellt, die mit `scripts/release-join.sh` geprüft und zusammengesetzt werden. **Der Installer schreibt auf den ausgewählten Datenträger – bitte ausschließlich disposable virtuelle Disks verwenden.**

</details>

<details>
<summary><b>Français (French)</b></summary>
<br>

**HSCL1 (Hypercharged Supreme Computing Layout 1)** est une station de travail Linux moderne basée sur Ubuntu 26.04 LTS (Kubuntu) et KDE Plasma 6.6 LTS, dotée d'une interface originale (barre supérieure épurée, dock d'applications flottant, fonds d'écran animés dynamiques), de l'outil CLI `hscl`, d'un Centre de contrôle natif en Qt6/QML, d'un manuel hors-ligne trilingue (EN/DE/FR), d'une gestion intelligente de la mémoire et d'un laboratoire de sécurité isolé.

**État : Pré-alpha (`0.1.4-alpha.0`).** Testé exclusivement dans des machines virtuelles (QEMU avec accélération WHPX/KVM), aucun test sur matériel physique réel. Les publications ne sont pas signées cryptographiquement (sommes de contrôle SHA-256 fournies). HSCL1 n'est ni Tails, ni une version officielle de Kali, et ne garantit aucun anonymat absolu. Les preuves et limitations sont détaillées dans [`docs/CLAIMS.md`](docs/CLAIMS.md) et [`docs/KNOWN_LIMITATIONS.md`](docs/KNOWN_LIMITATIONS.md).

L'image ISO dépassant 2 Gio, elle est distribuée sous forme de segments numérotés vérifiables et assemblables via `scripts/release-join.sh`. **L'installateur applique les changements sur le disque sélectionné – utilisez uniquement des disques virtuels jetables.**

</details>

---

## 🤝 Contributing & Security

Please read [`CONTRIBUTING.md`](CONTRIBUTING.md) and [`CODE_OF_CONDUCT.md`](CODE_OF_CONDUCT.md) before submitting contributions.
Security vulnerabilities must be reported privately according to our [`SECURITY.md`](SECURITY.md) vulnerability disclosure process.

## 📄 Licence

**GPL-3.0-or-later** for HSCL1-owned code, artwork, and documentation ([`LICENSE`](LICENSE), [`NOTICE`](NOTICE)).
Third-party components, including the Ubuntu/Kubuntu foundation, retain their respective upstream licenses ([`docs/LICENSES.md`](docs/LICENSES.md)).
Trademarks belong to their respective owners.
