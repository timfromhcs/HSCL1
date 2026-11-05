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
