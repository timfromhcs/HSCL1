# HSCL1 autonomous plan: from 0.1.0-alpha to a stable, hardened v2.0.0 (revision 2, 2026-11-06)

> **For the autonomous agent:** this file supersedes `2026-11-06-long-horizon-to-v2.md` (kept for history). Work the phases in order, in
> self-healing loops (section 2). A box is ticked only with evidence recorded in `docs/CLAIMS.md` or `docs/BUILD_LOG.md`.
> Status words: PLANNED, IMPLEMENTED, TESTED, VM-VERIFIED, HARDWARE-VERIFIED, EXPERIMENTAL, BLOCKED. Never upgrade without evidence.

**Goal.** A v2.0.0 ISO that is VM-verified end to end (live, install, LUKS2 install, update), hardened against the documented threat
model with measured evidence, trilingual (EN/DE/FR), reproducibly documented, attested, and published with an honest limitations list.
If a gate needs something only the owner can supply (physical hardware, trademark review, native-speaker review, production
deployment consent), v2.0.0 states exactly that gap instead of claiming it.

---

## 0. Verified baseline (2026-11-06)

| Fact | Evidence |
|---|---|
| Public repo `timfromhcs/HSCL1`, GPL-3.0-or-later, CI green (rust, python/shell, qml, cargo audit, cargo deny) | GitHub Actions on `main` |
| Pre-release `v0.1.0-alpha.0` (4 parts of 1.5 GB, SHA256SUMS, manifest) published; the verify workflow joined and hash-checked it | release verify run |
| That ISO was built from an NTFS checkout: payload files in the image were `rwxrwxrwx` (world-writable) | BUILD_LOG "M1 VM run 2" |
| Image `cd0bf42e...` (commit 9d1a9ec, clean, WSL-local build): KDE Connect listener gone (VM-VERIFIED), autotune at login matches `graphics detect` (VM-VERIFIED), stale apt lists reported as unknown (VM-VERIFIED), package files not group/world-writable (checked at image build) | `artifacts/e2e-m1c`, `remaster-m1d.log` |
| Open defect: the Workshop daemon "stops answering" mid-run. **Root cause now identified from research, fix under test** (section 1, R1) | BUILD_LOG, `scripts/workshop/vm.py`, `tests/unit/test_workshop_vm_rpc.py` |
| Not done: LUKS2, Secure Boot state in the guest, Security Lab, Privacy, AI on a real GPU, website deployment, SBOM wiring, reproducibility, signing/attestation, any physical hardware | CLAIMS.md |

---

## 1. Research findings that change the plan (each has a source and a consequence)

**R1 - virtio-serial hang (explains the Workshop daemon failures).** QEMU issue 4672: a guest write to a virtio-serial port that the
host chardev cannot take in one call throttles the port; if the host side closes meanwhile, the guest write can hang forever and later
clients get stuck too. The QEMU guest-agent notes add: data is queued/throttled whether or not a reader is connected, and neither side can
tell whether the other reconnected. Our harness opened a new TCP connection per call and re-sent the request after every timeout - exactly
that pattern, which also explains "a different check fails in every run" and why the first, lucky run passed. *Consequence:* persistent
host connection, request sent once, never closed after the guest has spoken (implemented, tested with a fake guest incl. mutation check);
guest daemon gets a write watchdog (P0); the systemd sandbox options are NOT the suspect and are restored once the next full VM run passes.
Sources: <https://gitlab.com/qemu-project/qemu/-/work_items/4672>, <https://wiki.qemu.org/Features/GuestAgent>. A fix patch for QEMU
(Sept 2026, patchew) exists upstream but is not in the QEMU 11.1 we run, so the workaround stays.

**R2 - LUKS2 on Kubuntu 26.04 + Calamares.** The signed GRUB EFI binary in Kubuntu 26.04 cannot open LUKS2/Argon2id; an encrypted root
with encrypted `/boot` drops to the GRUB rescue shell (Ubuntu Discourse "Fixing a broken FDE on (K)ubuntu 26.04"). Calamares also fails at
the end when there is more than one LUKS volume, e.g. an encrypted swap (Calamares issue 2517). Replacing the signed GRUB with the unsigned
one defeats Secure Boot. Ubuntu's supported FDE path is the TPM-backed one, still experimental. *Consequence:* our supported layout is
ESP + **unencrypted `/boot`** (ext4) + **one LUKS2 root** (the initramfs unlocks it, GRUB never opens LUKS), swap only as zram or a swap
file inside the encrypted root, never a second LUKS volume. Honest limits to publish: `/boot` and the initrd are not secret and not
integrity-protected by LUKS (the kernel is signed under Secure Boot; the initrd is not). TPM unlock is not offered. Sources:
<https://discourse.ubuntu.com/t/fixing-a-broken-fde-encrypted-boot-on-k-ubuntu-26-04/82326>,
<https://codeberg.org/Calamares/calamares/issues/2517>, GRUB manual `cryptomount` (PBKDF2 only for LUKS2 in older GRUB).

**R3 - Reproducible images.** reproducible-builds.org (System images): set `SOURCE_DATE_EPOCH`; pass it to `xorriso --modification-date`;
`mksquashfs` >= 4.5.1 honours it and clamps timestamps; clamp rootfs mtimes before squashing; initramfs and package-manager caches are the
usual leaks; filesystems must be created in one go. *Consequence:* build twice, compare at three levels (package list, rootfs file
list+hashes, ISO hash) and publish exactly what differs; no "reproducible" claim unless the ISO hashes match. Source:
<https://reproducible-builds.org/docs/system-images/>.

**R4 - Release integrity without a private key.** GitHub artifact attestations (Sigstore, keyless, `actions/attest-build-provenance`,
verified with `gh attestation verify`, needs gh >= 2.49) give signed provenance from CI without the owner creating a key; SBOMs can be
attested with `actions/attest-sbom`. A detached GPG/minisign signature stays optional and is an owner decision. *Consequence:* P9 adds an
attestation job; the notes say "provenance attested by GitHub (keyless)" and still "no maintainer signature" until a key exists. Source:
<https://www.mankier.com/1/gh-attestation-verify>. (Exact action inputs must be checked against the action's README at implementation time.)

**R5 - Secure Boot state must be cross-checked.** `mokutil --sb-state` alone can mislead (Launchpad bugs 1817950, 1776068). Read three
sources in the guest: `mokutil --sb-state`, the `SecureBoot-*` EFI variable under `/sys/firmware/efi/efivars`, and the kernel log line.
Claim only when all agree; also record the firmware (OVMF secboot with Microsoft keys). Source: <https://bugs.launchpad.net/bugs/1817950>.

**R6 - systemd sandboxing.** Use `systemd-analyze security UNIT` as the measurement; harden in phases and test after each phase; do not
put `ReadWritePaths=/usr` on a unit (it nullifies `ProtectSystem`). The Workshop daemon writes into allow-listed `/usr` paths, so its
confinement comes from being inert by default, the closed op set, the path allow-list, and an AppArmor profile (R7). Sources:
<https://www.ctrl.blog/entry/systemd-service-hardening/>, <https://roguesecurity.dev/blog/systemd-hardening>.

**R7 - AppArmor for a Python daemon.** A profile keyed to the script path may never attach because the process is `/usr/bin/python3`;
use a named profile referenced by `AppArmorProfile=` in the unit and verify attachment with `ps -Z`/`aa-status`; build the profile with
`aa-genprof` in complain mode, then enforce. Source: <https://lists.launchpad.net/touch-packages/msg37052.html> (discussion), man
`apparmor.d`. *Consequence:* P3 verifies "confined, not unconfined" in the VM, not just that a profile file exists.

**R8 - Rootless Podman defaults for the Security Lab.** `--cap-drop=ALL`, `--security-opt no-new-privileges`, `--read-only` with tmpfs
for writable paths, user namespace mapping, no host network, explicit mounts only. Pin the Kali image by the full digest read from
`podman pull`/`image inspect` at pin time (`kalilinux/kali-rolling` is refreshed weekly; `kali-last-release` follows the last release).
Sources: <https://www.kali.org/docs/containers/official-kalilinux-docker-images/>, Podman hardening guides. The Kali Podman page itself
must be read before implementing (not retrieved yet).

**R9 - Tor Browser verification.** Verify the download with the Tor Browser developers' signing key
(fingerprint `EF6E286DDA85EA2A4BA7DE684E2C6E8793298290` as listed on support.torproject.org; re-check on the official site at
implementation time) using `gpgv` with a pinned keyring; refuse on any failure. Source: <https://support.torproject.org/tbb>.

**R10 - Website accessibility in CI.** Combine axe-core/pa11y-ci (hard failures per violation, URLs from the sitemap) with Lighthouse CI
(score budgets); a Lighthouse score alone can hide individual failures. Sources: pa11y-ci and Lighthouse CI READMEs (verify config keys
at implementation time).

**R11 - Ubuntu 26.04 hardening baseline is not documented authoritatively.** No official sysctl/boot-parameter baseline was found;
third-party guides disagree. *Consequence:* derive the baseline by measuring the booted image (`sysctl -a`, `aa-status`, `lsmod`,
listening sockets), keep only settings we can show do something, and cite no one else's claims. AppArmor restricts unprivileged user
namespaces via `kernel.apparmor_restrict_unprivileged_userns`; rootless Podman needs a profile or a deliberate exception (test in P4).

**R12 - Calamares layout for LUKS2 + unencrypted `/boot` (concrete).** Upstream `partition.conf`: `luksGeneration` defaults to `luks1` because GRUB
did not support LUKS2+Argon2id; `luks2` is allowed (PBKDF2 works in GRUB). `partitionLayout` entries take `mountPoint`, `size`, `filesystem` and
`noEncrypt: true`, so `/boot` (ext4, about 1 GiB) can be exempted while `/` is encrypted; the ESP is prepended automatically; `initialPartitioningChoice: none`
already matches our "nothing preselected" rule; `showNotEncryptedBootMessage` controls the "boot not encrypted" warning (we show our own, localised).
Calamares' LUKS deployment doc says the keyfile modules and `GRUB_ENABLE_CRYPTODISK` are only needed when `/boot` is encrypted, so with an unencrypted
`/boot` the initramfs simply asks for the passphrase. Launchpad bug 2064909 (Kubuntu 24.04 failing to decrypt) must be read before P2.1.
Sources: <https://github.com/calamares/calamares/blob/calamares/src/modules/partition/partition.conf>, <https://calamares.euroquis.nl/docs/deploy-luks>.

**R13 - Official Kali Podman guidance.** The Kali images ship **without** the default metapackage (`apt update && apt install kali-linux-headless` etc.),
have no systemd, and resolve through the containers shortnames list (`kali-rolling` -> `docker.io/kalilinux/kali-rolling`). *Consequence:* the Security Lab
has two phases: an **install phase** (network on, only the capabilities apt needs to drop to its `_apt` user, namespaced by the rootless user namespace:
CHOWN, DAC_OVERRIDE, FOWNER, SETUID, SETGID; a hypothesis to test, alternative `-o APT::Sandbox::User=root`) that produces a local image, and a **run phase**
with `--cap-drop=ALL`, `no-new-privileges`, read-only root, no network unless chosen. Source: <https://www.kali.org/docs/containers/using-kali-podman-images/>.

**R14 - Attestation action.** `actions/attest-build-provenance` v4 is now only a wrapper around `actions/attest`; new workflows should call `actions/attest`
directly (pin by SHA, read its README for the subject and SBOM inputs at implementation time). Public repo -> public-good Sigstore; permissions needed:
`id-token: write`, `attestations: write`. Verify with `gh attestation verify FILE -R timfromhcs/HSCL1`. Sources: <https://github.com/actions/attest-build-provenance>,
<https://github.com/actions/attest>.

**R15 - llama.cpp Vulkan check.** Prebuilt Windows Vulkan binaries exist in the ggml-org/llama.cpp releases; the real test is `llama-server --list-devices`
(device names look like `Vulkan0: AMD Radeon Graphics (RADV RENOIR)` on Linux/RADV) plus the backend log line of the selected device; `GGML_VK_VISIBLE_DEVICES`
selects devices. Integrated GPUs report shared memory as device memory (large totals), which confirms our rule to show dedicated and shared memory separately.

**R16 - QEMU WHPX facts.** `-accel whpx,ssd=off` disables the "separate security domain" (branch-predictor flush on VM entry/exit): a large MMIO speed-up at the
cost of mitigations. WHPX has no SMM, so Secure Boot firmware tests stay on TCG. Legacy VGA modes are slow under WHPX. Source:
<https://www.qemu.org/docs/master/system/whpx.html>. *Consequence:* optional benchmark P1.7; adopt `ssd=off` only for our own disposable test VMs and only if it
is clearly faster; never for anything that runs untrusted code (Security Lab VMs).

**R17 - CI runner mirror stalls.** The Azure Ubuntu mirror intermittently stalls a package download without erroring; `Acquire::Retries` cannot help. Fixed in CI
with a download-only loop under `timeout` and an offline install (done 2026-11-06).

---

## 2. Self-healing loop protocol (applies to every task)

```
OBSERVE   run the gate command; save stdout, exit code, timestamp, artefact paths under artifacts/<task>/
CLASSIFY  code defect | test defect | harness defect | environment/capacity | upstream bug | flaky | missing feature
HYPOTHESE state the cause as a falsifiable sentence; list what would disprove it
EXPERIMENT cheapest discriminating experiment first (host-only unit test < existing image + new harness < rebuild image < new VM install)
FIX       smallest patch at the root cause; add a test that fails without it (mutation check) 
VERIFY    targeted test -> subsystem tests -> full suite -> gate on the real artefact (VM) when the claim concerns the image
RECORD    CLAIMS.md (claim + evidence + status), BUILD_LOG.md (what happened incl. dead ends), commit, push, PR, merge on green CI
```

Rules: at most **3 fix attempts per distinct failure**, then mark BLOCKED with evidence and move on. Never weaken a test, skip a gate,
lower a threshold, or disable AppArmor/firewall/Secure Boot/encryption/sandboxing to get a pass. A flaky result is repeated 3 times
before it is called flaky and recorded as such. When two hypotheses fit, run the experiment that separates them before building anything.
A failure found while verifying something else gets its own record and its own test; fix it in the same loop if small, otherwise add it
to the backlog (section 6).

**Stop-and-ask list (needs the owner, do not guess):** signing-key policy; production deployment of the website; physical-hardware
tests; trademark review; native-speaker translation review; anything that writes to a physical disk; changing repo visibility.

## 3. Resource policy (learned the hard way: the host reaped two builds)

- Host: 19.8 GB RAM, `.wslconfig` memory=8GB swap=8GB processors=6 (backup `~/.wslconfig.bak-20261106`).
- **Never** run an image build and a VM at the same time. Order: build in WSL -> copy ISO out -> `wsl --shutdown` -> VM test.
- Build from a **WSL-local clone** (`~/hscl1-src`, `git pull` from `/mnt/e/...`), never from `/mnt/e` (9p overhead, 0777 modes).
- Before any heavy step: free memory >= 9 GB host-side, no `qemu`/`vmmem` process left over. After: shut WSL down.
- If the host reaps a job, do not restart blindly: record it, shrink the job (fewer threads, smaller guest) or ask.
- Each VM test records its image sha256 + commit and writes to `artifacts/<name>/` (not in git). Disposable disks only.

---

## 4. Phases

Each task lists **Gate** (the command or observation that proves it) and **Evidence** (where it is recorded). `[x]` done, `[~]` partial.

### P0 - Make the test infrastructure trustworthy (blocks everything that needs a VM)

- [x] **P0.1 Persistent host RPC** (R1): `vm.py` one connection, send once, never re-send after the guest spoke; `tests/unit/test_workshop_vm_rpc.py`
  (fake guest, mutation-checked against the old behaviour). **Gate:** `e2e_cli.py` completes all 23 checks on image `cd0bf42e` (the one
  that wedged). **Evidence:** `artifacts/e2e-m1d/cli-report.json` - 23/23, no errors, first_error none (2026-11-06).
- [x] **P0.2 Guest write watchdog:** in `hscl_workshopd.py`, replies are written non-blocking with a poll timeout (e.g. 20 s); on timeout
  close and re-open the port, log to the journal, count restarts in `status`. Test: a unit test with a pipe that never drains. Evidence: `tests/security/test_workshopd_port.py` (Linux: 206 passed, 0 skipped on the whole suite); **not yet in a booted image** (needs the next rebuild, P1.1).
- [x] **P0.3 Replies bounded (simplified):** replies over 4 MiB are replaced by an error (`MAX_REPLY_BYTES`); streaming was judged unnecessary now that the host drains
  over one persistent connection and writes have a deadline. Evidence: `test_oversized_reply_is_replaced_by_an_error_not_written`.
- [x] **P0.4 Determinism:** `e2e_cli.py` runs 3 times in a row on one image with identical pass/fail (flake budget: 0). Record in BUILD_LOG. **Done:** 3 consecutive runs on `cd0bf42e`, 23/23 each, KDE Connect listener 0 each (`artifacts/e2e-m1d`, `-run2`, `-run3`).
- [x] **P0.5 Restore the sandbox options on the Workshop units** if P0.1 passes with them present in the image (they are in `cd0bf42e`);
  remove the A/B exemption in `tests/security/test_systemd_hardening.py`. If P0.1 still wedges, return to the hypothesis step (do not guess). **Done:** P0.1 passed with the options present; the A/B commit was reverted (options restored, exemption removed, suite 189 passed). Evidence: `artifacts/e2e-m1d`, git revert of ed84913.
- [x] **P0.6 Dev loop doc:** one page `docs/DEV_LOOP.md` with the resource policy, commands, and the harness API (what `vm.py` guarantees).
- [x] **P0.7 Harness typing:** `vm.type()` drops `;` and `|` (seen when typing a command line into the guest terminal); extend the key map; test by typing a line with
  every printable ASCII character into a guest `cat` and reading it back. **Done (host side):** SHIFTED/QCODES maps + `tests/unit/test_typing.py` (every printable ASCII char maps to a chord); a guest read-back is still to be run once.
- [ ] **P0.8 Guest-terminal diagnostics:** commit the scratch `diag_term.py` as `scripts/workshop/e2e_term.py` (open the terminal via the dock, type lines, screenshot).
  It found the missing `__main__` guard while the API was down.
- [x] **P0.9 Process-level tests:** every shipped daemon/CLI entry point has a test that starts it as a process (found by the p1 image failure). Evidence:
  `test_script_entry_point_runs_main`.

### P1 - Close M1 on the real image

- [x] **P1.1 Rebuild + full in-guest check** with everything from P0 in the image; 23/23 checks, 3 consecutive runs. Evidence: image `HSCL1-dev-p2.iso` (sha256 0eb7acb7...63ff, clean commit 3d89a43): `artifacts/e2e-p2-run1..3` all 23/23, KDE Connect 0 listeners, `status.port` restarts 0 / write_timeouts 0.
- [x] **P1.2 File modes inside the VM:** `find` over files owned by `hscl-*` packages: none group/world-writable; record the count checked. **Done:** 304 files, 0 bad (`artifacts/probe-baseline2`, image p2).
- [ ] **P1.3 `systemd-analyze security`** for every HSCL1 unit saved as evidence (feeds P3).
- [ ] **P1.4 Published image:** inspect `v0.1.0-alpha.0`'s squashfs for world-writable HSCL1 files; if confirmed, publish `v0.1.1-alpha` built
  from the fixed pipeline and add a **warning to the old release notes** (do not delete the old release without the owner's approval).
- [ ] **P1.5 Aurora wallpaper redesign** (ribbons) with before/after screenshots and a CPU-cost measurement; otherwise "not measured".
- [ ] **P1.6 Autotune on a different virtual GPU** (virtio-gpu) to see another fingerprint/profile: `graphics detect` vs state.
- [ ] **P1.7 Optional WHPX speed-up (R16):** boot-to-desktop time with and without `ssd=off` (3 runs each, same image); adopt for our own test VMs only if clearly
  faster; record the security trade-off.

### P2 - Installer, encryption, Secure Boot (R2, R5)

- [x] **P2.0 Offline facts first:** from the ISO read the Kubuntu Calamares config (`/etc/calamares/modules/partition.conf`, `settings.conf`,
  `grubcfg.conf`), the GRUB version, and whether the signed `grubx64.efi` contains `luks2`/`cryptodisk` (strings); read Launchpad bug 2064909. Record in `docs/INSTALLER_FACTS.md`. **Done** (read inside a booted VM): the stock Kubuntu `partition.conf` already has LUKS2 + unencrypted 4 GiB `/boot` + swap file; signed GRUB has `luks2`, `cryptodisk`, `pbkdf2`, no `argon`.
- [~] **P2.1 Calamares config (R12) - no layout change needed, only the notice:** the image's `partition.conf` already matches the target layout (INSTALLER_FACTS). Remaining: our own localised "/boot is not encrypted" notice (`showNotEncryptedBootMessage` is false). Original text: `partition.conf` with `luksGeneration: luks2`, `partitionLayout`: `/boot` ext4 1 GiB `noEncrypt: true`, `/` encrypted, ESP
  automatic, `initialPartitioningChoice: none`, our own localised not-encrypted-boot notice; no second LUKS volume; zram/swap-file only. Document why (R2).
  Gate: the P2.4 install boots.
- [ ] **P2.2 Installer branding EN/DE/FR + slideshow**, no unbound shortcuts; screenshots at 1366x768 and 1920x1080.
- [ ] **P2.3 Plain install:** disposable 40 GB qcow2, install, reboot, login; run the in-guest check set on the installed system.
- [x] **P2.4 LUKS2 install (+ keyfile gate) - VM-VERIFIED on image p2 (2026-11-06)**: automated Erase-disk + Encrypt install completed (~16 min, no installer failure) with ESP / unencrypted 4 GiB `/boot` / LUKS2 root; boot asks for the passphrase, a wrong one is rejected and the prompt returns, the correct one boots to the desktop (81 s after unlock); `luksDump`: LUKS 2, aes-xts-plain64 512-bit, argon2id, one keyslot; `crypttab` key field `none`, no `/crypto_keyfile.bin`, no keyfile in the initrd; unique marker passphrase not found in /var/log, /var/lib, /etc, /root, /home, /boot, /tmp or the journal. Evidence: `artifacts/luks-install`, `artifacts/luks-boot`. Limits: leak scan did not cover swap, the raw device or the live session's logs; keyboard layout at the prompt was US only. Original text:  after the install, `lsinitramfs /boot/initrd.img-*` must contain no LUKS keyfile and `/etc/crypttab` must name no key file for the root volume (the `luksbootkeyfile` module is in the stock sequence; with an unencrypted `/boot` a keyfile in the initrd would void the encryption). Then: same, plus reboot, unlock prompt, **wrong passphrase refused**, correct one unlocks; `cryptsetup luksDump` shows
  LUKS2 and the PBKDF; `grep` of installer logs and journal finds no passphrase or key material (test uses a unique marker passphrase).
- [ ] **P2.5 Recovery key flow:** `luksAddKey` with a generated key shown once; unlock with it in the VM; never stored in logs.
- [ ] **P2.6 Fault injection:** kill the installer mid-copy, fill the target disk, no network, power-off at 50%; each leaves the virtual disk
  in a state the installer reports honestly; the host is untouched.
- [ ] **P2.7 Secure Boot state (R5):** boot with OVMF Secure Boot (TCG, slow) and read all three sources in the guest; claim only on agreement.
  Also test: a tampered kernel/shim is refused (negative test) if the harness can do it cheaply, otherwise state "not tested".
- [ ] **P2.8 Offline install** (no network) and networked install; first-boot update path (`apt update` against the real archive, then
  `hscl system updates --check` shows fresh lists).
- [ ] **P2.9 OEM/prebuilt disk path** only if time allows; not a stable gate.

### P3 - Hardening with measurements (R6, R7, R11)

- [ ] **P3.1 Baseline measurement of the booted image:** `sysctl -a`, `aa-status`, `ss -tulnp`, `lsmod`, `systemd-analyze security`, `ufw status verbose`,
  `nft list ruleset`; stored under `artifacts/baseline-<date>/`; `docs/THREAT_MODEL.md` lists every listening socket with owner and reason.
- [ ] **P3.2 Listening-socket allow-list test** in the VM: only the documented sockets exist (mDNS, CUPS on loopback, resolver/NTP loopback).
  Anything new fails the gate. Decide per item: keep, bind to loopback, or disable (CUPS browsing, avahi).
- [~] **P3.3 Per-unit sandboxing - security-baseline unit done in source (predicted exposure 7.6 -> 2.5, ufw works under it in a VM); in-image first-boot verification pending the next rebuild; Workshop units stay the documented exception (8.6). Original text:** for all HSCL1 units to a target `systemd-analyze security` exposure (<= 5.0 where function allows), measured
  before/after, applied in phases with a VM test after each phase; the Workshop daemon stays the documented exception.
- [ ] **P3.4 AppArmor (R7):** named profiles for `hscl_workshopd`, the `hscl mcp` server, and `hscl` helpers; complain-mode run through the
  full e2e set, then enforce; gate: `ps -Z` shows the profile (not unconfined) and the e2e set still passes enforced.
- [ ] **P3.5 Kernel/userland knobs** proven by measurement (R11): keep the current sysctl file; add only settings that change an observed value;
  test that unprivileged userns behaviour matches the documented choice and that Podman still works (P4).
- [ ] **P3.6 Firewall tests:** inbound denied by default (probe from the host through the QEMU user-net forward), outbound allowed; profile switch tests.
- [ ] **P3.7 Privileged helper / Polkit:** if any Polkit action or helper exists, audit its rules; if none, state so (no hidden root path from the UI).
- [ ] **P3.8 Fuzz depth:** property/fuzz tests for the Rust CLI parsers that read untrusted input (model catalog, JSON from the backend,
  theme files); `cargo test` with seeded generators; no new dependencies unless audited by `cargo deny`.
- [ ] **P3.9 CI security gates stay on:** cargo audit, cargo deny, secret scan on every push, ShellCheck, pinned action SHAs (Dependabot PRs
  are reviewed, never auto-merged without green CI).
- [ ] **P3.10 Dependabot PRs open now:** triage each (checkout 7.x, upload-artifact 7.x, thiserror 2.x, sha2 0.11): merge only with green CI and a
  look at the changelog; record the decision.

### P4 - Security Lab MVP (R8)

- [ ] **P4.0 Podman in the image:** `podman` is NOT in the live image (measured). Add podman and its runtime dependencies (crun, netavark/pasta or slirp4netns, uidmap, fuse-overlayfs, containers-common) through the same signed-archive mechanism used for earlyoom/zram, verify offline installability, record the size increase; `verify-image.sh` checks they are present and that no daemon is enabled.
- [~] **P4.1 Read the Kali Podman page - read (R13); digest recorded in `containers/kali/image.pin` from the Docker Hub API (not yet pull-verified).** Original: **Read the Kali Podman page** and record the exact supported flags; pin the digest read from `podman pull` (full `sha256:`).
- [x] **P4.2 Container spec generator (two phases, R13) - IMPLEMENTED + unit-tested (`cli/hscl/src/lab.rs`, `hscl lab`, docs/SECURITY_LAB.md); not run in a VM, execution not wired (P4.3).** in Rust (`hscl lab ...`): typed options only; defaults = rootless, `--cap-drop=ALL`, `no-new-privileges`,
  `--read-only`+tmpfs, no host network/PID, no privileged, no socket mounts, no host home, explicit lab folder mount only, memory/CPU/PID limits.
  Unit tests assert the generated argv for the safe default and reject every unsafe override (privileged, `--net=host`, `/`, `/etc`, `/run`,
  `$SSH_AUTH_SOCK`, gpg-agent, browser profile paths, `~`).
- [ ] **P4.3 VM run:** rootless podman in the live/installed VM pulls the pinned image (needs guest network), runs `nmap --version`, and the
  inspect output matches the spec; `podman ps` after `lab destroy` is empty; user-selected evidence folder survives destroy.
- [ ] **P4.4 Authorization reminder** shown before enabling attack tooling (EN/DE/FR); stored locally, no telemetry.
- [ ] **P4.5 Toolset install/remove** for the basic group only (nmap, tcpdump, tshark, whois, dnsutils) inside the container; others PLANNED.
- [ ] **P4.6 Host APT sources contain no Kali repo** (existing test) and the image check stays.

### P5 - Privacy workflows (R9)

- [ ] **P5.1 Tor Browser launcher:** download from the official URL, verify with `gpgv` + pinned keyring (fingerprint checked against the
  official page at implementation time), fail closed on any mismatch (unit tests with tampered files), never run unverified.
- [ ] **P5.2 `hscl privacy tor status`** from the real daemon/control port; clear message when Tor is unavailable, no direct fallback in the launcher.
- [ ] **P5.3 Tails ISO verify/launch:** `hscl privacy tails verify IMAGE SIG` against the official key; launch in QEMU only after success.
- [ ] **P5.4 Decide the ephemeral Privacy session** against AGENTS.md 6.5 tests (swap off, no internal disk automount, journal volatile, DNS
  leak capture, IPv6 handling, fail closed). If not all pass: label **Experimental**; the stable release makes no anonymity claim either way.
- [ ] **P5.5 Docs** `docs/PRIVACY_MODE.md` with exact behaviour and gaps; website privacy page (EN/DE/FR).

### P6 - Local AI, coding and media tooling (verify before listing as working)

- [ ] **P6.1 CPU path** re-verified on the current image with the pinned llama.cpp and the 2B model (already VM-adjacent on the builder); record tokens/s as one measured sample, not a benchmark.
- [ ] **P6.2 Vulkan on real hardware (R15):** the owner's machine has a Radeon 680M. A Windows-host llama.cpp Vulkan smoke test is possible without
  rebooting (backend log shows the device); the Linux claim needs a physical boot -> owner task, otherwise "not verified on Linux".
- [ ] **P6.3 MTP / TurboQuant:** enable only if the pinned backend's `--help` advertises it; measure before/after on the same model.
- [ ] **P6.4 HCS Coder:** run the generated OpenCode config against the real tool; licence gate stays.
- [ ] **P6.5 Media AI catalogue and RSI loop:** only entries with licence + sha256 + one real run; everything else stays PLANNED (do not
  start before P1-P5 are done).

### P7 - UI/UX, accessibility, localisation, visual QA

- [ ] **P7.1 Control Center pages** for Graphics, Memory, Wallpaper Studio, AI/Models, Security, Updates: every value from `hscl ... --json`.
- [ ] **P7.2 First-run:** short, skippable, contextual hints; restartable from Help.
- [ ] **P7.3 Launcher:** `Meta+Space` focus, `Esc` closes and restores focus, tested by key injection.
- [ ] **P7.4 Accessibility:** keyboard-only path through installer + Control Center; accessible names; QML colours checked against tokens;
  targets >= 24 px; reduced-motion switch stops all animation.
- [ ] **P7.5 Visual QA matrix** {1366x768, 1920x1080} x {Midnight, Light} x {EN, DE, FR} x {Control Center, launcher, installer, lock screen};
  fix at the token/component, recapture; curated screenshots into `docs/img`.
- [ ] **P7.6 Translation completeness gate** for critical strings (installer, security, privacy, recovery) in CI; **native-speaker review is an
  owner task** - until then DE/FR are labelled "machine-assisted, not reviewed" on the website and in the handbook.
- [ ] **P7.7 Website:** remaining pages (install/USB only after a physical test - until then none, privacy, changelog), axe/pa11y-ci + Lighthouse CI
  with budgets (R10), link check, hreflang/canonical with the real `SITE_URL`, Vercel **preview** deployment; **production only with the owner's go**.

- [~] **P7.x Live-Ansicht bei VM-Laeufen (Owner-Wunsch 2026-11-06, gilt ab dem NAECHSTEN Lauf; laufende Laeufe nicht aendern).**
  Jeder visuelle/automatische VM-QA-Lauf (`qemu_boot_test.py`, `workshop/e2e_*.py`, `vm.py`) oeffnet waehrend des Laufs ein Popup-Fenster mit dem Gastbildschirm,
  damit der Owner zuschauen kann. Umsetzung: Flag `--watch` (Standard an bei interaktiver Sitzung, `--no-watch` fuer CI/headless). Option A: QEMU `-display gtk`
  bzw. `sdl` zusaetzlich zu QMP (Screenshots/Eingabe laufen unveraendert ueber QMP). Option B (falls GUI-Display die WHPX/OVMF-Laeufe stoert):
  `-display none` beibehalten und ein kleines Viewer-Fenster (Python/Tk oder `ffplay`), das periodisch QMP `screendump` zeigt (~2 fps), mit Statuszeile
  (Szenario, Schritt, verstrichene Zeit). Anforderungen: Fenster stoert keine Tastatur-/Maus-Injektion, schliesst sich am Ende selbst, Absturz des Viewers
  bricht den Test nicht ab, CI nutzt immer `--no-watch`. Test: Unit-Test fuer Argument-/QEMU-Kommandozeilenbau (watch an/aus) + ein manueller Lauf mit Beleg.
  **Stand 2026-11-06: IMPLEMENTED (Option B), nicht VM-verifiziert.** `scripts/workshop/watch.py` (Frame-Thread, `HSCL_WATCH`, CI aus) + `viewer.py` (Tk), in `vm.py` eingehaengt (QMP-Lock, `--no-watch`), alle `e2e_*`-Skripte ueber `VmManager`; Unit-Tests `tests/unit/test_watch.py`; Viewer-Smoke-Test ok (Fenster startet). Offen: erster echter VM-Lauf mit sichtbarem Fenster (Beleg), `qemu_boot_test.py` (eigene QMP-Verbindung, Installer-Szenarien) hat noch keine Live-Ansicht.

### P8 - Reproducibility (R3)

- [ ] **P8.1 Build twice** from the same commit in the same builder with `SOURCE_DATE_EPOCH` set to the commit time; `xorriso --modification-date`;
  `mksquashfs -all-time/-mkfs-time` per the installed squashfs-tools version (check `--help`); clamp rootfs mtimes.
- [ ] **P8.2 Compare** package manifest, rootfs file list + sha256, squashfs hash, ISO hash; publish the diff verbatim in
  `docs/REPRODUCIBILITY.md` (what matches, what differs and why: initramfs, caches, dpkg databases).
- [ ] **P8.3 Fix the largest sources of difference** found (initramfs, mime/font caches) with the smallest patches; re-compare. The word
  "reproducible" appears only if the ISO hashes are equal across two clean builds.

### P9 - Release engineering (R4)

- [ ] **P9.1 SBOM wired in:** `gen_sbom.py` run on the final rootfs (`var/lib/dpkg/status`) and `Cargo.lock`; attached to the release.
- [ ] **P9.2 Attestations (R14, `actions/attest`):** CI job attests the release files (provenance) and the SBOM; `gh attestation verify` documented on the download page.
- [ ] **P9.3 Optional maintainer signature:** only after the owner decides the key policy; until then "unsigned by a maintainer" stays in the notes.
- [ ] **P9.4 Release workflow dry run** on a prerelease tag; the verify workflow downloads, joins, hashes, checks attestations.
- [ ] **P9.5 RC process:** feature freeze, RC image built from a clean clone, full VM matrix on the exact artefact, hashes in BUILD_LOG.
- [ ] **P9.6 Docs match the artefact:** README, docs/*, website, handbook; every command in the docs executed as written once in a VM.

### P10 - Stable gates (all must be ticked with evidence, or the gap is stated in the release notes)

1. ISO built from repository scripts; hash, manifest, SBOM, attestation published; verify workflow green.
2. Boots in QEMU UEFI and BIOS; Secure Boot state read and cross-checked; **a physical boot report exists** or the stable claim is restricted to "VM-verified".
3. Plain and LUKS2 install + boot + unlock repeated on the release artefact; fault-injection cases pass.
4. In-guest check set passes 3 times in a row; `systemd-analyze security`, AppArmor attachment, listening-socket allow-list recorded.
5. Security Lab runs one real pinned container with the safe defaults; Privacy features limited to what the tests show.
6. Visual QA matrix and keyboard-only path done; EN/DE/FR critical strings complete; DE/FR review status stated honestly.
7. Reproducibility result published exactly as measured.
8. No unresolved critical/high finding in HSCL1-owned code; dependency audit green; every accepted residual risk written down.
9. Known limitations and trademark-review status published; maintainer signature present or absent as stated.

---

## 4b. Open questions and how each gets answered

| # | Question | Cheapest discriminating experiment | Where |
|---|---|---|---|
| 1 | Does the Kubuntu Calamares accept a `noEncrypt` `/boot` + LUKS2 root layout non-interactively, and does the installed system boot and unlock? | P2.0 offline config read, then P2.4 install in a VM | P2 |
| 2 | Does the signed GRUB in this ISO contain `luks2`/`cryptodisk`? | `strings` on `grubx64.efi` extracted from the ISO (no VM) | P2.0 |
| 3 | Does `apt` work in the Kali container with the restricted capability set, or does it need `-o APT::Sandbox::User=root`? | one rootless container in the VM, both variants | P4.3 |
| 4 | Does AppArmor really confine `hscl_workshopd` (the profile attaches to the interpreter path)? | `ps -Z` in the VM with a named profile | P3.4 |
| 5 | Are unprivileged user namespaces restricted in 26.04 in a way that breaks rootless Podman? | **Partly answered 2026-11-06:** `kernel.apparmor_restrict_unprivileged_userns = 0` in the live image (unrestricted); still needs one rootless run on the installed system | P3.5/P4.3 |
| 6 | Is the ISO reproducible, and where does it differ? | two clean builds with `SOURCE_DATE_EPOCH`, compare at 3 levels | P8 |
| 7 | Does `ssd=off` make the WHPX VM clearly faster? | 3 boots each, same image | P1.7 |
| 8 | Does the Windows Vulkan build of llama.cpp select the Radeon 680M? | `llama-server --list-devices` + backend log line on the owner's machine | P6.2 |
| 9 | Do the Dependabot majors (checkout 7, thiserror 2, sha2 0.11) change behaviour we rely on? | CI incl. tests; read changelogs | P3.10 |
| 10 | Is the DE/FR text acceptable to native speakers? | **owner** review | P7.6 |
| 11 | Does the image boot on a physical PC (UEFI, Secure Boot on/off)? | **owner** boot report | P10 |
| 12 | May the website go to production on Vercel, and under which domain? | **owner** decision; preview first | P7.7 |

## 5. Risk register

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| Host runs out of memory during build or VM | high (seen 3x, also with WSL capped at 8 GB) | job reaped | resource policy (section 3), sequential steps, WSL cap 6 GB, squash with 3 procs / 512M, restart only on the owner's word |
| Workshop wedge has a second cause besides R1 | medium | VM tests stay flaky | P0.4 three-run determinism gate before any other VM work |
| Calamares cannot produce the R2 layout non-interactively | medium | LUKS2 gate blocked | script the layout via `partition.conf` + `unpackfs` order, or document manual partitioning and test that path |
| Signed GRUB/shim behaviour changes in point releases | low | boot failures | pin the base ISO checksum; re-test on base updates |
| Upstream (Ubuntu archive) package drift breaks the build | medium | CI/builds red | pinned base ISO; record package versions in the manifest |
| Physical hardware never tested | certain until the owner does it | stable claim limited | state it; offer a one-page "boot report" template |
| Translations wrong in security warnings | medium | user confusion | labelled unreviewed; keep sentences short; owner review |

## 6. Backlog (found, not yet scheduled)

- QEMU upstream fix for issue 4672 (patchew, Sept 2026): re-test on a newer QEMU when available; keep the harness workaround.
- Dependabot majors (checkout 7, upload-artifact 7, thiserror 2, sha2 0.11): P3.10.
- `README`/CLAIMS wording audit for any remaining unverified phrase after each release.
- Website: JSON-LD only for true SoftwareApplication facts; OG image from a real screenshot.
- The old plan's M3/M4 AI/media items beyond P6.1-P6.4 stay PLANNED.

## 7. Tracking

Per task: set `[x]` only with an evidence line `Evidence: <path or run URL>`; `[~]` while partial. Update `docs/BUILD_LOG.md` after every loop (what
was tried, what failed, what the next safe action is) and `docs/CLAIMS.md` for every claim whose status changed. Commit on `codex/hscl1-v1`,
open a PR, merge into `main` when CI is green; never force-push; tag releases only per P9/P10.


---

## Addendum 2026-11-06 (pointer)

The expansion plan `2026-11-06-ux-ai-hardware-expansion.md` now also covers: the full product name (HSCL1 = Hypercharged Supreme Computing Layout 1) and the `hscl1` program (W13), the release path incl. the online single-file merger and README/screenshot overhaul (W14), the HCS shell, viewers, office/creative suite (W15-W17), the pentest tool registry with scope enforcement, job API and MCP (W18), the desktop API/MCP (W19) and measured hardening with `kernel-hardening-checker` and `lynis` (W20). New items for THIS plan:

- [ ] **P1.8 Release `v0.1.1-alpha.0`** supersedes P1.4's "publish a fixed release": see W14.1 for the gate list. The published `v0.1.0-alpha.0` gets a warning in its notes (two measured defects: world-writable HSCL1 payload files, `/` owned by uid 1000).
- [ ] **P3.11 Measured hardening report**: W20.1-W20.3.
