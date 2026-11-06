# HSCL1 master plan v3: fast loop, honest evidence, stable hardened v2.0.0 (rewrite of 2026-11-06, revision 3)

> **For the autonomous agent.** This file replaces revision 2 of itself (still in git history) and supersedes
> `2026-11-06-long-horizon-to-v2.md`. The sibling plans stay valid for their scope: `2026-11-06-ux-ai-hardware-expansion.md` (product work W0-W24)
> and `2026-11-06-forge-loop.md` (the control script and release loop in detail). **When two plans disagree, this file wins.**
> A box is ticked only with evidence in `docs/CLAIMS.md` or `docs/BUILD_LOG.md`. Status words: PLANNED, IMPLEMENTED, TESTED, VM-VERIFIED,
> HARDWARE-VERIFIED, EXPERIMENTAL, BLOCKED, UNVERIFIED (a research claim not yet checked against a primary source). Never upgrade without evidence.
> The 30-minute loop ping points here by path: keep the path.

**Goal.** A v2.0.0 ISO that is VM-verified end to end (live, install, LUKS2 install, update), hardened against the documented threat model
with measured evidence, trilingual (EN/DE/FR), reproducibly documented, attested, and published with an honest limitations list - reached by a
development rhythm that is an order of magnitude faster than today without giving up a single gate. Where a gate needs the owner (physical
hardware, trademark review, native-speaker review, key policy, production deployment, repository settings), v2.0.0 states exactly that gap.

---

## 0. Where we are right now (2026-11-06, evening)

| Fact | Evidence |
|---|---|
| Public repo `timfromhcs/HSCL1`, GPL-3.0-or-later, `main` at the merge of PR #20 (version 0.1.2-alpha.0), CI green | `gh run list` |
| Published prereleases: `v0.1.0-alpha.0` (notes now carry a warning about two security defects), `v0.1.1-alpha.0` (4 parts of 1500 MiB, SHA256SUMS, manifest, SBOM of the Rust CLI); workflow "Verify release assets": split verify and **Bundle one-file ISO** both green | release page, run 42222161027 |
| Release candidate `0.1.2-alpha.0` (full xz build from clean clone at `d20f557`, sha256 `56e4cafb...9d3d`, 5 026 480 128 B): 3 x 27/27 live checks, fresh LUKS2 install, installed boot to desktop in 188 s, `/` = `0:0 755`, no keyfile, secret scan clean, installer fully HSCL1 | `artifacts/e2e-rel2-run*`, `artifacts/luks-rel2`, `artifacts/luks-boot-rel2` |
| **That candidate is NOT released.** Content scan found visible upstream leftovers (installer donate link to kubuntu.org, "Kubuntu Website" and "Kubuntu Focus" menu entries, wrong SDDM description, live user/host named `kubuntu`, Plymouth message overlapping the logo). Fixed in commit `e6ee0d4` (+ gates, + tests) | `docs/BUILD_LOG.md` |
| Dev image `r5` failed to boot ("cow format specified as overlay and no support found"): setting `FLAVOUR` in `/etc/casper.conf` was the cause (same image with the r4 initrd booted in 90 s; initrd trees differ only in `casper.conf`, `os-release`, Plymouth descriptor, font caches). Fixed in `35ba640`: live user/host now come from `/.disk/info` on the medium. Dev image `r6` VM-VERIFIED: desktop after 90 s without a click, 28/28 checks incl. `live_identity` (user and host `hscl1`), `/` `0:0 755` | `artifacts/boot-r5`, `artifacts/boot-r5b`, `artifacts/boot-r6`, `artifacts/e2e-r6` |
| Rebrand boot tests r1-r4 found and fixed four real defects the gates had not seen (missing initrd `-map`, missing `BOOT=casper`, blocking upstream Try/Install prompt, ShellCheck findings) | BUILD_LOG "Rebrand round" |
| Live view of VM runs (`watch.py` + Tk viewer) implemented, frames written during real runs; screenshot of the window itself not captured | `artifacts/e2e-r1/vm/*/live.png` |
| Not done at all: Secure Boot state in the guest, Security Lab runtime, Privacy features, AI on a real GPU, website deployment, SBOM of the ISO package list, reproducibility, attestation, maintainer signature, any physical hardware | CLAIMS.md |

**Next three actions (in this order):** (1) PR the branch (green CI) and merge; (2) full release build of the fixed commit and all
release gates on that exact artefact; (3) publish 0.1.2-alpha.0 through the draft flow of section 7 and run the cloud merge.

---

## 1. Operating principles (distilled from what went wrong today)

1. **Prove it from the finished artefact.** A gate that inspects the file we meant to ship is worthless when the shipped file differs (the
   rebuilt initrd was never mapped into the ISO while every gate was green). Extract from the ISO / installed disk and compare.
2. **A boot is a gate.** No claim about an image without booting that exact image; boot failures are classified from a serial log, not guessed
   from a screenshot.
3. **Look at content, not only paths.** The Kubuntu prompt and the donate link were found by screenshots and config text, not by path scans.
4. **Run the cheapest discriminating experiment first** (unit test < hot patch in a live VM < layer image < full dev image < release build).
5. **Never idle during a build.** While WSL builds, research, write docs, tests and plans (host-only work). While a VM runs, do not build.
   (The user asked for this explicitly: "let the other run in the background".)
6. **Commit only after an explicit exit-code check.** `pytest | tail` hides failures (a red test was committed once).
7. **Write files with the file tool or from a script file.** The tool layer re-interprets backslash escapes inside inline code (PNG header, regex, printf); use `chr(92)`, files, or the Write tool.
8. **One truth per number.** Versions, hashes and sizes are written by scripts into manifests; prose copies them, never the other way round.
9. **Honest limits are part of the product.** Every release note lists what was not verified.

### 1.1 Self-healing loop (unchanged protocol, tightened)
```
OBSERVE   run the gate; save stdout, exit code, timestamp, artefact paths under artifacts/<task>/
CLASSIFY  code | test | harness | environment/capacity | upstream | flaky | missing feature | GATE BUG (gate green, reality red)
HYPOTHESIS falsifiable sentence + what would disprove it
EXPERIMENT cheapest discriminating experiment (principle 4)
FIX       smallest patch at the root cause + a test that fails without it (mutation check)
VERIFY    targeted -> subsystem -> full suite -> the real artefact (VM) when the claim is about the image
RECORD    CLAIMS.md, BUILD_LOG.md, commit (after exit-code check), push, PR, merge on green CI
```
At most **3 attempts per distinct failure**, then BLOCKED with evidence. Never weaken a test, skip a gate, lower a threshold, disable AppArmor,
firewall, Secure Boot, encryption or sandboxing for a pass. A flaky result is repeated 3 times before it is called flaky. A GATE BUG is fixed
before the product bug it hid, and gets a test of its own.

### 1.2 Stop-and-ask list (needs the owner, never guess)
signing-key policy; production deployment of the website; physical-hardware tests; trademark review; native-speaker translation review;
anything that writes to a physical disk; changing repository visibility **or repository settings (e.g. immutable releases, branch rules)**;
replacing network defaults of the base system (NTP, mirrors, update checks).

### 1.3 Resource policy
- Host: 19.8 GB RAM, Ryzen 7 7735HS (8C/16T), `E:` has been the scarce resource (49-64 GB free at times). `.wslconfig`: memory 6-8 GB cap.
- **Never** an image build and a VM at the same time. Order: build in WSL -> copy ISO out -> `wsl --shutdown` -> VM tests.
- Build from the **WSL-local clone** `~/hscl1-src` (ext4 inside the VHDX), never from `/mnt/e` (9p overhead, 0777 modes).
- Before a heavy step: host free memory >= 9 GB, no `qemu`/`vmmem` left over, disk >= 25 GB free on `E:`. After: `wsl --shutdown`.
- Delete only my own disposable artefacts (dev ISOs of older runs) when space is short; never user data, never releases.
- If the host reaps a job, do not restart blindly: record, shrink the job, or ask.

---

## 2. Research digest (sources; UNVERIFIED marks what must be checked before relying on it)

### 2.1 Carried over from revision 2 (still valid; details live in the cited sources)
R1 virtio-serial hang (QEMU issue 4672, persistent host connection: done) | R2 LUKS2 on Kubuntu 26.04: signed GRUB cannot open LUKS2/Argon2id, so
unencrypted `/boot` + one LUKS2 root, no encrypted swap volume | R3 reproducible images (SOURCE_DATE_EPOCH, xorriso, squashfs clamp) | R4 keyless
attestation via `actions/attest` | R5 Secure Boot state must be cross-checked in three places | R6 systemd sandboxing measured with
`systemd-analyze security` | R7 AppArmor for a Python daemon needs a named profile and an attachment check | R8/R13 rootless Podman defaults and the
two-phase Kali container | R9 Tor Browser signature check | R10 axe/pa11y + Lighthouse | R11 no authoritative Ubuntu 26.04 hardening baseline: measure
the booted image | R12 Calamares layout keys (`noEncrypt`, `luksGeneration`) | R14 `actions/attest` inputs | R15 llama.cpp Vulkan device check | R16 WHPX
`ssd=off` trade-off, no SMM so Secure Boot on TCG | R17 CI mirror stalls (download-only loop, done).

### 2.2 New in revision 3
| # | Finding | Source | Consequence |
|---|---|---|---|
| R18 | QEMU can boot a kernel directly (`-kernel`, `-initrd`, `-append`, `-nographic` sends the serial console to stdout). Extracting kernel+initrd from the ISO's casper directory and booting with `boot=casper` would skip UEFI+GRUB (about 40-45 s of our ~100 s to desktop). **UNVERIFIED** that casper finds the medium when the ISO is attached as a CD in this mode | QEMU linuxboot docs (https://github.com/qemu/qemu/blob/v8.2.1/docs/system/linuxboot.rst), forum answers | Experiment F2.1: measure; use only as a fast smoke tier, never as the boot gate (GRUB/UEFI path stays gate S1) |
| R19 | Whether GitHub-hosted `ubuntu-24.04` runners expose `/dev/kvm`: sources disagree (a user issue says yes for 2-vCPU Linux runners; an older article and a maintainer comment say nested virtualization is not supported) | https://github.com/jonaswre/boxlite-quick/issues/4 , https://actuated.com/blog/kvm-in-github-actions | Do not assume. Probe workflow `test -c /dev/kvm; ls -l /dev/kvm` (C5). Cloud boot tests only with measured KVM, otherwise TCG as a slow smoke or not at all |
| R20 | squashfs-zstd trade-off (2017 benchmark on an Ubuntu desktop tree, 128 KiB blocks, 2 cores): zstd level 1 ratio about 2.7 at about 96 MB/s, level 15 about 3.1 at about 11 MB/s, level 16 with 256 KiB blocks about 3.2 at about 8 MB/s. Flags `-Xcompression-level`, `-b 1M`, `-processors` and tmpfs effects were **not** covered | https://lore.kernel.org/patchwork/patch/819672/ | Dev images: zstd low level (already `zstd-fast`). Release: measure xz vs zstd 15-19 on our tree (size, build time, boot time) before changing; no guess |
| R21 | WSL `.wslconfig`: `autoMemoryReclaim` (experimental, `gradual`/`drop`, requires cgroups v1 off), `sparseVhd=true` (only new VHDs; existing ones need `Optimize-VHD`), fixed `memory` cap; keep project files on the Linux filesystem. The 9p-vs-ext4 speed numbers were **not** found | Microsoft WSL release notes (via https://www.elevenforum.com/t/windows-subsystem-for-linux-wsl-2-0-0-september-2023-update-released.18072/) | Keep builds on ext4 (already). Measure `drop` reclaim vs our `wsl --shutdown` habit; try sparse VHD for the build distro (owner's disk, low risk, reversible) |
| R22 | openQA identifies screen states with "needles" (PNG + JSON areas, OCR through Tesseract); an OCR-only needle feature was requested but not available | https://progress.opensuse.org/projects/openqa-improvement/wiki/T03_Remove_the_MD5_approach_and_create_a_new_API_semantic | Add a small OCR gate: Tesseract over our boot/installer/desktop screenshots, fail on banned strings (`Kubuntu`, `Ubuntu` outside an allow-list) - the check that would have found the Try/Install prompt and the donate link in minutes |
| R23 | GitHub **immutable releases** (GA 2025-10-28): when enabled in repo/org settings, new releases lock assets and protect tags, and an attestation is created automatically; recommended flow = draft, attach all assets, publish; tags of immutable releases cannot be reused even after repo deletion | https://github.blog/changelog/2025-10-28-immutable-releases-are-now-generally-available/ , https://docs.github.com/en/code-security/concepts/supply-chain-security/immutable-releases | Our release flow is already draft-first. Enabling it is an **owner decision** (repo setting); recommend it, because a wrong asset would otherwise be fixable only by a new tag |
| R24 | Ubuntu 26.04: `sudo-rs` is the default sudo (GNU sudo remains as fallback), `uutils` Rust coreutils replace GNU coreutils by default (GNU remains available), GNOME 50 is Wayland-only; Kubuntu ships Plasma 6.6 with a Wayland session by default, X11 session package unmaintained by the Kubuntu team (sources differ on KDE X11 status) | https://debugpoint.com/ubuntu-26-04-lts , https://linuxconfig.org/ubuntu-26-04-release-date-and-new-features-in-resolute-raccoon | Our hooks run bash with coreutils flags: record `coreutils --version` and `sudo --version` in the baseline; run the 27 checks once with GNU coreutils selected to catch flag drift; document sudo-rs in the threat model |
| R25 | Reproducible ISOs: xorriso honours SOURCE_DATE_EPOCH for metadata (`--modification-date`, `--set_all_file_dates` default); payload timestamps must be normalised first; Tails patched mksquashfs for the same purpose. `mksquashfs -mkfs-time/-all-time` behaviour **UNVERIFIED** | https://reproducible-builds.org/docs/system-images/ , https://lists.reproducible-builds.org/pipermail/rb-general/2017-October/000656.html | P8: read `man mksquashfs` of our version first; compare at three levels; no "reproducible" word without matching ISO hashes |
| R26 | Compliance/hardening tooling: OpenSCAP + ComplianceAsCode have Ubuntu 24.04 CIS workstation/server profiles, but `ssg-base` on 24.04 does not ship the datastream XML (needs the upstream release zip); `oscap xccdf eval` produces results usable in a gate; **offline rootfs scan UNVERIFIED** (documented path is containers). Lynis audits a live host, reports `hardening_index` in `/var/log/lynis-report.dat`; third-party blogs put a fresh Ubuntu at 50s-60s (anecdotal). kernel-hardening-checker and `systemd-analyze security` were not covered by the search | https://sources.debian.org/src/scap-security-guide/0.1.78-1/docs/workshop/lab2_openscap.adoc , https://richard-sebos.github.io/sebostechnology/posts/OpenSCAP , https://oneuptime.com/blog/post/2026-03-02-verify-security-hardening-lynis-ubuntu/view | Run Lynis and OpenSCAP **inside a booted VM** (live host, no offline tricks), store the index/score as evidence, fail on regression only after a baseline exists; read kernel-hardening-checker's README before use |
| R27 | SBOM + vulnerabilities: `syft dir:<rootfs>` then `grype sbom:<file>` (or `trivy sbom`) with `--fail-on` severity gating; reading squashfs/ISO directly **UNVERIFIED** | https://github.com/anchore/grype , https://lucaberton.com/blog/trivy-vs-grype-2026/ | Extract the finished squashfs with `unsquashfs`, scan the directory; keep ignore rules in a reviewed file; SBOM of the ISO package list attached to the release (P9.1) |
| R28 | Secure Boot/TPM test automation: QEMU + OVMF (Secure Boot variants) + swtpm; `aegis-hwsim` is a reference harness (signed Ubuntu chain scenario skipped in its own CI); UEFI menu automation is fragile (LAVA) | https://docs.rs/crate/aegis-hwsim/latest/source/README.md | P2.7 on TCG with the Microsoft-keys OVMF variant; no menu driving, read state in the guest; swtpm only if TPM is ever claimed |
| R29 | Calamares has no documented unattended/headless mode or module-skip-by-name; `calamares -d` is the debug mode; `prompt-install` is in `settings.conf` | https://sources.debian.org/src/calamares/3.4.2-1/settings.conf | Keep screenshot-driven installer tests, but **do not reinstall for every boot test**: install once per build, then boot qcow2 overlays of the installed disk (F4) |
| R30 | casper disabled the unattended-upgrades security origin in live sessions (2016 fix) because it can fill the live environment | https://bugs.launchpad.net/bugs/1619188 | Check that our remastered live root still has it disabled; installed systems keep their updates (P2.8) |
| R31 | QEMU WHPX snapshots: a 2022 patch added savevm/loadvm (XSAVE state saved as-is, migration blockers for some CPU features, multi-vCPU restore caveat); current status **UNVERIFIED**; internal `savevm` needs the disk holding RAM state attached on restore | https://lore.kernel.org/all/002301d8672f$b65a88a0$230f99e0$@sysprogs.com/T/ , https://qemu.googlesource.com/qemu/+/2d22b18f77ab0a488762e9216575b8582f1adb7d%5E%21/savevm.c | Experiment only (F2.4): snapshot a booted live desktop and measure restore time; if it works reliably it replaces the 100 s boot in most tests, otherwise forget it |
| R32 | Task runners: `just` (recipes, parameters, `--list`), Taskfile (YAML, watch), Make (file dependencies). Command runners are ergonomics, not logic | https://spin.atomicobject.com/just-task-runner/ | Logic stays in `scripts/forge.py` (stdlib); an optional `justfile` only forwards to it |
| R33 | README terminal demos: charmbracelet VHS (tape files render GIFs, reproducible, needs ttyd+ffmpeg), asciinema + `agg` (GIF under about 5 MB for GitHub) | VHS and asciinema pages (search results) | CLI demos for `hscl`/`forge` as tape files checked into `docs/demos/`; real OS screenshots stay harness-generated |
| R34 | CI speed: `Swatinem/rust-cache` caches `~/.cargo` and `target`, 10 GB repo cache limit with eviction (from forks' READMEs, upstream wording **UNVERIFIED**); `concurrency: cancel-in-progress` and `pytest-xdist` not covered | https://github.com/Swatinem/rust-cache | Add rust-cache and `concurrency` to CI, `pytest -n auto` locally; verify upstream docs when editing the workflow |
| R35 | Large release assets: 2 GiB limit per asset (one report of a 500 error at exactly 2 GiB), `--clobber` can delete old assets before a failed upload, per-release asset count limit **UNVERIFIED** (1 000 reported) | https://github.com/orgs/community/discussions/61733 , https://github.com/orgs/community/discussions/165616 | Parts of 1500 MiB (already), draft first, no `--clobber`, download back and compare hashes before publishing |
| R36 | GHCR (OCI artifact via ORAS) limits for a 5.5 GB blob were **not found** | search result gap | Measure with a real push in a throwaway workflow before documenting it as a mirror |
| R37 | Serial console capture: `console=ttyS0` plus a file-backed serial device catches early boot output; `panic=-1` ends a panicking VM; kernel-panic grep is general practice, not sourced | https://gitlab.archlinux.org/archlinux/arch-boxes/-/issues/129 | F3: serial log + classifier on dev images |
| R38 | `kubuntu-installer-prompt` is a small package (rebrand of the Lubuntu prompt): shows Try/Install after boot, launches Calamares or Plasma | https://code.launchpad.net/ubuntu/noble/+package/kubuntu-installer-prompt | Done: replaced by an HSCL1 starter; own prompt with language/network is W23.1 |

---

## 3. Speed architecture (the core of this revision)

### 3.1 Where the time goes today (measured this session, one machine)
| Step | Time | Notes |
|---|---|---|
| Dev image build (`--fast`, zstd) | about 25-30 min | squashfs of 16 GB rootfs on 3 processors and 512 MB buffers; plus ISO check hash of the 6 GB base |
| Release image build (xz) | about 45-60 min | measured once (0.1.2-alpha.0) |
| ISO copy WSL -> E: and hash | 3-6 min | 5.5 GB over 9p |
| Boot to desktop (UEFI, WHPX) | 100-150 s | GRUB timeout and UEFI included |
| 27 in-guest checks | about 60 s after desktop | |
| LUKS2 install | about 16-20 min | the biggest single test |
| Installed boot to login | about 190 s | |
| CI | about 3-4 min | 5 jobs |

### 3.2 Ladders (cheapest first). A change goes only as far up as its risk requires.
**Build ladder**
| Tier | What | Target time | Allowed for |
|---|---|---|---|
| T0 | unit tests, `bash -n`, ShellCheck, exec-bit, QML syntax | seconds | everything |
| T1 | `forge check` (pytest -n auto, ShellCheck in WSL, secret scan) | < 1 min | every commit (pre-push) |
| T2 | hot patch into a running live VM (Workshop put_file/hook/restart_shell, screenshot) | seconds | QML, desktop files, theme, session scripts |
| T3 | **delta layer image** (`--layer`): squash only `$ovl/up` into an extra `/casper/*.squashfs` stacked by casper (https://manpages.ubuntu.com/manpages/kinetic/man7/casper.7.html) | 2-5 min (to be measured) | branding, configs, packages without boot impact; **dev only** (installer copies one squashfs) |
| T4 | full dev image (`--fast`) | 25-30 min | anything touching boot, initrd, packages' maintainer scripts, installer, ownership |
| T5 | release image (xz or measured alternative) from a clean clone of `main` | 45-60 min | releases only |
Rule: boot/initrd/cmdline/ownership/maintainer-script/installer changes always need T4 before they are called verified; T3 results are never quoted as release evidence.

**Test ladder**
| Tier | What | Target time |
|---|---|---|
| S0 | direct kernel boot with serial log (R18), headless, no UEFI/GRUB | about 40-60 s (to be measured) - smoke only |
| S1 | UEFI boot to desktop with screenshots, no click | 100-150 s - **the boot gate** |
| S2 | 27 in-guest checks (`e2e_cli`) | + 60 s |
| S2b | OCR banned-string scan over S1/S2 screenshots (R22) | seconds |
| S3 | LUKS2 install once per T4/T5 build, then **boot qcow2 overlays of the installed disk** for every later check (R29) | 20 min once, then about 4 min per boot |
| S4 | Secure Boot on TCG (slow) | 15+ min, once per release candidate |
| S5 | snapshot/restore experiment (R31) | experiment |

### 3.3 This machine
- Keep every build tree on ext4 in WSL (done). Try `sparseVhd` for the build distro and `autoMemoryReclaim=dropcache`-style reclaim only if measured better than `wsl --shutdown` (R21); both reversible, both after a backup of `.wslconfig` (the existing backup stays).
- Squash resources: the host reaped builds three times at 6 processors / 1 GB; current defaults 3 processors / 512 MB are safe. Measure 4 processors / 768 MB when no browser is open (F1.3); never change without a record.
- Disk: keep `E:` above 25 GB free. Dev ISOs of older runs are deleted after the next one passes; the last release candidate and published parts stay until the release is verified online.
- **Parallel work while a build runs** (principle 5): research, plan edits, docs, host-only tests, offline inspection of the previous ISO with `unsquashfs` (not while a VM runs if memory < 9 GB).

### 3.4 Cloud (GitHub Actions)
| Job | Status | Notes |
|---|---|---|
| `ci` (rust, python/shell, qml, cargo audit, cargo deny) | exists, green | add `concurrency` cancel-in-progress and rust-cache (R34) |
| `verify` split ISO | exists, proven | |
| `bundle` one-file ISO (online merger) | exists, proven (artifact 90 days) | |
| `attest` (provenance of parts + merged ISO via `actions/attest`; optional keyless cosign of SHA256SUMS) | PLANNED | failure must fail the workflow loudly |
| `kvm-probe` (`test -c /dev/kvm`) | PLANNED, tiny | decides whether any cloud boot test is realistic (R19) |
| `smoke` boot of the merged ISO | PLANNED, depends on kvm-probe | else not done and said so |
| `mirror` of the merged ISO to GHCR/ORAS | PLANNED, **measure first** (R36) | only after a real 5.5 GB push works |
| Full ISO build in Actions | NOT planned | runner disk about 14 GB in community reports (not confirmed against current docs); revisit with a larger runner |

### 3.5 Control: `scripts/forge.py` (one command; spec in `2026-11-06-forge-loop.md`)
`forge check | build [--full|--layer] [--serial] | boot ISO | test ISO | install ISO [--luks] | diff A B | cycle | release TAG`. Each prints what it will do,
stops on the first failure, writes `artifacts/forge/<run>/summary.json`, never runs build and VM together, supports `--dry-run` and `--no-watch`.

---

## 4. Phases (IDs kept for traceability with BUILD_LOG/CLAIMS; status as of today)

### P0 - Trustworthy test infrastructure
- [x] P0.1 persistent host RPC (R1) | [x] P0.2 guest write watchdog | [x] P0.3 bounded replies | [x] P0.4 determinism (3 identical runs, repeated on 0.1.1 and 0.1.2 images) | [x] P0.5 sandbox options restored | [x] P0.6 `docs/DEV_LOOP.md` | [x] P0.7 harness typing | [x] P0.9 process-level tests
- [ ] P0.8 guest-terminal diagnostics script (`e2e_term.py`)
- [x] P0.10 live view of VM runs (IMPLEMENTED; window itself not yet captured)
- [x] P0.11 LUKS harness robustness (retype when the unlock field is still visible, short hook names, stdlib PNG reader)

### P1 - Close M1 on the real image / first releases
- [x] P1.1 full in-guest check on the rebuilt image (now 27 checks) | [x] P1.2 file modes inside the VM | [ ] P1.3 `systemd-analyze security` for every HSCL1 unit as evidence
- [x] P1.8 release `v0.1.1-alpha.0` published and cloud-verified (supersedes P1.4); warning added to `v0.1.0-alpha.0` notes
- [ ] P1.5 Aurora wallpaper ribbons | [ ] P1.6 autotune on virtio-gpu | [ ] P1.7 WHPX `ssd=off` benchmark (R16)

### P2 - Installer, encryption, Secure Boot
- [x] P2.0 offline facts | [~] P2.1 Calamares layout (no change needed, notice only)
- [~] P2.2 installer branding: HSCL1 logo/text in English verified; DE/FR and 1366x768 views open; donate link removed in `e6ee0d4` (to verify in r5)
- [ ] P2.3 plain (unencrypted) install | [x] P2.4 LUKS2 install + unlock + wrong passphrase + no keyfile (three times: p2, 0.1.1, 0.1.2 candidate)
- [ ] P2.5 recovery key flow | [ ] P2.6 fault injection | [ ] P2.7 Secure Boot state on TCG (R5, R28) | [ ] P2.8 offline + networked install, first-boot update path | [ ] P2.9 OEM path (optional)
- [ ] P2.10 installed system branding: boot menu entries (`GRUB_DISTRIBUTOR=HSCL1` set), EFI directory name (still upstream; change only after a Secure Boot check), SDDM and Plymouth on the installed system (unlock prompt and logo verified on the candidate)

### P3 - Hardening with measurements (R6, R7, R11, R24, R26)
- [ ] P3.1 baseline of the booted image (`sysctl -a`, `aa-status`, `ss -tulnp`, `lsmod`, `systemd-analyze security`, `ufw status`, **plus** `coreutils --version`, `sudo --version`) | [ ] P3.2 listening-socket allow-list test | [~] P3.3 per-unit sandboxing (baseline unit done, 7.6 -> 2.5) | [ ] P3.4 AppArmor named profiles + attachment check | [ ] P3.5 kernel/userland knobs only when measured | [ ] P3.6 firewall tests from the host through QEMU user-net | [ ] P3.7 polkit/helper audit | [ ] P3.8 fuzz depth for Rust parsers | [ ] P3.9 CI security gates stay on | [ ] P3.10 Dependabot PRs triage (owner-visible)
- [ ] P3.11 **measured hardening report**: Lynis `hardening_index` (booted VM), OpenSCAP CIS workstation profile result (datastream from the upstream release zip), `systemd-analyze security` table, kernel-hardening-checker run (after reading its README), each stored as evidence with the image hash; a score is a baseline for regression, never a marketing number
- [ ] P3.12 casper unattended-upgrades check in the live root (R30)

### P4 - Security Lab MVP (R8, R13)
- [ ] P4.0 podman in the image | [~] P4.1 Kali Podman page read, digest pinned from the API (not pull-verified) | [x] P4.2 container spec generator (`hscl lab`, unit-tested) | [ ] P4.3 VM run of the pinned image | [ ] P4.4 authorization reminder EN/DE/FR | [ ] P4.5 toolset install/remove (basic group) | [ ] P4.6 no Kali repo on the host (test + image check stay)

### P5 - Privacy workflows
- [ ] P5.1 Tor Browser launcher with signature check (R9) | [ ] P5.2 `hscl privacy tor status` | [ ] P5.3 Tails ISO verify/launch | [ ] P5.4 decide the ephemeral Privacy session against AGENTS.md 6.5 | [ ] P5.5 docs

### P6 - Local AI, coding and media tooling
- [ ] P6.1 CPU path on the current image | [ ] P6.2 Vulkan on the owner's Radeon 680M (Windows-host smoke test first) | [ ] P6.3 MTP/TurboQuant only if advertised | [ ] P6.4 HCS Coder against the real tool | [ ] P6.5 media catalogue entries only with licence + sha256 + one real run
- [ ] P6.6 hybrid-model (`qwen35`) KV/recurrent-state support in `hscl ai fit` from measured llama.cpp buffer logs (the first probe produced no output: rerun when no VM/build runs)

### P7 - UI/UX, accessibility, localisation, visual QA
- [ ] P7.1 Control Center pages from `hscl ... --json` | [ ] P7.2 first-run | [ ] P7.3 launcher keyboard test | [ ] P7.4 accessibility | [ ] P7.5 visual QA matrix | [ ] P7.6 translation gate | [ ] P7.7 website (axe/pa11y + Lighthouse, R10)
- [ ] P7.8 OCR banned-string gate over screenshots (R22): Tesseract in WSL, allow-list file reviewed by the owner

### P8 - Reproducibility (R3, R25)
- [ ] P8.1 build twice with `SOURCE_DATE_EPOCH` and compare at three levels | [ ] P8.2 publish the diff verbatim | [ ] P8.3 fix the largest sources (initramfs, caches); the word "reproducible" only with matching ISO hashes; read `man mksquashfs` for time-clamp flags first

### P9 - Release engineering (R4, R14, R23, R35)
- [ ] P9.1 SBOM of the final rootfs (`var/lib/dpkg/status`) + `Cargo.lock` + vulnerability scan (syft/grype, R27) | [ ] P9.2 attestation job (`actions/attest`) + documented `gh attestation verify` | [ ] P9.3 optional maintainer signature (owner key policy) | [~] P9.4 release workflow dry run (verify + merge proven on a real prerelease; attestation not yet) | [ ] P9.5 RC process: freeze, clean-clone build, full VM matrix on the exact artefact | [ ] P9.6 docs match the artefact (every command executed once)
- [ ] P9.7 **owner decision: enable immutable releases** (R23) | [ ] P9.8 draft-first release flow scripted in `forge release` with download-back hash comparison

### P10 - Stable gates (all ticked with evidence, or the gap is written in the release notes)
Unchanged in meaning from AGENTS.md section 20: boots in UEFI and BIOS, Secure Boot state documented, installer works, LUKS2 works, desktop usable,
EN/DE/FR critical strings complete, `hscl doctor` truthful, no Kali repo on the host, lab defaults safe, privacy claims match tests, SBOM +
checksums + signatures or limitations, README/docs match, website built, release assets verified, limitations published. **Not claimed until
done:** physical hardware, trademark review, native-speaker review, maintainer signature.

### P11 - Fast loop (new; details in `2026-11-06-forge-loop.md` and W24)
- [ ] F1 `scripts/forge.py` with `check`, `build`, `boot` (+ unit tests) | [ ] F1.3 squash resource measurement (4 procs / 768 MB when idle) | [ ] F1.4 `.wslconfig`/sparse-VHD experiment with backup
- [ ] F2.1 direct kernel boot smoke (S0, R18) | [ ] F2.2 serial log + failure classifier `scripts/boot_classify.py` (tested on r2's initramfs-shell case and a synthetic panic) | [ ] F2.3 `forge diff A B` (initrd/squashfs/package lists) | [ ] F2.4 snapshot experiment (R31)
- [ ] F3 delta layer image `--layer` (T3) with VM test of layer order and whiteouts | [ ] F4 installed-disk overlays for S3 | [ ] F5 offline inspection `scripts/inspect_iso.py` (extract from the finished ISO; used by gates) | [ ] F6 content scanner `docs/BRAND_INVENTORY.md` (replaces the path-only inventory)
- [ ] F7 pre-push script (`pytest -n auto`, ShellCheck in WSL, bash -n, exec bits) | [ ] F8 CI: concurrency + rust-cache (R34)
- [ ] F9 MCP audit of `scripts/workshop/mcp_server.py` (explicit annotations, `structuredContent`, scope enforced in our layer, no dangerous tool combination)

### P12 - Branding completion (W21, owner request "remove all Kubuntu logos")
- [x] B1 boot splash (HSCL1 theme in live and installed boot) | [x] B2 live session starts Plasma directly (Try/Install prompt replaced) | [x] B3 GRUB menu entries (live) | [x] B4 installer branding, slideshow of the old branding directory removed
- [x] B5 content-scan fixes in `e6ee0d4`: installer donate link, website launchers, SDDM metadata, live user/host `hscl1`, Plymouth overlap (verify in r5: VM) 
- [ ] B6 remaining visible names: Konsole profile names, `kubuntu-manage-software`/driver-manager display names, Plasma look-and-feel entries' preview images, package-owned strings in binaries (OCR/screenshot-driven)
- [ ] B7 own welcome app (language, network, Try/Install, no cloud account) - W23.1 | [ ] B8 base statement in text everywhere (README, About, website): built on Ubuntu 26.04 LTS packages with KDE Plasma, not an official Canonical/Kubuntu product
- [ ] B9 decide the network defaults inherited from the base (NTP `ntp.ubuntu.com`, `geoip.ubuntu.com` mirror lookup, `changelogs.ubuntu.com` release check, kde.org connectivity check): **owner decision**; until then they are disclosed in KNOWN_LIMITATIONS

### P13 - README and command simplification (new)
- [ ] D1 README restructure: 3-command quick start per audience (user: download, verify, boot a VM; developer: `python scripts/forge.py cycle`; reviewer: `forge check`), status table with honest columns (VM-VERIFIED / not verified), screenshots only from harness runs, link map to docs
- [ ] D2 `docs/CLI.md` and `docs/DEV_LOOP.md` regenerated from `--help` output so they cannot drift; a test compares them
- [ ] D3 CLI demos as VHS tape files (`docs/demos/*.tape`), GIFs under about 5 MB (R33), regenerated by one command
- [ ] D4 `docs/RELEASING.md`: the draft -> verify -> publish -> cloud merge flow in one page with the exact commands
- [ ] D5 every documented command executed once as written (P9.6); stale statements removed

### P14 - Later product work (pointers; see the expansion plan)
W1 hardware detect + drivers | W2 AI fit/estimate | W3 GPU/RAM bridges (experimental) | W4 GEMM simulator | W5 shortcuts/KRunner | W6 wallpaper maker | W8 coding tools | W15-W19 HCS shell, image/video viewers, office, pentest API/MCP, desktop MCP | W20 hardening reports. Each gets an entry here only when it is scheduled, with its own gate.

### P15 - Freeze, dev mode, bake (detail: `2026-11-06-freeze-devmode-memory-tiering.md`)
- [ ] E1 `systemd-sysext` on our image (merge/unmerge, `extension-release` match, effect on dpkg) | [ ] E2 live upperdir anatomy after a normal session | [ ] E3 freeze-plan prototype with exclusion mutation test (planted fake secret must make the export refuse)
- [ ] D1 `hscl dev` status + `freeze plan` (read-only) | [ ] D2 freeze export as a reviewable repository patch (allow-list, hard exclusions, root:root, manifest) | [ ] D3 `qa_image`-only private image path stays out of releases

### P16 - Memory tiering, speed test, KV cache (detail: same file, section 3)
- [ ] T-core pure functions in Rust (roofline ceiling, fit cross-check, KV type choice) with synthetic-hardware tests | [ ] T-bench bounded RAM and SSD speed tests, labelled when the page cache affects them | [ ] T-flags only flags the pinned llama.cpp lists in `--help`
- [ ] T-kv quality gate (perplexity/KLD f16 vs candidate) before any compressed KV type is recommended; default f16, q8_0 only when the context would not fit, q4_x opt-in | [ ] T-ttm advise-only TTM/GTT snippet, applied only through the narrow helper after confirmation, with cap and revert
- [ ] T-owner Windows-host Vulkan smoke test on the Radeon 680M; Linux-on-metal GTT test (owner boots the image) - **no claim before these**

### P17 - Safe RSI guard (detail: same file, section 4)
- [ ] S-protected `scripts/protected_paths.json` + `scripts/protected_paths.py` + test + CI step: a branch must not change the files that judge it without a human-review label | [ ] S-archive variant archive file (branch, parent, results) | [ ] S-sandbox candidates run in disposable VMs without secrets

---

## 5. Hardening, verification and testing improvements (cross-cutting, new)
1. **Content-aware gates**: OCR screenshot gate (P7.8), content scanner (F6), artefact-extraction gates (F5).
2. **Boot gates with causes**: serial log classifier (F2.2), diff against the last good ISO (F2.3).
3. **Measured hardening, not claimed**: P3.11 (Lynis, OpenSCAP, systemd, kernel checker) run in a booted VM; scores stored with the image hash; regression gates only after a baseline.
4. **Supply chain**: SBOM + grype gate (P9.1), attestation (P9.2), immutable releases (P9.7), SHA-pinned actions (Dependabot PRs triaged), download-back hash comparison in the release script (P9.8).
5. **Test depth**: mutation check for every new gate (the gate must fail on a broken input), fuzz for parsers (P3.8), process-level tests for every entry point (P0.9), a hook-name/daemon-rule test (done), CRLF/Windows pitfalls covered by byte-level test inputs.
6. **Windows-host hygiene**: tests that call `bash` must pass script text as bytes on stdin (Git-bash vs WSL launcher, CRLF) - pattern already in `test_live_starter.py`.
7. **Security of the dev tooling itself**: Workshop daemon stays inert by default in release images (gate), MCP tools annotated and scoped (F9), test passphrases are markers, the live view never shows secrets typed by the harness.

---

## 6. Open questions register (how each gets answered; owner items marked)
| # | Question | How to answer | Owner? |
|---|---|---|---|
| Q1 | Does casper find the medium with direct kernel boot (S0)? | F2.1 experiment on the exact ISO | no |
| Q2 | Does a GitHub-hosted runner expose KVM? | `kvm-probe` workflow | no |
| Q3 | Layer order and whiteouts in casper for `--layer` on the 26.04 ISO | F3 VM test | no |
| Q4 | GHCR limits for a 5.5 GB blob | throwaway ORAS push in a workflow | no |
| Q5 | xz vs zstd for the release squashfs (size, build time, boot time) | measure on our tree | no |
| Q6 | Which mksquashfs flags clamp timestamps in our squashfs-tools version | `man mksquashfs`, then P8.1 | no |
| Q7 | Does an offline-rootfs OpenSCAP scan work, or must it run in a VM | try; fall back to the VM (planned) | no |
| Q8 | Do the 27 checks pass with GNU coreutils selected instead of uutils | one run with `update-alternatives` | no |
| Q9 | Does the live user `hscl1` (casper `FLAVOUR` set) work in every flow (autologin, installer, our autostarts) | r5 VM run | no |
| Q10 | Is WHPX snapshot restore reliable enough to replace boots | F2.4 experiment | no |
| Q11 | Enable immutable releases on the repository? | recommend; **owner decides** | **yes** |
| Q12 | Replace inherited network defaults (NTP, GeoIP mirror, release check, connectivity check)? | present options with consequences | **yes** |
| Q13 | Maintainer signing key policy | present options | **yes** |
| Q14 | Dependabot major bumps (#1 checkout 7.x, #3 sha2, #4 thiserror, #2 upload-artifact) | triage with CI evidence; merging majors needs a go | **yes** |
| Q15 | Trademark review of the derivative naming | owner/legal | **yes** |
| Q16 | Native-speaker review DE/FR | owner | **yes** |
| Q17 | Physical-hardware tests, NVIDIA/Venus | owner machines | **yes** |
| Q18 | Is `systemd-sysext` usable as the dev-mode layer on this image (D1/D3 of the freeze plan) | E1 | no |
| Q19 | `ttm.` vs `amdttm.` prefix, default GTT share and the effect on the Radeon 680M under Linux | owner boots the image on the machine | **yes** |
| Q20 | Real NVMe streaming tokens/s for our model sizes | bounded speed test + one real run | no |
| Q21 | Perplexity/KLD tool in the pinned llama.cpp build and an acceptable quality threshold for compressed KV | pinned `--help`, calibrate on the 2B model | no |
| Q22 | Complete protected-path list for the RSI guard | review with the owner once | **yes** |

---

## 7. Release procedure (target form; implemented step by step in `forge release`)
1. Version bump PR -> green CI -> merge. 2. Clean clone of `main`, full release build, `git_dirty` must be false, manifest + hash.
3. Gates on that exact artefact: S1 boot without a click, S2 three runs x 27 checks, S2b OCR scan, S3 LUKS2 install + unlock + wrong passphrase + installed boot, secret scan.
4. Split into 1500 MiB parts, `SHA256SUMS` (parts + whole), manifest, SBOMs. 5. **Draft** release, upload without `--clobber`, download back and compare every hash.
6. Publish (immutable if enabled). 7. Workflow: verify, bundle (merged one-file ISO), attest. 8. Check the artefact size/hash, update `website/data/release.json`, notes with verified/not-verified lists.
9. BUILD_LOG + CLAIMS in the same PR as the metadata. Anything unverified is written in the notes, never implied.

## 8. Risk register
| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| Gate green but artefact wrong (happened) | medium | high | principle 1, F5, mutation checks |
| Host reaps a build/VM (happened 3x) | medium | medium | resource policy, small defaults, one heavy job at a time |
| `E:` fills up (happened) | medium | high | 25 GB floor, delete own old dev ISOs, check before copy |
| Live user rename breaks a flow (Q9) | medium | medium | r5 VM run before any release |
| Layer images mislead (T3 evidence quoted as release evidence) | low | high | dev-only rule, gate on `qa_image`/`layer` flags in the manifest |
| Trademark/IP issues of the derivative | unknown | high | Q15, keep text-only base statement, no upstream logos (gated) |
| Over-claiming hardening | medium | high | measured only, scores as baselines, limits listed |
| Tool-layer escape mangling of scripts | high | low | principle 7 |

## 9. Backlog (found, not scheduled)
GRUB theme for the live ISO menu; BIOS boot test of the new images; second language for the live welcome; `hscl doctor` extension for the new checks; handbook chapters for the new modes; website refresh with the 0.1.2 screenshots; HSCL1 Welcome Center page review (is `01-HSCL1.qml` shown as a later page?); icons for `kubuntu-*` named apps; check that `plasma-welcome` pages mention only HSCL1/KDE.

## 10. Tracking
Every working session ends with: BUILD_LOG entry (what ran, hashes, results, dead ends), CLAIMS rows updated, plan boxes ticked with evidence links, commit + push, PR merged on green CI, a short German summary to the owner.
