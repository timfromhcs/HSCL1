# HSCL1

**One system. Three modes. Your machine, your rules.**
*Made with love by hcsmedia* · Publisher: HCSMEDIA

HSCL1 is a Linux workstation built on **Ubuntu 26.04 LTS (Kubuntu base) and KDE Plasma 6**. It adds an original
design language (the *HCS Hybrid Desktop*: slim top bar plus floating dock), a command line tool (`hscl`), a Control
Center, an offline trilingual handbook (English, Deutsch, Français) and a conservative security baseline.

> **Status: pre-alpha (`0.1.0-alpha.0`).** No release has been published. The image boots in virtual machines only;
> nothing has been tested on physical hardware. Read [Known limitations](docs/KNOWN_LIMITATIONS.md) before trying it.

HSCL1 is **not Tails** and **not an official Kali release**, and it is not endorsed by Canonical, Offensive Security
or the Tails project. It makes no anonymity claim.

## What exists today (evidence in [`docs/BUILD_LOG.md`](docs/BUILD_LOG.md))

| Area | State |
|---|---|
| Bootable live/installer ISO (remastered Kubuntu 26.04.1) | boots in QEMU: UEFI, BIOS, Secure-Boot firmware; installer (Calamares) starts |
| HCS Hybrid Desktop (top bar, floating dock, HSCL1 themes) | first boot verified by screenshot |
| Four themes: Midnight, Light, Nord, Aurora (design tokens → wallpapers, Plasma colour schemes, QML) | unit-tested |
| `hscl` CLI: `version`, `about`, `status`, `doctor`, `report`, `system info`, `security status`, `ai detect`, `appearance theme …` | unit-tested |
| Control Center (Overview, Appearance, Security, About; EN/DE/FR) | unit-tested (C++/QML) |
| Handbook (EN/DE/FR, offline) | built and tested |
| Security baseline (sysctl hardening, first-boot firewall) | unit-tested; VM verification pending |
| Security Lab, Privacy mode, Local AI runtime, installer branding, LUKS2 tests | **not implemented / not verified yet** |

## Try it in a VM

Build host and steps: [`docs/BUILDING.md`](docs/BUILDING.md). Tested VM settings: 4 GB RAM, 4 vCPUs, standard VGA,
user-mode networking, UEFI (OVMF/edk2) or BIOS. **Installing writes to the selected disk. Use a disposable virtual disk.**

## Command line

```console
$ hscl --help
$ hscl status
$ hscl doctor
$ hscl appearance theme list
```

Full reference: [`docs/CLI.md`](docs/CLI.md).

## Documentation

- Handbook sources: [`handbook/en`](handbook/en/src), [`handbook/de`](handbook/de/src), [`handbook/fr`](handbook/fr/src)
- [Architecture](docs/ARCHITECTURE.md) · [Threat model](docs/THREAT_MODEL.md) · [Decisions](docs/DECISIONS.md) · [Testing](docs/TESTING.md)
- Product contract: [`AGENTS.md`](AGENTS.md)

## Licence

The repository owner has not chosen a licence yet, so **no licence is granted** until one is added. Third-party
components keep their own licences (Ubuntu, KDE, Qt, Calamares).
