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

- [~] **P0.1 Persistent host RPC** (R1): `vm.py` one connection, send once, never re-send after the guest spoke; `tests/unit/test_workshop_vm_rpc.py`
  (fake guest, mutation-checked against the old behaviour). **Gate:** `e2e_cli.py` completes all 23 checks on image `cd0bf42e` (the one
  that wedged) - *running now*. **Evidence:** `artifacts/e2e-m1d/cli-report.json`.
- [ ] **P0.2 Guest write watchdog:** in `hscl_workshopd.py`, replies are written non-blocking with a poll timeout (e.g. 20 s); on timeout
  close and re-open the port, log to the journal, count restarts in `status`. Test: a unit test with a pipe that never drains.
- [ ] **P0.3 Replies bounded:** cap one reply at 1 MiB, stream big outputs (`respin`, screenshots) in <= 64 KiB lines with sequence numbers;
  host reassembles. Test both sides.
- [ ] **P0.4 Determinism:** `e2e_cli.py` runs 3 times in a row on one image with identical pass/fail (flake budget: 0). Record in BUILD_LOG.
- [ ] **P0.5 Restore the sandbox options on the Workshop units** if P0.1 passes with them present in the image (they are in `cd0bf42e`);
  remove the A/B exemption in `tests/security/test_systemd_hardening.py`. If P0.1 still wedges, return to the hypothesis step (do not guess).
- [ ] **P0.6 Dev loop doc:** one page `docs/DEV_LOOP.md` with the resource policy, commands, and the harness API (what `vm.py` guarantees).

### P1 - Close M1 on the real image

- [ ] **P1.1 Rebuild + full in-guest check** with everything from P0 in the image; 23/23 checks, 3 consecutive runs.
- [ ] **P1.2 File modes inside the VM:** `find` over files owned by `hscl-*` packages: none group/world-writable; record the count checked.
- [ ] **P1.3 `systemd-analyze security`** for every HSCL1 unit saved as evidence (feeds P3).
- [ ] **P1.4 Published image:** inspect `v0.1.0-alpha.0`'s squashfs for world-writable HSCL1 files; if confirmed, publish `v0.1.1-alpha` built
  from the fixed pipeline and add a **warning to the old release notes** (do not delete the old release without the owner's approval).
- [ ] **P1.5 Aurora wallpaper redesign** (ribbons) with before/after screenshots and a CPU-cost measurement; otherwise "not measured".
- [ ] **P1.6 Autotune on a different virtual GPU** (virtio-gpu) to see another fingerprint/profile: `graphics detect` vs state.

### P2 - Installer, encryption, Secure Boot (R2, R5)

- [ ] **P2.1 Calamares config:** `partition.conf` with `luksGeneration: luks2`, an explicit layout (ESP, 1 GiB unencrypted ext4 `/boot`, LUKS2
  root), no second LUKS volume; zram/swap-file only. Document why (R2).
- [ ] **P2.2 Installer branding EN/DE/FR + slideshow**, no unbound shortcuts; screenshots at 1366x768 and 1920x1080.
- [ ] **P2.3 Plain install:** disposable 40 GB qcow2, install, reboot, login; run the in-guest check set on the installed system.
- [ ] **P2.4 LUKS2 install:** same, plus reboot, unlock prompt, **wrong passphrase refused**, correct one unlocks; `cryptsetup luksDump` shows
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
- [ ] **P3.3 Per-unit sandboxing** for all HSCL1 units to a target `systemd-analyze security` exposure (<= 5.0 where function allows), measured
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

- [ ] **P4.1 Read the Kali Podman page** and record the exact supported flags; pin the digest read from `podman pull` (full `sha256:`).
- [ ] **P4.2 Container spec generator** in Rust (`hscl lab ...`): typed options only; defaults = rootless, `--cap-drop=ALL`, `no-new-privileges`,
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
- [ ] **P6.2 Vulkan on real hardware:** the owner's machine has a Radeon 680M. A Windows-host llama.cpp Vulkan smoke test is possible without
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

### P8 - Reproducibility (R3)

- [ ] **P8.1 Build twice** from the same commit in the same builder with `SOURCE_DATE_EPOCH` set to the commit time; `xorriso --modification-date`;
  `mksquashfs -all-time/-mkfs-time` per the installed squashfs-tools version (check `--help`); clamp rootfs mtimes.
- [ ] **P8.2 Compare** package manifest, rootfs file list + sha256, squashfs hash, ISO hash; publish the diff verbatim in
  `docs/REPRODUCIBILITY.md` (what matches, what differs and why: initramfs, caches, dpkg databases).
- [ ] **P8.3 Fix the largest sources of difference** found (initramfs, mime/font caches) with the smallest patches; re-compare. The word
  "reproducible" appears only if the ISO hashes are equal across two clean builds.

### P9 - Release engineering (R4)

- [ ] **P9.1 SBOM wired in:** `gen_sbom.py` run on the final rootfs (`var/lib/dpkg/status`) and `Cargo.lock`; attached to the release.
- [ ] **P9.2 Attestations:** CI job attests the release files (provenance) and the SBOM; `gh attestation verify` documented on the download page.
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

## 5. Risk register

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| Host runs out of memory during build or VM | high (seen 2x) | job reaped | resource policy (section 3), sequential steps, WSL cap |
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
