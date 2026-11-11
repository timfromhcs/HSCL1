# HSCL1 architecture

> Made with love by hcsmedia. Pre-alpha; sections describe the *design* and mark implementation status.

## Layers

```text
UEFI/BIOS -> shim -> GRUB -> Ubuntu kernel          (upstream signed chain preserved by the remaster)
  Live Workstation / Installer      squashfs layers + RAM overlay (casper), Calamares (Kubuntu)
  Installed Workstation             Ubuntu 26.04 LTS (resolute) + Plasma 6.6, HSCL1 defaults, hscl CLI
  Security Lab (opt-in)             rootless Podman + pinned official Kali OCI images, or disposable VMs
  Privacy                           Tor Browser workflow; official Tails ISO launcher (verified); no Tails claim
```

## Package-source policy

Allowed: Ubuntu `resolute`, `resolute-updates`, `resolute-security` (+ a signed HCS repo only if truly needed).
Forbidden on the host: Kali, Debian, Ubuntu interim/devel pockets, PPAs, unsigned repositories.
`hscl security status` and `hscl doctor` enforce this by scanning `/etc/apt` (`FAIL` on violation).

## Image pipeline (decision record)

| Option | Verdict |
|---|---|
| Remaster official Kubuntu 26.04.1 ISO (xorriso + squashfs-tools, replay boot metadata) | **Chosen for PoC**: keeps signed boot chain and upstream installer. |
| `livecd-rootfs` full build | Fallback: heavy, needs Launchpad-style infrastructure. |
| Debian `live-build` | Fallback only; not assumed to work with Ubuntu `resolute`. |
| Cubic | Exploration only; GUI-first, not CI-friendly. |

The decision is final only after the PoC ISO boots (see `docs/BUILD_LOG.md`).

## Components

| Component | Path | Status |
|---|---|---|
| CLI | `cli/hscl` (Rust, clap) | TESTED (unit) |
| Design tokens | `themes/tokens/tokens.json`, validated by `scripts/check-tokens.py` (WCAG AA) | TESTED |
| Privileged helper | `services/hscl-privileged-helper` | PLANNED |
| Control Center | `apps/control-center` (Qt 6/QML) | PLANNED |
| Installer branding | `distro/installer` | PLANNED |
| Website | `website/` (Vercel) | PLANNED |

## Privilege model

UI and CLI run unprivileged and **never escalate**. A command that would need root produces the exact
command instead of running it: `hscl security firewall profile set` prints the `ufw` lines,
`hscl system updates --install` prints `sudo apt-get dist-upgrade -y`, and `hscl lab` prints the
`podman` invocation. The user copies it into a terminal, so the privileged step is visible and typed
by a person, not by the UI.

A finite, typed, Polkit-authorised helper (`services/hscl-privileged-helper` in the AGENTS.md layout)
does **not** exist yet; there is no `services/` directory and no Polkit action in this repository.
Until it does, nothing in the product performs a privileged action on the user's behalf. Read-only
inspection (`hscl doctor`) never needs root and reports `skip`/`unknown` for values it cannot read
rather than guessing.
