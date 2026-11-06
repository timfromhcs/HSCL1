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
