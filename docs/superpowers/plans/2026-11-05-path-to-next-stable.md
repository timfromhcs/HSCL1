# Path to the next stable release

> Executed autonomously. Evidence in `docs/BUILD_LOG.md`. Parents: `2026-11-05-hscl1-to-v2-stable.md`, `2026-11-05-prebuilt-image-and-updates.md`. AGENTS.md wins on conflict.

**Goal:** a release ladder with honest gates. Every rung ships only what has evidence; a rung is skipped, never faked.

| Rung | Name | Meaning | Exit gate |
|---|---|---|---|
| R1 | `0.1.0-alpha.1` | local release set: live ISO + prebuilt OEM qcow2, both VM-verified, credential-clean | W0 + W1 green |
| R2 | `0.2.0-beta.1` | installer/boot hardening evidence: Secure Boot state read in the guest, LUKS2 install, fault injection, EN/DE/FR installer run, visual QA matrix | W2 + W3 + W4 green |
| R3 | `2.0.0-rc.1` | feature-complete v2 scope, supply-chain evidence, website, docs | W5 + W6 + W7 green |
| R4 | `v2.0.0` stable | every AGENTS.md §14.2/§20 gate passes, owner decisions made, signed | W8 |

Published/signed/tagged artifacts need the owner's decisions (repo visibility, licence, signing key) - until then every rung is a **local** release set.

## Constraints learned (drive the order)

- The host has 19.8 GB RAM; `.wslconfig` gave WSL 16.5 GB, so a build plus a VM starves Windows and the session gets reaped. `E:` has 26 GB free of 466 GB.
- Build time is dominated by unpacking the 5 GB squashfs and re-squashing; both variants (release, QA) were built twice.
- Never restart a reaped job automatically; free resources first.

## W0 - Resources and a smarter build engine (now)

- [ ] **Free resources (HSCL1-owned data only):** stop stale QEMU/WSL jobs; delete HSCL1 test disks and superseded ISOs under `artifacts/`; keep evidence PNG/JSON; drop WSL page cache; remove the superseded `work/rootfs`.  Never touch `~/hcs-build` (an older, unrelated project).
- [ ] **Memory policy:** `.wslconfig`: `memory=10GB`, `processors=8`, `[experimental] autoMemoryReclaim=gradual`, `sparseVhd=true`; keep a backup copy of the old file. VM tests use 4 GB; builds are capped separately.
- [ ] **Build engine:** (a) cache the pristine unpacked rootfs and customise through an overlayfs (no 15 GB re-unpack, no `rm -rf`); (b) `mksquashfs -processors N -mem 1G` (bounded RAM); (c) `--variants release,qa` produces both ISOs in one run: release is squashed first and verified, then `hscl-qa` is added to the overlay and the QA ISO is squashed; (d) the final ISO is written to the WSL disk and copied once.
- [ ] Test: shellcheck; a run proving the second build skips the unpack and finishes faster; both manifests exist, `qa_image` false/true correct; `verify-image.sh` passes on the release variant and the release rootfs has **no** `hscl-qa`.
- [ ] Add a guard to the harness and scripts: refuse to start a build or VM when free memory is below a threshold (Windows `Get-CimInstance`, WSL `/proc/meminfo`) and print how to free it.

## W1 - Prebuilt image and release set (R1)

- [ ] Release ISO (no QA) with all pending fixes (SDDM theme, avatar, `hscl1_*` labels, OEM launcher name).
- [ ] Explore Calamares OEM mode in a VM; write `install-oem.json`; install to a 40 GB qcow2; the VM powers off at the end and the disk is not touched afterwards.
- [ ] `scripts/make-prebuilt.sh` with `--allow-user <oem account>`; fix findings until the scan is clean (no extra users, no SSH keys, empty machine-id).
- [ ] Verify on a **copy**: OEM first-boot screen, create a throw-away user, desktop, `qa_report` (QA ISO variant of the same build for the report); screenshots.
- [ ] `make_release.py 0.1.0-alpha.1 ...` -> `artifacts/release/0.1.0-alpha.1/` (ISO, qcow2, SHA256SUMS, manifest, notes). Update BUILD_LOG and KNOWN_LIMITATIONS.

## W2 - Updates (completes the update plan, R2)

- [ ] Control Center: "Updates" row (allow-listed `system updates --check`), de/fr strings, QML test with mock data, broken-apt state shown as an error.
- [ ] `remaster --upgrade`: apt dist-upgrade of the overlay (security+updates pockets), regenerate casper initrd, copy kernel/initrd to the ISO, kernel-consistency check in `verify-image.sh`; boot test; record package delta. BLOCKED with evidence if the kernel cannot be made consistent.
- [ ] Installed-system check in a VM: `hscl system updates --check` with network, `unattended-upgrades --dry-run` output proves only the security origin.

## W3 - Boot and install hardening (R2)

- [ ] Secure Boot inside the guest: TCG run with `--qa-out`; `mokutil --sb-state` must say enabled; record. Wrong claim -> keep "no Secure Boot claim".
- [ ] LUKS2 install: scenario with encryption checked; reboot; unlock with the passphrase; wrong passphrase refused; assert no passphrase in `/var/log/installer`, `/var/log/calamares`.
- [ ] Fault injection: kill the VM mid-copy and with a full disk; the second attempt on a fresh disk succeeds; no other disk is touched (single-disk VM).
- [ ] Installer DE and FR run (language chosen on the welcome page): screenshots for every page, no clipped buttons.

## W4 - Visual QA and accessibility (R2)

- [ ] Scenario matrix: {desktop, launcher, overview, Control Center pages, installer pages, login, lock screen} x {1366x768, 1920x1080} x {dark, light} x {en, de, fr}; reference screenshots in `tests/visual/baselines/` (small, curated); perceptual diff and clipped-text check (`tests/visual/compare.py`).
- [ ] Define and bind the documented shortcut set (AGENTS.md §4.5) in `hscl-desktop`; generate `docs/shortcuts.json` from the shipped file; test every row is bound; only then mention shortcuts in UI/handbook.
- [ ] Keyboard-only walk through launcher, Control Center, installer; accessible names audited from the QML tree; reduced-motion and high-contrast scenarios.

## W5 - v2 feature scope (R3)

- [ ] `hscl tools` catalog (manifest-driven, dry-run, licence field); bundles Developer/Creator/Privacy.
- [ ] Security Lab: rootless Podman run-spec generator with tests for every unsafe default; Kali image by pinned digest; disabled by default.
- [ ] Privacy: `tails verify` (gpg + sha256, tamper tests), Tor status/launch; Privacy Session stays EXPERIMENTAL without packet-capture evidence.
- [ ] Local AI: `ai setup/model/storage` with checksum and licence prompts; CPU fallback; no weights in the ISO.
- [ ] Privileged helper + Polkit for `firewall profile`, `updates --install`; fuzz/property tests for argument parsing.
- [ ] More handbook chapters (Security Lab guide, Privacy and Tails distinction, Local AI, Developer workflow, Installation guide, FAQ) in EN/DE/FR, command-tested.

## W6 - Hardening and supply chain (R3)

- [ ] `cargo audit`/`deny`, clippy, shellcheck, ruff, qmllint, secret scan in `scripts/ci-local.sh` and pinned-SHA GitHub workflows (not run until a remote exists).
- [ ] SBOM (SPDX from the image dpkg database), package manifest, build manifest from the final ISO; licence report -> `docs/LICENSES.md`.
- [ ] `docs/CLAIMS.md`: every README/website claim mapped to a test or removed; threat model re-synced.

## W7 - Website and docs (R3)

- [ ] Astro site (EN/DE/FR, tokens shared with the OS), real screenshots from W4 only, "Release not published yet" until a release exists, download metadata generated from `build-manifest.json`; build, link check, Lighthouse smoke, no horizontal overflow at 390 px.
- [ ] Complete the AGENTS.md §13.2 docs set.

## W8 - Release (R4)

- [ ] Clean-environment rebuild, full matrix, §14.2/§20 checklist walk; any red item -> stay at rc.
- [ ] Owner decisions requested once: repo visibility, licence, signing key; then tag, signed checksums, upload, Vercel; verify downloads.

## Review focus

- A build or VM starts while memory is short and the session is reaped -> W0 guard and 10 GB cap.
- The QA variant leaks into a release -> manifests carry `qa_image`; `make_release.py` refuses it; the release rootfs is checked for `hscl-qa`.
- Overlay cache serves a stale pristine rootfs -> cache key = base ISO sha256; mismatch rebuilds.
- Evidence deleted by cleanup -> cleanup keeps PNG/JSON/logs and only removes disks and superseded ISOs.
