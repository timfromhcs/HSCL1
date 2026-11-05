# HSCL1 Build Log

> Made with love by hcsmedia. Status vocabulary: PLANNED, IMPLEMENTED, TESTED, VM-VERIFIED,
> HARDWARE-VERIFIED, EXPERIMENTAL, BLOCKED. A status is never upgraded without evidence.

## Phase 0 - Reconnaissance (2026-11-05)

### Repository state
- `E:\hcslinux222` contained only `AGENTS.md` (not a git repository). Initialised locally on branch
  `codex/hscl1-v1` (default branch name `main`). No remote configured.
- GitHub account `timfromhcs` (gh authenticated, token scopes include `repo`, `workflow`). Repository
  `timfromhcs/HSCL1` does **not exist**. A different, unrelated public repository `timfromhcs/hcs-linux`
  ("AI-Native, Local-First, Privacy-Oriented Linux Distribution") exists and was **not touched**.
- Creating `HSCL1` needs the owner's visibility decision (AGENTS.md 17.1) -> BLOCKED until answered; work
  continues locally.
- Licence: none chosen by the owner -> BLOCKED for public release (AGENTS.md 19). `LICENSE` is intentionally absent.
- Vercel CLI authenticated as `timfromhcs`. No HSCL1 project exists yet.

### Build host
| Item | Value |
|---|---|
| Host OS | Windows 11 Pro 10.0.26200 (x86_64), AMD Ryzen 7 7735HS (8C/16T), ~21 GB RAM (per Win32), Radeon 680M |
| Builder | WSL2 distro `Ubuntu` = Ubuntu 26.04.1 LTS, 16 threads, 15 GB RAM, ~890 GB free, passwordless sudo |
| `/dev/kvm` in WSL | **absent** (no nested virt exposed) -> QEMU in WSL would use TCG (slow) |
| Windows virtualization | firmware virtualization enabled; hypervisor platform active (WSL2 runs). Windows-native QEMU with WHPX is the candidate for fast VM tests |
| Tools present (WSL) | xorriso, mksquashfs, debootstrap, cargo/rustc 1.99.1, python3, node, git, 7z |
| Tools installed this phase | qemu-system-x86, qemu-utils, ovmf, shellcheck, shfmt, mtools, swtpm, jq |
| Host tools (Windows) | git, gh, node 22, cargo, python 3.14, docker, vercel CLI |

### Upstream base
- `https://cdimage.ubuntu.com/kubuntu/releases/26.04/release/` offers `kubuntu-26.04.1-desktop-amd64.iso`.
  SHA256 from upstream `SHA256SUMS`: `831e4d4bb85098339ba43d3502cd6619b27e76daf37246a084cd68a6413090b8`.
  The download is checksum-verified and the `SHA256SUMS.gpg` signature checked by `scripts/fetch-base-iso.sh`.

### Pipeline decision (provisional, to be confirmed by the Phase 2 PoC)
Scripted remaster of the official Kubuntu 26.04.1 ISO (`xorriso` + `squashfs-tools`, boot structure replayed from the
original El Torito/GPT metadata via `xorriso -report_el_torito as_mkisofs`), because it preserves the signed
shim/GRUB/kernel boot chain and the upstream installer. `livecd-rootfs` from-scratch builds and Debian `live-build`
are fallbacks only. Decision becomes final only after the PoC boots.

## Phase 5 (early slice) - `hscl` CLI foundation
- Rust workspace `cli/hscl`: `version`, `about`, `status`, `system info`, `security status`, `ai detect`, `doctor`.
- `cargo fmt`, `cargo clippy -D warnings`: clean. `cargo test`: 10/10 pass. Status: **TESTED** (unit) and executed
  on Ubuntu 26.04.1 in WSL: `doctor` correctly reports AppArmor disabled (WSL kernel) -> exit code 3.
- Not yet VM-verified on an installed HSCL1 system.

## Phase 2 - Image pipeline PoC (2026-11-05) - status: VM-VERIFIED (UEFI, BIOS, Secure-Boot firmware boot)
Pipeline: `scripts/remaster-iso.sh --fast` (xorriso + squashfs, zstd-fast) on the WSL builder; ISO copied to
`artifacts/iso/HSCL1-poc-fast.iso` (5,491,654,656 bytes; ignored by git). Boot tests run on **Windows-native QEMU 11.1
with WHPX** (`scripts/qemu_boot_test.py`; WSL has no /dev/kvm, TCG needs >5 min per boot).

| Test | Result | Evidence (`artifacts/`, not in git) |
|---|---|---|
| UEFI (edk2), 4 GB / 4 vCPU, WHPX | live Plasma desktop with HSCL1 Midnight wallpaper in 137 s, wallpaper match 0.996 | `boot-whpx-2/desktop-final.png`, `result.json` |
| Legacy BIOS (SeaBIOS) | same, 137 s | `boot-whpx-bios/` |
| Installer launch (no disk attached) | Calamares (Kubuntu 26.04 branding) starts; refuses to continue: "no partitions to install on" - expected, nothing written | `boot-whpx-inst2/installer-6.png` |
| Secure Boot firmware (OVMF secboot code + MS-key vars, SMM on), TCG | live desktop reached in 688 s (wallpaper match 0.518 with Welcome window open); shim/GRUB/kernel boot under Secure-Boot firmware. **In-guest Secure Boot state (`mokutil --sb-state`) not yet read** -> claim limited to "boots with Secure Boot firmware" | `boot-tcg-sb/` |

Defects found: the first remaster silently did not apply the HSCL1 wallpaper (Kubuntu paths differ from the PoC
assumption). Fixed: hook now patches look-and-feel `defaults`, layout JS and `kscreenlockerrc` and fails if < 4 files change
(patched 5). Residual Kubuntu branding visible: desktop icons "Install Kubuntu"/"Kubuntu Website", Calamares title, Welcome
Center, GRUB/Plymouth/SDDM -> milestones M1/M3/M6.
Harness additions: Windows/WHPX support, TCP QMP, resolution-change safe wallpaper check, `--dismiss-welcome`,
`--launch-installer`.

## Milestone M1 (started) - brand
`scripts/gen_brand.py` generates the original HSCL1 logo family (hexagon mark with "1", outlined wordmark, lockups in
dark/light/mono SVG, PNG sizes, favicon.ico); 6 unit tests pass. Themes HCS Nord and HCS Aurora added; `check-tokens.py`
passes for all 4 themes. APT source policy + test added (`distro/base/apt`, `tests/security`).

## Milestones M1-M4 progress (2026-11-05, same session)
| Item | Status | Evidence |
|---|---|---|
| Logo family (mark, wordmark, lockup, favicon), 4 themes (Midnight, Light, Nord, Aurora) | TESTED (unit) | `tests/unit/test_brand.py`, `check-tokens.py` |
| `hscl-branding` (wallpapers, logos, icon, os-release/issue/About via dpkg-divert, colour schemes) | VM-VERIFIED (UEFI boot) | in-image `verify-image.sh` (all checks pass), `artifacts/boot-whpx-3` |
| `hscl-desktop`: HCS Hybrid Desktop (slim top bar, floating centred dock, default look-and-feel) | VM-VERIFIED (first boot, screenshot) | `artifacts/boot-whpx-3/desktop-final.png` shows top bar with HSCL1 launcher, centred clock, tray and floating dock |
| `hscl-security`: sysctl hardening + first-boot firewall service | TESTED (static/script); not yet VM-verified | `tests/security/*` |
| `hscl-handbook`: EN/DE/FR offline handbook, locale-aware launcher | TESTED; installed in image (verified present) | `tests/unit/test_handbook*.py` |
| `hscl` CLI: `appearance theme list/show/current/set/restore`, `report` | TESTED (19 unit tests) | `cargo test` |
| Control Center (Qt6/QML: Overview, Appearance, Security, About; allow-listed CLI backend; de/fr) | TESTED (C++ + QML tests pass in WSL); not yet seen in a VM | `ctest` 2/2, `tests/unit/test_cc_i18n.py` |
| VM QA channel (`hscl-qa`, virtio port, `qa_report.py`) | IMPLEMENTED + unit-tested; first VM run pending | `tests/unit/test_qa_*.py` |

Known defects after these runs: desktop icons and the installer still show Kubuntu branding; the dock reuses the HSCL1
mark for the handbook icon; Secure Boot state inside the guest not yet read; no physical hardware tested.

## Next safe actions
1. Finish ISO download + verification, run remaster PoC, boot in QEMU (UEFI + BIOS).
2. Design tokens, architecture/threat-model docs, package manifests.
3. Ask owner: repository visibility and licence.
