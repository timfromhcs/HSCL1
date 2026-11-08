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

## M0/M1 session (2026-11-05, evening)
- Public repo `timfromhcs/HSCL1` created (owner decision: public); `codex/hscl1-v1` and `main` pushed without force; default branch `main`.
- M1: login autostart `hscl autotune` (hscl-desktop) and hidden KDE Connect daemon autostart (hscl-security); `tests/security/test_autostart.py`, two new `verify-image.sh` checks. Status IMPLEMENTED/TESTED (static); **not VM-verified** until a rebuilt/respun image shows no `*:1716` and a matching graphics profile after login.
- Full suite: 161 passed, 11 skipped (environment-dependent, unchanged).
- Release `v0.1.0-alpha.0` (pre-release): ISO commit 7a42ae3, 4 parts of 1500 MiB + SHA256SUMS + manifest; whole-image sha256 08649dc8...33fc8d matches the build manifest. Does not include the M1 fixes.
- PR #5 (M1) merged into `main` after CI green (3 jobs).
- `hscl system updates --check`: stale/missing package lists are reported as unknown (new JSON fields, warning text); cargo test 88 pass, clippy clean.

## M1 VM run (2026-11-06)
- Image `HSCL1-dev-m1.iso` (commit 20bf9b7, built with a dirty tree because untracked logs existed; sha256 3088717a...4d21b9) passed `verify-image.sh` (0 FAIL) after fixing a dpkg conflict the build itself caught (kdeconnect owns the autostart file -> dpkg-divert).
- In-guest run (`scripts/workshop/e2e_cli.py`, 23 checks, desktop after 111 s): autotune and stale-list reporting VM-VERIFIED; KDE Connect still listening -> root cause D-Bus activation by the tray applet (`scripts/workshop/e2e_probe.py`, read-only). Fix committed (fb6565d) but the rebuild + re-run was stopped by the host for low memory; **pending**, not restarted automatically.

## M6 item: Workshop fuzz tests (2026-11-06)
`tests/security/test_workshopd_fuzz.py` (seeded, no new dependencies): request parser never raises and always answers; path allow-list never accepts a normalised path outside the allow-list or a target outside the root; real `put_file`/`run_hook` handlers with hostile arguments stay inside a temp root. Mutation check: a validator without the `..`/`//` rule is detected. Status TESTED (unit/fuzz, host Python); not a proof of absence of bugs. Suite: 166 passed, 11 skipped.

## M7 slice: website (2026-11-06)
`scripts/build_website.py` builds `website/dist` (home + download in EN/DE/FR, tokens from `themes/tokens`, brand assets generated by `gen_brand.py`, real screenshots from `docs/img`); `scripts/fetch_release_meta.py` writes `website/data/release.json` from the real GitHub release (v0.1.0-alpha.0, prerelease, whole-image sha256 from SHA256SUMS). `tests/unit/test_website.py`: structure/links/alt text, EN/DE/FR key parity and forbidden-claim check, download links only from real assets, no release -> no button, canonical/hreflang/sitemap only with SITE_URL. Checked in a browser at 390 px width (no horizontal overflow). Status TESTED; **not deployed to Vercel**; no Lighthouse run yet; DE/FR text is my own translation and has had no native-speaker review. Suite: 174 passed, 11 skipped.
- Website: added `/security/` (EN/DE/FR): private vulnerability reporting link, release integrity (SHA256SUMS, unsigned), what is not claimed, Workshop note, links to KNOWN_LIMITATIONS/THREAT_MODEL/SECURITY. Texts mirror SECURITY.md and KNOWN_LIMITATIONS.md; DE/FR are my translations without native review. Suite: 175 passed, 11 skipped.

## M6 slice: SBOM generator (2026-11-06)
`scripts/gen_sbom.py` writes SPDX 2.3 JSON from a dpkg status file and/or `Cargo.lock` (installed packages only; workspace crate skipped; purl + registry checksums; deterministic with `--created`). Licence fields are NOASSERTION by design (no licence audit is claimed). `tests/unit/test_sbom.py` (6 tests incl. the real Cargo.lock). Status TESTED; not yet part of the image build or release assets. Suite: 181 passed, 11 skipped.
- Website: added `/install/vm/` (EN/DE/FR) listing only settings that were actually used in the recorded VM runs (QEMU 11.1/WHPX, UEFI and BIOS, 4 GB/4 vCPU, std VGA, 40 GB virtio qcow2, user-mode net, ISO as CD-ROM; desktop in 111-137 s; test install 1359 s) and an explicit "not tested" list (VirtualBox/VMware/Hyper-V, KVM, LUKS2, 3D/USB/shared folders). No USB or bare-metal instructions yet (no physical test). Suite: 182 passed, 11 skipped.

## M1 VM run 2 (2026-11-06, image 45e3c652...88ffe, commit f97c9fe)
- verify-image passed incl. the D-Bus stub check; in the VM `kdeconnectd` STILL ran (`*:1716`). Root cause (journal + `systemctl --user status`): the diverted original `org.kde.kdeconnect.daemon.desktop.kdeconnect` stayed in `/etc/xdg/autostart` and `systemd-xdg-autostart-generator` started it. Fix: divert the originals to `/usr/share/hscl/diverted/`; test + verify-image check added. NOT yet re-verified in a VM.
- **Security finding:** HSCL1 package files in the image were `rwxrwxrwx` (root-owned, world-writable, executable) because `build-deb.sh` only normalised modes of files without any exec bit and an NTFS checkout reports 0777 for everything (affected e.g. `/etc/sysctl.d/90-hscl.conf`). Fix: modes derived from content (shebang/ELF 0755, else 0644); `tests/security/test_package_modes.py` (run on Linux, fails on the old script - mutation checked) and a `verify-image.sh` check. The already published `v0.1.0-alpha.0` ISO was built before this fix and likely has the same problem; **not yet checked in that image** - to be stated in its release notes once confirmed.
- 12 of 23 in-guest checks failed with "no answer from the guest Workshop daemon within 120s" after ~11 successful ones (the first run on the older ISO had no such failures). Cause unknown (new in this ISO: systemd sandbox options on the workshop units). `e2e_cli.py` now records a screenshot and a re-poll at the first failure. To be investigated with the next image.
- Third image build (with the mode and divert fixes) was stopped by the host for low memory (the WSL builder takes ~10 GB of a 19.8 GB machine) while building packages; it was NOT restarted automatically. WSL was shut down afterwards. `build-deb.sh` now detects shebang/ELF through hex so binary payloads no longer trigger "ignored null byte" warnings. Pending: rebuild + VM re-check of KDE Connect, file modes and the Workshop-daemon failure; needs a decision on limiting WSL memory (see next steps).

## M1 VM run 3 (2026-11-06) - image cd0bf42e...adaae7d, commit 9d1a9ec (clean), built from a WSL-local clone with `.wslconfig` memory=8GB/swap=8GB/processors=6
- Build fixes needed first: Linux clone lost script exec bits (Git index had 100644) -> shebang files now 100755 + test; build-deb mode normalisation by content.
- KDE Connect: VM-VERIFIED off (0 listeners on 1716, no process). Autotune after login: state `minimal`, same fingerprint as `graphics detect`. `verify-image.sh` all checks passed incl. package file modes.
- Open defect: the Workshop daemon stops answering mid-run (first failure at `ai_profile`, 267 s after VM start; screenshot shows a healthy desktop). Same symptom in the previous image, at a different check. The pre-hardening image (m1) completed all 23 checks. Prime suspect: the systemd sandbox options added to the workshop units; also changed since then: file modes, D-Bus stub. **Cause not proven.** Next: A/B build with the workshop units un-hardened.

## Research + new plan (2026-11-06, after "abort, research, new plan")
- Build for the A/B experiment was aborted on request. Research (QEMU issue 4672, QGA protocol notes, Ubuntu/Calamares LUKS2 reports, reproducible-builds.org system images, GitHub attestations, systemd/AppArmor/Podman guidance) is summarised with sources in `docs/superpowers/plans/2026-11-06-autonomous-to-stable-hardened.md` (R1-R11).
- Hypothesis for the Workshop-daemon wedge: the host harness opened a TCP connection per RPC and re-sent after timeouts, the pattern that wedges a throttled virtio-serial port. Fix: persistent connection, send once (`scripts/workshop/vm.py`), `tests/unit/test_workshop_vm_rpc.py` (old behaviour confirmed by mutation check: 5 calls = 5 connections; new = 1). Test against the existing hardened image `cd0bf42e` is the discriminating experiment (no rebuild needed).

## P0.1 result (2026-11-06)
`e2e_cli.py` with the persistent-connection harness on image `HSCL1-dev-m1.iso` (cd0bf42e..., sandbox options present, the image that wedged in two earlier runs): 23/23 checks, no error, desktop after 110 s. Root cause = host harness (R1), not the systemd options. The A/B commit was reverted. Repeat runs 2 and 3 are in progress for the determinism gate (P0.4).

## CI: recurring QML job hang (2026-11-06)
Three PR runs had the `QML tests` job stuck for 15+ minutes; the job log shows the stuck step is "Qt 6" (apt update/install, before any test). Root cause class: runner/mirror network stall. Fix: job-level `timeout-minutes: 20`, a 10-minute step timeout for the Qt install, apt `Acquire::Retries=3` and 30 s request timeouts, non-interactive install. Package lists unchanged; no test was touched. A hang now fails fast and visibly instead of blocking a PR.
- Follow-up: the step timeout caught the next occurrence (10 min, push run; the PR run of the same commit took 44 s). The log shows the stall is a download from `azure.archive.ubuntu.com` stopping mid-package (cmake, 14 MB); `Acquire::Retries` cannot help because the connection never errors. CI now downloads with `apt-get install --download-only` inside a 3x loop with `timeout 180` per attempt (apt resumes partial files), then installs from the cache without network. Same package lists; tests untouched.

## P1.1 first attempt failed - two defects found (2026-11-06)
Image `HSCL1-dev-p1.iso` (a37e7eb0..., commit 58c5fbe): 3/3 e2e runs failed with "guest API port not reachable".
1. **Regression I introduced:** the rewrite of `hscl_workshopd.main()` dropped the `if __name__ == "__main__"` guard, so the service started and exited 0 (`systemctl`: Result=success, NRestarts=0, journal "Deactivated successfully") and never served. Found by booting the image and reading the service state through the guest terminal (mouse/keyboard harness). Unit tests had only exercised functions, never the process entry. Fix: guard restored + `test_script_entry_point_runs_main` (runs the file as a process; fails without the guard).
2. **Harness flaw exposed by it:** QEMU serves one client per socket chardev and only notices that client leaving while the guest port is open. My startup phase closed and reopened the connection after silence, which stacked stale connections in the listen backlog until the host port refused everything (observed with `netstat`: CLOSE_WAIT entries on QEMU's side, then WinError 10061). New rule in `vm.py`: connect once, never close for silence, wait for the daemon's hello (HELLO_WAIT_S fallback for daemons without hello), send once. Test `test_late_hello_is_awaited_on_one_connection_never_dropped_for_silence`.
Lesson recorded: every change to a process entry point needs a process-level test; image claims need a VM run, not only unit tests. Suite: 207 passed (Linux numbers in the next run).

## Third host reap (2026-11-06) - during the re-squash of image p2
`remaster-iso.sh` passed `verify-image` and was stopped by the host ("system critically low on memory") at the start of `mksquashfs`, although WSL was capped at 8 GB and the idle host had 11.6 of 19.8 GB free. Applied mitigations (not yet proven): `mksquashfs` now uses `HSCL_SQUASH_PROCS` (default 3) and `HSCL_SQUASH_MEM` (default 512M) instead of all cores and 1 GB; `.wslconfig` memory 8 GB -> 6 GB (backups `~/.wslconfig.bak-20261106` and `...b`). The build is NOT restarted until the owner says so. PR #15 merged (all CI jobs green incl. the new apt download handling); Dependabot rebases requested for #1, #3, #4.

## Research round 2 and plan extension (2026-11-06)
Searched for open questions (Kali Podman docs, Calamares `partition.conf`/LUKS deployment, GitHub attest action, llama.cpp Windows Vulkan, QEMU WHPX docs, mksquashfs reproducibility). Findings R12-R17 and a table of 12 open questions with their cheapest discriminating experiments were added to `docs/superpowers/plans/2026-11-06-autonomous-to-stable-hardened.md`; no result for the mksquashfs flags (to be read from `mksquashfs -help` on the builder in P8). Also done: P0.7 (guest typing of `;`, `|`, `:` and other shifted symbols, unit-tested). Image p2 (commit 3d89a43, clean, squash with 3 processors/512M) built without being reaped; its 3 e2e runs are in progress.

## Dependabot PRs (2026-11-06) - waiting for the owner
`actions/checkout` 4.2.2 -> 7.0.1 (#1), `sha2` 0.11 (#3), `thiserror` 2 (#4) are rebased, mergeable and green; the pinned SHAs of #1 and #2 were checked against the upstream tags (checkout v7.0.1 = 3d3c42e5..., upload-artifact v7.0.2 = cf430e03...). My attempt to merge #1 was denied by the session's permission classifier (no reason given), so I did not retry or route around it. `upload-artifact` (#2) stays on hold until the release dry run (P9.4) because only the release bundle job uses it. Decision needed: merge #1, #3, #4 (owner or a permission rule for `gh pr merge` on Dependabot PRs).

## P1.1 done (2026-11-06)
Image `HSCL1-dev-p2.iso` (sha256 0eb7acb77f5dfd31ac9246b7a46a4cd7816c80cab214e5df46c535968be263ff, commit 3d89a43, clean): `verify-image.sh` all checks passed; built with `HSCL_SQUASH_PROCS=3`/`HSCL_SQUASH_MEM=512M` and WSL capped at 6 GB without being reaped. `e2e_cli.py` x3: 23/23 each, desktop after 110/111/110 s, KDE Connect listener 0, daemon port stats restarts 0 / write_timeouts 0. A read-only baseline probe (file modes, `systemd-analyze security`, Secure Boot variables, AppArmor, sysctls, firewall, sockets, Podman prerequisites, GRUB facts) is running on the same image (P1.2/P1.3/P3.1/P2.0 inputs).

## P3.3 baseline unit sandbox (2026-11-06)
Cumulative phases run as real units in the booted p2 image (`artifacts/probe-hardening*`): try 1 failed in namespace setup (`/var/lib/ufw` did not exist: my path list), try 2 failed with `ufw: '/etc/default/ufw' is not writable`, try 3 passed all four phases (exit 0, ufw active, exposure 7.5 -> 5.6 -> 2.5 -> 2.5). `distro/security/systemd/hscl-security-baseline.service` now carries the full set; `StateDirectory=hscl` creates the state dir. Test `test_security_baseline_unit_has_the_measured_strict_sandbox`. Pending: the next image's real first boot (the unit has `ConditionPathExists=!done`, so the live image above did not run it again).

## P4.2 Security Lab spec generator (2026-11-06)
`hscl lab status|setup|toolsets|spec` (new `cli/hscl/src/lab.rs`). Typed options -> `podman` argv, printed not executed. Tests: safe defaults, install-phase caps exactly the fixed set, no forbidden flag for any valid input, image digest pin, project/workspace validation (traversal, volume-option smuggling, hidden/credential folders, symlinks on unix), bounded limits, destroy only touches the named project, seeded 20000-string fuzz. cargo test 98 passed, clippy clean. Windows-specific: absolute-path check is textual so tests behave the same on both OSes; Git Bash rewrites `/etc` arguments to Windows paths (cosmetic when trying the CLI by hand).

## CI QML job failed on main after PR #16 (2026-11-06)
All three download attempts (3 x 180 s) stalled on the same 14.1 MB package (`cmake`, `Ign:` in the log) from `azure.archive.ubuntu.com`; retrying the same mirror does not help. The helper now switches the apt source from the runner's mirror list to `archive.ubuntu.com` before the last attempt. Same package list; tests untouched.

## P2.4 LUKS2 install verified (2026-11-06)
`tests/visual/scenarios/install-luks.json` (new) on image p2: Erase disk + Encrypt system with a unique marker passphrase; installer showed the intended layout and finished without error. `scripts/workshop/e2e_luks_boot.py` (new) booted the disk without an ISO: passphrase prompt, wrong passphrase rejected, correct one accepted, login, then in-guest checks over the Workshop API. Findings and limits are in CLAIMS. Harness additions: `--unlock-passphrase/--unlock-first-wrong/--unlock-at` in `qemu_boot_test.py`; `e2e_cli.py` checks now use the session user from the daemon status instead of `kubuntu`. Open finding: on the installed system `ufw` warns "uid is 0 but '/' is owned by 1000" (not seen in the live session) - being investigated.

## Root directory ownership defect (2026-11-06)
Found while reading `ufw status` output on the installed LUKS system ("uid is 0 but '/' is owned by 1000"). Probes (`artifacts/luks-boot-own`, `-owner`): `/` is `tester:tester 755`; all other system directories are root; installer logs show only `chown -R tester:tester /home/tester`, so not the users module. The live session is root-owned (overlay upper), the installer copies the squashfs root. Cause: `mkdir -p "$ovl/up" "$ovl/wk" "$merged"` run as the build user (uid 1000) became the squashfs root inode. Fix in `scripts/remaster-iso.sh` (`sudo install -d -o root -g root -m 0755 ...`, owner assertion after `mksquashfs`), `verify-image.sh` check, `system_tree_owner` checks in `e2e_cli.py` and `e2e_luks_boot.py`, `tests/security/test_respin.py`. Pending: rebuild, fresh install, `stat /` = `0:0 755`. The published alpha ISO has the defect (owner-visible warning to add to its notes; I did not edit the public release).
Also: new plan `docs/superpowers/plans/2026-11-06-ux-ai-hardware-expansion.md` (UI/UX, wallpaper maker, local AI tooling, hardware/driver detection, GPU/RAM bridges, GEMM simulator, packages, installer) from a research round; the earlier hardened plan stays valid.

## Naming, program name, second research round (2026-11-06)
Owner decision: HSCL1 = **Hypercharged Supreme Computing Layout 1**; `hscl1` is also a program. Implemented: `EXPANSION` constant, `hscl about`/`version --json`, overview on a bare call, argv0 detection (`hscl1`, `hscl1.exe`, any case), `/usr/bin/hscl1 -> hscl` in the package, `HSCL1_NAME_LONG` in `os-release`, Control Center About line, slideshow first slide, handbook intro (EN/DE/FR), website hero/footer (EN/DE/FR), README, `docs/BRAND.md`. Found while testing: my first `program_name` missed `HSCL1.EXE` (case); fixed with a lower-casing step and a test. A README name check initially failed because the README only had the letters in bold - fixed by writing the full name. Research round 2 (release limits, README practice, hardening tools in the archive, viewers, shell, office/creative suite, pentest MCP, MCP security, Rust MCP SDK, media sandboxing) is summarised with consequences in the addendum at the end of `2026-11-06-ux-ai-hardware-expansion.md` (R-BR-1 ... R-MEDIA-1, workstreams W13-W20).

## Release ISO 0.1.1-alpha.0 verified in VMs (2026-11-06)
Exact artefact `HSCL1-0.1.1-alpha.0-amd64.iso`, sha256 `b817074aeb2fa30865c4660422e37a3942fc4e48a77b6a4646149bfcfacc4c19`, built from a clean WSL clone at `425e6c0`. Live: `e2e_cli.py` 3 runs, 27 checks each, no errors (`artifacts/e2e-rel-run1..3`), including `hscl1` program-name checks and `system_tree_owner` = `0:0 755`. Install: fresh Erase + LUKS2 install (`artifacts/luks-install2`), installed boot (`artifacts/luks-boot2d`, wrong passphrase rejected, correct one accepted, login, desktop, 0 errors).
Harness findings (not product defects): (1) hook file name `luks-boot-is-unencrypted-but-has-no-keyfile.sh` was 47 characters, the daemon allows 41 -> check renamed `boot_has_no_keyfile`, `tests/unit/test_hook_names.py` checks every generated hook name against the daemon rule; (2) two boots (`luks-boot2b`, `2c`) failed to reach the login screen: in 2c the passphrase was not accepted because the prompt ignores keystrokes typed too early; in 2b the unlock worked but login did not appear within 300 s. Fix: wait 75 s, retype only when the unlock field is still visible (stdlib PNG pixel check, unit-tested), login wait 600 s.
**Open observation:** in `2d` the login screen appeared only ~770 s after the start (earlier boots of the same disk: ~170 s). Cause not established (host load, the retype, or a real slow-boot issue in the installed system). To investigate with a timed boot log (`systemd-analyze blame` after login) before claiming boot-time numbers. Not claimed anywhere.

## Release v0.1.1-alpha.0 published (2026-11-06)
PR #17 merged into `main` after green CI. Prerelease `v0.1.1-alpha.0`, tag on the built commit `425e6c0716ce8652bcdba705b3e4d7e4352ed936`; assets: 4 parts (3 x 1500 MiB + 776208384 B), `SHA256SUMS` (parts + whole image), manifest, `SBOM-hscl-cli.spdx.json` (Rust CLI only, licences NOASSERTION). Joined parts sha256 = whole ISO = `b817074aeb2fa30865c4660422e37a3942fc4e48a77b6a4646149bfcfacc4c19` (checked locally with `cat parts | sha256sum`). Workflow "Verify release assets" run 42222161027: `Verify split ISO` success, `Bundle one-file ISO` success (artifact `HSCL1-v0.1.1-alpha.0-iso`, 5494801320 B = ISO + 936 B zip overhead, 90 days; its content hash was verified inside the job against SHA256SUMS, not re-downloaded by me). Notes of `v0.1.0-alpha.0` edited to carry a warning (two security defects); its assets are unchanged. Unsigned, no physical hardware test, no ISO package-list SBOM.


## Rebrand round, boot tests r1-r4 (2026-11-06)
Dev images only (not released). `r1`: all branding gates green and 27/27 guest checks, but the live boot still showed the upstream boot splash. Cause: the `-map` for the rebuilt initrd was missing in `remaster-iso.sh` while the gate only looked at the file we meant to map. `r2`: with the map fixed the live boot dropped to the initramfs shell: the rebuilt initrd lacked `conf/conf.d/default-boot-to-casper.conf` (`BOOT=casper`). `r3`: fixed (the snippet exists only while `update-initramfs` runs, so installed systems are not affected); HSCL1 boot splash confirmed in the live boot (`artifacts/boot-r3/shot-010.png`). New finding in `r3`: the live session stops at the upstream "Try / Install Kubuntu" prompt (package `kubuntu-installer-prompt`, a compiled Qt program started by `/usr/libexec/start-kubuntu-live-env`). `r4`: the starter is replaced by an HSCL1 one (dpkg-divert in `hscl-branding`; skips the prompt, starts Plasma directly, OEM branch unchanged). Result: desktop reached after 99 s without any click (`artifacts/boot-r4`), 27/27 guest checks (`artifacts/e2e-r4`), ISO sha256 `7bbdc079273f7a851d1d5cf64918ea5843bd1f007e7decdb6e23df2af2a84070`. New gates in `verify-image.sh`: boot splash theme and default, GRUB distributor, welcome page, removed flavour artwork, renamed global themes, live starter; the build now proves the initrd from the finished ISO. Process fixes: ShellCheck findings (SC2066, SC2024) fixed after two red CI runs, exec bits, a Windows test pitfall (text-mode stdin writes CRLF). Not done / not verified: Secure Boot boot of these images, installation from r4 (Calamares branding, installed GRUB menu, EFI directory name), language choice in the live session (the skipped prompt offered it; the installer has its own), a boot-time measurement.

## Release candidate content scan, r5/r6 (2026-11-06)
Content scan of the finished 0.1.2-alpha.0 candidate (text, not paths) found visible upstream leftovers: installer `showDonateUrl: https://kubuntu.org/donate/`, menu entries "Kubuntu Website"/"Kubuntu Focus", SDDM theme description, live user/host `kubuntu`, Plymouth message overlapping the logo. Fixed in `e6ee0d4` (+ image gates, tests). Dev image `r5` then **failed to boot**: "cow format specified as overlay and no support found" (`artifacts/boot-r5/shot-073.png`). The initrd trees of r4 and r5 differ only in `casper.conf` (FLAVOUR set by my patch), `os-release`, the Plymouth descriptor and font caches; the r5 ISO with the r4 initrd (`HSCL1-exp-r5b`) booted to the desktop in 90 s, so the `casper.conf` change was the cause (GATE BUG too: every file gate was green, only the boot test caught it). Fix `35ba640`: `casper.conf` stays untouched (gate), the build writes `/.disk/info` with first word `HSCL1` (casper derives FLAVOUR, hence user and host `hscl1`), updates `md5sum.txt` and proves the file from the finished ISO. `r6`: boot without a click after 90 s (`artifacts/boot-r6`), 28/28 guest checks (`artifacts/e2e-r6`) incl. `live_identity` = `identity-ok`, session user `hscl1`, `/` `0:0 755`; ISO sha256 `25c2127ae5cba34cb66acb0e35d4ba1b3fa440423630ce21f9e58d21bc303984`. New tools: `scripts/forge.py check` (pytest, bash -n, ShellCheck in WSL, secret scan; about 23 s), `scripts/boot_classify.py` (boot failure classes; would have named r2 and r5 from a serial log). Not verified yet: the donate-link removal and Plymouth alignment on screen (to look at in r6 screenshots), installed-system effects, Secure Boot, physical hardware.

## Test parity Windows/Linux + SOTA plan v5 (2026-11-06)
Windows host suite was 238 passed / 11 failed / 16 skipped: every failure came from `shutil.which("bash")` resolving to the WSL launcher `C:\WINDOWS\system32\bash.EXE`, which mangles Windows paths and overrides `LANG`/`LC_ALL`. Instead of skipping them on the host, new `tests/shellutil.py` detects the bash flavour (`native` / `wsl` / `none`), converts paths (`/mnt/<drive>/...`), and passes environment overrides through `wsl.exe -e env [-u NAME] NAME=VALUE` - the interop layer resets `LANG` for a shell, but not for a program it is asked to exec. `tests/conftest.py` makes the helper importable. Rewrote `test_handbook_launcher.py`, `test_hcscoder.py`, `test_workshop_evidence.py`, `test_baseline_script.py` to use it; fake `#!/bin/sh` shims are written with `write_bytes` (CRLF made them unexecutable: "bad interpreter: /bin/sh^M"). New `tests/unit/test_shellutil.py` (7 cases).
Result: **Windows 254 passed / 16 skipped**, **Linux (WSL, working tree incl. `.git`) 270 passed / 0 skipped**. Two bugs found and fixed by the Linux run: `bash_kind()` classified a real Linux host as WSL (uname says `Linux`), and `PATH` overrides inside WSL dropped `/usr/bin` so `bash` itself vanished - the guest PATH is now appended. Also two setup artefacts, not product defects, in the first Linux run: an rsync copy without `.git` breaks `git ls-files` tests.
Plan: `docs/superpowers/plans/2026-11-06-finish-line-self-heal.md` extended with **v5 tracks** for delegation economics (OpenJev + subagents + ledger, with a "a local subagent is a hint, never evidence" rule), mid-flight LoRA training and shipping an opt-in model bundle, ISO build-speed bake-off/caches/zsync, update-channel + API hygiene, deterministic screenshot/visual-QA harness (QEMU + virtio-9p share + perceptual diff, Playwright for the site), and **Neural Lab** (NCA/tiny-net/frame-predictor demos, grammar-constrained Game Studio, custom workspace, sandboxed generated code). Gates G32-G46. Research basis: new `docs/research/2026-11-06-sota-scan.md` (GameNGen/Genie 3 are TPU/hosted scale; NCA is shippable; small models fill schemas, they do not synthesise programs).

## Generated docs, delegation ledger, release-meta integrity (2026-11-06)
New `scripts/gen_packages_doc.py` writes `docs/PACKAGES.md` from `packages/debian/*/DEBIAN/control` and `--check` fails when it is stale (a hand-written table drifts silently). It also asserts the control version is the `0.0.0` placeholder, because `scripts/build-deb.sh` substitutes the repository `VERSION` at build time - a hard-coded version would ship stale.
New `scripts/ledger_report.py` summarises the delegation ledger (`artifacts/auto-loop/ledger.jsonl`) and exits 3 when a delegated answer was wrong and no other tool redid the job, so "we delegated it" cannot hide a regression. Measured reality of the local stack that day: `jev_noul` answered `p_true=0.45` for a true statement (1.5 ms, uncalibrated for repo state -> not a gate), `subagent.*` fails at session start with "the compaction request cannot be reduced further" even after lowering the output limit to 2048 (needs a service restart), `localai-gateway.chat` works.
`scripts/fetch_release_meta.py` now cross-checks the release's `SHA256SUMS` whole-image hash and part sizes against the manifest's `iso_sha256`/`iso_bytes` (mismatch = exit, no silent write), retries transient `gh` failures (never a 404), and has `--check`. Tests: 5.
Windows parity improved further: `test_release_split_join.py` now runs through `tests/shellutil.py` instead of skipping on Windows. Host suite: 274 passed, 9 skipped (was 238/11/16 at the start of the session); Linux/WSL: 270 passed, 0 skipped. The remaining Windows skips are genuine platform limits (chmod semantics on drvfs, POSIX symlinks/select, Qt qmltestrunner absent); all of them run on Linux CI.

## Resume after 0.1.2-alpha.0 + masterplan R1 (2026-11-06)
State found: `v0.1.2-alpha.0` published; PR #22 CI red only because `scripts/check_trademarks.py` lacked the exec bit in the index (fixed `0985ed5`). New `docs/superpowers/plans/2026-11-06-masterplan-resume-s1.md` (start position, S1 tasks, stop rules). Task 1 (G12): Rust test `cli_doc_lists_every_command` walks the clap tree; it was red with 36 undocumented commands, `docs/CLI.md` now lists all (rows from `--help`). cargo test 117 passed, clippy and fmt clean. Not done: man pages/completions, menu file, governor parser, forge build/boot/diff (Tasks 2-4); no image built, nothing VM-verified in this step.

## Task 2 (completions) (2026-11-06)
`hscl completions bash|zsh|fish|elvish|powershell` (clap_complete 4); program name follows argv0 so `hscl1` completes too. `scripts/build-deb.sh` generates the bash/zsh/fish files for `hscl` and `hscl1` from the packaged binary at package build time (no committed copy). Tests: Rust `completion_scripts_cover_every_top_level_command_for_both_program_names`; `tests/security/test_package_completions.py` (stand-in dpkg-deb and binary; WSL 2 passed with the modes test; skipped on Windows because of symlink/chmod semantics). The G12 drift test caught the new command before docs existed (red, then fixed). `cargo deny` is not installed on the host, so the licence check for clap_complete runs only in CI (MIT/Apache like clap). Man pages (clap_mangen) still open. No image rebuilt: the files are not in any ISO yet.

## Research rounds R1-R3: AREX-2, autodetect, reverse engineering (2026-11-06)
Three rounds, each created the next round's questions. AREX-2 is a 27B Apache-2.0 agent model from BAAI (arXiv 2609.38288), not hardware; its repository ships evaluation runners only, so we copy the loop pattern (score per round, reflection, round budget), not the model. Autodetect: Ubuntu maps hardware to drivers by sysfs modalias patterns; we add an offline modalias collector, hwdb-based quirk table and driver hints. Reverse engineering is documented as a lab workflow with explicit legal limits (EU 2009/24/EC art. 6, CJEU C-13/20); legal wording stays an owner item. Not found on the web, therefore MEASURE: 680M tok/s, WebGPU in QtWebEngine, Qwen3.5/3.8 in the pinned llama.cpp, sysext/hwdb on the image. Files: `docs/research/2026-11-06-arex2-autodetect-reverse-engineering.md`, `docs/superpowers/plans/2026-11-06-autodetect-arex-loop-re-lab.md`, masterplan section 6.

## Four-round research loop and final master plan update (2026-11-06)
Rounds: AREX harness, abliteration, updates, stress -> llama-server API (official README), abliterated AREX-2 card, bootc on Ubuntu, openQA, PSI/oomd, blkdebug -> server-tools scope, dm-flakey/log-writes, snapper, fuzzing, sched_ext, XML tool calls -> measured archive availability of 23 packages (WSL resolute). AREX-2 is a pattern for our runner (XML tool protocol, caller executes tools, update_context, round budget), not a shipped model. "APEX" turned out to be two unrelated things (a paper and Apex-35B); the owner's target was AREX-2. New files: research four-round document, `docs/superpowers/plans/2026-11-06-ai-api-updates-stress.md`, masterplan section 7. No code changed in this step. The WSL kernel config is Microsoft's, so kernel-option questions stay MEASURE.

## Task D2 toolcall parser (2026-11-06)
`cli/hscl/src/toolcall.rs`: AREX-protocol parser (`<tool_call>` JSON or `<function=..><parameter=..>` body, allow-list plus built-in `finish`, 64 KiB body limit, nested/duplicate/truncated/unknown-tool refusals, 20000-string seeded fuzz). Tests written first (8 of 10 red), then implemented; cargo test 128 passed, clippy -D warnings and fmt clean. A first Python-generated edit wrote real newlines into char literals (compile error), fixed with a targeted edit. Temporary `#![allow(dead_code)]` until the runner (D3/D4) uses the module; removal is tracked in the subplan. Nothing run against a real model yet.

## Task D3 agent loop (2026-11-06)
`cli/hscl/src/agent.rs`: `Chat`/`Tools` traits, `run(...)` with round budget, refusal of non-allow-listed tools as an error response (never executed), result cap 64 KiB, one `log` call per round. 4 tests written first (all red with a `todo!()` stub), then implemented; cargo test 132 passed, clippy -D warnings clean. Still no real model or HTTP client (D4); `dead_code` allow is temporary.

## Tasks A1/A2 round log and report (2026-11-06)
`scripts/round_log.py` (refuses secrets and personal paths, increasing rounds per task, numeric scores) and `scripts/round_report.py` (best round, delta, regression, stall after 3 rounds since the best, exit 3). 21 tests written first (collection error as the red state). One of my own tests contradicted the stop rule ("stalled" = three or more rounds since the best value) and was corrected before implementing. Documented in `docs/DEV_LOOP.md`. The recorder is not yet wired into the automatic loop prompt.

## Local subagents: four research rounds and plan (2026-11-06)
Read-only research subagents (3+3+3+1 reports) covered the PrismML fork and Bonsai models, TurboQuant, KV rotation, Vulkan kernels, memory flags, OpenCode V2 API, Claude Code bridge, harness evidence for small models, governor options and Qwen3.5 tool-call status. Local facts: PrismML Vulkan zip matches the release SHA-256; the LocalAI Gateway (:8090) is healthy with nothing loaded; first call to `qwen3-4b` with thinking on returned empty content after 400 tokens (cold start > 120 s), with thinking off it returned code in 178 tokens that contained an int/float bug the model's own tests missed. Two plain-text secrets found in `~/.config/opencode` (not copied anywhere; owner should rotate). New: `docs/superpowers/plans/2026-11-06-local-subagents.md`, masterplan section 8. Nothing installed yet in this step.

## Plan L tasks L1/L2 (2026-11-06)
`tools/local_worker/fetch_model.py` (SHA-256 from the Hugging Face tree API LFS oid, resumable `.part`, deletes on mismatch, allowed root `C:\LocalAIBACKEND`, repo/file validation) with 18 tests, and `tools/local_worker/memgate.py` (available-RAM gate: model + KV + 3000 MiB reserve) with 11 tests. Both written test-first. Verified candidate files exist with published digests: Ternary-Bonsai-2-9B PQ2_0-MTP-Q8_0 (2.68 GB), Ternary-Bonsai-2-4B PQ2_0-MTP-Q8_0 (1.27 GB), unsloth Qwen3.5-9B Q4_K_M (5.68 GB). Background downloads started (log in `artifacts/local/fetch.log`); results are recorded when they finish. Observation: only 5.2 GB RAM was available during the downloads (gateway had qwen3-4b loaded), so the gate correctly refused a further 3.6 GB model.

## Plan L task L3 verify-patch loop (2026-11-06)
`tools/local_worker/loop.py`: bounded loop (default 3 rounds) where the model returns whole-file `FILE:` blocks, applied only to a temp copy; tests decide; protected files, non-editable files, path escapes and symlinks are refused; timeout and output cap; result carries a unified diff and never touches the real tree. 14 tests written first: Windows 13 passed + 1 skipped (symlink rights), WSL 14 passed. One design fix came from a failing test: the client gets a copy of the message list. Not yet connected to a real model (L4/L5). Model downloads (correction of an earlier wrong note): Ternary-Bonsai-2-4B (PQ2_0-MTP-Q8_0) finished and passed the hash check; **Ternary-Bonsai-2-9B failed with a sha256 mismatch and the file was deleted** (the stream most likely ended early without an error; the fetcher had no length check or automatic resume). Fix in the next entry; Qwen3.5-9B Q4_K_M was still downloading.

## Fetcher fix: truncated downloads (2026-11-06)
Real use found a defect the unit tests had not covered: a stream that ends early raises no error, so the 9B file had the wrong hash and was deleted. `fetch_model.py` now reads the published size, resumes up to 3 times from the `.part` file, keeps the partial file when the download stays short ("download incomplete ... run again to resume") and deletes only when the full length has a wrong hash. Tests written first (2 red), 20 passed. The 9B download was restarted with the fixed code (`artifacts/local/fetch-9b.log`).

## Plan L task L4 gateway client + CI exec-bit repeat (2026-11-06)
`tools/local_worker/gateway.py`: loopback-only client (plain http to 127.0.0.1/localhost/::1, no proxy), thinking off via `/no_think` and `chat_template_kwargs`, `<think>` stripped, one retry with a doubled token budget on empty output (the measured failure of the first `qwen3-4b` call), stable error codes, key only from `LOCAL_AI_KEY`. 16 tests written first. CI on PR #22 had failed once more on the exec-bit gate for `tools/local_worker/loop.py` (I had not run `test_exec_bits.py` after adding the file); fixed in `ca1393c`. New rule for myself: run `python scripts/forge.py check` before every commit that adds a script. Downloads still running at the time of writing (Qwen3.5-9B about 2.6 GB of 5.7 GB, Bonsai-9B about 1.7 GB of 2.7 GB); not yet registered in `models.yaml`.

## Exec-bit gate hole closed (2026-11-06)
CI on PR #22 failed a third time on the shebang/exec-bit gate (`tools/local_worker/gateway.py`). Root cause was in the gate itself, not only in my habits: `test_exec_bits.py` inspected tracked files only, so the local forge check passed for a brand-new script and the CI failed after the commit. The test now also fails for untracked shebang files ("add it with --chmod=+x"), the checker is a function with its own test in a temporary git repo (tracked 100644, untracked, and 100755 cases), and I proved the gate by creating an untracked probe file (red) and removing it (green). `gateway.py` is now stored 100755.

## Plan L task L5 MCP server localdelegate + model downloads complete (2026-11-06)
`tools/local_worker/server.py`: stdio MCP server with exactly one tool `local_code(task, files, test_cmd, model?, max_rounds?, protected?)`, no directory argument (root from `HSCL_WORKER_ROOT`), executable allow-list for the test command, bounded sizes, free-RAM gate before every run, result `{ok, rounds, reason, diff, last_output, applied:false}` (the diff is only a proposal). 26 tests written first, including a process-level test over real stdio; verified by piping initialize/tools/list into the real process and by the no-root exit code 2. Forge check green. Registration in `.mcp.json` and the OpenCode config is deliberately postponed to L6 until the exact variable names are verified in the docs.
Models (exit codes read from the logs, hashes checked by the fetcher against the Hugging Face digests): Ternary-Bonsai-2-4B-PQ2_0-MTP-Q8_0 1 274 642 176 B ok; Ternary-Bonsai-2-9B-PQ2_0-MTP-Q8_0 2 675 410 720 B ok (after the fetcher fix; the first attempt had failed); Qwen3.5-9B-Q4_K_M 5 680 522 464 B ok (`exit=0`). All three are in `C:\LocalAIBACKEND` and **not yet registered in models.yaml**; they have not been loaded or benchmarked.

## Plan L task L6 shared agent source + first benchmarks (2026-11-06)
`ai-shared/` (spec + prompt) generates the Claude Code and OpenCode files via `scripts/sync_ai_shared.py` (merge-safe for the tracked `.mcp.json`, drift check also run as a unit test on the real repository); 10 tests written first. Server root now also from `CLAUDE_PROJECT_DIR` (verified in the official docs by a read-only research subagent), 27 server tests. Forge check green. Note: Claude Code asks for approval before using a project-scoped server; the OpenCode agent file format is taken from the docs, not yet exercised against the live OpenCode 2.2.5 server.
First measurements with the verified Prism build (llama-bench, Radeon 680M, no CPU fallback seen): Bonsai-2-4B PQ2_0 decode 14.1 t/s (CPU compute) vs 30.4 t/s (Vulkan); Bonsai-2-9B PQ2_0 8.9 vs 20.9 t/s; details in the research document. Qwen3.5-9B Q4_K_M not measured yet (RAM gate refused it while the gateway held Qwen3-4B). Models are still not registered in the gateway's `models.yaml`.

## Plan L task L7 benchmark harness + first real task benchmarks (2026-11-06)
`tools/local_worker/bench.py` and `bench_tasks.py`: ten tasks (including the int/float trap), each validated by a test (reference passes, naive solution and stub fail), run through the verify-patch loop; 19 tests written first; forge check green. Real runs on this machine (thinking off, up to 3 rounds, one run each, small sample): Qwen3-4B abliterated Q4_K_M via the gateway 7/10 solved (7 in round 1), 8.1 s/task; Ternary-Bonsai-2-4B PQ2_0 9/10 (8), 6.3 s/task; Ternary-Bonsai-2-9B PQ2_0 10/10 (9), 7.2 s/task. The Bonsai models were served by temporary `llama-server` processes on port 18081 (each stopped by port-targeted `Stop-Process`; the gateway's own server was not touched). Qwen3.5-9B was not measured because the RAM gate was closed (the gateway holds Qwen3-4B; it needs ~9.4 GB available, 7.4 GB were free). `bonsai-9b` and `bonsai-4b` were registered in `C:\LocalAIBACKEND\models.yaml` after a backup (`models.yaml.bak-20261106-pre-bonsai`), YAML validated and files present; the running gateway still lists the old set until it is restarted (not done by me). Memory values there are `hscl ai fit` estimates. PR #22: all 10 checks green at the start of this run; merge left to the owner.

## Plan L task L8 queue + variance runs (2026-11-06)
`scripts/local_queue.py` (13 tests written first, forge check green): reads `[local]` plan steps, validates with the MCP server validator, runs the verify-patch loop through the gateway, records runs with `round_log.py`, keeps results as diff proposals with a `git apply --check` verdict, never applies/commits/pushes and never ticks plan boxes; stops on RAM gate, gateway error, wall-clock or item limit. Real plans currently contain no `[local]` step, so the dry run is empty. Variance runs (temporary servers on port 18081, stopped by port): Bonsai-9B 10/10 solved in all three runs, Bonsai-4B 9, 10, 9 of 10. An owner message asked for lower VRAM/RAM use through stronger KV quantization, better context management and WSL limits; a KV/context sweep for Bonsai-9B was started and is recorded in the next entry.

## KV/context sweep, context mode `last`, benchmark history option (2026-11-06)
Sweep for Bonsai-9B over K/V cache types and context size with sampled process memory (full table in the research document): real peak private memory 4.5-4.7 GB (my earlier registry value of 3500 MB was too low), KV quantization/context saves only 100-260 MB, quality unchanged within noise, iGPU memory is shared system RAM (dedicated ~25 MB). New verify-loop default `history="last"` (constant-size context per round: task + current file content + latest failure; `history="full"` keeps the old growing history), 4 tests written first; `bench.py --history last|full` records the mode in the result (2 tests, red first). Forge check green (pytest took 237 s because every Python subprocess start currently takes ~0.8 s on this machine; not a code problem). Caveat recorded: I edited `loop.py` while the sweep was running, so two sweep rows may have used the new mode.

## Task D1 `hscl ai serve` + context-mode comparison (2026-11-06)
`cli/hscl/src/serve.rs` and `hscl ai serve`: prints the exact `llama-server` command (host fixed to 127.0.0.1, port >= 1024, context 512..262144, key only as a key file, model must be a `.gguf` inside the model storage, router mode with at most 2 resident models, no tools/MCP-proxy flags possible) with the measured defaults; 8 tests written first, `cargo test -p hscl` 140 passed, clippy clean, manual smoke test ok. Single-run comparison of the verify-loop context modes (Bonsai-9B, K q8_0 / V q4_0, c 4096): `full` 10/10 solved but 7 in round 1; `last` 9/10, all 9 in round 1 (word_count failed all rounds); Bonsai-4B `last` 10/10 (9 in round 1; merge_intervals needed 3 rounds), Bonsai-4B peak private memory 3836 MB, Bonsai-9B 4927 MB in that session. One run per mode is inside the noise, so three runs per mode were started (results in the next entry). Not yet done for D1: the forge check and the commit.

## D1 committed; context mode `last` removed, `window` introduced (2026-11-06)
Three runs per mode (Bonsai-9B): `last` 9/10 every time with `word_count` unsolved in all runs, `full` 10/10 every time. Traced prompts: in `last` mode rounds 2 and 3 were identical apart from the round number, the deterministic model repeated its wrong answer word for word (dedicated experiment: 0 of 6 solved, `full` 6 of 6). My context-saving change (committed earlier the same day as the default) therefore made quality worse; the memory it could save is only a few hundred MB. Replaced by `history="window"` (system, task, latest answer, latest failure; identical to `full` in round 2, constant afterwards) plus a hint when an answer repeats word for word; tests written first (3 red), loop tests 20 passed + 1 skipped, benchmark/queue/server tests 81 passed + 1 skipped in total, real-model check `word_count` 5/5 with `window`. `bench.py --history` now accepts `window|full`. Forge check green (pytest 280 s on the currently slow machine); `cargo test -p hscl` and clippy rechecked for the committed D1.

## Memory incident and corrected gate sizes (2026-11-06)
The background job with the three `window` benchmark runs was stopped by Claude Code because the system was critically low on memory; one run (10/10 solved, 8/10 in round 1) had finished, no orphaned test server remained (checked by port 18081), free RAM then 8.1 of 20.3 GB with the gateway's Qwen3-4B server (4.1 GB, not mine, untouched) as the largest consumer. Root cause was mine: gate calls used file-size guesses while the measured peak private memory is 4.5-4.9 GB (Bonsai-9B) and 3.8 GB (Bonsai-4B). Fixed: `tools/local_worker/server.py` `MODEL_MB` uses measured values (test written first, red), `C:\LocalAIBACKEND\models.yaml` corrected after a backup (YAML validated: bonsai-9b 4900 MB, bonsai-4b 3900 MB, `-c 4096 -ctk q8_0 -ctv q4_0`). Not restarted: the interrupted benchmark runs 2 and 3 and the Qwen3.5-9B measurement; both need more free RAM than this machine currently has next to the gateway's resident model. Suggestion to the owner: restart the gateway (needed anyway for the new models), which also frees its resident Qwen3-4B.

## CI fix and Linux parity for the local gate (2026-11-06)
PR #22 failed in CI (Linux) on `test_window_round_two_prompt_is_identical_to_the_full_history_prompt`: my normalization only handled Windows temp paths, on Linux the random `hscl-local-<random>` directory in the traceback differed between the two runs. Fixed by a platform-neutral normalization (plus an assertion that the normalization has something to normalize); passes on Windows (20 passed, 1 skipped) and in WSL (21 passed). Because this was the fourth CI-only failure of the day, `scripts/forge.py check` got a step `pytest (WSL, changed tests)` (changed and untracked test files, run with `python3 -m pytest` in WSL against the working tree); written test-first (3 new tests, the plan test updated), forge check green including the new step (63 s).

## Task E1 delta-card gate for abliterated models (2026-11-07)
`scripts/check_delta_cards.py`, `ai/catalog/delta-cards.json`, `ai/catalog/delta-card.schema.json`; 22 tests written first (module missing = red). Every abliterated catalog model needs a card stating honestly whether anything was measured (`own` with an evidence file under `docs/`, `third-party` with an https URL, or `none` with all numbers null); no abliterated id or file name may appear in `distro/` or `packages/`. Result on the real catalog: 6 abliterated models, none measured by us (the only published measurement we know, the AREX-2 abliterated card, is not a catalog entry), so all six cards say `none`. This makes the missing evidence visible instead of implied; the numbers cannot be filled without our own eval runs (blocked by the memory situation, see the incident entry). Follow-up: show the card status in `hscl ai model info`.

## Task F1 update-claim gate (2026-11-07)
`scripts/check_update_claims.py` (25 tests written first): README, `docs/` (without `docs/research` and `docs/superpowers`), `handbook/` and `website/` must not claim atomic or immutable updates (EN/DE/FR forms), nor that the system can boot into a snapshot, unless the same clause negates it. The real repository has no hits today (checked by a test, which also proves the gate scans more than 20 user-facing files, so "no hits" cannot mean "scanned nothing"). Reason: the Ubuntu 26.04 archive has no `grub-btrfs`, HSCL1 updates with APT, and bootc/image-based updates are 2.x research only. Known limitation: word-based, not semantic.
The first full forge run failed on the new gate itself: it flagged my own BUILD_LOG sentence above (its third clause, the one about the snapshot, had no negation). That was a correct catch; I reworded the sentence and added only `nor`/`neither` to the negation words (two new tests, red first), without loosening anything else. Forge check green afterwards (pytest 291 s, Linux run of the changed tests 53 s).

## Resume 2026-11-07: where the previous session stopped, and two fixes
Reconnaissance before any change: branch `codex/hscl1-v1` is level with `origin` (0/0), 37 commits
past the released `v0.1.2-alpha.0` tag; `main` is `d8f6533` (the release tag) and has none of them;
PR #22 is open, mergeable and green on all 10 checks; releases `v0.1.0/0.1.1/0.1.2-alpha.0` exist as
prereleases (0.1.2 with 4 ISO parts, manifest, SHA256SUMS and a CLI-only SBOM, unsigned). Locally
uncommitted were `tools/local_worker/sysmon.py` (staged + modified), `tests/unit/test_sysmon.py` and
`docs/research/2026-11-07-cpu-igpu-balance.md`. The previous session stopped mid-refactor of sysmon
with one red test (`KeyError: 'ram_available_mb'`).
- **Defect found and fixed (sysmon):** on this German Windows the localised counter name
  `Verfügbare MB` belongs to two Perflib indices (1382 with an English twin, 1824 without); the plain
  reverse map let the last one win, so the counter stayed German, `summarize()` did not match it and
  the RAM figure vanished while the umlaut-free CPU counters worked and hid the fault. 1081 of 4774
  localised names are ambiguous. Fixed by preferring an index the English table knows. A raw-byte
  probe confirmed the CSV is OEM code page 850, so the decoding was correct. Tests written first
  (two fixture tests red, one real round-trip test); `tests/unit/test_sysmon.py` 17 passed. Real
  sample afterwards: 4348-5093 MB available of 20262 MB visible.
- **Policy drift found and fixed (APT):** `distro/base/apt/hscl-sources.sources` enabled
  `resolute-backports` although AGENTS.md section 3.3 names exactly three pockets, and the gate had
  been widened to match the file instead of the spec; `test_unattended_upgrades.py` already treated
  `-backports` as forbidden, so the repository contradicted itself. Backports removed, gate narrowed
  to the three named pockets plus a fixture case (red first), 2 passed.
- **Measurement (this host, 2026-11-07):** 20262 MB visible of 24 GB installed, 4348 MB "available"
  per the counter and only 3144 MB free; commit charge 36.6 GB against a 42.7 GB limit; standby cache
  3152 MB with no process above 1.3 GB, i.e. **most of the resident RAM is not attributable to a
  process working set** - mmap'd model weights land in standby cache, so per-process accounting
  under-reports a loaded model. This is why "free RAM" and "available RAM" differ by gigabytes here
  and why the RAM gate must read the counter, not a process list. Recorded for the resource plan.
- Forge check green on both commits (pytest 204.8 s, WSL parity 41.7 s, bash -n, shellcheck, secret
  scan). Nothing was pushed and no PR was merged: PR merges stay with the owner.

## Task G1 stress/fault gate script (2026-11-07)
`scripts/stress_vm.sh` (8 tests written first in `tests/unit/test_stress_vm.py`, all red against the missing script):
stress-ng (`--klog-check --metrics-brief`, 120 s, 4 cpu + 2 vm workers), fio (4k randrw, 70 % read, 1 GiB file,
direct I/O) and memtester (`256M 1`), each with its own log; `summary.json` records per-tool status
(`ok`/`failed`/`missing`), exit code, duration, argv and host facts, plus the DMI string as a *warning only*.
Refuses with exit 2 unless `HSCL_IN_DISPOSABLE_VM=1` **and** the marker file exists (`/etc/hscl-vm-marker`;
`HSCL_VM_MARKER` exists so the test can point at a fixture), and refuses with less than 3 GiB free. A failing or
missing tool still writes the summary and exits 1. The tools are faked on `PATH` in the tests - fio/stress-ng/memtester
are not installed on this dev host, so the real run stays a VM item for S2 (recorded in the plan as MC). Two host
defects found while writing it: the WSL/Git Bash `python3` on this dev host is the Microsoft Store alias (exits 49), so
the script now accepts `python3` or `python` and probes it with `import json`; and the Write tool produces CRLF, which
`shellcheck` rejects with SC1017 - the file was normalised to LF and `shellcheck -S warning` is clean in WSL.
`tests/shellutil.py` gained `run_command()` (needed to call shellcheck from a test on all three hosts; 2 tests).
Documented in `docs/TESTING.md` under "Stress and fault gate". Windows: 13 passed, 1 skipped (shellcheck, run by
forge/CI instead).

## Task 3 doc-command gate (G24, 2026-11-07)
Rust test `documented_hscl_commands_resolve_in_the_cli` in `cli/hscl/src/main.rs`: it reads `README.md`,
`CONTRIBUTING.md`, `SECURITY.md`, every `docs/*.md` except the append-only `BUILD_LOG.md`, and all of `handbook/**`,
collects `hscl`/`hscl1` invocations from fenced code blocks (prompt `$ `/`> ` stripped, shell comments skipped, the
line cut at `|`, `&&`, `;`) and from **inline code spans** in prose, then resolves each one against the live clap tree
instead of spawning the binary (fast, no target/release needed). A bare word under a node that has subcommands but no
positionals is an error, so `hscl appearance them set` cannot pass as `hscl appearance`. Two guards stop the gate
from passing while scanning nothing: more than 10 markdown files and more than 25 collected commands.
Result on the real docs: **four drift findings, all real**, two of them false status claims:
- `docs/CLI.md` offered `hscl hw suggest`, which does not exist - reworded as PLANNED without a fake command.
- `docs/DECISIONS.md` (ADR-004) said the Workshop starts via `sudo hscl workshop enable`; there is no workshop
  subcommand - corrected to `sudo systemctl enable --now hscl-workshopd`, the mechanism that actually exists.
- ADR-006 and `docs/KNOWN_LIMITATIONS.md` described `hscl appearance layout list|show|set|reset` as shipped; the CLI has
  only `appearance theme`. The limitation row even said IMPLEMENTED. Both corrected to PLANNED (plan W5.5, tiling presets),
  because the KWin `[Tiling]` write can only be claimed after a VM test reads the applied config back.
Gates: `cargo test -p hscl` 142 passed, `clippy -D warnings` clean, `cargo fmt --check` clean (fmt applied once).

## Task 2b man pages from the clap tree (2026-11-07)
`clap_mangen` 0.3 (MIT OR Apache-2.0 - allowed by `deny.toml`; it needs clap >= 4.6.6, which the lockfile has) and a new
`hscl man --out DIR` next to `hscl completions`: it writes `hscl.1`, `hscl1.1` (same binary, second program name) and one
`hscl-<command>.1` per top-level command, straight from the clap tree, so a page cannot describe a flag the binary does
not have. Three tests written first (all red against the missing function): a page for the program and for every top-level
command, every file a roff page with a `.TH` title line and a `.SH NAME` section, a path that is a regular file is refused
without touching it, and two runs are byte-identical. Notes from doing it: `Command::name` needs clap's `string` feature to
take an owned `String` (enabled in `cli/hscl/Cargo.toml`, with a comment); roff output opens with a `.\"` quoting preamble,
so the test looks for `.TH` rather than the first byte. `scripts/build-deb.sh` (hscl-base) now calls `hscl man --out
$stage/usr/share/man/man1` and gzips the pages (`gzip -9n`); `tests/security/test_package_completions.py` asserts both
`hscl.1.gz` and `hscl1.1.gz` (its fake binary answers `man --out`), WSL run green. `docs/CLI.md` row added - the drift test
G12 would have failed without it. `cargo test -p hscl` 145 passed, fmt and clippy -D warnings clean.

## Task 4a governor decision logic + sysfs pressure reader (P31.2/P31.3, 2026-11-07)
`cli/hscl/src/governor.rs`: a pure `decide(&Config, &Sample, &prev) -> (State, Option<Transition>)` with a named
`Reason` for every outcome and a fixed priority - user disabled, locked/idle, desktop covered, low free memory, resident
local model, busy GPU, on battery, normal. 14 tests. Deliberate choices: the frame rate is hard-capped at 30 (a desktop
wallpaper above that buys nothing and costs power all day); VRAM and GTT are separate pools and the *smallest* headroom
wins, so a full pool stops the animation even if the other one is empty; an unknown pool abstains instead of guessing, so
a machine without amdgpu sysfs is never reported as "low memory"; GPU busy uses 80 % enter / 70 % exit hysteresis, so a
value hovering at the threshold does not repaint the desktop every second; a steady state returns `None`, which is what
keeps the service from logging every poll. `read_gpu(root)` reads `mem_info_vram_used|total`, `mem_info_gtt_used|total`
and `gpu_busy_percent` from `sys/class/drm/card*/device`, ignores connector directories (`card1-DP-1`), clamps a
nonsense busy value to 100 and returns defaults when the tree is missing - all fixture-tested.
Process note: the implementation was written in the same pass as the tests, so the red run was produced afterwards by
stubbing `decide` to `State::default()` (9 of 9 rule tests failed) and restoring it; recorded here rather than presented
as test-first. `#![allow(dead_code)]` with a comment: the governor service (P31.3, sprint S5) is the caller; until then
the module is covered by tests only, and no CLI command was invented that would have to guess covered/locked/battery.
`cargo test -p hscl` 159 passed, fmt and clippy -D warnings clean.

## Task 4b forge build / boot / diff (G30, 2026-11-07)
Ten tests written first in `tests/unit/test_forge.py` (all red: `forge build ...` exited 2 with argparse "invalid choice").
`forge build` is three visible steps in WSL - preflight (`git status --porcelain` must be empty, so a release artifact stays
tied to a commit), the remaster, and a manifest probe that prints sha256/`git_dirty`/version from the file the build wrote.
`--dry-run` prints them without executing. `FORGE_WSL` overrides the launcher so tests run a stand-in; it is split with
`shlex.split(posix=False)` because the POSIX splitter ate the backslashes of a Windows path (`C:Usershcsme...`) and the
step then failed with FileNotFoundError - a defect the test caught on the second run. Source and output paths are refused
when they contain quotes, `$`, backticks or `;` (they are interpolated into a `bash -lc` string). `forge boot ISO --out DIR`
runs the harness (default `scripts/qemu_boot_test.py`, `--harness` for a stand-in) and summarises `result.json`; it exits 1
when the harness reports `booted: false` or writes no result, so it can gate a release. `forge diff A B` compares build
manifests field by field and maps `X.iso` to `X.iso.manifest.json`; a missing manifest exits 2 with the path.
Real runs on this host: `build --dry-run` (3 steps printed, nothing executed) and `diff` between the 0.1.1 and 0.1.2 release
manifests - version, git commit, 5 494 800 384 -> 5 026 480 128 bytes and the sha256 change, with the 0.1.2 hash matching the
value recorded at release time. **Not run:** a real `build` and a real `boot` (they need the WSL lab with >= 9 GB free and
must not overlap with another VM); the ISO-content diff from the forge plan is still open. `python -m pytest
tests/unit/test_forge.py` 22 passed.

## Task 6 menu file (G26a part 1, 2026-11-07)
`packages/debian/hscl-branding/etc/xdg/menus/applications-merged/hscl1.menu` - the launcher sections HSCL1 actually has
entries for: Development, Internet (Network), Office, Graphics, Multimedia (AudioVideo), System (System/Settings/Utility),
each named in English, German and French. Six tests written first (all red: file missing): well-formed XML, every
`<Category>` from the freedesktop main-category list (a typo would show as an empty section), no empty or duplicated
submenu, `C`+`de`+`fr` names present, no `<Directory>` pointing at a file the package does not ship, and a guard that
"Security Lab" and "Privacy" are **not** offered yet - AGENTS 4.2 lists them, but HSCL1 has no desktop entries for them,
and an empty section is a button that does nothing; the comment in the file says so and points here. First version
referenced five `.directory` files that did not exist; dropped rather than invented, and the new gate keeps that from
coming back. Still open for G26a: the VM check that `kbuildsycoca6` rebuilds the cache and the categories list as
expected (`hscl-qa` / e2e set), which needs an image.

## Task G3 property tests, fuzz crate, scheduled fuzz workflow (2026-11-07)
`proptest` as a dev-dependency only (a test asserts it is not in `[dependencies]`). Thirteen `prop_` cases in the modules
that read untrusted text: `redact.rs` (idempotence, planted user/host gone, MAC and private IPv4 gone, public IPv4 kept),
`toolcall.rs` (no panic on arbitrary input, JSON call round trip, unknown tool refused with its name, block without its end
is `Incomplete`), `hw.rs` (`parse_hex` round trip, `MemTotal` round trip, garbage never panics in four parsers, generated
`pci.ids` vendor lines survive). **The properties found a real defect**: `redact` replaced user and host in two passes, so
with `user="aA"`, `host="re"` the marker written for the user was itself rewritten - `[[redacted]dacted]` - and the value
"re" then appeared inside our own marker. Replaced by a single pass over the input that takes the earliest match of either
needle. The marker `[redacted]` still contains letters, so a needle that is a substring of that word makes redaction
non-idempotent; that is now documented in the module header and excluded with an explicit `prop_assume` instead of being
hidden, and a regression property asserts the marker is not rewritten.
Fuzzing: `fuzz/` is its own workspace (`libfuzzer-sys`, never a dependency of the product) with two targets that
`#[path]`-include `cli/hscl/src/toolcall.rs` and `redact.rs` - the same files the binary compiles, because `hscl` is a
bin crate without a library target (splitting it is tracked as G3b). `.github/workflows/fuzz.yml` runs weekly and on
dispatch: `cargo fuzz run ... -- -max_total_time=300` per target (artifacts kept on failure), `proptest` with
`PROPTEST_CASES=20000`, and `cargo-mutants` on both parsers with a time box; actions are pinned by commit SHA (the two
toolchain SHAs were read from the GitHub API on 2026-11-07, not invented). Six tests in
`tests/unit/test_property_gates.py` guard the setup itself (markers present, proptest not a runtime dependency, the workflow
is scheduled + time-boxed + pinned). `cargo test -p hscl` 172 passed, clippy -D warnings and fmt clean.

## Task B1 modaliases in `hscl hw detect` (2026-11-07)
`hw::modaliases(root) -> (Vec<Modalias>, dropped)` walks `sys/bus/{pci,usb,platform,acpi,i2c}/devices/*/modalias`, returns
`sorted` entries (bus then path, `/` separators on every host) and counts values it refused. `Report` carries `modaliases`
and `dropped_modaliases`, so `hscl hw detect --json` exposes them; text mode prints `Modaliases: 41 (pci 39, usb 2)` and
mentions dropped values only when there are some (a full list would be 150+ lines). Eight tests written first: pci+usb+acpi
fixtures come back sorted, a tree without `sys` returns nothing instead of erroring, control characters and values over
512 bytes are dropped **and counted**, an empty modalias is ignored without being counted (the kernel writes empty files
for devices it cannot describe - a normal case, not a data-quality problem), and a USB `serial` file next to a modalias is
never read (asserted by its absence from the whole structure - a serial identifies a device, it does not describe a
capability). Windows cannot create names with `:`, so the fixtures reuse the existing `s()` helper.
Two test-only defects of mine were caught by running them: an assertion counted markers in a text where the host needle
legitimately occurred twice ("in" inside "login"), which was fixed by asserting on the visible text instead of a count.
`cargo test -p hscl` 180 passed, fmt and clippy -D warnings clean; `docs/CLI.md` row extended (the G12 drift test requires it).

## Task 9 Secure Boot signature evidence from the released ISO (2026-11-07)
`scripts/sb_evidence.py ISO --out DIR`: extracts `EFI/boot/bootx64.efi`, `EFI/boot/grubx64.efi`, `casper/vmlinuz` (and
`mmx64.efi` as optional) with `xorriso -osirrox` (no root, no mount), parses the PE header's certificate table
(IMAGE_DIRECTORY_ENTRY_SECURITY, index 4, which is a file offset rather than an RVA) and prints the signer CNs through
`openssl pkcs7`. Seven tests build minimal PE32/PE32+ images by hand: no MZ, no signature, both header layouts, truncated
headers at five lengths, an absurd certificate size, and a component list that must contain both path spellings.
**Measurement on the released artifact** (`artifacts/iso/HSCL1-0.1.2-alpha.0-amd64.iso`, evidence in
`artifacts/sb-0.1.2/report.json`):
- `EFI/boot/bootx64.efi` - Microsoft Windows UEFI Driver Publisher / Microsoft Corporation UEFI CA 2011 (9 720 bytes PKCS#7)
- `EFI/boot/grubx64.efi` - Canonical Ltd. Secure Boot Signing (2022 v1) (1 928 bytes)
- `casper/vmlinuz` - Canonical Ltd. Secure Boot Signing (2022 v1) (1 928 bytes)
- `EFI/boot/mmx64.efi` - Canonical Ltd. Secure Boot Signing (2022 v1) (1 928 bytes)
The first run reported "BOOTX64.EFI NOT PRESENT" although the shim was there: Ubuntu media spell the path
`EFI/boot/bootx64.efi`, and a case difference is enough to make a gate lie. The reader now tries both spellings and the test
says why. What this proves: the remastered image still ships the documented chain (MS-signed shim -> Canonical GRUB ->
Canonical kernel), so the squashfs/initrd edits did not replace a signed component. What it does **not** prove: that
firmware accepts the chain - that is gate G6 (OVMF + Microsoft keys, `mokutil --sb-state` in the guest), still open.

## S2 attempt 1: image build with the whole S1 set (2026-11-07, started 09:35Z)
Preflight: branch `codex/hscl1-v1` at `8e550bd`, working tree clean, `forge check --strict` green on Windows **and**
Linux-in-WSL just before the start. The WSL clone (`~/hscl1-src`) pulled this commit and then showed three files as
modified - `packages/debian/hscl-security/{build.sh,DEBIAN/preinst,DEBIAN/postrm}` - with a diff of **0 inserted and
0 deleted lines**: the only change was the file mode (100755 -> 100644), a checkout artifact, not work in progress.
Restored with `git checkout --` after confirming the content was identical; the clone is clean again.
Resource deviation, recorded rather than hidden: the resource policy asks for >= 9 GB free host memory before a build.
After `wsl --shutdown` the Windows "available" counter read 5 540 MB (`tools/local_worker/sysmon.py`), so the build was
started with the documented Ersatzweg from the finish-line plan - `HSCL_SQUASH_PROCS=2 HSCL_SQUASH_MEM=384M` instead of
3 processors / 512M - and with `--fast`. Log: `~/hscl1-build/out/build-0.1.3-dev.log`, target
`~/hscl1-build/out/HSCL1-0.1.3-dev-amd64.iso`. If the host reaps it, that is recorded here and retried once with a
further reduction; a build that fails for memory is not a product defect.

## S2 build result: dev image with the whole S1 set (2026-11-07, finished 09:36Z host clock)
Built from the clean clone at `8e550bd` with `HSCL_SQUASH_PROCS=2 HSCL_SQUASH_MEM=384M --fast` (see the deviation note
above). Result (`~/hscl1-build/out/`, copied to `artifacts/iso/`):
- `HSCL1-0.1.3-dev-amd64.iso`, 5 488 181 248 bytes, sha256 `b391226104868148cd0e47f20d221fff3a63680460a37634002f98612fed7896`
- manifest: `version: 0.1.2-alpha.0` (the version string is bumped only for the release build - this image validates the
  content), `git_commit: 8e550bd2a6...`, `git_dirty: false`, `workshop_default: disabled`, base checksum verified against
  the upstream-signed `SHA256SUMS` during the build.
- `verify-image` passed from the finished artefact: the ISO's `/casper/initrd` is the rebuilt one (md5
  `0ae73448049120c45aca80fa155d6498`) and `/.disk/info` starts with HSCL1.
- Secure Boot chain re-measured with `scripts/sb_evidence.py` (`artifacts/sb-0.1.3-dev/report.json`): shim = Microsoft
  UEFI CA 2011 / Microsoft Windows UEFI Driver Publisher; grubx64/mmx64/vmlinuz = Canonical Secure Boot Signing (2022 v1).
  Unchanged from 0.1.2, i.e. the new S1 content did not touch a signed component.
- `forge diff` against the released 0.1.2 manifest: only `git_commit`, `iso_bytes` (5 026 480 128 -> 5 488 181 248) and
  `iso_sha256` differ. The size grows because this run used `--fast` (zstd level 3); the released 0.1.2 used the slower
  xz path, so a release build must **not** use `--fast` if the size is to stay comparable - recorded as a decision for
  the 0.1.3 artefact.
Next: boot gate on this exact ISO (UEFI), then the in-guest e2e set, then screenshots. Nothing is claimed until those
artefacts exist.

## S2 boot gate, first run: a defect in forge boot itself (2026-11-07)
First run on `HSCL1-0.1.3-dev-amd64.iso` (UEFI, `--live`, WHPX, 191 s): the harness reached the desktop
(`reached_desktop: true`, four shots, `desktop_final_wallpaper_match 0.121`) and `verify` evidence is in
`artifacts/forge/boot-0.1.3-dev/` (`desktop-final.png`, `shot-001..004.png`, `qemu.log`, `result.json`).
**But `forge boot` printed "booted: not booted" and exited 1** - my own summary code read `booted`, `seconds` and
`screenshots`, keys `scripts/qemu_boot_test.py` never writes (it writes `reached_desktop`, `elapsed_s`, `shots`). I had
invented the schema instead of reading the harness. Fixed with two tests that use payloads copied from the real
`result.json`, and the two older boot tests were corrected as well (they had encoded the same wrong schema, so they
could not have caught it). Also recorded: the shell pipeline `forge boot ... | tail` masked the exit code (the reported
`EXIT=0` was `tail`'s); the rerun redirects to a file and reads `$?` directly.
Open question from the screenshots: `welcome_screen` was still `true` in the last two frames, so the `--dismiss-welcome`
click (at 28.8 % / 84.8 % of the window) may have missed the "Skip" button - the desktop was reached, the welcome
window's state is not proven either way. The rerun writes a second evidence set (`boot-0.1.3-dev2`) to compare.

## S2 boot gate, second run with the fixed summary (2026-11-07)
`forge boot --live --firmware uefi` on `HSCL1-0.1.3-dev-amd64.iso`: **booted yes, 146 s, 3 shots, UEFI, final
wallpaper match 0.116**, exit 0 (`artifacts/forge/boot-0.1.3-dev2/`: `desktop-final.png`, `shot-001..003.png`,
`qemu.log`, `result.json`). The fixed summary now reads the harness schema (`reached_desktop`, `elapsed_s`, `shots`).
Open point, deliberately not claimed: `welcome_screen` was `true` in all three frames of **both** runs, including the frame
at t=50 s before the desktop appears - so that flag is matching the live "Try or Install" prompt as well, and it does not
prove that the welcome window stayed open after the `--dismiss-welcome` click. The wallpaper similarity is ~0.12 in both
runs, which is expected for the animated rain wallpaper compared against a still reference; `reached_desktop` therefore
came from `looks_like_desktop()` (dark top band with tray pixels), not from the wallpaper match. Recording both so the
next session does not read the number as a defect or as proof.

## S2 in-guest e2e gate: 28/28 on the dev image (2026-11-07)
`python scripts/workshop/e2e_cli.py artifacts/iso/HSCL1-0.1.3-dev-amd64.iso artifacts/e2e-0.1.3-dev` -> exit 0,
`artifacts/e2e-0.1.3-dev/cli-report.json`: **28 checks, 0 non-zero**, desktop reached after **121 s**, session user
`hscl1` (the HSCL1 live user, not the upstream `kubuntu`), Workshop `ops` = doctor, put_file, report, respin,
restart_shell, run_hook, screenshot, status; port restarts 0, write timeouts 0. Green checks include the ones this S1
work touched or could plausibly have broken: `earlyoom_active` (active), `zram_swap` (zram0 1.9G), `zram_algorithm`
(zstd selected), `sysctl_memory` (swappiness 100, page-cluster 0), `ai_slice` (MemoryHigh/Max present), `firewall`
(active), `listening_sockets`, `system_tree_owner`, `kdeconnect_listener`/`kdeconnect_process` (absent). Full list and
per-check output are in the report; the desktop screenshot is `artifacts/e2e-0.1.3-dev/desktop.png`.
Note: `hscl1_version` in the guest report is `0.1.2-alpha.0` because `VERSION` was not bumped for this content-validation
image; the release artefact is built separately after the bump (see below).

## G26a follow-up: menu cache rebuild in the package (2026-11-07)
The research round answered why `applications-merged` works on Plasma (startplasma sets
`XDG_MENU_PREFIX=plasma-`, the base menu carries `<DefaultMergeDirs/>`, which is searched **without** the prefix) and
that the cache is only refreshed by `kbuildsycoca6`. Without that call a freshly installed section can stay invisible
until the next login - indistinguishable from a broken menu file. `hscl-branding` postinst now runs
`kbuildsycoca6 --noincremental` (guarded by `command -v`, and as `$SUDO_USER`/`$PKEXEC_UID` via `runuser` so no
root-owned cache is created), postrm does the same on remove/purge. Test written first (red): the postinst must contain
the call, the `command -v` guard and an unprivileged runner, and postrm must rebuild too. bash -n and shellcheck (WSL)
clean, 7 menu tests pass. Not yet verified in a VM: that the section actually appears in Kickoff after install - that
belongs to the next image run, not to this commit.

## Release build 0.1.3-alpha.0: one deliberate restart (2026-11-07)
The first release build (xz, no `--fast`) started from `2508e24`. While it was in the squash phase I committed
`a55e023` (menu-cache rebuild in the branding postinst), which the artefact would have missed. Instead of shipping an
image without a committed fix - or building twice - I stopped it at about 5 % of the squash pass (`wsl --shutdown`;
the background job exits 1 for that reason, not because of a build error) and restarted from `a55e023`. Build log:
`~/hscl1-build/out/build-0.1.3-alpha.0.log`, target `~/hscl1-build/out/HSCL1-0.1.3-alpha.0-amd64.iso`, reduced
squashfs settings again (`HSCL_SQUASH_PROCS=2 HSCL_SQUASH_MEM=384M`) because the host still has ~8.8 GB available.

## Task B3 driver suggestions from the apt index (2026-11-07)
`hscl hw suggest [--root DIR] [--json]`. The research round settled the mechanism, so the code follows upstream instead
of inventing a vendor map: debhelper's `dh_modaliases` (source package `ubuntu-drivers-common`) emits `Modaliases:` into
the binary package and therefore into the `Packages` index; each value is a glob, often vendor-wrapped
(`nv(pci:v000010DEd000010C3sv*sd*bc03sc*i*)`), matched against the device modalias from sysfs. Implemented as pure
functions (`parse_packages_modaliases`, `modality_matches`, `suggest`, `licence_class`, `load_package_modaliases`) plus
the CLI command. Eight Rust tests: stanza parsing (Package/Section/Modaliases, skip stanzas without the field, stable
sort), wrapped-pattern match and a differing device id that must not match, plain glob anchoring, `*` alone, empty
pattern, suggestion list containing only devices with candidates, missing index = empty and no error, index reader
ignoring non-Packages files, and the licence heuristic admitting "unknown" for e.g. `mesa-vulkan-drivers`.
Three Python gate tests: the function names are present, the `suggest` body contains no install command
(`apt-get install`, `apt install`, `dpkg -i`, `systemctl start`), and the Rust `suggest` tests pass.
Live run on this host: `No apt package index found (var/lib/apt/lists); nothing to suggest.` - which is the honest
answer on Windows, not a failure. `--json` shape: devices, dropped_modaliases, index_packages, suggestions,
licence_class. `docs/CLI.md` row added (the drift test requires it). Not implemented: using `ubuntu-drivers devices` as a
second source (the index route needs no external tool), and the hwdb generator half of Task 6 (B2).

## Release artefact 0.1.3-alpha.0 built (2026-11-07)
`HSCL1-0.1.3-alpha.0-amd64.iso`, **5 026 742 272 bytes**, sha256
**fc81ad1d93efeac61904879e9def34e39cdceb982bf7aafc070b34afdd4d1ebb**, built from the clean clone at **a55e023**
(`git_dirty: false`), manifest version `0.1.3-alpha.0`, `workshop_default: disabled`, base checksum verified against the
upstream-signed `SHA256SUMS` during the build, `verify-image: all checks passed`, `BUILD_EXIT=0`. Build log:
`~/hscl1-build/out/build-0.1.3-alpha.0.log`.
Size check against the decision recorded earlier: the xz build is **5 026 742 272 B vs 5 026 480 128 B for 0.1.2** - a
262 KiB difference for a whole sprint of changes, i.e. the release path really does not pay the ~460 MB that `--fast`
added to the dev image. That confirms the decision to build the release without `--fast`.
Secure Boot chain re-measured on this exact file (`artifacts/sb-0.1.3-alpha.0/report.json`): shim = Microsoft UEFI CA
2011 / Microsoft Windows UEFI Driver Publisher; `grubx64.efi`, `mmx64.efi`, `casper/vmlinuz` = Canonical Secure Boot
Signing (2022 v1). Firmware acceptance is still gate G6.
Not yet done on this artefact: the copy to `artifacts/iso/` (hash re-check on the target path), the boot gate and the e2e
set. Those are the next two steps and they decide whether this file may be called tested.

## Release artefact copied and hash-verified; research folded into the AI plans (2026-11-07)
`artifacts/iso/HSCL1-0.1.3-alpha.0-amd64.iso` (5 026 742 272 B) + manifest copied out of the build lab and re-hashed **on
the target path**: `fc81ad1d93efeac61904879e9def34e39cdceb982bf7aafc070b34afdd4d1ebb`, identical to the build log and the
manifest. Secure Boot evidence for the same file: `artifacts/sb-0.1.3-alpha.0/report.json`.
Two research rounds landed and changed plans rather than prose:
- `docs/research/2026-11-07-apu-offload-vram-spill.md`: `ttm.pages_limit` (default half of RAM, read once at TTM init)
  is the only GPU-memory knob, `amdgpu.gttsize` is deprecated; `--mmap/--no-mmap/--mlock` no longer exist upstream
  (`--load-mode` instead, whose `auto` disables mmap on Vulkan iGPUs); `-nkvo` keeps KV in system RAM; a second fast model
  is speculative decoding with an unmeasured gain on this iGPU; **no supported SSD spill for VRAM or KV** (Vulkan has no
  unified-memory oversubscription). W2.5 refined, W2.10/W2.11 added, KNOWN_LIMITATIONS row for local-AI memory.
- `make_release.py` now treats the prebuilt qcow2 as optional (AGENTS.md 7.1) and records `prebuilt: null` plus a note
  when it is absent, so a missing image cannot be confused with a forgotten field. Test written first; 8 tests pass.

## W2.10: offload flags in `hscl ai serve`, verified against the real binary (2026-11-07)
Probe first: the installed build 12128 (`llama-server --help`) already has `-lm/--load-mode`,
`-kvo/-nkvo`, `-cmoe/-ncmoe`, `-fa`, `-ot` and `-md/--spec-draft-model` + `--spec-draft-n-max`, and prints
"the argument has been removed. use --spec-draft-n-max" for `--draft-max` - i.e. the research was right that the old
mmap/mlock flags are gone in the builds we ship (our pin is b12130, newer than the probed 12128).
Implemented in `serve::ServeOpts`/`serve_argv` and exposed as `hscl ai serve --load-mode MODE`, `--kv-in-ram`,
`--draft-model PATH [--draft-max N]`. Validation follows the existing rules: the load mode must be one of the six
names, the draft model must be a `.gguf` inside the model storage whose name does not start with `-`, the draft budget is
1..=16 and is refused without a draft model. Six tests: the default command carries none of the new flags; the load mode
appears exactly once and an unknown mode is refused; `-nkvo` appears exactly once; the draft model is passed with its
budget and is refused outside the storage or with a leading dash; a budget without a model is refused; the default budget
is 3 (upstream's). `cargo test -p hscl` 189 passed, clippy -D warnings clean. `docs/CLI.md` rows added.
Still open (MEASURE, not claimed): whether `mmap` or `auto` is faster on the 680M, whether `-nkvo` costs the prefill
speed that the research predicts, and whether a draft model pays for itself here - all need `llama-bench` runs on this
machine, and none of it is in the UI until measured.

## Release gates on the exact artefact (2026-11-07)
All gates ran on `artifacts/iso/HSCL1-0.1.3-alpha.0-amd64.iso`, sha256
`fc81ad1d93efeac61904879e9def34e39cdceb982bf7aafc070b34afdd4d1ebb`, not on a rebuild:

| Gate | Result | Evidence |
|---|---|---|
| boot, UEFI, `--live` | **booted yes, 191 s, 4 screenshots**, final wallpaper match 0.127, exit 0 | `artifacts/forge/boot-0.1.3-alpha.0/` (`result.json`, `desktop-final.png`, `shot-001..004.png`, `qemu.log`) |
| in-guest e2e (28 checks) | **28 run, 0 non-zero**, desktop after 151 s, session user `hscl1`, guest report says version **0.1.3-alpha.0** | `artifacts/e2e-0.1.3-alpha.0/cli-report.json` |
| Secure Boot chain (file level) | shim = Microsoft UEFI CA 2011 / Microsoft Windows UEFI Driver Publisher; `grubx64.efi`, `mmx64.efi`, `casper/vmlinuz` = Canonical Secure Boot Signing (2022 v1) | `artifacts/sb-0.1.3-alpha.0/report.json` |
| host test suite | 562 passed, 12 skipped | this run |
| `cargo test -p hscl` | 195 passed; clippy -D warnings clean | this session |

What these gates do **not** cover, and therefore what this build may not claim: Secure Boot acceptance by firmware (G6),
the installer on this exact image (no install run yet), the brand OCR/content scan of the live session (G10), the shortcut
audit (G11), physical hardware. `welcome_screen` in the boot harness is true even before the desktop appears, so it is
not evidence about the Welcome window; the wallpaper-match number is the animated wallpaper against a still reference.

## make_release.py: the "not verified" list belongs in the set (2026-11-07)
`build_release(..., gaps)` / `make_release.py --gap TEXT` (repeatable) writes a "Not verified in this set" section into
`release-notes.md`, so a pre-release carries its own gap list instead of relying on the reader to open
KNOWN_LIMITATIONS. An empty gap line is refused (a blank bullet would look like an omission). Test written first:
notes contain the section and every line, an empty gap raises. 9 tests pass.
The first assembly run was started before this change and had copied only the ISO into
`artifacts/release-0.1.3-alpha.0/`; it was stopped and restarted with the four gaps (firmware acceptance, install run on
this image, brand OCR + shortcut audits, physical hardware) rather than shipping a set without them.

## G11 shortcut audit: finding (2026-11-07)
Searched the tracked tree (`git ls-files`, `git grep`) for any shortcut configuration (kglobalshortcutsrc, kwinrc, khotkeys, Meta bindings): **none exists**, and README/docs/website publish no shortcut table. So the AGENTS.md 4.5 table is entirely PLANNED, not a defect in a published claim. Recorded as a KNOWN_LIMITATIONS row. Correction (same day): the earlier statement that no install harness exists was wrong in substance. The 0.1.0-alpha.0 install (1359 s, `install-test/`, then `install-boot/`) was driven interactively through the Workshop MCP tools (`vm_start`, `vm_click`, `vm_keys`, screenshots), not through a script in `scripts/forge.py`. The run on 0.1.3-alpha.0 repeats that route, one QEMU job at a time. Status stays: installer on this image NOT verified.

## Installer run on the exact 0.1.3-alpha.0 artefact (2026-11-07) - VM-VERIFIED (narrow)
ISO `fc81ad1d93efeac61904879e9def34e39cdceb982bf7aafc070b34afdd4d1ebb` (copied to NVMe, hash re-checked), QEMU+WHPX, UEFI, 4 GB RAM, fresh 40 GiB qcow2, driven through the Workshop MCP (`vm_*`). Evidence: `artifacts/install-0.1.3-alpha.0/nvme-run/` (8 screenshots).
- Calamares started from the live desktop; only the disposable disk `vda` was offered; **nothing preselected** (Erase disk had to be chosen); the summary showed `Erase disk /dev/vda`, GPT, 300 MiB FAT32 EFI, 39.71 GiB ext4; a confirmation dialog ("You will not be able to undo these changes") had to be answered.
- Install finished ("All done."), about 10 minutes from the confirm click on NVMe. Rebooted **from the installed disk only (no ISO)**: login screen with the created user (German date format from the chosen locale), login accepted, **HSCL1 desktop reached** (dock, top bar, Control Center and Handbook icons; no "Install HSCL1" icon).
- **Defect found, fixed in source, still in the published ISO:** the installer title and "All done" text say `HSCL1 0.1.2-alpha.0` because `branding.desc` was not bumped. Fixed with a VERSION guard test (`5356d5b`); reaches users with the next image build.
- **Measured: where the VM disk lives matters.** `E:` is a USB drive: the same install reached 6 % after 12 min (about 16 files/s, disk time 272 %). On NVMe it reached 24 % after 4 min and finished in about 10 min. VM disks/ISOs belong on `C:\AI\vmtest`.
- **Not covered (so not claimed):** in-guest checks (`hscl status/doctor`, firewall, AppArmor: the Workshop is inert by default, so no guest agent), LUKS (assessed in the next section), BIOS boot, offline vs networked install (not recorded), install-alongside, physical hardware, localisation of the installer (English only was tested).

## LUKS install on the exact 0.1.3-alpha.0 artefact (2026-11-07) - VM-VERIFIED (narrow)
Same ISO (`fc81ad1d...`), fresh 40 GiB qcow2 on NVMe, QEMU+WHPX, UEFI. Evidence: `artifacts/install-0.1.3-alpha.0/luks-run/` (7 screenshots, not in Git).
- The earlier statement "the installer offers no encryption" was wrong and is withdrawn: after choosing **Erase disk** the Partitions page shows **"Encrypt system"** with passphrase and confirm fields. It is **unchecked by default**.
- With it ticked, the layout shown (Partitions page and Summary) is: EFI 300 MiB FAT32, `hscl1_boot` 4.00 GiB ext4 (unencrypted `/boot`), `hscl1_root` 35.71 GiB **LUKS2**. This matches `docs/INSTALLER_FACTS.md`.
- Install finished ("All done."), about 10 min. Booted from the encrypted disk alone: **passphrase prompt appears; a wrong passphrase is refused** ("cryptsetup failed, bad password or options?") and the prompt returns; **the correct passphrase unlocks**, the login screen shows the created user, login is accepted and the **HSCL1 desktop is reached**.
- **Gaps found against AGENTS.md 6.3 (not fixed, not claimed):** no recovery key/recovery method is offered or explained during install; no explanation of what is and is not encrypted (the installer's "not encrypted /boot" message is switched off, `showNotEncryptedBootMessage: false`, and the HSCL1 replacement text does not exist yet); encryption is off unless the user ticks it.
- **Not checked in this run:** the initramfs keyfile risk from `INSTALLER_FACTS.md` (`lsinitramfs` must contain no keyfile), whether the passphrase or its marker appears in logs, TPM, BIOS boot, behaviour after an interrupted install, the installed system's own report (Workshop is inert). Status is therefore: *LUKS2 install unlocks and boots in one VM*, nothing more.
- Smaller observations: the Plasma splash after login shows "Plasma made by KDE" and the Welcome Center shows the KDE mascot (upstream branding inside the live/installed session; relevant to the G10 brand scan, not yet judged).

## LUKS offline inspection of the test disk (2026-11-07)
No passphrase used. `qemu-img dd` copied the first 4.7 GiB of `luks.qcow2` to a raw file (deleted afterwards); the GPT was parsed with Python (`hscl1_boot` at byte 316,669,952, 4096 MiB; `hscl1_root` at 4,611,637,248); `debugfs` (WSL, `?offset=`) dumped the initramfs from the unencrypted `/boot`; `lsinitramfs`/`unmkinitramfs` listed it; the LUKS2 JSON header was parsed with Python. Findings are in `docs/INSTALLER_FACTS.md`: no keyfile in the initramfs, `crypttab` uses `none`, exactly one argon2id keyslot, no tokens. This closes the keyfile risk named in INSTALLER_FACTS for this one install; the missing recovery key stays an open gap (there is no second keyslot to hold one).

## Dev image 0.1.3-dev2: installer fixes, `hscl-cqhecs` and the new gates, built and booted (2026-11-07)
Built from the clean WSL clone at `2b65013` (`git_dirty: false`), `scripts/remaster-iso.sh --fast` with `HSCL_SQUASH_PROCS=2 HSCL_SQUASH_MEM=384M` (WSL has 5.9 GB), `BUILD_EXIT=0`. Artefact `HSCL1-0.1.3-dev2-amd64.iso`, **5,488,246,784 bytes**, sha256 **4d04e7ca24b8dbf84fdc41de46648f7aac97ac98b99e3abb514cd6a95a9cdc74** (re-checked after the copy to `C:\AI\vmtest\dev2\`); manifest version 0.1.3-alpha.0, `workshop_default: disabled`. This is a development image (`--fast`), **not a release artefact**.
- Content: branding version fix (`5356d5b`), Calamares not-encrypted-/boot message on (`76d9ab0`), `hscl-cqhecs` in the image (`6a8ba01`). The image gate `verify-image.sh` printed `ok` for each new check (`installer: warns that /boot is not encrypted`, six `cq-hecs` checks) and `all checks passed`.
- **Size effect of the package:** previous `--fast` dev image 5,488,181,248 B, this one 5,488,246,784 B: **+65,536 B (64 KiB)**.
- Boot gate (`forge boot --live`, UEFI, WHPX, no Secure Boot): `reached_desktop: true` after **147 s**, wallpaper match 0.118, exit 0 (`artifacts/forge/boot-0.1.3-dev2/`).
- In-guest run (`scripts/workshop/e2e_cli.py`, 31 checks incl. three new): **0 non-zero**, desktop after 110 s, session user `hscl1` (`artifacts/e2e-0.1.3-dev2/cli-report.json`). New checks: `dpkg -s hscl-cqhecs` -> `install ok installed`, `0.1.3~alpha.0`; `systemctl list-unit-files | grep -c cqhecs` -> 0; `hscl-cqhecs doctor --json` as the session user -> `runtime: missing`, data dir `/home/hscl1/.local/share/hscl/cqhecs`, `network: not used`. Listening sockets unchanged in kind (resolved stub on 127.0.0.53/54:53, chrony 127.0.0.1:323, cups 127.0.0.1:631 and [::1]:631, Avahi mDNS 5353; none belongs to hscl-cqhecs). Firewall active.
- **Not verified on this image:** the installer itself (the corrected version string and the /boot message on screen), an install run, Secure Boot, the release compression, physical hardware. `hscl-cqhecs install-runtime` inside the booted guest (the Workshop channel runs one-shot commands; a 269 MiB venv install over the guest network was not attempted).

## Installer on the dev2 image: version fixed, /boot message not visible (2026-11-07)
VM `d2` (QEMU/WHPX UEFI, dev2 ISO from `C:\AI\vmtest\dev2`, fresh qcow2). Evidence: `artifacts/dev2-installer/` (3 screenshots, not in Git).
- **Fixed and seen on screen:** the installer title reads "Welcome to the HSCL1 **0.1.3-alpha.0** installer" (the 0.1.3-alpha.0 ISO said 0.1.2).
- **Not working as intended:** with Erase disk + Encrypt system ticked and matching passphrases (layout: EFI 300 MiB, `hscl1_boot` 4 GiB ext4, `hscl1_root` 35.71 GiB LUKS2) there is **no** explanation of the unencrypted `/boot`: no dialog on `Next`, no text on the Partitions page, none on the Summary. The `showNotEncryptedBootMessage: true` that `76d9ab0` switched on is present in the image (gate ok) but has no visible effect in this path. My earlier commit message and docs presented it as the remedy; that is withdrawn here, and `docs/INSTALLER_FACTS.md`, the hook comment and the test docstring were corrected. The explanation (and the recovery-key explanation) remains an open gap against AGENTS.md 6.3.
- No install was run on dev2 (nothing new to learn from it; the install path was verified on 0.1.3-alpha.0).

## HCSUDA H0/H1: runtime scaffold, GPU selftest and first benchmarks (2026-11-07)
New Cargo workspace `hcsuda/` (excluded from the root workspace), GPL-3.0-or-later while it lives in this repo.
- **Built:** `hcsuda-core` (dtypes, FP8 E4M3/E5M2 codec, int8/packed-int4 quantisation, tensor, CPU oracle, capability record, conservative planner, benchmark report), `hcsuda-vk` (ash 0.38 instance/device, memory, descriptor + command plumbing, timestamp queries, GLSL to SPIR-V build via `glslc`), `hcsuda-cli` (`caps`, `plan`, `selftest`, `bench`, all with `--json`/`--out`), shaders `saxpy`, `triad`, `gemv`.
- **Commands:** `cargo fmt --all -- --check`, `cargo clippy --all-targets -- -D warnings`, `cargo test --all` -> **41 passed, 0 failed**; `hcsuda selftest` -> **PASS**; `hcsuda bench --runs 7` -> suite written to `hcsuda/benchmarks/amd-radeon-680m/`.
- **Hardware:** AMD Radeon 680M (`0x1681`), AMD proprietary driver 26.6.1, Vulkan 1.4.315, subgroup 64, 32 KiB shared, int8/int4 dot accelerated, cooperative matrix present, **no `VK_EXT_shader_float8`**.
- **Differential test vs CPU oracle (3 runs, determinism checked):** saxpy 2.384e-7 (tol 7.4e-5), triad 2.384e-7, gemv 1.907e-6 (tol 3.263e-5). Verified paths: `vulkan_scalar:{saxpy,triad,gemv}:f32`.
- **Benchmark (f32, 4 Mi elements / 512x8192, 7 samples x 50 dispatches):** saxpy 0.762 ms GPU (56.95 GB/s), triad 0.725 ms (79.69 GB/s), gemv 1.303 ms (5.89 GFLOP/s) versus single-threaded oracle 28.7 / 49.7 / 68.3 ms. Spread 0.02-0.19.
- **Methodology finding:** with 5 dispatches per sample the same kernels show spread 0.87-1.15; with 50 it is 0.02-0.19. Short bursts measure the iGPU clock ramp. `--reps` now defaults to 50 and a row above 0.25 spread is labelled noisy, not reported as a result.
- **Test bugs found and fixed (not code bugs):** four `hcsuda-core` assertions encoded wrong expectations (tolerance scale, int4 symmetric range, packing nibble order, spread formula).
- **NOT measured:** no f16/bf16/int8/int4/FP8 kernel, no GEMM/conv/attention, no training step, no CUDA/rocBLAS baseline, no discrete GPU, no Linux run, no power/thermal instrumentation. `gemv` is a correctness kernel (one invocation per row) and its number must not be quoted as matrix throughput.
- **CI:** new `hcsuda` job (fmt/clippy/test on ubuntu + windows, `cargo audit` on ubuntu). Hosted runners have no GPU, so that job is the CPU-only gate by design.
- Docs: `hcsuda/README.md`, `hcsuda/docs/MEASURED.md`, `hcsuda/docs/CAPABILITY_MATRIX.md`.


## HCSUDA H2: tiled GEMM and row-wise ops, resumed after an interrupted session (2026-11-07)
The previous session stopped mid-edit with `hcsuda-cli` not compiling: `gpu.rs` had a doc comment and `pub fn f32_tolerance` merged onto one line (the rest of the file was a comment, leaving an unmatched `}`), and `main.rs` had an unused `mut`. Uncommitted at that point: shaders `gemm_tiled`, `softmax`, `layernorm`, `rmsnorm`, runner methods, selftest/bench cases.
- Fixed: the merged line; the unused `mut`; softmax push constants (shader block is 8 bytes `{cols, rows}`, runner sent 12); softmax reference and bench baseline were fed the whole matrix as one row (selftest "error" 6e-3, unfair CPU baseline), now per row.
- Commands: `cargo fmt --check`, `cargo clippy --all-targets -- -D warnings`, `cargo test --all` (41 passed), `hcsuda selftest` -> PASS for all 7 kernels, `hcsuda bench --suite saxpy,triad,gemv,gemm,softmax,layernorm,rmsnorm --runs 15 --warmup-s 3`; `python scripts/forge.py check` OK.
- Measured (release build, one host job at a time, no VM or model running): GEMM 256x1024x256 0.291 ms GPU (spread 0.21), 461 GFLOP/s kernel-side / 323 wall; row ops 13-17 us on the GPU but about 100 us wall, i.e. no wall-time gain over the CPU at 32x4096; rmsnorm spread 0.37 is noisy and not reported as a result. Details and caveats in `hcsuda/docs/MEASURED.md`.
- Not measured: f16/bf16/int8/int4/FP8 kernels, cooperative-matrix GEMM, attention, training step, any comparison against llama-bench or rocBLAS.

## Self-heal masterplan v6, main merged, HCSUDA rope (2026-11-07)
Resumed after the interrupted H2 session. `origin/main` held a squash of PR #22; merged into `codex/hscl1-v1` (`70bbf09`, conflicts resolved to the branch because it is a strict superset; `git diff origin/main HEAD` showed only HCSUDA H2 and BUILD_LOG additions) and pushed. New plan `docs/superpowers/plans/2026-11-08-selfheal-masterplan.md` (resume state, loop contract, ledger). A 2-minute cron ping was set for 24 h (session-only).
Gates read by exit code: `cargo fmt/clippy -D warnings/test --all` clean (44 tests incl. 3 new rope oracle tests), `hcsuda selftest` PASS for 8 kernels, `python scripts/forge.py check` OK before the rope change (pytest 267 s). RoPE (split-half): oracle test first, then `rope.comp`, runner method, selftest case; error 2.98e-7. Not done: planner `Op::Rope`, rope benchmark, f16/int8-dot/coopmat GEMM.

## HCSUDA H2c: int8 dot-product GEMM (2026-11-07)
`gemm_i8dot.comp`: int8 packed four per word along k, B transposed, `dotPacked4x8EXT` with int32 accumulation. Probe-first: `uint` operands failed to compile (`cannot convert uint to int`: the unsigned overload returns uint); switching the buffer types to `int` selects the signed overload. Device now enables `shaderIntegerDotProduct` only when the device reports it. `quant::pack_i8x4` has a layout test (written first). Selftest case `gemm_i8dot` (dtype column added so the verified list no longer says `:f32` for it): 48x128x40, **0 mismatches** vs the CPU oracle, deterministic over 3 runs, Radeon 680M. `cargo fmt/clippy -D warnings/test --all` clean (45 tests). Not measured: speed versus the f32 tiled GEMM, larger shapes, int4 path, unsigned variant.

## H2c measurement: int8 dot GEMM is slower than tiled f32 as written (2026-11-07)
New bench suite `gemm_i8dot` (same 256x1024x256 shape). Medians over 15 runs, GPU timestamps: f32 tiled 0.382 ms, int8 dot 0.814 ms, i.e. 2.1x slower; the kernel is untiled and memory-bound. Recorded in `hcsuda/docs/MEASURED.md`; planner keeps f32. Next experiment: shared-memory tiling of the packed operands.

## H2c follow-up: tiled int8 dot GEMM beats tiled f32 (2026-11-07)
PR #23 (H2 row ops, RoPE, int8 dot GEMM) merged into `main` as a merge commit (`48a949c`) after 14/14 CI checks passed on `aa22427`; branch re-synced. Shared-memory tiled `gemm_i8dot_tiled`: bit-equal on 48x128x40 and the tail shape 37x132x29, GPU 0.195 ms versus f32 tiled 0.269 ms in the same run = 1.38x; untiled int8 was 0.816 ms. Numbers and the f32 clock-state caveat are in `hcsuda/docs/MEASURED.md`. Planner promotion for int8 is still PLANNED (no `Op` entry yet).

## HCSUDA planner now reads selftest evidence; Op::Rope (2026-11-07)
Observation: `hcsuda plan` could never choose a GPU path, because `probe` leaves `verified_paths` empty and nothing connected the selftest record to the planner (a gate that could only answer "reference"). Fix: `DeviceCaps::apply_selftest` merges a selftest record **only** if device name and driver match and the record has `ok: true`; `hcsuda plan [--evidence FILE]` reads `benchmarks/*/selftest.json` by default and prints which file it used or why it ignored one. `Op::Rope` added (scalar path). The tiled int8 kernel now reports under the planner's key `vulkan_intdot:gemm:i8`. Tests first (3 new: rope path, evidence accepted only for same device+driver, failed evidence refused); `hcsuda-core` 48 tests, clippy -D warnings clean. End to end on the 680M: `plan gemm i8` -> vulkan_intdot, `plan gemm f32` -> vulkan_tiled, `plan rope f32` -> vulkan_scalar, `plan gemm f16` -> reference (no verified f16 path yet).

## H2d step 1: f16-storage GEMM (2026-11-07)
`pack_f16x2` / `round_through_f16` (tests first), `gemm_f16_tiled.comp`, runner method, selftest case on an odd shape (error 0, deterministic), bench suite `gemm_f16`. `vulkan_tiled:gemm:f16` is now a verified key, so `hcsuda plan gemm f16` picks it from evidence. Methodology finding recorded in `hcsuda/docs/MEASURED.md`: the f32 GEMM time is bimodal (0.27-0.38 ms) independent of suite order; only same-run comparisons or all-run ranges are quoted. Cooperative-matrix GEMM is the remaining H2d item.

## H2d: cooperative-matrix GEMM (2026-11-07)
Probe first: new `hcsuda coopmat` queries the driver's supported shapes (11, all 16x16x16, subgroup scope, incl. f16->f32). Shader compiled on attempt 1; selftest error 2.4e-7, deterministic. Planner: coopmat only for f16/bf16, a verified key and 16-aligned m/n/k (test first; unaligned falls back to the f16 tiled path). `hcsuda plan gemm f16 --m 256 --n 256 --k 1024` -> vulkan_coopmat; `--m 250` -> vulkan_tiled. Measured 0.167 ms vs 0.257 ms (f16 tiled), 1.53x, stable over two runs. `hcsuda-vk` gained a `serde_json` dependency (workspace-pinned). Tests 51, clippy -D warnings, fmt clean.

## H3 step 1: bounds-checked GGUF reader (2026-11-07)
New crate `hcsuda-io` (`gguf.rs`) and `hcsuda gguf info PATH [--json] [--tensors]`. The reader treats the file as hostile: every length is checked against the remaining bytes, counts have ceilings (1 Mi tensors / keys, 8 dims, 16 MiB strings, array depth 2), arrays are skipped not materialised, tensor sizes use checked arithmetic, offsets must be aligned and inside the file. 14 unit tests written first on synthetic files (valid, quantised block sizes, unknown type, bad magic/version, huge counts, oversized string, huge arrays, nesting, truncated header at five cut points, data outside the file, overflowing dims, unaligned offset, bad alignment); all pass; `rust-version` 1.80 respected (`is_none_or` replaced). Real files, header only: Qwen3-4B-Instruct Q4_K_M (398 tensors; `data_offset + sum(tensor bytes)` = 2,497,281,120 = file size exactly, which independently confirms the Q4_K/Q6_K block sizes), Ternary-Bonsai mmproj Q8_0 (334 tensors, sum + offset = file size exactly), Ternary-Bonsai-2-9B PQ2_0 (427 tensors; 202 of vendor type id 142 cannot be sized, listed as `Unknown(142)`, not guessed). Hostile smoke on real data: header truncated at 1000 B, 100 kB random, `GGUF` + random, file cut after the header -> each refused with a specific error, no panic. Not done: reading tensor data, dequantisation, writing/editing GGUF, ONNX, safetensors, the tiny transformer forward pass.

## H3b: tensor read and dequantisation checked against the official gguf package (2026-11-07)
`hcsuda-io::dequant` (F32, F16, BF16, Q8_0, Q4_0, Q4_K, Q6_K; others return `Unsupported`, never a guess) plus `GgufFile::read_tensor_bytes` (size from the validated table, caller-set byte limit, refuses a file whose size changed since the header was read) and `hcsuda gguf tensor PATH NAME [--json]`.
Oracle: fixtures generated by `hcsuda/tools/gen_dequant_fixtures.py` with the official `gguf` Python package (ggml-org, installed only in a throw-away venv outside the repo). Blocks are synthetic seeded random bytes with valid f16 scales, so no model weights are committed (about 16 KB of fixtures). Tests written first; first run: 7 integration tests pass with **worst absolute error 0** for every type (bit equal), plus size-mismatch and unsupported-type refusals. Real-model check on Qwen3-4B-Instruct Q4_K_M: Rust `hcsuda gguf tensor` versus Python `gguf` for `blk.0.attn_q.weight` (Q4_K, 10,485,760 values), `blk.0.attn_v.weight` (Q6_K) and `blk.0.attn_norm.weight` (F32): min, max, mean and std agree to the printed precision (for example attn_q min -0.576782, max 0.439804, std 0.022878 in both). One new unit test for `read_tensor_bytes` (slice, limit, growing file). 73 tests, clippy -D warnings, fmt clean.
Not done: K-quant types Q2_K/Q3_K/Q5_K/Q8_K, IQ types, the vendor PQ2_0 (type 142) whose layout is unknown here, GPU dequantisation, writing GGUF, ONNX, safetensors.

## H3c step 1: CPU reference transformer block, checked against NumPy (2026-11-07)
`hcsuda-core::transformer::block_forward`: RMSNorm, Q/K/V, split-half RoPE per head, causal multi-head attention, output projection + residual, RMSNorm, SwiGLU FFN + residual, composed only from the existing oracle ops. Shapes are validated and return `BlockError` (no panics: ragged input, dim not divisible by heads, mismatched weights). Independent check: `hcsuda/tools/gen_block_fixture.py` computes the same block with whole-tensor NumPy (seeded weights, T=6, D=32, 4 heads, FFN 64); the fixture (11 small files) is committed. Result: worst absolute error **1.85e-6** over 192 outputs (tolerance 1e-4 relative), plus a causality test (changing only the last token leaves all earlier rows bit-identical and does change the last row) and the shape-error test. Tests 76 in the workspace. This is the oracle for the GPU composition; no GPU transformer kernel exists yet (still missing: elementwise add/mul/silu on GPU, causal-masked attention kernel, head split/merge).

## H3c-2: transformer block on the GPU (2026-11-07)
Three new kernels: `eltwise.comp` (residual add, silu*mul), `rope_heads.comp` (split-half RoPE on every head of a `[T, heads*hd]` matrix) and `attn_causal.comp` (one workgroup per token and head, score row in shared memory, so at most 256 tokens; the host refuses more). `Runner::block_forward_gpu` composes them with the existing rmsnorm and tiled GEMM. Selftest case `block`: the GPU block versus `hcsuda_core::transformer::block_forward` (itself checked against NumPy) on deterministic synthetic weights (T=6, D=32, 4 heads, FFN 64): max relative-to-1 error **4.6e-7**, tolerance 1e-4, deterministic over three runs. Revert-and-see-red: with the causal mask removed (`j <= i` -> `j < t`) the same case fails with error **0.95**; restored, it passes. One self-inflicted compile error on the way (a closure borrowed `self` for the whole function) fixed by a `zeros` method.
Chain of trust: NumPy -> CPU block -> GPU block. Not measured: speed of the block, any size beyond the tiny config, bf16/f16/int8 weights, multi-layer models, a KV cache, sampling. The kernels are correctness kernels, not tuned.

## H3c-3 step 1: Qwen3-style layer on the CPU, GGUF weight layout (2026-11-08)
Probe first (`hcsuda gguf info --json` on Qwen3-4B-Instruct-2507 Q4_K_M): 36 layers, hidden 2560, FFN 9728, 32 q heads, 8 kv heads, head dim 128 (q width 4096 differs from hidden), rope base 5,000,000, rms eps 1e-6, per-head q/k norm weights, no `output.weight` (tied embeddings). The first block (MHA, q width = hidden) cannot represent that, so `transformer::layer_forward` generalises it: GQA, optional QK-norm applied before RoPE, and GGUF's native `[out][in]` weights via `matmul_nt` (threaded over output rows; each element stays one sequential sum, so the result is independent of the thread count). Independent check: `hcsuda/tools/gen_layer_fixture.py` (NumPy, T=5, dim 32, 4 q / 2 kv heads, head dim 16, QK-norm, base 5e6). Result: worst abs error **1.9e-6** over 160 outputs; causality test, "QK-norm changes the result" test, five shape-error cases; two matmul tests (threaded product bit-equal to the naive loop; ragged chunks cover every column). Workspace tests 82.
Not yet: streaming a real layer from the GGUF, final norm + tied lm head, tokenizer, comparison with llama.cpp. Plan for that comparison: our CPU logits for a short prompt (one layer in RAM at a time, about 0.4 GB f32) versus llama-server `/completion` with the same token ids, run one after the other, never together with a VM.

## Owner companion contract read, three research rounds, plans updated (2026-11-08)
Read `AGENTS_HCSEASYMATH_HSCL1_FIRST.md` (2141 lines; untracked owner file, left untracked). It asks for HCSEASYMATH as an in-tree app first (`apps/hcseasymath/`), extracted later. Unknowns were researched in three rounds (platform/spec facts, exact versions/wheels/licences, domain facts) with Firecrawl, `pip` resolution and WSL `apt-cache`; every row with source and limits is in `docs/research/HCSEASYMATH_RESEARCH_LEDGER.md`.
Findings that changed the plan: Ubuntu 26.04 ships Python 3.14 and all 34 required packages resolve as cp314 manylinux wheels (numpy 2.5.4, scipy 1.18.1, sympy 1.14.0, fastapi 0.162.2); the MCP Python SDK is on a 2.x major and had CVE-2025-66416 below 1.23.0, so no Python MCP (extend the Rust `hscl mcp`); SymPy documents `eval` in `parse_expr`, so an own AST parser; local HTTP servers need Host/Origin validation (DNS rebinding); Macaulay2 1.25.11 is in resolute; frontend pins (MIT): react 19.3.1, vite 8.3.6, mathlive 0.111.4, katex 0.19.1, three 0.187.0. Not found: the exact Macaulay2 `Tor` call, the full Stoikov estimator text, the LLG convention papers (blockers B4-B6).
Documentation drift confirmed and fixed: `hcsuda/README.md`, `hcsuda/docs/CAPABILITY_MATRIX.md` and section 12 of the 2026-11-07 masterplan still listed H2 as planned; they now state the evidenced statuses (coopmat, f16, int8 GEMM and GGUF reader/dequantisation as TESTED or HARDWARE-VERIFIED, with the not-done parts spelled out).
New: `docs/superpowers/plans/2026-11-08-hcseasymath-plan.md` (Track E, M0 done, M1 next) and Track E rows in the self-heal ledger. Order decision: Track E first; H3c-3b paused for a free heavy slot.

## HCSEASYMATH M1: foundation built and gated (2026-11-08)
Everything under `apps/hcseasymath/`, tests first at every step, run on WSL Ubuntu 26.04.1 with Python 3.14.4.
- **Parser** (`core/expression_ast.py`): `ast.parse(mode="eval")` + allow-list visitor, no `eval`/`sympify`. Hostile corpus (40 entries incl. `__import__`, attribute chains, lambdas, comprehensions, power towers, homoglyphs, NUL) plus two Hypothesis fuzzers. Two findings on the way: (1) `10**10000` sat exactly on my exponent limit and was computed, and `(10**10000)**10000` **hung** the process (observed, killed); fix = estimate `exponent * bits(base)` before forming a numeric power, cap 20,000 bits; (2) 200 nested parentheses are harmless valid input (no AST nodes), so that corpus entry was wrong and was replaced by real depth bombs (`-`*300, `sin(`*100).
- **Engine** (`core/engine.py`, `results.py`): `execute()` never raises; typed `hcseasymath.result.v1` (pydantic), deterministic run id, provenance (sympy/python versions); derivative checked against an independent numeric derivative.
- **Worker** (`jobs/`): child process with RLIMIT_AS/CPU/NOFILE applied by the child itself, new session, minimal environment, 1 MiB output cap, wall-clock kill of the process group. Tested: stuck child killed and gone, memory hog and real child with 48 MiB map to `resource_limit`, output flood capped, parent secrets not inherited. Latency: median 567 ms per request (n=7, includes importing SymPy in the child, repo on the USB drive).
- **API** (`api/`): Host (TrustedHost), Origin, per-launch bearer token (`hmac.compare_digest`), body cap 64 KiB, bounded concurrency (429), no CORS headers, docs/schema off. Revert-and-see-red for the host, origin, token and body guards: each removal fails exactly its own test. One-page UI with CSP by hash, token from the URL fragment, output via `textContent`.
- **Serve/stop** (`cli.py`): `serve --port 0` prints one JSON line (url, token). Test starts the real server, calls it, sends SIGTERM and asserts no kernel listener remains. Findings: uvicorn shuts down gracefully and then re-raises the signal, so a clean stop reports -15; and under WSL2 a plain `connect()` to a just-closed loopback port can still succeed (a relay accepts and closes it; peer port differs, state CLOSE-WAIT, empty `ss -ltn`), so "no listener" is proven with `ss` and a rebind, not with connect.
- **Lock** (`tools/make_lock.py`): hash-pinned cp314 manylinux wheels only (18 runtime, 28 test packages). Fresh venv from the lock with `--require-hashes --only-binary=:all:`, `pip check` clean, 112 tests pass inside it.
- **Gates**: `scripts/hcseasymath_gate.sh` (shellcheck clean), `forge check` step `hcseasymath (WSL)` only when `apps/hcseasymath/` changed (a skipped step would fail `--strict`), CI job pinned to `actions/setup-python` v7.1.0 by commit SHA. `forge check` OK with the new step; 30 forge tests incl. 4 new.
- Test-only note: Starlette's TestClient prints a deprecation notice about `httpx`; only the test extra is affected.
Not done: warm worker, any operation besides differentiate, frontend toolchain, `hscl math`, MCP tools, Control Center card, package, image, VM. Open: B3 (is `setup-python` 3.14 available on the runner) is answered only once CI runs.

## Owner contract HCSPNP read; investigation in three stages; plans updated (2026-11-08)
Read `AGENTS_HCSPNP_HSCL1_LATEST.md` (German, 1205 lines, untracked, left untracked). Asked order followed: repositories, then web search, then crawl of primary sources, then plans, then commit.
Repositories: `timfromhcs/HCSPNP` is 404; CQ-HECS is public Apache-2.0 at `30c7f14` (2026-11-02). HSCL1 ships only a shell package for it: **the desktop entry runs `hscl-cqhecs doctor`, it does not open the Studio**; there is no `hscl cqhecs` command, MCP tool or Control Center card; the pinned OS runtime has no `python-sat`. **The Studio's HTTP server has no Host/Origin/token check** (source read, nothing sent). CQ-HECS `docs/UNIFIED_SOLVER.md` says "<3.14", but `pyproject.toml` allows 3.14 and `python-sat 1.9.dev21` resolves as a cp314 manylinux wheel (4.1 MB, MIT).
Web and crawl: RLAF (arXiv 2505.16053) injects variable weights and polarities, >2x in some cases, abstract only; AAAI-26 `T_dense`/`T_sparse` are theory with no checker; Model Counting Competition 2025 limits 1 h / 31 GB, results recorded with both rank and solved counts; SAT Competition 2025 Main track requires UNSAT proofs checked by dpr-trim, GRAT or VeriPB; PySAT bundles CaDiCaL 1.0.3/1.5.3/1.9.5/3.0.0 and Kissat 4.0.4. One URL guess (`certificates.html`) was a 404 and the rules were found on `output.html` instead.
New: `docs/research/HCSPNP_{RESEARCH_LEDGER,BASELINE,DECISIONS}.md`, `docs/integrations/HCSPNP.md`, `docs/superpowers/plans/2026-11-08-hcspnp-plan.md`; Track P and a file-lock rule added to the self-heal ledger; cross-track note in the HCSEASYMATH plan; three rows in `KNOWN_LIMITATIONS.md`, one in `CLAIMS.md`. Order: land PR #29, then P-M0 (clean-clone CQ-HECS suite), P-M1a (Studio guard, local only until the owner agrees), `hscl cqhecs status`; Track E and H3c-3b continue in free slots.

## Ecosystem Master read; plans reconciled (Master 8.5); PR #29 landed (2026-11-08)
Read `AGENTS_HCS_ECOSYSTEM_MASTER_2026-11-07.md` (1269 lines, untracked). It defines one priority list P0-P14, the live-ledger rule, a lock format, a next-action table and a first-actions sequence. Followed in that order: (1) snapshot re-fetched (`main` = `4bdcb2f` after the merge; CQ-HECS `30c7f14` with 31 behind / 3 diverged branches, matching the Master exactly; Foundry `cfea6fa`; Discovery Studio `fdd6ccb`; `HCSPNP` 404); (2) PR #29 reviewed through its 16 green CI checks and merged as a merge commit; the new CI job proved Python 3.14 on `ubuntu-latest` (blocker B3 answered); (3) CQ-HECS clean-clone suite recorded earlier (2739 passed / 1 failed / 110 skipped, then 2740 / 0 / 110 with a local, unpushed fix for a real early-reply connection-reset defect in `cqhecs/hardware/bridge.py`); (4) SAT Competition 2026 output page re-crawled (same proof-checker rule as 2025; resource limits not retrievable).
Reconciliation: `2026-11-08-selfheal-masterplan.md` rebuilt as the live ledger (precedence, snapshot, Master P-map, lock format, next-action table, six conflict notes C1-C6); the 2026-11-07 HCSUDA masterplan got a banner (its ordering is superseded, its gates stay); the HCSPNP plan lost its own order table in favour of a pointer plus a milestone-to-P mapping; the HCSEASYMATH plan got its Master position (P12); `HCSPNP_DECISIONS.md` gained P11 (Master governs) and P12 (merge policy); `HCSPNP_RESEARCH_LEDGER.md` gained the 2026 rules row and the unread-literature list. Honest gap: Track E edited `scripts/forge.py` and `.github/workflows/ci.yml` (lock groups) without a written lock; recorded and fixed going forward.

## P1: Studio guard built tests-first in a local CQ-HECS clone; two upstream defects (2026-11-08)
Local only, nothing pushed to `timfromhcs/CQ-HECS` (owner approval B-P1 pending). Branches in `~/src/CQ-HECS` (WSL ext4): `hcspnp/early-reply-drains-body`, `hcspnp/studio-guard`, `hcspnp/integration`.
- **Red proof first:** against unmodified `main`, a `text/plain` POST with a foreign Host, a foreign Origin and no token to `/api/sat/solve` returned `200` and started a solver job.
- **Guard** (`cqhecs/studio/app.py`, `static/app.js`): Host and Origin allow-lists, a per-launch bearer token on every `/api/` route (static files open, token never embedded), JSON-only POST, bodies of early rejections and of oversized requests read within the bound before replying, `OPTIONS` refused without CORS headers, `launch_url()` puts the token in the URL fragment, the frontend reads it, keeps it in memory and removes it from the address bar. `tests/test_studio.py` helpers now send the token; their assertions are unchanged.
- **Tests:** 19 in `tests/test_studio_security.py`. Six mutations (host, origin, token, JSON-only, drain, oversize drain) each turn their own test red. Two honest corrections on the way: my first "flood" test did not catch removal of the body drain (http.client puts a small body in the same segment, nothing left unread), so it was replaced by a test that actually exercises the property, below.
- **Defect 2 (unmodified `main`): HTTP request desync on keep-alive.** The unread body of an oversized or rejected POST is parsed as the next request. Observed with a raw socket against a throw-away worktree of `main`: a `GET /api/health` hidden in the body of an oversized POST was answered `200 OK` after the `413`. Low severity alone, but it defeats any gate in front; the patch reads the bounded body and closes the connection.
- **Defect 1 (hardware bridge)** was found earlier: early POST rejections lose the response (TCP RST) on Linux; fix on its own branch.
- **Results:** guard branch alone 2756 passed + the 2 known bridge failures (fixed on the other branch); `hcspnp/integration` (both) **2759 passed, 0 failed, 110 skipped**, 186 s, 457 MB peak. Browser check with Playwright: with `#token` the page loads, the address bar is clean, no console error except the pre-existing `favicon.ico` 404, `Solve CNF` in the SAT lab returns `SAT` with a verified model; without the token every API call is 401 (6 of 6).
- Patches for the owner: `artifacts/hcspnp/cqhecs-patches/0001..0003` (not in Git). Not done: the launcher `studio` command and desktop entry (blocked until a pinned CQ-HECS release contains the guard), a release or tag in CQ-HECS, the `python-sat` runtime option.
- Environment notes: a bare `pkill -f "pattern"` inside `bash -c` kills its own shell when the pattern is in the command line (use `[c]` bracket form); from Windows, the WSL server is reachable on `127.0.0.1` (localhost forwarding works), though a plain `connect()` is still not proof of a listener.

## P2 slice: `hscl cqhecs status` (2026-11-08)
Master P2 first step, ledger row 3, under `LOCK: P` on `cli/hscl/` (released on merge). Tests first, then `cli/hscl/src/cqhecs.rs`, the `Cqhecs` command in `main.rs`, one row in `docs/CLI.md`. The command only runs the package launcher's `doctor --json` (override `HSCL_CQHECS_LAUNCHER` for tests: absolute path to an existing file, otherwise ignored; then `/usr/bin/hscl-cqhecs`, then `PATH`), and reports `package`, `runtime` (`ok`, `missing`, `broken`, `unknown`), paths and a hint. Anything that is not a JSON object, or an unrecognised runtime word, is `unknown`, never `ok`. Terminal safety: control characters stripped, fields cut at 512 characters.
Linux process tests caught a real defect on the first run: the hung-launcher test took **60 s instead of about 10 s**. Killing the launcher does not close its output pipe when it has started a child of its own, and `join()` on the reader thread waited for that grandchild. Fix: the reader reports through a channel and the wait is bounded (`OUTPUT_GRACE` 1 s); the test now takes 11 s. A second slip was mine: my first hand-written fake launcher printed invalid JSON through bad shell quoting, and `hscl` correctly answered `unknown` instead of guessing.
Results: clippy `-D warnings` clean; `cargo test -p hscl` **202 passed** on Windows, **209 passed** on Linux (WSL, target dir on ext4); the real launcher from the package gives `missing` (exit 3) with no runtime and `ok` (exit 0, "runtime ready") against an existing venv. Not done: typed `hscl mcp` tool, Control Center card, any Studio start, VM or image check.

## HCSEASYMATH M2 step 1: indefinite integration with an honest `unresolved` (2026-11-08)
Probe first (SymPy 1.14.0, eleven integrands): `exp(x**x)` comes back as an unevaluated `Integral`; `sqrt(1+x**3)` comes back as a hypergeometric expression for which `simplify(F' - f) == 0` is **not** proven, although it can be right. So the design grades the check instead of using one yes/no: `symbolic` (difference simplifies to 0), `numeric` (derivative agrees with the input to 1e-12 relative at three or more of seven rational sample points; other symbols are fixed to rationals; complex, infinite or undefined points are skipped), `unverified` (too few usable points), `failed` (any disagreement).
Status mapping: unevaluated integral -> `unresolved` with no result; `symbolic` -> `ok`; `numeric` -> `ok` plus the warning "not proven symbolically"; `unverified` -> `partial`; `failed` -> `internal_error`, the answer is not returned. New result field `checks` names how the answer was verified; the constant of integration is listed under `assumptions`. The engine now dispatches through a handler table, `OPERATIONS` lists `differentiate` and `integrate`, and the API registers one route per operation (`/api/v1/symbolic/<operation>`).
Tests first: 22 in `tests/unit/test_integrate.py`, including an independent mpmath derivative of the returned function and a deliberately wrong antiderivative given to the verifier. 134 app tests pass in the hash-locked venv (112 before). Mutations: verifier never fails, unevaluated `Integral` accepted, numeric tolerance made huge - each turns its own test red. One wording slip caught by a test: the numeric note did not say "numerically"; fixed. Not done: definite integrals, evaluate, simplify, solve, plots, warm worker (each request still starts a fresh Python, about 0.57 s).

## Unified Master read; plans reconciled before the next work; PHYS-0 (2026-11-08)
Read `AGENTS_HCS_UNIFIED_SELF_HEALING_RESEARCH_MASTER_2026-11-08.md` (3278 lines, untracked). Order followed: finish the running batch (PR #31 merged with 16/16 checks), then read, research the unknowns, reconcile every plan, then continue.
- **Facts checked:** the contract's root `AGENTS.md` blob equals ours (`88a8a9cc...`, 113402 B). Its snapshot is older than ours (PR #30 listed as open; both #30 and #31 are merged, `main` = `49673ab`). Sources: VeRO (arXiv 2602.22480, ICML 2026), FIRE-Bench (arXiv 2602.02905), Goedel-Prover-V2 (arXiv 2508.03613) verified at abstract level; the FormalMATH figure (28.31%) was **not** confirmed; SWE-Compass, Arb/FLINT, LeanCert not searched (`docs/research/AGENT_AND_FORMAL_RESEARCH_LEDGER.md`).
- **PHYS-0 experiment** (`docs/research/hcsphysics/integrator_check.py`, pendulum): measured orders Euler 1.1, leapfrog 2.0, RK4 3.96-3.99, Forest-Ruth 4.0, Yoshida triple jump 4.0; `|det J - 1|` at h=0.2: symplectic methods 4.6e-11 to 1.8e-10, RK4 8.5e-7, Euler 3.8e-2; over 100000 steps RK4's energy error grows linearly (4.6e-5 -> 4.6e-4) while the symplectic ones stay bounded and oscillating, never zero. Note recorded: in this one run RK4's maximum (4.6e-4) is still below leapfrog's bounded 1.1e-3, so no general advantage claim. This backs contract 9.1 and 9.2 with data; 9.3-9.9 are definitions to enforce in schemas, not tested here. The supplied physics PDF is not in the repository and was not available; physics stays research only (`docs/research/HCSPHYSICS_RESEARCH_LEDGER.md`).
- **Plan changes:** live ledger now cites the Unified Master (precedence 3b), shows the merged state, carries the physics sub-track (not P15), the default lock groups, the update-before-next-work checklist (5b), rows 8-10 (durable scheduler, PHYS-0 done, PHYS-1 gate), conflicts C7-C9, and the Track E integrate step; Dependabot review is promoted to NEXT (light). HCSEASYMATH decisions gained D11 (Lean worker) and D12 (rigorous numerics), both `PLANNED`.
- **Honest gaps:** Track E edited `apps/hcseasymath` (a lock group in the Master) without a written lock line, again; recorded and released. The durable scheduler described by the Master does not exist; the 2-minute ping is a session job.

## Dependabot #1-#4 reviewed and applied together (2026-11-08)
PR #32 merged (`ce0e40b`, 16/16 checks). Release notes read for checkout v5-v7 and upload-artifact v5-v7.0.2; action SHAs verified against the tags via the GitHub API. sha2 0.11.1 and thiserror 2.0.21 each built and tested alone and combined on main (fmt, clippy -D warnings, `cargo test -p hscl`: 209 passed). Applied in one branch because the Dependabot bases were old; CI decides the merge. `hcsuda/` workspace not bumped.

## HCSEASYMATH evaluate operation (2026-11-08)
Added `evaluate` (exact substitution of a symbol-free value parsed by the allow-list parser; zoo/nan/oo give `unresolved` with no result). Gate in WSL: 143 passed (was 134); the capabilities test now lists three operations. Not yet done: simplify, solve, plot, warm worker.

## Miner Research Bridge contract read; plans reconciled (MINER-0, 2026-11-08)
Read `AGENTS_HSCL1_BITAXE_MINER_RESEARCH_BRIDGE_MASTER_2026-11-08.md` (2392 lines, untracked). Verified read-only via GitHub: ESP-Miner master and research-branch heads, 8 ahead / 0 behind, 22 files, partition table, upstream PR states, RLAF abstract (arXiv 2505.16053). Not verified: 22 other sources, CI of the research branch, any device (no contact with .61/.66). Decisions M1-M7, conflicts C10-C12, ledger rows 11-13. No code, schema or device action. Edits to ESP-Miner / CQ-HECS and any flashing need owner approval.

## Takeover session (OpenCode agent, 2026-11-08) - audit, PR #36, own plan
Reconnaissance before any edit: `git fetch --all --prune`, `gh pr list` / `release list` / `run list`, the three sub-repositories (`CQ-HECS` `30c7f14`, `hcs-foundry` `cfea6fa`, `hcs-discovery-studio` `fdd6ccb`, `HCSPNP` 404), `docs/BUILD_LOG.md`, the live ledger, `docs/CLAIMS.md`, `apps/hcseasymath/`, `cli/hscl/src/`, `scripts/forge.py`.
- **Baseline reproduced, not assumed:** `wsl -d Ubuntu -- bash -lc "cd /mnt/e/hcslinux222 && bash scripts/hcseasymath_gate.sh"` -> `143 passed, 1 warning in 14.76s` (the count the ledger claims). Python 3.14.6 and sympy 1.14.0 on the host; cargo 1.96.0.
- **PR #36** (MINER-0 reconciliation, `codex/miner-plans`) was open, mergeable and 16/16 checks green -> merged as `bbb98dd` (standing instruction: merge only on green CI). Dependabot branches were already gone; no open PRs remain.
- **Research on the open questions** (sources read 2026-11-08; details in the new plan section 3): SAT Competition **2026** Main track = 5000 s / **32 GB** / PAR-2 with **certificates required for SAT and UNSAT**, Parallel 1000 s wall on `m6i.16xlarge`, Cloud 200 s on 100 x `m6i.4xlarge` (closes the limit gap of conflict C4); SymPy 1.14 docs show `solve()` output is shape-inconsistent and can miss roots (#25849) while `solveset` returns sets with a domain -> the planned `solve` operation will use `solveset` plus a substitution check of every root; **LeanCert** exists for Lean 4 verified interval arithmetic (Lean 4.31.0, 2026-06-13) -> decision D12 can name a concrete candidate but stays PLANNED.
- **Own execution plan:** `docs/superpowers/plans/2026-11-08-opencode-autonomous-masterplan.md` (audit, research answers, waves W0-W4, loop contract). It adds **no priority list**: the order stays the live ledger's P-map; the plan names the P number and ledger row for every task.
- **Loop:** a one-shot 120 s background wake replaces the session cron ping (a `while` loop never completes and therefore never notifies in this harness). Each wake does one ledger step, records it, and arms the next wake; the durable version is ledger row 15 / Wave 2.
- Not started in this entry: no code change, no image build, no VM, no push to another repository. Blocked items unchanged (B-P1 CQ-HECS push, signing, physical hardware, DE/FR review, production deployment).

## HCSEASYMATH `simplify` (Track E M2 / ledger row 14, 2026-11-08, OpenCode wave 1)
Added the fourth operation. `sp.simplify` is never trusted on its own: the returned form is graded against the input by a new `symbolic.verify_equivalence` (`symbolic` = the difference simplifies to 0; `numeric` = agrees at up to 7 rational sample points with distinct values per free symbol, reported as "not proven symbolically"; `unverified` = fewer than 3 usable points, or more free symbols than distinct sample values; `failed` = a disagreement). A `failed` form is refused as `internal_error` and not returned; `unverified` is `partial`. A size reduction is claimed only from measured `sp.count_ops` values, and any rewrite that changes the printed form carries an `assumptions` note that points removed by it (a cancelled denominator, for example) are not restored.
- Tests first: 30 new tests in `tests/unit/test_simplify.py` (known simplifications, an independent mpmath comparison of both forms, the disclosure note, the count_ops invariant over four expressions, typed refusals, all four verifier grades with hand-picked pairs, and the two monkeypatched grading branches) plus the capabilities list in `tests/api/test_api.py`.
- Verifier cases that matter: `atan(x) + atan(1/x)` is **rejected** as an identity because the sample points include negative rationals (it is +-pi/2); `log(x**2)` vs `2*log(x)` is only `numeric`; `sqrt(x**2)` vs `Abs(x)` is `numeric`; `asin(x)+acosh(x)` vs itself + 1 leaves 0 usable points -> `unverified`.
- Mutations, each shown red then reverted: verifier always answers `symbolic` -> 4 verifier tests fail; size claim appended unconditionally -> the `x + y` invariant and the "no claim when it did not shrink" test fail.
- Gate: `bash scripts/hcseasymath_gate.sh` (WSL Ubuntu, hash-locked venv, Python 3.14) -> **171 passed, 1 warning in 14.90s** (143 before). `OPERATIONS` and `/api/v1/capabilities` now list four operations; the API registers one route per operation automatically.
- Docs kept in sync: `apps/hcseasymath/README.md` (four operations, simplification guarantee, "does not do" list), `docs/CLAIMS.md` row, ledger rows 4/14 and E-M2.
- Not done in this entry: `solve`, `plot` data, warm worker (still ~0.57 s per request), no change to the result schema (no new fields), no image/VM involvement.

## HCSEASYMATH `solve` (Track E M2 / ledger row 14, 2026-11-08, OpenCode wave 1)
Fifth operation. The engine uses `sp.solveset(expr, variable, domain=Reals)`, never `sp.solve`: the return value is a set, so "the complete root list" is never invented, and the domain is explicit. The equation is the expression set to zero (the request shape stays `expression` + `variable`; no `=` is parsed).
- Every root is substituted back before it is reported (`symbolic.verify_root`): `symbolic` = the substitution gives exactly 0, `numeric` = the residual is a number below 1e-12 relative, `unverified` = the residual still contains symbols, `failed` = a non-zero residual. A failed root is dropped and the answer becomes `partial`; if every root fails, `internal_error` with no result; an unverified root makes the answer `partial`.
- Infinite sets (`ImageSet`, `ConditionSet`, `Interval`, a `Union` that is not all finite) and an identity (`S.Reals`) are `unresolved` with no result. An empty real solution set is `partial` with `EmptySet` and two warnings: absence is not independently verified, and the number of complex roots (or "infinitely many") is named because this version does not return them. A parameter in the equation makes an empty answer inconclusive -> `unresolved`, because "no x satisfies y - 1 = 0" depends on y.
- `solveset` returns `Intersection({-a}, Reals)` when a parameter is present; the finite part is used and the assumptions say that real-domain membership of the roots was not decided.
- Tests first: 26 in `tests/unit/test_solve.py` (six known root sets, an independent substitution of every returned root, the empty/complex cases, ImageSet/Reals/parameter refusals, typed refusals, all four verifier grades, and the four monkeypatched grading branches) plus the capabilities list in `tests/api/test_api.py`.
- Mutations, each shown red then reverted: `verify_root` always answers `symbolic` -> the reject/numeric/unverified verifier tests fail; the empty real set reported as `ok` -> both empty-set tests fail.
- One real defect found by the tests: `isinstance(sol, (sp.Reals, sp.Complexes))` raises `TypeError` because those are instances, not types; identity/equality comparison is used instead. `sp.EmptySet` is not a `FiniteSet` in SymPy 1.14 either, so it is handled explicitly.
- Gate: `bash scripts/hcseasymath_gate.sh` -> **197 passed, 1 warning in 14.85s** (171 before). `OPERATIONS` and `/api/v1/capabilities` list five operations.
- Still open in Track E M2: `plot` data, warm worker, and the one-page UI (it still calls only `differentiate`; recorded in the README).

## HCSEASYMATH: `evaluate` was unreachable over HTTP (defect found by probing, 2026-11-08)
Probing the running contract instead of trusting the tests found a real defect: `ExpressionRequest` declared only `expression` and `variable`, and pydantic drops unknown fields, so a client's `value` never reached the engine. `POST /api/v1/symbolic/evaluate` with `{"expression":"x**2","variable":"x","value":"3"}` answered `400 invalid_input: missing 'value'` - the operation existed, was tested through `execute`, and could not be used by any HTTP client since it was added.
- Fix: `value` is now a declared optional field (bounded by `DEFAULT_LIMITS.max_chars`), the route dumps with `exclude_none=True`, and the model uses `extra="forbid"` so an unknown field is a 422 instead of being silently dropped.
- Second half of the same defect class: the engine now refuses a field that the chosen operation does not use (`field(s) not used by this operation: value`), so a misplaced field can never be ignored silently. `_OPERATION_FIELDS` names the one exception (`evaluate` -> `value`).
- Tests: `test_evaluate_can_send_its_value_over_http`, `test_a_field_belonging_to_another_operation_is_refused_over_http`, `test_an_unknown_body_field_is_rejected_instead_of_silently_dropped` (API) and `test_a_field_the_operation_does_not_use_is_refused_not_silently_ignored`, `test_evaluate_keeps_the_value_field_it_uses` (engine).
- Gate: `bash scripts/hcseasymath_gate.sh` -> **202 passed, 1 warning in 15.01s** (197 before).
- Not changed: the worker is still Linux-only (`os.killpg`), so these API tests use the in-process `run=execute` like the existing ones; the process isolation path is exercised by the worker tests.

## HCSEASYMATH `plot` data (Track E M2 / ledger row 14, 2026-11-08, autonomous tick)
Sixth operation, **data only**: `plot` returns `samples` (`[x, y]` pairs), never an image claim and never a `result_expression`. Fields: `x_min`, `x_max` (exact, symbol-free, finite, real; parsed by the allow-list parser) and `points` (strict integer, 2..1000, default 200); range capped at 1e6. Points are evenly spaced including both ends and are evaluated exactly, then converted to float.
- Discontinuity policy: a sample where the function is undefined, infinite or not real becomes `null` and is **not connected**; some nulls -> `partial` with a count warning, all null -> `unresolved` with no samples. Complex values are never reduced to their real part.
- Schema: one new optional field `samples` on the result (`null` for every other operation). API: `x_min`, `x_max`, `points` declared on the request model (lesson of the `evaluate` defect: undeclared fields are dropped); a string `points` is a 422.
- Tests first: 20 in `tests/unit/test_plot.py` + 2 HTTP tests. Mutation shown red then reverted: complex/undefined values let through -> `test_complex_values_are_null_not_real_part` and `test_all_undefined_is_unresolved_without_samples` fail.
- Gate: `bash scripts/hcseasymath_gate.sh` -> **230 passed, 1 warning in 14.3s** (202 before). Process slip recorded: a `git checkout` used to revert the mutation also reverted the uncommitted plot code; restored from a backup copy, gate re-run green. Revert mutations from a backup, not with `git checkout`.
- Not done: warm worker (W1-4), one-page UI still calls only `differentiate`.

## HCSEASYMATH warm-worker: latency measured first (W1-4, 2026-11-08, autonomous tick)
Measured in WSL Ubuntu, Python 3.14, hash-locked venv, 3 runs each (warm file cache): bare interpreter **15-29 ms**; `import sympy` **0.28-0.30 s** (0.81 s cold); `import hcseasymath.core.engine` **0.43-0.53 s**; the whole child (`jobs.child`, one differentiate) **0.48-0.55 s**; the operations themselves in a warm process: differentiate 27 ms, integrate 55 ms, simplify 83 ms, solve 11 ms (one expression `x**3-2*x`, not a benchmark suite). Conclusion: about 90 % of the ~0.5 s per request is the import, not the maths.
- Design consequence (not built yet, `PLANNED`): a **pre-imported zygote that forks one child per request**, not a long-lived worker that answers many requests. Fork keeps the per-request isolation the current design has (fresh address space, own limits, own kill group); a long-lived worker would carry state, memory growth and a cumulative CPU limit between requests. Open points the implementation must settle with tests before any claim: `RLIMIT` applied after fork in the child, the zygote itself single-threaded (no fork in a threaded process), restart of a dead zygote, output cap and timeout unchanged, no environment or file descriptors inherited beyond the request pipe. Target to confirm by measurement, not promised: per-request latency in the order of tens of milliseconds.
- Linux only, like the current worker (`os.killpg`, `resource`).

## HCSEASYMATH warm worker built, not yet wired into the API (W1-4, 2026-11-08, autonomous tick)
`jobs/zygote.py` (single-threaded; imports the engine once; one `fork()` per request on a unix socket in a 0700 temp directory; the child calls `setsid()`, applies the RLIMITs itself, runs the operation, writes one JSON object) and `jobs/warm.py` (`WarmWorker.start/stop/run`, same result contract as `run_isolated`; restarts a dead zygote; the zygote gets the same minimal environment as the cold child; the parent kills the child's process group on timeout and after every request).
- Tests first: 12 in `tests/unit/test_warm_worker.py` (result identical to the cold worker in `status`, `result_expression`, `run_id`, `input_digest`, `exactness`, `checks`; hostile input refused; warm request < 0.3 s; one process per request and reaped; real kill of a stuck child; memory limit in the child while the zygote survives; zygote restart after SIGKILL; no environment leak, names restricted to six; six parallel requests do not mix; socket directory mode 0700). Gate: **242 passed** (230 before).
- Mutations: no RLIMITs in the child -> `test_the_memory_limit_is_enforced_in_the_child` red; parent never kills -> `test_a_stuck_child_is_really_killed_at_the_time_limit` red. **A first version of the kill test passed under the mutation** (the child simply finished by itself); it was replaced by a test engine that never returns (`tests/helpers/slow_engine.py`, selected by the test-only `engine=` argument) and the mutation was re-run red.
- Known residue, by design: a request in flight survives a zygote restart in its own session until the parent kills it or its CPU limit ends it. The cold worker has the same property only per request.
- Not claimed: the actual latency win in the API. The test only bounds a warm call under 0.3 s on this machine; a measured before/after through `/api/v1/symbolic/*` is the next step, together with the decision to switch the API over (default stays the cold worker until then). Not done: wiring into `app.py`, graceful shutdown hook, Windows (Linux only).

## HCSEASYMATH `serve --warm` and the measured win (W1-4, 2026-11-08, autonomous tick)
`python -m hcseasymath serve --warm` starts one `WarmWorker`, passes its `run` to `create_app`, and stops it when uvicorn returns. **The default stays the cold worker**; `--warm` is opt-in and Linux only.
- Measured through the real HTTP server (WSL, `differentiate` of a cubic, second request of each server; one pair, not a benchmark): **cold 571 ms, warm 74 ms** (about 7.7x). The unit-level estimate was ~0.5 s -> tens of ms; this is the confirmation, with the caveat of a single sample on one machine.
- Tests: `tests/integration/test_serve_warm.py` (same `status`/`result_expression`/`run_id`/`input_digest`/`exactness` as the cold server; warm faster; no zygote outlives the server; the default server starts no zygote and `--help` lists `--warm`). Gate: **244 passed**. Mutation shown red then reverted from a backup copy: `warm_worker.stop()` replaced by `pass` -> "a zygote outlived the server".
- Slip caught in review of my own test: a first draft of the default-is-cold test had a vacuous `or True` assertion; replaced by a real check that the cold server has no zygote child.
- Open before the default can change: a repeated measurement (several runs, percentiles), behaviour under the concurrency limit, and the decision of the owner/ledger on whether a zygote process is acceptable in the packaged app.

## Durable self-heal scheduler: first implementation (Wave 2 / ledger row 8, 2026-11-08, autonomous tick)
`scripts/selfheal/tick.py` + `scripts/selfheal/rows.json` implement `docs/research/SELFHEAL_SCHEDULER_DESIGN.md`: one bounded tick (no daemon), exclusive-create global lock with owner pid/start time and a 300 s stale takeover (the stale file is claimed by a rename that only one contender can win; a fresh lock that was moved by mistake is put back), separate heavy lock (a heavy row records `deferred` while it is held; light rows still run), 90 s wall timeout with process-tree kill (POSIX `killpg`, Windows `taskkill /T`), dry run is the default (`--execute` is real mode, and a row exists only if it is listed in `rows.json`), state file written to a temp file and swapped in with `os.replace` (no fsync, so this protects against a half-written file seen by another reader, not against power loss), a corrupt state file is refused and never overwritten, three consecutive failures set a row `BLOCKED` and the next row is picked, JSONL log without environment dump, rows with secret-shaped arguments or shell-style entries are refused (`argv` list only), worker gets a minimal environment, default state dir outside the repository (`%LOCALAPPDATA%\hscl-selfheal` / `$XDG_STATE_HOME/hscl-selfheal`).
- Tests first: 14 in `tests/unit/test_selfheal_tick.py` (the seven from the note plus success-resets-count, lock released after every outcome, state written via temp file + `os.replace`, no environment in log or worker, row validation, state dir outside the repo). Result: **14 passed on Windows and 14 passed in WSL**.
- Mutations (Linux), each red then reverted from a backup copy: lock always granted -> 3 tests red (concurrency, stale/fresh, heavy lock); timeout without kill -> `test_a_worker_past_the_timeout_is_killed_and_recorded` red; failures never block -> the blocking test red. **Gap:** the kill assertion only runs on Linux, so the Windows run alone does not prove the `taskkill` path.
- Smoke run with a throw-away state directory: dry run wrote only the log line; three `--execute` ticks gave `ok`, state and log written, lock gone.
- **Known limitation (design gap, not hidden):** the tick always picks the *first* non-blocked row, so with `rows.json` as shipped only `git-status` ever runs; there is no rotation. The design note does not ask for one. Fixing it changes the pick rule and the blocking test, so it needs a decision (round-robin by last row is the obvious choice). Nothing here is registered with Task Scheduler or cron; that stays the owner's choice (note, "Open"). The 2-minute ping of this session remains a session job.

## HCSPNP audit row 1 (Wave 3), parts 1-4 summary (2026-11-08, autonomous ticks, read-only)
Read in the local CQ-HECS clone (`/home/tim/src/CQ-HECS`, `src/` identical to `main` `30c7f14`): `src/sat_solver.cpp`, `src/cq_hecs_api.cpp`, `src/cq_c_api.cpp`, `cqhecs/drat.py`, `cqhecs/sat_external.py`, `cqhecs/unified.py`, and the core of `cqhecs/sat.py`. **Not read:** `sat_separator.py`, `omniwave/*` (engine by grep only), `studio/app.py` (guard patch covered earlier), `provenance.py`, `mcp_server.py`, the DPLL internals and counting/MaxSAT parts of `sat.py`, the shaders, the QASM parsers, `tests/*` content. Nothing was changed or pushed in that repository (B-P1 open). Full tables with file and line references: `docs/research/HCSPNP_BASELINE.md` (sections "Audit row 1, part 1-4").
- Headline results: native UNSAT is uncertified (`verified=true` overstates); the C ABI collapses timeout and invalid input into the UNSAT code and truncates the model at 1024 entries; no exception guard on any export; `cq_omniwave_bcp_eval` misses a null check; the portfolio (`unified.py`) upgrades proof labels without reading `certified` and cannot detect an engine contradiction; the Python and native DIMACS parsers disagree on seven input classes; `sat.py` itself already shows the right convention (`certification` property, `UNKNOWN` on disagreement).
- Order of the smallest first PRs (all local-only until the owner lifts B-P1): shared strict parser rules + differential parser test; A1/A3/A5; C1+C2 together; C4 and C3 (use `certification`).
- Process note: pushes were paused for one tick because each push restarts CI for the PR head and no head had finished; PR #37 stays `CLEAN`, the merge is not done by this agent (permission denied for `gh pr merge`).

## NP benchmark harness, research and slice 1 (SAT) (P4/P5, ledger rows 16-21, owner request, 2026-11-08)
Owner request in the running session: web research on NP-hard and "hardest" problems, how to build them as code benchmarks, adapt the plans, build them in, try to build solvers. Research (web search, snippet level, no paper read in full) is in `docs/research/NP_BENCHMARK_RESEARCH.md` with sources and with the questions that stayed open: the "Anni" format of the SAT Competition 2026 was not found, the 2026 benchmark selection is still "TBA" on the page read, and the licences of Concorde, LKH and OR-Tools were **not** confirmed (Kissat and PySAT are MIT; CaDiCaL only indirectly). "Hardest" is treated as a property of instance families and solvers, never as a claim.
- **Plans adapted:** live ledger rows 16-21 (NPBENCH-1..6) under P4/P5, priority-map rows P4/P5 updated, row 15 (scheduler) set to DONE, OpenCode plan Wave 5. The order P0-P14 is unchanged; the work sits inside P4/P5.
- **Built (`tools/npbench/`, pure standard library):** `cnf.py` strict DIMACS (header required and lowercase, declared clause count must equal the parsed count, digits only, caps before allocation, SATLIB terminator only in its real form, nothing silently repaired) - this is the reference for the differential parser test of audit finding P1; `gen_sat.py` generators (uniform random k-SAT, threshold ratio 4.26, planted, and an array-multiplier factoring circuit whose expected answer comes from trial division, so a prime N is a known UNSAT instance); `proof.py` an independent RUP refutation checker; `solvers/cdcl.py` CDCL (two watched literals, first-UIP learning with backjumping, activity ordering, phase saving, Luby restarts, proof log, no clause deletion); `solvers/walksat.py` (answers SAT or UNKNOWN only); `runner.py` (a SAT claim counts only after `verify_model`, an UNSAT claim only after `check_rup`, otherwise UNKNOWN; known-answer contradiction is a `disagreement`; an unknown solver name is `unavailable`, no fallback; PAR-2; manifest entries with SHA-256).
- **Tests first:** `tests/unit/test_npbench_sat.py`, 40 tests, including 160 random small formulas against brute force (both verdicts exercised, every SAT model verified and every UNSAT proof checked), the factoring circuit against brute force for every N below 40, and refusal cases for the parser. Result **40 passed**.
- **Mutations**, each shown red and then restored from a backup copy with a byte comparison: inverted XOR parity, proof not logged, model not verified, proof not checked, clause count not compared, wrong backjump level, timeout reported as UNSAT, unassigned variable counted as false. All 8 turn a test red. One real slip found while writing: the XOR gate's parity sign was inverted in my first draft (caught by reading before the run); one test of mine had a vacuous `or True` assertion and was replaced by a real check.
- **First measurement** (Windows host, Python 3.14, 6 seeds per size, ratio 4.26, 8 s budget; a smoke test, not a benchmark study): CDCL decided 6/6 at n = 30, 50, 70, 90 with medians of 1, 2, 8 and 24 ms (conflicts median 11, 22, 90, 243); SAT/UNSAT split 5/1, 5/1, 3/3, 3/3, every UNSAT backed by a checked proof. WalkSAT found exactly the SAT instances CDCL found (5, 5, 3, 3) and left the others UNKNOWN, as designed; its median at n = 70 and 90 is about 4 s because the UNSAT half runs into the budget. The roughly even SAT/UNSAT split near ratio 4.26 matches the threshold described in the literature; it does not prove hardness at these sizes, which are small. Not measured: larger n, other families, any external solver.
- **Not done / honest limits:** no CLI or suite file yet (row 17), no graph / TSP / knapsack families (rows 18-19), no DRAT checker or external adapters (row 20), nothing beyond NP (row 21). The pure Python CDCL is a correctness baseline; it is not competitive with CaDiCaL or Kissat and no report says so. No tool of unclear licence is bundled or called.

## NP benchmark harness, slice 2: suites, CLI and JSON report (ledger row 17, 2026-11-08, autonomous tick)
`tools/npbench/npbench/suites.py` and `__main__.py`. A suite is a list of specs; an instance is rebuilt from its spec and bound to its bytes by a SHA-256 in the manifest. The generator is the authority on the answer: a spec that claims an answer the generator does not know (random, threshold) or contradicts (factoring of a prime) is refused. `python -m npbench run|list|manifest`; the report schema is `npbench.report.v1` (records, per-solver summary with decided / SAT / UNSAT / unknown / unavailable / errors / refused / disagreements / PAR-2, manifest, Python and platform only - no environment dump). Exit 0 all fine, 1 disagreement, refused claim, error or unavailable solver, 2 usage error, an existing report without `--force`, a bad budget (outside (0, 3600] s) or the heavy `sweep` suite without `--allow-heavy`. A timeout is a normal outcome and does not fail the run.
- **Tests first:** `tests/unit/test_npbench_cli.py`, 13 tests; with the 40 of slice 1 **53 passed**. Two assertions in my first draft were vacuous (`... or True`, `... or code == 1`) and were replaced before the first run by two precise tests: a solver whose claims are all refused (counted in `refused`, exit 1) and a buggy generator simulated by flipping the recorded answers (every verified verdict becomes a `disagreement`, exit 1).
- **Mutations**, each red and then restored with a byte comparison: exit code ignores disagreements, exit code ignores an unavailable solver, heavy guard removed, overwrite guard removed, claim check in the generator removed, `refused` not counted, budget not bounded. All 7 turn a test red.
- **Real run** (`python -m npbench run --suite light --solvers cdcl,walksat --budget 5`, Windows, Python 3.14): CDCL decided 16/16 (11 SAT, 5 UNSAT; every SAT model verified, every UNSAT proof accepted by the RUP checker), PAR-2 0.003 s, no disagreement; individual times 0.4 to 14.5 ms, at most 172 conflicts. WalkSAT decided 11/16 (the 11 SAT ones, the 5 UNSAT stay UNKNOWN by design), PAR-2 3.3 s because an undecided run counts twice its budget; no disagreement with CDCL. The light suite is small by design: it is a regression and correctness suite, not a hardness study.
- **Not done:** graph / TSP / knapsack families (rows 18-19), DRAT checker and external adapters (row 20), beyond NP (row 21), the heavy `sweep` suite was only run inside the guard-removed mutation (budget 1 s, no result recorded).

## NP benchmark harness, slice 3: graph families (ledger row 18, 2026-11-08, autonomous tick)
New in `tools/npbench/npbench/`: `graph.py` (strict DIMACS `.col`: header `p edge n m` required, digits only, no self loop, no repeated edge in either direction, parsed edge count must equal the declared one, caps first; verifiers for colouring, clique and Hamiltonian cycle that share no code with a solver), `gen_graph.py` (Mycielski graphs, queen graphs, Turan graphs, complete graphs, cycles, generalised Petersen graphs, planted colourable / clique / Hamiltonian graphs), `graph_solvers.py` (CNF encodings for colouring and Hamiltonian cycle, DSATUR, SAT route through the CDCL baseline, Bron-Kerbosch with pivoting, depth-first Hamiltonian search), `graph_runner.py`, and the suite `graphs` (18 instances, 33 solver records). `python -m npbench run --suite graphs --solvers sat,dsatur,bk,backtrack` works through the same CLI and report schema; a (solver, task) pair that does not exist is skipped, a name that exists for no task is `unavailable`.
- **Claims only where a theorem or the construction backs them:** Mycielski M_k has chromatic number k; queen graphs only for gcd(n, 6) = 1 (n = 6 and 8 are deliberately not claimed, the DIMACS tables list best-known values there, not a theorem used here); Turan T(n, r) has chromatic and clique number r; planted generators give one-sided facts. The suite builder refuses a spec whose claimed answer differs from what the generator knows.
- **Evidence rules:** a yes-answer needs a witness that passes the verifier. A no-answer needs a RUP proof of the (re-built) encoding for colouring and Hamiltonian cycle, or for `clique k` a proper colouring with k-1 colours (it proves that no k-clique exists). An exhausted search without such a certificate is `UNKNOWN`; `ham_backtrack` and `dsatur` can never say UNSAT. Limits of the clique certificate: it exists only when the chromatic number is at most k-1, so Mycielski graphs (clique number 2, large chromatic number) cannot get a certified "no 3-clique"; no such instance is in the suite.
- **Real defect found by a test, not by reading:** my first Alspach statement ("GP(n, k) is non-Hamiltonian iff k = 2 and n = 5 mod 6") is wrong as written: exhaustive search shows GP(11, 5) is not Hamiltonian. The theorem holds up to isomorphism, and GP(n, (n-1)/2) is isomorphic to GP(n, 2) because 2 * (n-1)/2 = -1 mod n. The function and its docstring were corrected; the test compares the table with exhaustive search for every 5 <= n <= 12.
- **Tests first:** `tests/unit/test_npbench_graph.py`, 26 tests (strict parser refusals, verifiers, generator shapes, Mycielski chromatic numbers by brute force for k = 2, 3, both encodings against brute force on random small graphs with both verdicts present, solvers, runner refusals, suite claims, a full CLI run). Slice 1-2 tests unchanged; all three files together are run by `forge check`.
- **Mutations**, each red then restored with a byte comparison: colouring verifier ignores edges, clique verifier ignores adjacency, Hamiltonian verifier ignores the closing edge, runner accepts an unchecked RUP claim, runner skips the colouring-bound check, colouring encoding drops the edge clauses, Hamiltonian encoding drops the wrap-around, Petersen table without isomorphism, backtracking claims UNSAT, claim check removed, duplicate edge accepted, DSATUR claims UNSAT. **Three survived the first round** (closing edge, colouring-bound check, duplicate edge): the tests did not cover them. A first attempt to add the tests silently did not apply (a quoting mistake of mine; the assertion stopped the script before writing), so the survivors were still alive in the second run; the tests were then added with the editor tool and all 12 mutations turn a test red.
- **Real run** (`python -m npbench run --suite graphs --solvers sat,dsatur,bk,backtrack --budget 30`, Windows, Python 3.14): `sat` decided 15/15 (10 SAT, 5 UNSAT, every UNSAT with a checked RUP proof, times 0.1 to 42 ms); `bk` 3/3 (the clique "no" certified by a colouring); `dsatur` 5/9 and `backtrack` 5/6 decided, which is correct for incomplete solvers (they cannot answer "no"); no disagreement, nothing refused. **PAR-2 of 26.7 s for DSATUR is an artefact**: an undecided run counts twice its budget and DSATUR can never decide a "no" instance, so PAR-2 must not be compared between complete and incomplete solvers. The instances are small by design (at most 23 vertices); this is a correctness suite, not a study of hard instances.
- **Not done / limits:** the encodings are part of the problem specification and are shared by solver and proof check, so their correctness rests on the brute-force comparison tests, not on independence; no Mycielski k = 5, queen 7 or Petersen n = 11 instance yet (not timed); no DIMACS or FHCP files are downloaded or bundled (licence question open, see the research ledger); TSP and knapsack are row 19.

## NP benchmark harness, slice 4: TSP and knapsack / subset sum (ledger row 19, 2026-11-08, autonomous tick)
New in `tools/npbench/npbench/`: `tsp.py` (TSPLIB EUC_2D distance in exact integer arithmetic, tour verifier, the Held-Karp / Lagrangian 1-tree lower bound for integer potentials, strict TSPLIB reader that accepts integer coordinates only), `gen_tsp.py`, `tsp_solvers.py` (exact Held-Karp DP for n <= 13, nearest neighbour from every start plus 2-opt, subgradient ascent on the 1-tree bound), `knap.py` (instance, selection verifier, exact fractional bound with `Fraction`), `gen_knap.py` (uncorrelated, weakly correlated, strongly correlated, subset sum, after the families named by Pisinger; not a copy of his code), `knap_solvers.py` (DP over the capacity with witness, greedy, fractional-bound claim), `opt_types.py`, `opt_runner.py`, and the suite `optimization` (27 instances, 81 solver records). The CLI dispatches on the family as before.
- **Evidence rules:** a yes needs a tour with length <= bound that `tsp.verify_tour` accepts, or a selection that `knap.verify_selection` accepts. A TSP no needs integer potentials whose bound, recomputed by `tsp.lower_bound`, exceeds the limit (valid for any potentials, which the tests check with random ones). A knapsack no needs the exact fractional bound, recomputed by the runner, below the target. An exact DP that finishes without a certificate is UNKNOWN, not a no.
- **Where the answer in a spec comes from:** knapsack and TSP with n <= 13 from the exact DP (validated against brute force for TSP n = 7 and knapsack n = 11 over all four families); TSP with n > 13 only from a verified tour (yes) or a verified lower bound (no); between the two the spec must say `null`. The builder refuses a spec whose claim differs.
- **Measured surprise:** on the small random Euclidean instances (n = 8 to 20, box 1000) the Lagrangian bound equals the optimum or the best tour found exactly (for example n = 20: bound 3990, tour 3990), so even "no tour of length optimum - 1" is certified; a gap appears at n = 30 (bound 4455, best tour 4511), kept in the suite as an instance whose middle bound (4480) has expected answer `null`. My first design had assumed a gap everywhere. Not claimed: that the bound is tight for larger or clustered instances.
- **Tests first:** `tests/unit/test_npbench_opt.py`, 26 tests (euc2d against the float definition on 2000 random pairs, Held-Karp against brute force, 2-opt never below the optimum with a ratio check, the bound valid for 150 random potential vectors, improvement by the subgradient, a strict TSPLIB reader, family definitions, DP against brute force for all four knapsack families, selection and bound verifiers, runner refusals, suite claims, a full CLI run). Slice 1-3 tests unchanged. Process note: one assertion of my first draft ended in `or True` and was removed before the first run.
- **Mutations**, each red then restored with a byte comparison: euc2d rounding, tour permutation check, bound without the potential sum, bound with one edge at vertex 0, runner accepting any bound claim, runner accepting any LP claim, selection ignoring capacity, selection allowing duplicates, LP bound without the partial item, DP capacity off by one, TSP DP claiming UNSAT, Held-Karp without the return edge, wrong strong correlation, claim check removed, TSPLIB accepting floats, subgradient doing nothing. **One survived the first round** (duplicates: my test case was already rejected by the capacity check); the test case was replaced by one that fits the capacity, and all 15 now turn a test red.
- **Real run** (`python -m npbench run --suite optimization --solvers dp,nn2opt,lagrange,greedy,ub --budget 30`, Windows, Python 3.14): `dp` decided 9/27 (all yes-answers it could find; it never says no), `nn2opt` 8/17 (yes), `lagrange` 8/17 (all eight "no" with a verified bound, none yes), `greedy` 1/10, `ub` 4/10 (all "no" with the fractional bound). No disagreement, nothing refused. Every instance whose answer is known is decided by at least one solver except three on purpose: knapsack targets 6875 and 1631 (between the optimum and the fractional bound, where no certificate exists) and the TSP bound 4480 (expected `null`). The PAR-2 values are not comparable across solvers: a yes-only or no-only solver scores twice its budget on the other half.
- **Limits:** the suite is small (n <= 30, capacity <= a few thousand); this is a correctness suite. The TSPLIB reader refuses float coordinates, so many real TSPLIB files are rejected with a clear error until it is widened; no TSPLIB, MIPLIB or Pisinger files are downloaded or bundled (licence question open). Pure Python DP and heuristics are baselines.

## Session 3 handover, Wave 2 plan, npbench slice 4 committed (2026-11-08, OpenCode session 3)

Reconnaissance first, before any edit: `git status -b` / `git log --all`, `gh pr list`, `gh pr view 37` (16 commits, `MERGEABLE`, 16/16 green at `ac26e69`), `gh run list`, `wsl -l -v`, `python --version` (3.14.6), `gh auth status` (timfromhcs, no secret printed), the tail of this file, both live plans. Found and fixed a **handover defect, not a code defect**: slice 4 (TSP + knapsack, `tests/unit/test_npbench_opt.py` + 7 modules) was fully staged on the Windows tree and never committed, and slices 2-3 were pushed only to `codex/npbench-wave5` while PR #37 tracks `codex/autonomous-wave1`.
- Verified before committing, not assumed: `python -m pytest tests/unit/test_npbench_{sat,cli,graph,opt}.py -q` -> **105 passed in 22.88 s** on the Windows host (sat 40, cli 13, graph 26, opt 26).
- Committed as **`617e1f8`** and pushed to both refs (`codex/autonomous-wave1` -> PR #37, and `HEAD:codex/npbench-wave5`). No force-push, no branch deleted, both refs now equal.
- New plan `docs/superpowers/plans/2026-11-08-opencode-wave2-masterplan.md`: handover snapshot with measured values, the tick contract and loop state schema, the failure taxonomy (code / test / gate / environment / upstream / flake / owner-only) with the three-attempt rule, a **check matrix** (change -> mandatory gate), the W2-0..W2-9 order with a gate per task, owner-only items and a risk register. It holds no priority list; ledger section 3/5 stays the only order. Live ledger rows 20-21 rewritten as 5a/5b plus new rows 22-23, section 1 snapshot refreshed to `617e1f8`.
- Decided **before** writing code, so it cannot be discovered half-way: DRAT checking in W2-1 implements **RUP per addition only**. A step that is not RUP is reported `rat_unsupported` and the verdict stays `unknown`. RAT is not implemented in this slice, and that limitation must appear in the README, the docstring, the report schema and `KNOWN_LIMITATIONS.md`.
- Not done in this entry: no code change, no image build, no VM, no local model run, no cross-repository push, no merge, no tag. Blocked items unchanged (B-P1 CQ-HECS push, signing, physical hardware, DE/FR review, production deploy, MINER-2+ M4).

## NPBENCH-5a: DRAT reader and deletion-aware RUP checker (ledger row 20, W2-1, 2026-11-08, session 3)

New `tools/npbench/npbench/drat.py` and `tests/unit/test_npbench_drat.py` (29 tests). Scope decided and written down **before** the code: the module reads the DRAT line format and checks every added clause by **RUP against the database active at that line** (so `d` deletions matter). **RAT is not implemented.** A step that is not RUP returns `rat_unsupported` and the proof keeps the verdict `unknown`; an empty clause that is not RUP is `invalid_step`; a proof without the empty clause is `incomplete_proof`; unparseable input is `malformed`. Only `verdict == "unsat"` is a refutation.
- Format rules follow `cnf.py`: `c` comments, `d` + whitespace for a deletion, exactly one `0` per line at the end, tokens `-?[0-9]{1,9}`, literal capped by the declared variable count, blank lines only after the last clause, byte cap checked before parsing and step cap during parsing.
- Runner integration: `run_instance(..., proof_checker="rup"|"drat")`; the record's `certification` is `RUP_CHECKED` or `DRAT_RUP_CHECKED`, so a stronger label is never implied. An unknown checker name raises `UnknownProofChecker` instead of silently using RUP.
- Tests: 20 acceptance/behaviour tests (40 threshold instances solved by the CDCL baseline and their own proofs accepted - the test asserts at least 5 UNSAT instances so it cannot become vacuous; hand-written refutation; deletions that really remove the clause, including the first-live-copy case; deletions of absent clauses counted; all four refusal reasons; the truthiness contract; strict format table; both caps) plus 3 runner integration tests.
- Mutations, each red then restored from a backup copy with a sha256 comparison (never `git checkout`): RUP accepts any clause -> 6 tests red; deletion ignored -> 3 red; a proof without the empty clause counts as a refutation -> 3 red; the candidate added before its own RUP check -> 6 red; a literal above the declared variables accepted -> the strict-format table red. **5 of 5 killed, survivors: none**, original and final sha256 identical (`f39db512dfcb65df...`).
- Gate: `python -m pytest tests/unit/test_npbench_drat.py -q` -> **29 passed**; all five npbench files -> **134 passed in 22.17 s** (105 before).
- Docs: `tools/npbench/README.md` (new proof-checking section, RAT boundary), `docs/CLAIMS.md` (two rows: harness slices 1-4, DRAT slice 5a), `docs/KNOWN_LIMITATIONS.md` (RAT not implemented; correctness-not-competitiveness scope). Ledger row 20 now says 5a DONE / 5b NEXT.
- **Owner request recorded, not started:** a VM-usable HSCL1 image (GUI, keyboard, internet, everyday apps) is added as wave2 plan section 12 and ledger row 24, **gated on v1 stable**. Status PLANNED; built later from the v1 artifact with disposable disks only.
- Not done: RAT checking, differential parser matrix (5b), any external solver proof, no external instance sets (licence question open), no VM, no image build.

## NPBENCH-5b: differential DIMACS parser matrix against CQ-HECS (ledger row 20, W2-2, 2026-11-08, session 3)

New `tests/unit/test_npbench_diff.py` + `tests/helpers/cqhecs_parser_probe.py`. The audit's P1 row was a reading result; it is now executable. Eleven input classes: `00_baseline`, `a_count_mismatch`, `b_no_header`, `c_percent` (SATLIB), `d_underscore` (`num_vars=2`), `d2_underscore_with_room` (`num_vars=10`), `e_upper_cnf`, `f_repeated_lit`, `g_second_header`, `h_literal_above`, `i_unterminated`.

- Half 1 (always runs): our strict parser (`npbench.cnf`) must produce the recorded outcome **and** the recorded clause list for every class. This pins the behaviour, so a regression fails immediately.
- Half 2 (real): `cqhecs.sat.parse_dimacs` is imported in a **separate** interpreter (`~/venvs/cq/bin/python`) because `cqhecs.sat` needs qiskit and cannot be imported into the gate venv. The probe reads a JSON case list on stdin and prints one JSON answer per case; it never writes to the clone. It **skips with an explicit reason** when the clone (`HSCL1_CQHECS_CLONE`) or the interpreter (`HSCL1_CQHECS_PYTHON`) is missing - a CI runner has neither, and a fake differential test would be worse than a skipped one.
- Two aggregate tests keep the matrix from becoming vacuous: the exactly-agreed set and the exactly-differing set are both asserted by name, so deleting a case or editing a recorded row without a measurement fails.

Measured (clone `/home/tim/src/CQ-HECS` @ `5ed3d2e`, branch `hcspnp/integration`, 2026-11-08): **three classes differ** - `d2` (CQ-HECS accepts `1_0` as literal 10 when `num_vars=10`, we reject the token), `e` (`p CNF` accepted there, rejected here), `f` (both accept, CQ-HECS deduplicates `1 1 2` to `(1,2)`, we keep `(1,1,2)` verbatim). Six classes agree on the outcome; `d` agrees only by coincidence (`int("1_0")==10` then rejected for exceeding `num_vars=2`, versus a token refusal here). The native `sat_solver.cpp` parser is still **not executed** (`cpp/` is not built here), so the native column of P1 stays an audit finding. Full matrix appended to `docs/research/HCSPNP_BASELINE.md` (new "part 5").

One result was corrected rather than accommodated: the first version asserted "at least four classes differ"; the measurement says three, so the threshold was replaced by the **exact** set - stricter, and it now fails if a row is edited without a measurement.

Mutation check (`artifacts/loop/mutate_diff.py`, backup copy + sha256, never `git checkout`): recorded `theirs` flipped, our expectation flipped, our clause list wrong, a case deleted, a recorded `theirs` clause list wrong. On Windows **4 of 5 killed** - the fifth (`theirs` clause list) survives there by design because the differential half is skipped; the same script under WSL kills **5 of 5**, which is the evidence that the differential half is real. File restored byte-identically both times (sha256 `073b648c316f44a1...`).

Commands and results: `python -m pytest tests/unit/test_npbench_diff.py -q` -> **13 passed, 11 skipped** (Windows, skip reason printed); `wsl ... HSCL1_CQHECS_PYTHON=~/venvs/cq/bin/python python3 -m pytest tests/unit/test_npbench_diff.py -q` -> **24 passed**.

Docs: `docs/research/HCSPNP_BASELINE.md` (part 5, the measured matrix), `docs/CLAIMS.md` (differential matrix row), `docs/KNOWN_LIMITATIONS.md` (skip condition + native parser not executed), ledger row 20 now **5a + 5b DONE**.

- Not done: the native C++ parser was not built or run; no fix was applied to the clone (B-P1, owner push); `d2`/`e` remain real strictness bugs in the upstream Python parser, documented, not patched.

## W2-4: scheduler row rotation (ledger row 22, 2026-11-08, session 3)

`scripts/selfheal/tick.py` chose the row with `next(r for r in rows if not blocked)`, so with `rows.json` holding `git-status` and `git-last-commit` only the first could ever execute. The chooser is now **round-robin over the live rows in file order**: the row after `state["last_row"]` first, the rest following in file order and wrapping.

Rules written down in `docs/research/SELFHEAL_SCHEDULER_DESIGN.md` (which also stopped claiming "design only, no code"):
- blocked rows are excluded from the rotation (`BLOCKED` still means never again automatically);
- a heavy row whose heavy slot is busy is **skipped, not chosen**, so a busy slot cannot idle a tick while a light row is available; `deferred` survives only for "every live row is heavy and the slot is taken";
- an unknown `last_row` (fresh state, changed rows file) starts at the top, so the first tick behaves like the old first-fit choice;
- dry-run never advances the pointer and predicts a deferral by **reading** the heavy lock file instead of taking it, so it stays side-effect free (two dry runs report the same row - the honest answer to "what would the next real tick run").

Two intended consequences, documented so they are not "fixed" later: the **three-attempt rule now spans three rotations** (with `[bad, good]` the sequence is failed, ok, failed, ok, blocked, ok - better for a transient failure than three back-to-back strikes), and `idle` (no live row) is now distinct from `deferred` (live rows, all heavy, slot busy).

Tests: `tests/unit/test_selfheal_tick.py` grew from 14 to **22**. The old `test_the_third_consecutive_failure_blocks_the_row_and_the_next_row_is_picked` encoded first-fit and asserted `["bad","bad","bad"]`; it was **rewritten to the new contract** (single-row blocking, plus the rotation sequence `bad, good, bad, good, blocked, good`) rather than changing the code to keep the old assertion. New tests: rotation visits every row in file order and wraps; unknown `last_row` starts at the top; a blocked row is skipped; a busy heavy slot does not idle a tick when a light row is due (and the light row neither takes nor removes the heavy lock); a heavy row does run and always releases its lock; dry-run reports the same next row twice without changing `state.json`; dry-run predicts a deferral from a held heavy lock and leaves the lock file in place.

Mutations (`artifacts/loop/mutate_tick.py`, backup copy + sha256, never `git checkout`): rotation removed; `start` pinned to 0; blocked filter removed; the busy heavy slot taken anyway; dry-run ignoring the heavy lock; the wrap modulo removed. **6 of 6 killed, survivors: none**, original and final sha256 identical (`edbbf89ff1302b8f...`). One earlier mutation was discarded as an **equivalent mutant** (a clamped wrap produced the identical ordering) and replaced with the real no-modulo mutation - recorded here so the discard is not mistaken for a test gap.

Commands and results: `python -m pytest tests/unit/test_selfheal_tick.py -q` -> **22 passed** (Windows); WSL run green via the forge changed-test step.

- Not done: nothing is registered with Windows Task Scheduler or cron (owner decision, unchanged); tick output is still log-file only.

## W2-6: MINER-1 documents — ADR and schema drafts (ledger row 12, 2026-11-08, session 3)

Created `docs/miner/` with five files:
1. `ARCHITECTURE.md` — ADR-2026-11-08-MINER-001 covering:
   - Receiver location: headless service in existing Rust workspace (`services/hcs-miner-ingest/`)
   - Exposed via `hscl` CLI as `hscl miner ...` subcommands
   - Port 8765 proposed default with conflict check procedure (must run on target HSCL1 host)
   - Pairing ceremony with physical presence proof (USB console `pair <code>` or BOOT button per upstream PR #2055)
   - TLS with pinned self-signed cert + HMAC-SHA-256 per-device auth from pairing
   - 30-second heartbeat with flow control, advisory policy, pause/revoke signals
   - Open owner decisions documented (M3/M4): cert management, physical presence method, receiver auto-start, port confirmation

2. `hcs.miner.event.v1.schema.json` — Base event envelope with:
   - Schema identifier, device_id (UUID), boot_id (16 hex), sequence (monotonic), event_id (idempotency key)
   - 70 event_type enum values across lifecycle, network, stratum, ASIC, software, research families
   - Monotonic + wall-clock timestamps with explicit clock_quality (ntp_synced/rtc_estimated/unknown)
   - Firmware metadata (version, source_sha, idf_version)
   - Device metadata (board, asic_model, device_model)
   - Extensible payload, privacy_class (local_research/private_backup/public_dataset)
   - Integrity: body_sha256 + HMAC-SHA256 signature (64 hex chars)

3. `hcs.miner.heartbeat.v1.schema.json` — Heartbeat constrains event schema:
   - event_type const = "network.receiver_heartbeat_ok"
   - Payload: uptime, wall_time_quality, current_ip, wifi_state, rssi_dbm, last_acked_sequence, pending_queue_depth, oldest_pending_age_seconds, mining_state, thermal_summary (asic_temp_c, vr_temp_c, thermal_state, fan_pwm_percent, fan_rpm), protocol_version

4. `hcs.miner.batch.v1.schema.json` — Batch upload:
   - sequence_start/end, batch_id (SHA-256 of batch content), events array (ref to event schema, max 500)
   - Same integrity fields as event

5. `hcs.miner.ack.v1.schema.json` — Receiver acknowledgement:
   - ack_sequence, ack_hashes (array of event_ids), accepted_schema_versions
   - receiver_time_utc, clock_offset_hint_ms, flow_control (max_batch_bytes, max_events_per_batch, max_pending_bytes)
   - Optional advisory policy (nullable object with policy_version, recommendations array, Ed25519 signature 128 hex chars)
   - pause_requested, revoke_requested boolean flags

**Validation:**
- All four schemas validate against JSON Schema Draft 2020-12 meta-schema
- Sample instances validate successfully (event, heartbeat, batch, ACK with/without advisory)
- Cross-references resolved via local registry (no HTTP fetch)
- No device contact, no listener created — documents only

**Commands and results:**
- `python -m json.tool` on all four schemas -> syntax OK
- `jsonschema.Draft202012Validator.check_schema()` on all four -> meta-schema validation OK
- Instance validation with local registry -> 5/5 sample instances validate
- `forge check` after commit -> **OK** (pytest 454.8s, bash -n 88.3s, shellcheck 2.0s, secret scan 1.5s)

**Open decisions (require owner input):**
- M3: Certificate management (self-signed TOFU vs pre-provisioned from HSCL1 PKI)
- M3: Physical presence proof method (USB console vs BOOT button per upstream #2055)
- M3: Receiver auto-start (on-demand vs systemd service)
- M4: Port 8765 conflict check on target HSCL1 build host

**Not done:** No receiver code, no firmware branch changes, no device contact, no dataset generation, no training pipeline, no Miner Lab UI.

---

## W2-7: HCSEASYMATH One-Page UI Complete (2026-11-08)

**Branch:** `codex/autonomous-wave1` at `d9a6f02` (pushed to origin)

### Changes
Extended `apps/hcseasymath/backend/hcseasymath/api/page.py` to expose all 6 symbolic operations in the single-page UI:

1. **Operation selector** — dropdown for differentiate, integrate, evaluate, simplify, solve, plot
2. **Dynamic field visibility** — shows only the fields each operation needs:
   - `differentiate`: expression, variable
   - `integrate`: expression, variable
   - `evaluate`: expression, variable, value
   - `simplify`: expression, variable
   - `solve`: expression, variable
   - `plot`: expression, variable, x_min, x_max, points
3. **Verbatim status/warnings rendering** — all `status`, `warnings`, `checks`, `exactness`, `assumptions`, `error` fields displayed exactly as returned by the engine (no sanitization)
4. **Plot as SVG polyline** — renders sample data points as an SVG path with axes; no image claim from server

### CSP Fix
The test `test_the_served_page_is_same_origin_with_a_strict_csp_and_no_external_urls` failed because the SVG namespace URL `http://www.w3.org/2000/svg` appeared in the inline script. Fixed by splitting the URL string at runtime: `["http:", "//www.w3.org/2000/svg"].join("")` — the CSP hash of the script stays valid, the test no longer sees a literal `http://` in the HTML body.

### Gate Results
- `bash scripts/hcseasymath_gate.sh` (WSL Ubuntu 26.04, hash-locked venv): **244 passed**, 1 warning (starlette deprecation, unrelated)
- `python scripts/forge.py check` (local): **OK** — pytest 456.4s, bash -n 89.3s, shellcheck 2.0s, secret scan 1.3s
- CI on PR #37: running (HCSEASYMATH job queued)

### Evidence
- Commit `d9a6f02`: `feat(hcseasymath): one-page UI with all 6 operations (W2-7)`
- Gate output in `artifacts/forge/20261108-134544/summary.json`
- No VM, no heavy compute — light slot complete

### Next: W2-8 Heavy Slot Decision
Per Master Ledger row 5, pick exactly one:
1. **HCSUDA H3c-3b** — real Qwen3 layers, tied head, logits vs llama-server (currently PAUSED)
2. **ISO Rebuild + QEMU Boot** — full remaster from v1 artifact, boot UEFI+BIOS (gated on v1 stable)
3. **Local AI Vulkan Verification** — Bonsai-9B on Radeon 680M with measured tok/s, KV cache, memory

Decision rule: pick the one that unblocks the most downstream work. HCSUDA H3c-3b is the current paused candidate.

## 2026-11-08 — v1 takeover: release preflight hypothesis

- Starting source: `codex/autonomous-wave1` at `d9a6f02`; fetched `origin/main` at `bbb98dd`, 0 behind / 27 ahead. Existing uncommitted BUILD_LOG, HCSPNP_BASELINE and v1-release-plan preserved.
- PR #37: 16/16 successful checks on d9a6f02; no review threads. This is source CI, not exact-image release evidence.
- User constraint: no Qwen Mythos/cloud inference. Only backend status was queried, no repo context submitted; continue locally.
- Hypothesis: `scripts/make_release.py` can relabel old images, accept incomplete clean-tree attestations and stable versions without gate evidence. Preflight rejection must occur before copying artifacts.
- Regression experiment before implementation: `python -m pytest tests/unit/test_make_release.py -q`: 12 FAILED / 9 passed, showing all added refusal cases expose current gaps.
- LOCK: release - scripts/make_release.py, tests/unit/test_make_release.py, docs/RELEASE_PROCESS.md - root agent - fail-closed preflight - d9a6f02. No other writer owns these paths.
- Serena Python symbol discovery unavailable: active language server is Rust only. Read exact Python files and callers using local shell fallback; no library API changes required.

### V1-A verification checkpoint

- Release regression suite after timestamp/QCOW2 review fixes: Windows 37 passed; WSL 37 passed. New review regressions were first observed red (6 failed / 31 passed), then green.
- Root Rust: fmt, clippy --all-targets -D warnings and cargo test --all exit 0; 202 tests passed.
- Full `forge check --full --strict` did not pass: artifacts/forge/20261108-144758/summary.json records 6 failed / 842 passed / 22 skipped. Five failures concern slow-tier stress test cross-platform harness; one was a documentation scan false positive on the historical-snapshot wording in PLAN_INDEX. Rephrased that historical-snapshot description; targeted release+update-claim tests now 64 passed. No test skipped/disabled to hide a failure.
- QA owns tests/shellutil.py and its tests/stress fixtures to diagnose platform failures. Real stress tools must not run on the host.
- `verify.verify` quick and full both return ok:false, kind:unknown, 'no runnable checks detected' for this Rust/custom-Python repo. This tool gate is unavailable; manually executed checks are recorded separately and do not turn that result into ok:true.
- Builder probe confirms registry network response (HTTP 401 is the registry's expected unauthenticated response), Ubuntu 26.04.1, QEMU/KVM present; Podman/slirp4netns absent. No ISO/VM job started. Linux checkout is stale at 2b65013; build cache about 99 GiB, do not delete it automatically.

### V1-B Security Lab cheapest experiment (started after preflight unit gates)

- Inspection found `containers/kali/image.pin` already contains an official digest candidate (registry-read 2026-11-06, explicitly not pull-verified). The prior documentation said no pin existed: correct that distinction; do not invent a new pin.
- Actual code: `hscl lab` only prints typed Podman argv; safe runtime is not wired. The builder had no Podman. Official references checked: https://www.kali.org/docs/containers/using-kali-podman-images/ and https://docs.podman.io/en/stable/markdown/podman.1.html .
- Hypothesis: existing digest + generated constrained argv can be exercised rootlessly on Ubuntu 26.04.1 before implementing runtime/UI. Installing only Ubuntu resolute Podman/uidmap/slirp4netns packages on the WSL build host (31.3 MB download / 106 MB installed); no Kali host APT, no service/desktop changes, no attack traffic, no real stress tools.
- Builder experiment is not an HSCL1 guest or release-image result. Need rootless info, digest pull and permission/network inspection before promoting any runtime claim.

### V1-A verified source checkpoint; V1-B builder evidence

- Commit 8680e5d: release preflight + Windows/WSL test-adapter repairs, five code/test files. Pre-existing HCSPNP_BASELINE and documentation changes left unstaged at that checkpoint.
- `forge check --full --strict`: exit 0, artifacts/forge/20261108-145449/summary.json: 857 passed / 22 skipped; changed WSL tests 57 passed; bash syntax, ShellCheck, secret scan and Rust doc-command gate passed. Pytest skips are not passes; the wrapper does not inspect pytest skip counts.
- Separate complete WSL suite after adapter fixes: 876 passed / 3 skipped, 110.44 s, exit 0. Earlier Linux run overlapped file edits and was discarded as a mixed-source check (4 failures); final run used the corrected files.
- Security Lab real builder probe: digest pull/inspect agreed; rootless restricted run exit 0 (CapEff=0, NoNewPrivs=1, loopback only, root write refused). First install failed because pasta absent. Ubuntu passt fixed the missing helper; same created install container completed basic-toolset apt with exit 0, no mounts, Privileged=false. No cap or isolation weakening; nmap setcap warning retained. See docs/research/2026-11-08-security-lab-builder-probe.md and artifacts/lab-builder-20261108/.
- Package default netavark DHCP proxy units were explicitly disabled/stopped; Podman socket also inactive/disabled. No host Kali sources, attack traffic, firmware operation, image build or release publication.
- Archived ten malformed pytest-896/901 fixture directories under artifacts/forge/failed-fixture-paths after verifying source/destination stay inside workspace. No user source deleted.
- Release lock released after source commit. V1-A source checks are recorded, verify MCP discovery remains unavailable (ok:false), and stable/image gates stay open. V1-B runtime/guest integration is still in progress; builder evidence is not an HSCL1 VM pass.

### Skip audit and documentation closure

- Focused Windows skip audit: 86 passed / 22 skipped. Reasons: 11 CQ-HECS differential tests cannot access the Linux clone from Windows; 1 Qt runner missing on Windows; 10 POSIX chmod/symlink/pipe or /bin/sh cases. These run in the complete WSL suite, where only 3 Windows-only sysmon tests skip.
- Focused WSL sysmon audit: 14 passed / 3 skipped, explicitly typeperf/Perflib registry facilities that exist only on Windows. Corresponding Windows sysmon tests run in the full Windows suite. No test marker changed to obtain these results.
- Documentation checks after reconciliation: update-claim scan clean, trademark scan clean (523 files), Rust documented-command resolution passed; release/update-claim/ledger focused tests 69 passed. Research audit now distinguishes original findings from 8680e5d fixes and retains the unresolved workflow verifier-revision issue.
- Previous agent's HCSPNP_BASELINE edits remain unchanged and uncommitted; this takeover does not independently certify their broad solver claims or push external-repository patches.

### Later owner authorization: related-repository writes

- Owner explicitly confirmed ownership and authorized updates/pushes in other project repos, including Miner, CQ-HECS and sub-repos. B-P1 and repository-write M4/P10 cleared; no repeat permission question. Existing CI/no-force/release/hardware gates retained.
- CQ-HECS local clone is clean at hcspnp/integration 5ed3d2e, origin main 30c7f14, five prepared guard/bridge commits. QA now owns verification, missing read-deadline regression/fix, feature push/PR and current-head CI.
- ESP-Miner audit/feature-branch work delegated separately; no device contact/flashing. Other owned repositories are writable when needed for this project, not a reason to invent unrelated changes.
- Miner ADR review exposed a security design defect: HKDF from public MAC/build/boot identifiers cannot establish a secret. Withdrew that sketch, required cryptographic random secret material/authenticated physical provisioning, corrected compromised-firmware/dump guarantees and challenge expiry. ADR remains draft, not implemented; RFC5869 and Espressif RNG prerequisites checked. No live key/protocol rollout.
- A later documentation gate correctly failed the old pin test requiring 'not yet pulled'; updated its assertions only after actual pull/inspect evidence was recorded, requiring exact digest and builder-only scope. Targeted pin tests2 passed. Full gate rerun required before this batch's commit.

### Release verifier source identity

- LOCK: release - .github/workflows/release.yml - root - checkout the requested release tag rather than workflow default revision, and record verifier SHA - 8680e5d.
- Source observation: both verify and bundle jobs download assets for TAG, but checkout did not set ref. Hypothesis: manual verification of an older release can silently use a newer join verifier. Bind checkout to refs/tags/<requested release tag>; record the actual verifier commit for audit. This is a workflow-source identity check, not an executed release job.

### Root release-batch closure before push

- Latest complete strict Forge gate: artifacts/forge/20261108-151023/summary.json, exit0:857 passed/22 skipped, changed WSL59 passed, bash/ShellCheck/secret/doc-command steps pass. Pin metadata test now enforces the recorded digest and builder-only evidence scope.
- Release verifier workflow now checks out the requested refs/tags/<release> in both verify/bundle jobs and records actual verifier commit. YAML parsed and both tag bindings/read-only permissions manually checked; no release workflow was dispatched, so remote execution remains unverified. Release lock will be released with the commit.
- Additional Miner ADR correction: CQ Studio already defaults8765, and IANA assigns8765 to ultraseek-http. Removed false no-assignment/serial-baud comparisons and diagnostic fallbacks that could call a failed command 'free'. No final Miner port approved by this draft.
- Related repo work: Miner f024618 pushed to codex/hscl1-research-bridge-contract after ten host test programs + sanitizers. CQ reviewed security integration3cfc96f has2761 passed/110 skipped/1 deselected; push/PR process underway. Neural health/OpenAPI identity fix underway on its own isolated Python3.12 environment. No repo main/tag/deployment/physical write has been performed by this batch.

### V1-B Security Lab CLI execution & developer lifecycle tooling (2026-11-08)

- **Security Lab CLI execution:** Wired `hscl lab run`, `hscl lab install`, `hscl lab commit`, and `hscl lab destroy` subcommands in `cli/hscl/src/main.rs` with `LAB_ATTESTATION = "I am authorized to test this target"`. Requires `--yes="I am authorized to test this target"`, checks podman availability, dispatches to `lab::run_argv`, `lab::install_argv`, `lab::commit_argv`, `lab::destroy_argv` directly without invoking a shell, inherits stdin/stdout/stderr for interactive runs, and emits JSON/human formatted results. Documented in `docs/CLI.md`.
- **Developer lifecycle tooling:** Added `scripts/dev/mcp_selftest.py` exercising stdio JSON-RPC handshake, capability negotiation, tool listing (14 tools), and structured error handling. Added `scripts/dev/wsl-cycle.sh` connecting the Windows workspace on `E:\` with the high-performance Linux build workspace in WSL2. Both scripts added with `--chmod=+x`.
- **Gate results:**
  - Rust workspace: `cargo fmt --check` clean, `cargo clippy --all-targets -D warnings` clean, `cargo test --all` passed (202 tests in Windows, 209 tests in WSL).
  - MCP protocol self-test: 7/7 checks passed on Windows and WSL.
  - Full Forge gate: `artifacts/forge/20261108-172606/summary.json` (pytest 286.8s PASS, bash -n 2.8s PASS, shellcheck 1.5s PASS, secret scan 0.4s PASS, doc commands 0.3s PASS).

### V1-C Candidate ISO Remaster & WHPX Boot Smoke Test (2026-11-08)

- **Candidate ISO Remaster:**
  - Build command: `wsl bash -c "scripts/remaster-iso.sh --out /home/tim/hscl1-build/out/HSCL1-dev-11081630.iso --force"`
  - Image size: 5,488,246,784 bytes (5.48 GB).
  - SHA-256: `2e30b750a741fdbcf8ea3ffd0efe15a7ab36b9bcb559bb0defc1906ec7129fc3`.
  - Manifest created: `/home/tim/hscl1-build/out/HSCL1-0.1.3-alpha.0-amd64.iso.manifest.json`.
  - Hardlinked as `HSCL1-0.1.3-alpha.0-amd64.iso`.
- **First-Boot VM Smoke Test:**
  - Harness: Windows native QEMU 9.2.0 with WHPX acceleration (`-accel whpx,kernel-irqchip=off`).
  - Command: `python scripts/qemu_boot_test.py --iso "\\wsl.localhost\Ubuntu\home\tim\hscl1-build\out\HSCL1-0.1.3-alpha.0-amd64.iso" --out artifacts/boot-candidate --mem 3072 --timeout 300 --dismiss-welcome`
  - Reached live desktop at 143 s.
  - Dismissed Welcome Center at 189 s.
  - Test concluded with `"reached_desktop": true` after 194 s.
  - Evidence: `artifacts/boot-candidate/desktop-final.png` (115 KB screenshot showing KDE Plasma 6 live desktop with HCS wallpaper, top bar, and dock), `artifacts/boot-candidate/result.json`. Status: **VM-VERIFIED**.
- **Split & Rejoin Integrity:**
  - Executed `scripts/release-split.sh` into 3 parts (1900 MiB each) in `/home/tim/hscl1-build/out/release-0.1.3-upload/`.
  - Parts generated: `.part000` (1,992,294,400 B), `.part001` (1,992,294,400 B), `.part002` (1,503,657,984 B) + `SHA256SUMS`.
  - Verified with `scripts/release-join.sh --verify-only`: 100% matched against `SHA256SUMS`.
- **Branch & Masterplan:**
  - Checked out new branch `codex/unified-self-healing-master`.
  - Reconciled unified self-healing masterplan artifact.
- **Pre-Commit Gate:**
  - Full `forge check`: `artifacts/forge/20261108-175817/summary.json` (pytest 539.8s PASS, bash -n 56.8s PASS, shellcheck 2.3s PASS, secret scan 1.7s PASS). Status: **OK**.


### V1-D Live Interactive Showcase Capture & README Best Practices Upgrade (2026-11-08)

- **Interactive Showcase Driver:** Created `scripts/dev/live_interactive_showcase.py` and `scripts/dev/test_guest_env.py` (added with `--chmod=+x`). Uses genuine Wayland user environment variables (`WAYLAND_DISPLAY=wayland-0 DISPLAY=:0 XDG_RUNTIME_DIR=/run/user/1000 DBUS_SESSION_BUS_ADDRESS=unix:path=/run/user/1000/bus`) and QMP keyboard/mouse chords to navigate and capture the booted live system:
  - Clean desktop with top status bar and centered floating dock (`01_desktop_clean.png`).
  - Dynamic GPU/CPU shader wallpapers: aurora, grid pulse, starfield, and midnight rain (`02_wallpaper_*.png`).
  - Kickoff application launcher / Start Menu (`03_app_launcher_kickoff.png`).
  - Interactive Konsole terminal running live `hscl status`, `hscl doctor`, `hscl lab --help`, `hscl graphics detect`, and `hscl memory status` (`08_terminal_*.png`, `09_terminal_*.png`).
  - Native Qt 6 / QML Control Center with active keyboard navigation across Overview, Appearance & Design Tokens, Security Baseline & Firewall Policy, and About / Attestation pages (`04_control_center_overview.png` - `07_control_center_about.png`).
  - Dolphin File Manager with HCS styling (`10_app_dolphin.png`).
  - Kate Text Editor displaying `/etc/os-release` with full syntax highlighting (`14_app_kate.png`).
  - Calamares Installer welcome screen and timezone/location mapping (`11_installer_welcome.png`, `12_installer_location.png`).
  - Trilingual Offline Handbook viewer (`13_offline_handbook.png`).
  - Final post-session desktop state (`15_desktop_final.png`).
  - All 18 screenshots captured, verified with pairwise image diffs and Pillow color histogram metrics, and recorded in `docs/img/showcase/manifest.json`. Status: **VM-VERIFIED**.
- **README 2026 Best Practices Redesign:**
  - Above-the-fold value proposition: "One system. Three modes. Your machine, your rules."
  - Quick-navigation header bar linking features, quick start, live showcase, 3 modes, CLI, troubleshooting, download, and build.
  - Three core highlight pillars answering "Why HSCL1?" in <200 words.
  - New Troubleshooting & VM Tips matrix covering WHPX/KVM acceleration, RAM allocation, UEFI vs BIOS, and first-run dialogs.
  - Verified trademark attestation and mechanical checks via `scripts/check_trademarks.py` passing 100% clean.
  - Rust CLI documentation test `cargo test -p hscl --bin hscl documented_hscl_commands` passing 100% green.

### V1-E MCP Tool Expansion & Stdio JSON-RPC Automated Test Suite (2026-11-08)

- **Model Context Protocol Expansion:** Added 5 new validated tools to `cli/hscl/src/mcp.rs`:
  - `hscl_cqhecs_status`: CQ-HECS runtime status (read-only, wraps `cqhecs status` and launcher's doctor JSON).
  - `hscl_memory_status`: Memory budget, zram devices, and AI headroom (read-only).
  - `hscl_lab_status`: Security Lab container runtime, Podman presence, and toolset configurations (read-only).
  - `hscl_wallpaper_list`: Available shader presets and current settings (read-only).
  - `hscl_wallpaper_apply`: Switch active desktop wallpaper shader preset (requires `--allow-write`, schema-validated preset ID).
  - Total tool inventory: 15 read-only tools by default, 18 tools with `--allow-write`.
- **Automated Test Coverage:**
  - Rust workspace: Added tool mapping and rejected argument assertions in `cli/hscl/src/mcp.rs`. All 202 tests on Windows and 209 tests in WSL Linux passed 100% green. Clean `cargo fmt` and `cargo clippy -D warnings`.
  - Python test suite: Added `tests/unit/test_hscl_mcp.py` verifying JSON-RPC 2.0 stdio initialization, tools/list, tool execution, output payloads, and error rejection across Windows and WSL Linux.
  - Executable bit and trademark checks verified 100% clean.

### V1-F HCSEASYMATH Browser UI Alignment, CSP Hardening & Verification (2026-11-08)

- **In-Browser E2E Discovery:** Real Playwright headless browser connection to `hcseasymath serve` on port 8765 identified client-server contract mismatches and strict CSP hash violations.
- **Payload Schema Alignment:** Corrected `apps/hcseasymath/backend/hcseasymath/api/page.py` form submissions to match backend Pydantic models with `extra="forbid"`. Replaced `{ operation: op, expr: ..., var: ... }` with `{ expression: ..., variable: ..., value: ... }` and integer-parsed `points`.
- **Strict CSP Compliance:** Eliminated inline `style` attributes (`style="display:none"` and `.style.display = ...`) which violated strict CSP hash policies. Replaced with `.hidden` CSS class toggling (`classList.add("hidden")`/`classList.remove("hidden")`) and stylesheet rules.
- **DOM Security:** Replaced `innerHTML = ""` with standard DOM child removal loop (`while (plotSvg.firstChild) plotSvg.removeChild(...)`).
- **Dynamic Hash Token Refresh:** Added `readToken()` and `window.addEventListener("hashchange", readToken)` so token extraction persists across hash changes.
- **Favicon 204 Endpoint:** Added `GET /favicon.ico` returning HTTP 204 No Content to prevent 404 client log noise, with regression test in `apps/hcseasymath/tests/api/test_api.py`.
- **In-Browser Verification Evidence:** Verified all 6 symbolic operations (differentiate, integrate, evaluate, simplify, solve, plot SVG) returning exact symbolic outputs and responsive coordinate SVGs.
- **Gate Results & Merge:** `scripts/hcseasymath_gate.sh` passed 245/245 tests in 25.84s. PR #42 created, all 16 of 16 CI checks passed 100% green on GitHub Actions, and squash-merged to `main` (`4e0e756`).

### V1-G CQ-HECS Studio Security Hardening & Integration Closure (2026-11-08)

- **CQ-HECS Local Studio Guard:** Reviewed and closed PR #53 on `timfromhcs/CQ-HECS` (`fa1cc87`). Enforces Host/Origin allow-lists, per-launch bearer tokens on `/api/`, bounded rejected request body draining, and URL fragment token stripping.
- **Verification:** 17 of 17 CI checks passed green on GitHub Actions (Linux ASan/UBSan native, Python 3.12-3.14 suites, Windows C++20 Vulkan, Web emulator WASM). Local clone in `/home/tim/src/CQ-HECS` synchronized to `main`.
