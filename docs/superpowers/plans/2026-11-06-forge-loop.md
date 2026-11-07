# HSCL1 Forge Loop: patch, debug, rebuild, split, upload (one plan, one control)

Owner request 2026-11-06: simpler control, a perfectly planned loop for patching, update loop, debugging, error finding, fixing, rebuilding, splitting the new ISO, uploading it, and merging it back into the full ISO in the cloud on GitHub (Actions and workflows). Plan first, then work.
This file refines W24 of `2026-11-06-ux-ai-hardware-expansion.md` and the self-healing protocol of `2026-11-06-autonomous-to-stable-hardened.md` (section 2). Where they disagree, this file wins for the build/test/release loop.

## 0. Lessons that shape the design (from r1, r2, r3 and the release)
| Event | Cost | Design consequence |
|---|---|---|
| Rebuilt initrd was never mapped into the ISO, gates green | one 30 min build + one boot | **Prove it from the finished artefact** (extract from the ISO and compare), never from the file we meant to ship |
| Rebuilt initrd lacked `BOOT=casper`, dropped to the initramfs shell | one build + boot | Boot test is mandatory; serial log + failure classifier so the cause is read, not guessed from a screenshot |
| Kubuntu "Try / Install" prompt found only by screenshot, not by path scan | a whole turn | Scan file CONTENT and the running session, not only paths (W24.6) |
| ShellCheck failed in CI twice | two red runs | Run the CI linters locally before pushing (pre-push) |
| Heredoc/escape mangling of scripts by the tool layer | several retries | Write files with the Write tool or from a file; never put backslash escapes inside inline Python |
| `git add -A` after a failing pipe (`pytest | tail`) committed red tests | Commit only after an explicit exit-code check |

## 0a. Status 2026-11-07 (measured)
| Subcommand | State | Evidence |
|---|---|---|
| `check` | DONE | `forge check --strict` green; WSL parity step added 2026-11-06 |
| `build` | DONE (core) | 3 steps + `--dry-run`, 4 tests, `FORGE_WSL` override; **not tried on a real build yet** (needs the WSL lab and >= 9 GB free) |
| `boot` | DONE (core) | runs `qemu_boot_test.py`, summarises `result.json`, exit 1 when not booted; **no real boot run in this session** |
| `diff` | PARTIAL | manifest field diff implemented and run on the two release manifests (0.1.1 -> 0.1.2: version, commit, 4.6 GB -> 5.0 GB, sha256); ISO-content diff (unmkinitramfs / unsquashfs / package lists) still open |
| `test`, `install`, `cycle`, `release` | PLANNED | not in `--help` |

## 1. Single control: `scripts/forge.py` (standard library, no install)
Subcommands (each prints what it will do first, stops on the first failure, writes `artifacts/forge/<run>/summary.json`):
- `forge check` - local pre-push gate: `pytest -n auto`, ShellCheck (WSL), `bash -n`, exec-bit test, secret scan. Seconds to 1 minute.
- `forge build [--full|--layer] [--serial]` - sync WSL clone from the working tree, memory check (>= 9 GB, no qemu), build, inspect artefact offline, copy ISO out, `wsl --shutdown`, hash check.
- `forge boot ISO [--firmware uefi|bios] [--watch]` - boot smoke with serial log, failure classifier, screenshots, live window.
- `forge test ISO` - boot + 27 in-guest checks (`e2e_cli`); `forge install ISO [--luks]` - install into a qcow2 overlay disk, boot it, checks.
- `forge cycle` - check -> build -> boot -> test, one command. Ends with a table: step, result, evidence path.
- `forge release TAG` - section 5. Always draft first; never touches an existing release without `--yes-this-release`.
Rules: never build and VM together; never delete or overwrite an existing release asset; every step logs its exact command; `--dry-run` everywhere.
Optional later: a `justfile` that only calls `forge.py` (a command runner is ergonomics, not logic: https://spin.atomicobject.com/just-task-runner/).

## 2. Patch and update loop (levels, cheapest first)
1. **Edit + unit tests + `forge check`** (seconds). Static facts: file contents, modes, scripts, generated assets (Plymouth frames, QML syntax via `qmllint` where available).
2. **Hot patch into a running live VM** (seconds): Workshop `guest_put_file`, `guest_hook`, `guest_restart_shell`, screenshot. Good for QML, desktop files, theme files, session scripts. Not for initrd or boot.
3. **Delta layer image** (`--layer`, minutes, dev only): only `$ovl/up` squashed into an extra `/casper/*.squashfs`, stacked by casper (https://manpages.ubuntu.com/manpages/kinetic/man7/casper.7.html). Must be proven by a VM test of layer order and whiteouts before any other use. The installer copies one squashfs, so installs from a layered image are not valid test subjects: use full images for install tests.
4. **Full image** (`--full`, ~25 min): the only kind that is released or used for install tests.
Decision rule: a change that touches boot, initrd, kernel cmdline, squashfs ownership, packages' maintainer scripts or the installer always needs level 4 before it is called verified.

## 3. Debug and error finding (so the cause is read, not guessed)
- **Serial log for dev images**: `--serial` adds `console=ttyS0,115200 console=tty0` to the dev GRUB entries; QEMU runs with `-serial file:LOG`; the harness reads it ([approach](https://gitlab.archlinux.org/archlinux/arch-boxes/-/issues/129)). Release images keep the stock command line; their boot test falls back to screenshots.
- **Failure classifier** (`scripts/boot_classify.py`, unit-tested on saved logs): `initramfs-shell` (`(initramfs)`, `Gave up waiting for root`, `BusyBox`), `kernel-panic` (`Kernel panic`, `end Kernel panic`), `casper-no-medium` (`Unable to find a medium containing a live file system`), `emergency-mode`, `sddm-failed`, `plasma-crash`, `hang` (no new serial output and unchanged screen for N s). Each class names the first thing to check. `panic=-1` on dev images so a panic ends the VM instead of hanging.
- **Offline diff against the previous good ISO** (`forge diff A B`): `unmkinitramfs` file lists, `unsquashfs -ll` list, package list; r2's missing `conf/conf.d/default-boot-to-casper.conf` would have shown in seconds.
- **Evidence bundle** per run: commands, serial log, screenshots, in-guest reports, hashes, git commit and dirty flag; large files stay in `artifacts/` (ignored by git), the summary goes into BUILD_LOG.

## 4. Self-healing rules (tightened)
Three tries per failing gate, then stop and write the blocker. A fix must come with a test that fails before it and passes after. Never weaken a gate, never skip a test, never disable a protection. When a gate passes but reality fails (as with the missing `-map`), the bug is in the gate: fix the gate first and add a test for it.

## 5. Release: build locally, verify and merge in the cloud
Local (`forge release TAG`): full image -> boot + e2e + install tests green -> split into parts of 1500 MiB (limit is 2 GiB per asset; one report says an asset of exactly 2 GiB failed with a 500 error, so stay well below: https://github.com/orgs/community/discussions/61733) -> `SHA256SUMS` (parts + whole image) -> manifest + SBOM.
Upload (GitHub CLI): create a **draft** release, upload parts without `--clobber` (an upload failure after `--clobber` deleted the old assets in one report: https://github.com/orgs/community/discussions/165616), download everything back and compare hashes, only then publish. Retry transient failures twice with backoff and a hash check.
Cloud (GitHub Actions, workflow `release.yml`, triggers `release` and `workflow_dispatch`):
1. `verify`: download parts, verify each and the joined image against `SHA256SUMS` (stream, no second copy). Exists, proven on v0.1.1-alpha.0.
2. `bundle` (online merger): join parts into the full ISO as an Actions artifact (90 days). Exists, proven.
3. `attest`: build provenance for the parts and the joined ISO via `actions/attest` (https://github.com/actions/attest-build-provenance), subject = checksum file; keyless `cosign sign-blob` of `SHA256SUMS` as an optional second signature (pattern: https://upd.dev/foundry-rs/foundry/src/branch/master/SECURITY.md). Attestation failure must fail the workflow loudly, not leave a silent unsigned release.
4. `mirror` (to be MEASURED before promising): permanent home for the merged ISO beyond the 90-day artifact, e.g. an OCI artifact on GHCR via ORAS. GHCR layer and storage limits were NOT found in this research; test with a real push of the 5.5 GB file in a draft workflow, record the result in BUILD_LOG, and only then document it.
5. `smoke` (to be MEASURED): boot the merged ISO headless with TCG on the runner (slow, no WHPX/KVM guarantee on hosted runners) to the live desktop, serial log as artifact. If hosted runners cannot do it in time, say so and keep the local boot test as the gate.
Building the full ISO inside Actions is NOT planned for now: a hosted runner has about 14 GB of free disk by default in community reports (not confirmed against current docs), a full build needs far more. Revisit with a larger runner or the free-disk-space approach only if local builds become the bottleneck.

## 6. Immediate work order (after this plan)
1. **Patch the Kubuntu prompt** (blocker, owner-reported): `kubuntu-installer-prompt` is a compiled Qt program started by `/usr/libexec/start-kubuntu-live-env`, selected through the SDDM session `kubuntu-live-environment`. Decision: do not rebrand a binary we cannot rebuild; replace the starter (dpkg-divert in a new package `hscl-live` or in `hscl-branding`) by an HSCL1 starter that skips the prompt and starts Plasma directly (the tail of the stock script), keeps the OEM branch unchanged, and leaves the installer reachable from the desktop icon "Install HSCL1" and the Control Center. A proper HSCL1 welcome (language, network, Try/Install) is a later product item (W23.1). Tests: file contents + divert + verify-image check + serial/boot test.
2. `forge.py` skeleton with `check`, `build`, `boot` (serial + classifier) and unit tests for the classifier on saved logs (r2's initramfs-shell screenshot case and a synthetic panic).
3. Build r4 with fix 1 through `forge cycle`; evidence into BUILD_LOG; then branding scanner (W24.6) and the remaining W21 items.
4. Layer mode (W24.2) only after 2 and 3 work; then hot-patch documentation; then cloud `attest` and measurements for `mirror` and `smoke`.

## 7. Open questions (no guessing)
- GHCR size/storage limits for a 5.5 GB layer: unknown, measure.
- Current hosted runner disk/RAM and artifact limits: check GitHub docs before relying on them.
- casper layer order on the 26.04 ISO (single `filesystem.squashfs` today): measure in a VM.
- Whether `kubuntu-installer-prompt` has any role in the OEM flow beyond the `oem-config` branch: read the stock script first (done: OEM branch calls `calamares-launch-oem` directly).
