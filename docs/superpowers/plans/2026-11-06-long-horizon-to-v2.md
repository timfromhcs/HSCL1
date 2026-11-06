# HSCL1 long-horizon plan: 0.1.0-alpha.0 to v2.0.0 stable (hardened)

> **For agentic workers:** use superpowers:executing-plans (native) or subagent-driven-development. Steps are checkboxes. This
> plan supersedes the ordering in the earlier plans in this folder; their detailed designs (AI, wallpaper studio, Workshop,
> prebuilt image) stay valid and are referenced, not repeated.

**Goal:** a v2.0.0 stable ISO that is VM-verified end to end, hardened to the documented threat model, visually QA'd, trilingual,
signed, reproducibly documented, and published with an honest limitations list.

**Architecture:** unchanged (remastered Kubuntu 26.04 + HSCL1 packages; Rust CLI; Qt6 Control Center; inert-by-default Workshop).
All work lands through the **Workshop loop**: push changed files into a running VM via the API, test, then respin to a new ISO;
full `remaster-iso.sh` rebuilds only at milestone cuts.

**Spec:** `AGENTS.md` (product contract), `docs/CLAIMS.md` (evidence rules), `docs/DECISIONS.md`.

## Global constraints

- **No claim without evidence.** Every status change is written to `docs/CLAIMS.md` with a pointer to the artefact, using the
  vocabulary PLANNED / IMPLEMENTED / TESTED / VM-VERIFIED / HARDWARE-VERIFIED / EXPERIMENTAL / BLOCKED.
- No force-push, no history rewriting on the remote; interim pushes go to `codex/hscl1-v1`; `main` only through a reviewed merge.
- No secrets, ISOs, VM disks or model weights in Git. ISO parts < 2 GiB, joined/verified by `scripts/release-join.sh`.
- Destructive installer tests only on disposable virtual disks.
- Workshop stays **disabled by default** in every release image (`workshop_default: disabled` in the manifest, checked by `verify-image.sh`).
- Kali tooling only in rootless containers/VMs; no Kali or Debian repositories on the host; no Tails-equivalence or anonymity claim.
- Status of this document's items is tracked by checkboxes; unchecked means not done.

## Review focus (failure modes the tests must pin)

1. A respin/update that silently drops HSCL1 branding or re-enables the Workshop -> `verify-image.sh` fails the build (test exists; extend per phase).
2. Low RAM (<= 4 GB) with animation + AI + installer running -> no OOM freeze; animation degrades first (memory-pressure test, M4).
3. Software-rendered GPU (QEMU VGA, old iGPU) -> minimal graphics profile chosen automatically, UI still usable at 1366x768.
4. Long German/French strings in installer, Control Center and notifications -> no clipping (visual QA matrix, M5).
5. Interrupted or tampered release download (missing part, flipped byte) -> `release-join.sh` refuses and leaves no partial image (tests exist; keep in CI).

## Research basis for UI/UX decisions

These are the sources the design rules below rest on; they are cited so they can be re-checked, not as proof the result is good.

- KDE Human Interface Guidelines (<https://develop.kde.org/hig/>): consistency with Plasma conventions, discoverability, keyboard access.
- WCAG 2.2 (<https://www.w3.org/TR/WCAG22/>): AA targets we adopt: 1.4.3 contrast (4.5:1 text), 1.4.11 non-text contrast (3:1), 2.4.7 focus visible,
  2.4.11 focus not obscured (minimum), 2.5.7 dragging alternative, 2.5.8 target size (minimum 24x24 CSS px), 2.3.3-style reduced motion respected
  (AAA, adopted anyway for the animated wallpapers). 2.4.13 focus appearance is AAA and is a stretch goal, not a gate.
- Own design decisions (not externally proven; validated only by our visual QA): contextual hints in place of a one-time tour, a
  command palette that closes on Esc and returns focus, animation as the first thing degraded under load.

## Release ladder

| Tag | Meaning | Gate |
|---|---|---|
| `v0.1.0-alpha.0` | first public pre-release (this push) | boots in VM; hashes published; limitations listed |
| `v0.2.0-alpha` | Workshop + memory + graphics autotune at login; KDE Connect off | M1-M2 |
| `v0.3.0-beta.1` | AI/coding stack verified with real models; Security Lab MVP | M3-M4 |
| `v0.9.0-rc.1` | feature freeze; hardening and full QA matrix | M5-M7 |
| `v2.0.0` | stable | all gates in "Definition of done" |

Versions use semver pre-release tags; the ISO embeds its version and the manifest records the commit.

## Milestones

### M0 - First public push (now)

- [x] Licence GPL-3.0-or-later, NOTICE, SECURITY, CONTRIBUTING, CODE_OF_CONDUCT, LICENSES, README, CI + release-verify workflows, Dependabot.
- [x] Create public repo `timfromhcs/HSCL1`; create `main` from HEAD; push `main` and `codex/hscl1-v1` (no force). Secret scanning + push protection, private vulnerability reporting enabled.
- [ ] Split ISO (`scripts/release-split.sh`), create pre-release `v0.1.0-alpha.0` with parts, SHA256SUMS, manifest, notes (unsigned, VM-only).
- [ ] CI green on GitHub (`gh run watch`); `Verify release assets` workflow green; fix failures, never weaken checks.
- [ ] Enable on GitHub: private vulnerability reporting, secret scanning + push protection, Dependabot alerts (settings via `gh api`; report what the account permits).

### M1 - Close known defects in the image (via Workshop loop)

- [~] KDE Connect listener (`:1716`) off by default: autostart entry hidden (IMPLEMENTED, unit + verify-image checks); **VM listening-socket check still pending**.
- [~] Autotune at login: XDG autostart running `hscl autotune` (idempotent via fingerprint, honours lock) IMPLEMENTED; **VM test after login pending**.
- [ ] Aurora wallpaper redesign (ribbons); screenshots before/after; CPU cost measured and recorded (`hscl wallpaper` perf note) - or the claim stays "not measured".
- [x] Stale-package-list issue: `hscl system updates --check` now reports `lists_age_days`/`lists_stale` (JSON) and a WARNING "unknown, not 'up to date'" when lists are missing or >= 7 days old (TESTED, unit; VM run pending).
- [ ] Refresh `docs/KNOWN_LIMITATIONS.md` and `CLAIMS.md` from evidence after each fix.

### M2 - Installer, encryption, update path

- [ ] Installer branding (EN/DE/FR) and slideshow; screenshot QA at 1366x768 and 1920x1080.
- [ ] LUKS2 install in a VM: install, reboot, unlock; wrong-passphrase path; recovery-key flow; no secret in logs (grep test).
- [ ] Fault injection: kill the installer mid-copy, full disk, no network; confirm failure is reported and the host disk (virtual) state is sane.
- [ ] Prebuilt/OEM disk image path (see `2026-11-05-prebuilt-image-and-updates.md`) and ISO refresh `--upgrade`; kernel/initrd consistency check.
- [ ] Secure Boot: read the state inside the guest (`mokutil --sb-state`) before writing any claim.

### M3 - AI, coding and media tooling (verified against real models)

- [ ] Vulkan backend on a real GPU host: smoke test that confirms the selected device in the backend log. Until then: "not verified".
- [ ] MTP / TurboQuant: enable only if the pinned backend's `--help` advertises them; record measured speed before/after on the same model, else no speed claim.
- [ ] HCS Coder: run the generated OpenCode config against the real tool; licence gate stays for unconfirmed entries.
- [ ] Media AI catalogue (FLUX 3 klein GGUF, image-to-3D, rigging): licence + sha256 per entry, warning for restrictive licences, one real generation per tool before it is listed as working.
- [ ] Blender and Godot MCP servers: finite typed tools, no arbitrary code exec from the model, run against the real apps in the VM/builder.
- [ ] RSI loop R1-R6 with evidence gates (data capture, filter on successful runs, tiny-net GGUF edit, train, eval vs baseline, rollback); promote a model only if the held-out eval improves; test with at least one real model.
- [ ] Image/VAE storage tool (lossy-latent storage) with a round-trip quality measurement.

### M4 - Memory, performance, Security Lab

- [ ] Memory-pressure test in a 4 GB VM: start AI server + browser-like load + animation; earlyoom/zram behaviour recorded; animation degrades first.
- [ ] `hscl-ai.slice` limits verified with a real model that exceeds the budget (must be refused or killed cleanly, desktop stays responsive).
- [ ] Security Lab MVP: rootless Podman, digest-pinned official Kali image, non-privileged defaults, no host home/sockets; tests inspect the generated container spec; one container run in a VM.
- [ ] Privacy mode: Tor Browser launcher + status only if verified; otherwise it stays PLANNED. No ephemeral-mode claim without the AGENTS.md section 6.5 tests.

### M5 - UI/UX and visual QA

- [ ] First-run: short, skippable, contextual hints (no forced multi-step tour); restartable from Help.
- [ ] Control Center: pages for Graphics, Memory, Wallpaper Studio, AI/Models, Security, Updates; every value read from the real CLI (`--json`).
- [ ] Command palette / launcher behaviour: opens on `Meta+Space`, focus in the field, Esc closes and restores focus; tested with the Workshop key-injection harness.
- [ ] Accessibility: keyboard-only path through installer + Control Center; accessible names on all controls; contrast check script over design tokens (exists: `check-tokens.py`) extended to the QML colours; target size >= 24 px; reduced-motion switch stops all animation.
- [ ] Visual QA matrix: {1366x768, 1920x1080} x {Midnight, Light} x {EN, DE, FR} x {Control Center, launcher, installer, lock screen}; screenshots in `artifacts/` (not Git), curated set in `docs/img`; defects fixed at the token/component, then re-captured.
- [ ] Logos/branding consistency check across boot splash, SDDM, installer, About, website.

### M6 - Hardening and supply chain

- [ ] AppArmor profile for `hscl_workshopd` and the MCP servers; Workshop confined (allow-listed paths already enforced in code).
- [~] systemd hardening of HSCL1 services: baseline option set on all units + test (IMPLEMENTED/TESTED statically; Workshop daemon intentionally without ProtectSystem, see THREAT_MODEL); **`systemd-analyze security` evidence from a booted image still pending**.
- [ ] Listening-socket and open-service audit on the installed system; list in `docs/THREAT_MODEL.md`.
- [x] Fuzz/property tests for the Workshop JSON-RPC parser and path allow-list (seeded, 4000+4000+1500 cases, dependency-free; checked to fail on a deliberately weakened validator); `cargo audit` in CI (added, green on main; `cargo deny` licences/bans/sources job added, green in CI).
- [ ] SBOM (SPDX) generated from the actual image and attached to releases; build manifest includes package versions.
- [ ] Release signing: **user decision required** (create a signing key and publish its fingerprint). Until then releases stay "unsigned" in the notes.
- [ ] CI: pin all actions by SHA (done for checkout; add for any new action), least-privilege `permissions`, Dependabot for cargo/actions.
- [ ] Reproducibility statement: re-run the remaster twice and compare manifests; record exactly what differs (no "reproducible" claim otherwise).

### M7 - Website, handbook, release candidate

- [ ] Handbook update for every new feature (EN/DE/FR) with translation coverage check; link check.
- [~] Static website: plain static generator (`scripts/build_website.py`, no Node needed) with EN/DE/FR home + download pages, real release data, tests, mobile check at 390 px done; **not deployed** (Vercel preview first; `vercel.json` added); more pages (install, VM, security, privacy, changelog) still open. Original item: download page generated from the real release metadata; Vercel preview first, production after tests.
- [ ] Hardware table: stays empty until a physical machine is tested; at least one real-hardware boot report before v2 can claim "works on PCs".
- [ ] RC build from a clean checkout, full test + VM matrix on the exact artefact, hashes recorded in `docs/BUILD_LOG.md`.

### M8 - v2.0.0

- [ ] All "Definition of done" boxes ticked with evidence links.
- [ ] PR `codex/hscl1-v1` -> `main` (merge commit, no force), tag `v2.0.0`, release assets split + verified by the workflow, release notes with limitations.
- [ ] Post-release: download the published assets on a clean machine and verify; update website metadata.

## Definition of done for v2.0.0

1. ISO built from repository scripts; hash/manifest/SBOM published; `Verify release assets` green.
2. Boots in QEMU UEFI and BIOS; Secure Boot state read and documented; at least one physical machine boots (HARDWARE-VERIFIED row in the hardware table) or the stable claim is restricted to "VM-verified".
3. Install (plain and LUKS2) to a virtual disk and boot, repeated on the release artefact; fault-injection cases pass.
4. Visual QA matrix complete; EN/DE/FR coverage of critical strings complete; keyboard-only path verified.
5. `hscl doctor` truthful; all CLI commands in the docs run as written in a VM test.
6. Security gates in M6 done or explicitly accepted in writing with the residual risk; no unresolved critical/high finding in HSCL1-owned code.
7. Every AI/media/RSI feature listed as working has a recorded run with a real model; the rest is marked PLANNED/EXPERIMENTAL.
8. Release signed, or the stable release notes state clearly that it is unsigned.
9. Known limitations and trademark review status published.

## Critical path and parallelism

Critical path: M0 -> M1 -> M2 (installer/LUKS2) -> M5 (QA matrix) -> M6 (hardening) -> M7 (RC) -> M8.
Parallel, low coupling to the path: M3 (AI/media/RSI), M4 (Security Lab, memory), website in M7.
Efficiency rule: one Workshop VM kept running; batch changes, push, test, respin once per batch; full remaster only at tags.

## Risk register

| Risk | Impact | Mitigation |
|---|---|---|
| Builder RAM/disk limits (WSL, 24 GB host) | build failures, frozen host | memory guard, bounded `mksquashfs -mem`, sequential jobs, free caches that are HSCL1-owned only |
| No physical hardware / no KVM | claims limited to VMs | explicit labels; request a hardware tester; keep software-render path first-class |
| Upstream drift (Kubuntu point release, llama.cpp, models) | breaks pins | pins with sha256; re-verify before each release |
| Canonical trademark/IP policy for derivatives | publishing risk | review pending (listed in limitations); drop Ubuntu/Kubuntu from marketing copy if the review requires |
| Model licences and abliterated variants | legal/safety | licence + warning gate per model; never bundled |
| CI differs from local (Windows vs Linux) | false green/red | run suite on Linux in CI; narrow documented skips only |
| Signing key not available | unsigned releases | user decision in M6; unsigned stated everywhere until then |
| Scope creep (AI/media/game stack) | v2 never ships | M3 items ship only when verified; otherwise labelled PLANNED and moved to a post-v2 list |

## Working rules for the autonomous loop

1. Before work: `git status`, current branch, free disk/RAM; free HSCL1-owned caches first if RAM is low.
2. One vertical slice at a time: failing test -> implementation -> targeted test -> subsystem tests -> VM check where relevant -> CLAIMS/BUILD_LOG update -> commit.
3. Max three fix-and-retest iterations per distinct failure, then document the blocker and move on.
4. Push `codex/hscl1-v1` after every milestone (not force); open the `main` PR only at M8.
5. Ask the user only for blocking decisions (signing key, hardware access, trademark review outcome).
