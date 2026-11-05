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

## Install verification (2026-11-05) - status: VM-VERIFIED (test install, QA ISO)
Run: `scripts/qemu_boot_test.py` + `tests/visual/scenarios/install-normal.json` on Windows QEMU 11.1 / WHPX, UEFI,
4 GB / 4 vCPU, one 40 GB virtio qcow2 (disposable, `artifacts/install-test/`, not in git, contains a throw-away test user).

| Step | Result | Evidence |
|---|---|---|
| Installer start | Calamares with HSCL1 branding (title "Welcome to the HSCL1 0.1.0-alpha.0 installer", HSCL1 logo, sidebar, support link) | `artifacts/inst-explore/ex-welcome.png` |
| Disk selection | single disk `vda` 40 GiB; **no option preselected** (erase had to be chosen explicitly) | `ex-partitions.png` |
| Summary before writing | "Erase disk /dev/vda": GPT, 300 MiB FAT32 EFI, 39.71 GiB ext4 | `install-test/i08-summary.png` |
| Install | completed, "All done. HSCL1 0.1.0-alpha.0 has been installed"; disk idle afterwards; 1359 s total run | `install-test/i12-before-finish.png`, `result.json` |
| Boot from the installed disk only (no ISO) | login screen with the created user, login succeeds, HCS desktop | `install-boot/` |
| Guest report (installed system) | os-release HSCL1, hscl status/doctor JSON valid, kernel.kptr_restrict=2, firewall active (deny in / allow out), no failed hscl units, desktop session running | `install-boot/guest-report.txt`, `qa_report.py` |
| Control Center on the installed system | shows live values: OS, kernel 7.0.0-30-generic, AppArmor yes, firewall yes, health 5 passed / 0 failed | `install-boot/cc-overview.png` |

Defects found by this run and fixed in the source: Control Center pages never received the backend (self-binding), shared
dock icon, Kubuntu filesystem labels (`kubuntu_2604` -> `hscl1_root`), Kubuntu SDDM theme and avatar (derived `hscl1`
SDDM theme, HSCL1 default avatar), slideshow advertised an unbound shortcut, welcome image contrast, a first run cut off at
85 % because the screen went idle (harness now keeps the guest awake and waits for the disk to go idle).
Not yet re-verified in an image: the SDDM/avatar/label fixes (need a rebuilt ISO).

## Workshop, main ISO and local AI (2026-11-05, later session)
Only what was run is listed; see `docs/CLAIMS.md` for the full evidence table.
- Single main ISO built on the cached overlay engine in 3.5 min (cache hit), `verify-image.sh` passed incl. "Workshop is inert" checks; manifest `workshop_default: disabled`.
- Workshop over the virtio port: daemon started by udev without any enable symlink, `status` answered (session user `kubuntu`), desktop reached 101-111 s after boot.
- API update path: a hook pushed the current `hscl-respin`/daemon files into the running VM, a second hook formatted the scratch disk (`/dev/vda ext4`), `respin` squashed the live state in 373 s. The first xorriso step then failed (device busy); fixed with `stdio:`; the full proof (new ISO boots with the pushed file) is still running and **not yet verified**.
- Real model test (WSL builder, CPU): pinned llama.cpp b12130 tarball sha256 OK; `hscl ai model download qwen3.5-2b-abliterated` verified size+sha256; `hscl ai profile` produced the plan (cpu, ctx 32768, KV q8_0, 4 threads); llama-server listened on loopback only; the chat reply was "pong"; server reported 21.55 tokens/s (single tiny request, not a benchmark).
- **Development loop proven (VM-VERIFIED):** the respin finished in the guest in 420 s; the ISO was extracted from the scratch disk (5,494,013,952 bytes, sha256 100ab53a...c840, equals its manifest); booting it reached the desktop in 110 s; the Workshop daemon answered with `live: true` (this is the code pushed through the API, the base image reported `false`); the proof file pushed through the API was present (prefix match only). Screenshot: number rain on the real desktop, HSCL1 mark, top bar, dock, HSCL1 icons.
- **Main ISO with memory protection (3.5 min build, verifier passed incl. earlyoom, zram generator, slice, sysctl):** in a booted VM (4 GB) earlyoom is active, zram0 swap 1.9 G uses zstd, `vm.swappiness=100`, `hscl-ai.slice` has MemoryHigh 60 % / MemoryMax 75 %; 18 `hscl` and system checks ran inside the guest through the API (`artifacts/e2e3/cli-report.json`). Observed: KDE Connect listens on `*:1716` (open item).
- **Apply against the real session:** `hscl graphics apply --force` set AnimationDurationFactor 0 and blur off; `hscl wallpaper apply` switched the desktop to aurora, grid pulse, starfield and number rain (`artifacts/e2e4`).
- Memory incidents: two background jobs were stopped by the system for low memory (a VM plus WSL page cache for a 10 GB raw conversion plus a model download). Mitigations now in the scripts: no page cache for the conversion (`-t none -T none`), WSL shut down before the next VM boots, free-memory guards.
- Found and fixed on the way: live-session detection (no `boot=casper` on the Kubuntu command line), virtio hello handshake race, Qwen3.5 returns empty `content` when thinking consumes the token budget (test disables thinking via `chat_template_kwargs`).
- Implemented and unit-tested only: `hscl graphics`, `hscl wallpaper`, `hscl mcp`, `hscl code`, `hscl low-vram`, Wallpaper effects (QML tests), model catalog generator, backend pin generator.

## Next safe actions
1. Finish ISO download + verification, run remaster PoC, boot in QEMU (UEFI + BIOS).
2. Design tokens, architecture/threat-model docs, package manifests.
3. Ask owner: repository visibility and licence.
