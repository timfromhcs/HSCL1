# Prebuilt image + live/prebuilt update plan

> **For agentic workers:** executed natively and autonomously. Evidence goes to `docs/BUILD_LOG.md`; status words follow AGENTS.md §0.4. Parent plan: `2026-11-05-hscl1-to-v2-stable.md` (this covers its M6, parts of M9/M11).

**Goal:** (1) prove that the installer really installs HSCL1 to a disk and that the installed system boots and passes the guest checks; (2) produce a **prebuilt disk image** (qcow2) from that install; (3) define and implement how the **live ISO** and the **prebuilt image** receive updates; (4) package a local release set with truthful manifests.

**Architecture:** The installer is the shipped Calamares (Kubuntu base). A VM driver (`scripts/qemu_boot_test.py` scenarios over QMP) clicks through it onto a disposable qcow2. The prebuilt image is the qcow2 of an **OEM-mode** install (Calamares OEM: no user is created at build time; the first boot asks for the user), so the image carries **no default credentials**. Updates stay APT-based; the CLI only reads state (`hscl system updates --check`); installing updates stays an explicit user action.

**Spec:** AGENTS.md §3.3 Update system, §7.1 (prebuilt qcow2 only after a successful installed-system boot test, credential-free first boot), §14.2 gates, §17.3 release policy.

## Decisions

| # | Decision | Why |
|---|---|---|
| D1 | Prebuilt image = OEM install, not a scripted rootfs copy | uses the supported, tested installer path (bootloader, initramfs, fstab); avoids shipping a user/password |
| D2 | Two different artifacts from the install runs: **test install** (throw-away user, never published) and **OEM image** (publishable candidate) | a test user would be a default credential |
| D3 | Live ISO is immutable. "Updating live" means a refreshed ISO (new release), plus APT inside the RAM session if the user wants it | live overlay is lost on shutdown; no persistence in v1 |
| D4 | The ISO refresh keeps kernel and initrd on the ISO identical to the kernel inside the squashfs; the verifier fails otherwise | a mismatched kernel/module set is unbootable |
| D5 | Installed systems update through APT only: Ubuntu `resolute`, `-updates`, `-security`; unattended **security** upgrades on, no automatic reboot | AGENTS.md §3.3/§6.2 |
| D6 | No update check phones home. `hscl system updates --check` talks to the APT mirrors the user already configured and compares nothing against an HSCL1 server | AGENTS.md rule 9 (no telemetry); a signed `latest.json` channel stays PLANNED until a signing key exists |
| D7 | Publishing to GitHub/Vercel stays blocked until the owner decides repo visibility, licence and signing key; this plan produces the local release set only | AGENTS.md §17.1, §19 |

## Tasks

### U1 - Install verification (test install)
- [ ] Scenario `tests/visual/scenarios/install-normal.json` + harness option `--disk PATH` (qcow2 created with `qemu-img`, virtio disk) drive Calamares: language, location, keyboard, partitions (erase disk, explicit), user `tester`, summary, install, finish.
- [ ] Screenshots of each page are saved; installer shows HSCL1 branding (no "Kubuntu" in title, sidebar, launcher name).
- [ ] Reboot from the disk only (no ISO): `scripts/qemu_boot_test.py --disk` reaches the login screen; log in via scenario; `hscl-qa` guest report passes `qa_report.py` with installed-system profile (os-release HSCL1, firewall active, sysctl, LNF default).
- [ ] Record: disk size, partition table, bootloader entry name, time. Status: VM-VERIFIED only if all of the above hold.

### U2 - Prebuilt OEM image
- [ ] Scenario `install-oem.json` (launcher `calamares-launch-oem`), install to a new qcow2, shut down at the end - the disk stays untouched afterwards.
- [ ] `scripts/make-prebuilt.sh`: `qemu-img convert -c -O qcow2` (compressed, sparse), writes `.sha256` and `prebuilt-manifest.json` (image size, virtual size, partition table, base ISO sha256, HSCL1 version, package list from the image).
- [ ] Verify on a **copy**: boot, OEM first-boot screen appears, create a throw-away user in the verification run only, desktop reached, guest report passes. The delivered image is never the verified copy.
- [ ] Credential scan: mount the image read-only (loop in WSL) and assert no `/home/*` user other than the OEM account, no SSH host/user keys, no `/var/log/installer` secrets, no machine-id (first boot generates it).

### U3 - Update mechanics
- [ ] `hscl system updates --check [--json]`: read-only; runs `apt-get -s dist-upgrade`-equivalent parsing (`apt list --upgradable` fallback), reports count, security count, reboot-required, last apt update time; exits 0 always unless apt is unusable (exit 1). Unit tests parse fixture outputs (none, some, security-only, broken apt).
- [ ] `hscl system updates --install` stays absent from help until the privileged helper exists (documented as PLANNED in handbook).
- [ ] `hscl-security` ships `/etc/apt/apt.conf.d/52hscl-unattended-upgrades`: origins = `${distro_id}:${distro_codename}-security` only, `Automatic-Reboot "false"`, `Remove-Unused-Dependencies "false"`; test asserts exact origins and no `-proposed/-backports`.
- [ ] Control Center "Updates" row on Overview shows the count from `hscl system updates --check` (allow-listed command), de/fr strings.
- [ ] Handbook chapter "Updates" (EN/DE/FR): live vs installed, what is automatic, how to check, how to reboot.

### U4 - Live ISO refresh
- [ ] `remaster-iso.sh --upgrade`: bind-mount `/etc/resolv.conf`, `apt-get update && apt-get -y dist-upgrade` inside the chroot (pockets from D5 only), then regenerate casper initrd (`update-initramfs -u -k all`), copy `vmlinuz` and `initrd` from the rootfs to `/casper/` on the ISO, refresh `md5sum.txt`.
- [ ] `verify-image.sh` gains: kernel version in rootfs `/boot/vmlinuz-*` equals the version string of `/casper/vmlinuz` (via `file`), fails otherwise; APT sources inside the image pass `tests/security/test_apt_sources.py` rules.
- [ ] Boot the refreshed ISO (UEFI) and rerun the guest report; record both package-count deltas in the manifest.
- [ ] If the upgrade pulls a new kernel and the ISO cannot be made consistent, the task stays BLOCKED with evidence; the unrefreshed ISO remains the release candidate.

### U5 - Local release set
- [ ] `scripts/make-release.sh VERSION`: collects ISO, qcow2 (OEM), `SHA256SUMS`, `build-manifest.json` (real sizes/hashes/commit/date, test evidence paths), `release-notes.md` (generated from BUILD_LOG status table: only VM-VERIFIED items are claimed), under `artifacts/release/VERSION/`. Fails if any placeholder string or missing artifact is detected.
- [ ] No tag, no upload, no signature without the owner decisions of D7; the script prints exactly what is blocked.

## Review focus

- Installing onto the wrong disk: the VM has exactly one virtio disk; the scenario asserts the Calamares summary page screenshot shows the VM disk size (40 GB) before "Install".
- The OEM image contains the test user or SSH keys: credential scan (U2) must fail the release script.
- Live ISO and refreshed ISO ship different kernels than their initrd: verifier (U4).
- Update check reports "0 updates" when apt is broken: tested explicitly (broken apt fixture → error, not zero).
- Security-only unattended upgrades silently widen to `-updates`: exact-origin test.
