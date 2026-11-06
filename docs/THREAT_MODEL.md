# HSCL1 threat model (v0, pre-alpha)

## Assets
User data, passwords, SSH/GPG keys, browser profiles, project source, local model files, disk-encryption keys,
network identity, device/boot integrity.

## Adversaries
Opportunistic malware; malicious downloads/containers; other local users; lost/stolen device; untrusted network
(public Wi-Fi); malicious USB; a compromised host/hypervisor/firmware; a targeted, well-resourced attacker.

## Trust boundaries
Firmware -> boot chain -> kernel -> host OS -> user session -> Polkit helper -> containers/VMs -> Tor -> removable
media -> release infrastructure (GitHub, Vercel).

## Mitigations by mode (design intent; each needs test evidence before it is claimed)
| Mode | Intended mitigation | Evidence today |
|---|---|---|
| Workstation | AppArmor, deny-incoming firewall, LUKS2, signed updates, no unneeded listeners | none yet (CLI can *report* AppArmor/UFW state) |
| Security Lab | rootless Podman, no host mounts/sockets/devices by default, pinned image digests | none yet |
| Privacy | Tor-only egress for the privacy workflow, fail-closed, no persistence by default | none yet |

## Not provided
Anonymity guarantees, protection from a compromised firmware/hypervisor, forensic invisibility, Tails-equivalent
security, Kali certification, protection of data once a user logs into personal accounts over Tor.

## Release-integrity threats
Compromised upstream mirror (mitigated: SHA256 + GPG verification of the base ISO), tampered release asset (planned:
signed `SHA256SUMS`), leaked secrets (planned: secret scan in CI; `.gitignore` excludes keys and `.env`).

## Gaps
Everything not listed under "Evidence today". This file is updated as tests are added.

## systemd sandboxing of HSCL1 units (2026-11-06)
All HSCL1 system units set `ProtectKernelModules`, `ProtectControlGroups`, `ProtectHostname`, `LockPersonality`, `RestrictRealtime` and
`SystemCallArchitectures=native` (enforced by `tests/security/test_systemd_hardening.py`). The security-baseline unit additionally has
`NoNewPrivileges`, `PrivateTmp`, `ProtectHome` and `RestrictAddressFamilies`. The Workshop daemon deliberately has **no** `ProtectSystem`
and no `NoNewPrivileges`: it writes into allow-listed `/usr` paths and runs root hooks on request. Its protection is that it is inert unless
a hypervisor provides the virtio port (or an admin starts the local socket variant), plus the closed operation set and path allow-list.
Status: static check only; `systemd-analyze security` output from a booted image is **not yet collected**.

**Update (2026-11-06):** the Workshop-unit sandbox options were restored. The Workshop-daemon failures that made us suspect them were caused by the host test
harness (a TCP connection per RPC plus re-sends, which wedges a throttled virtio-serial port); with a persistent connection the image that carries the options
completed all 23 in-guest checks. Status: one VM run; three consecutive runs are the gate.

## Measured baseline of the live image (2026-11-06, image HSCL1-dev-p2.iso, evidence `artifacts/probe-baseline/probe.json`)

Measured in a booted VM (QEMU/WHPX, non-Secure-Boot firmware); not a statement about installed systems or physical hardware.

| Item | Measured value |
|---|---|
| Listening sockets | `avahi-daemon` UDP 5353 on all interfaces (mDNS, IPv4 and IPv6); `systemd-resolved` 53 on loopback; `chronyd` UDP 323 on loopback; `cupsd` TCP 631 on loopback. **No `*:1716`**, no other wildcard listener. |
| Firewall | `ufw` active: default deny (incoming), allow (outgoing); default ufw rules additionally accept ICMP echo, DHCP replies, mDNS (224.0.0.251:5353) and SSDP (239.255.255.250:1900) |
| Kernel | 7.0.0-30-generic, 79 modules loaded; command line `BOOT_IMAGE=/casper/vmlinuz --- quiet splash` |
| Sysctls | `kptr_restrict=2`, `dmesg_restrict=1`, `unprivileged_bpf_disabled=1`, `yama.ptrace_scope=1`, `protected_symlinks=1`, `protected_hardlinks=1`, `suid_dumpable=0`, `tcp_syncookies=1`, `rp_filter=2`; `kernel.unprivileged_userns_clone=1`, `user.max_user_namespaces=11209`, `kernel.apparmor_restrict_unprivileged_userns=0` (**not restricted** in this image), `kernel.apparmor_restrict_unprivileged_unconfined=1` |
| AppArmor | module loaded; 21 profiles, all enforce (snap/firefox/thunderbird/rsyslogd and similar); **no HSCL1 profile yet** |
| Secure Boot (this VM) | `mokutil`: "doesn't support Secure Boot"; no `SecureBoot` EFI variable; kernel log "secureboot: Secure boot disabled" - consistent: this run used firmware without Secure Boot. Canonical's signing certificates are loaded in the kernel keyring. Not a Secure Boot test (P2.7 needs the Secure Boot firmware under TCG). |
| systemd exposure (`systemd-analyze security`) | `hscl-workshopd` 8.6, `hscl-workshopd-local` 8.6, `hscl-workshop-evidence` 8.6, `hscl-security-baseline` 7.6, `earlyoom` 0.9 (all EXPOSED except earlyoom); the HSCL1 units are the target of P3.3 |
| Running services of note | `snapd` (Firefox snap), `avahi-daemon`, `cups` + `cups-browsed`, `ModemManager`, `wpa_supplicant`, `unattended-upgrades`, `hscl-workshopd` |
| Rootless containers | **`podman` is not installed in the image**; `/proc/sys/user/max_user_namespaces` = 11209 |
| Bootloader | `grub-efi-amd64-signed 1.215+2.14-2ubuntu1`, `shim-signed 1.59+15.8-0ubuntu2`; EFI files `bootx64.efi`, `grubx64.efi`, `mmx64.efi` |

Consequences recorded in the plan: Security Lab needs podman and its dependencies added to the image (P4.0); the userns restriction question (Q5) is answered for this image
(unrestricted); the avahi/mDNS listener and `cups-browsed`/`snapd` are candidates for the "Public Wi-Fi" profile and for the service review in P3.2.
