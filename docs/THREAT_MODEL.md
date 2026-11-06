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
