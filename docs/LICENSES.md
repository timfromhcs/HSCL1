# Licences and attributions

## HSCL1-owned work

Code, scripts, packaging, themes, logos, wallpapers, the Workshop, the handbook and documentation in this repository are
licensed **GPL-3.0-or-later** (see [`LICENSE`](../LICENSE) and [`NOTICE`](../NOTICE)). Copyright (C) 2026 HCSMEDIA.

## Distributed images (ISO)

An HSCL1 ISO is a remaster of the official **Kubuntu 26.04.1** live image plus HSCL1 packages. It contains thousands of
third-party packages, each under its own licence (GPL, LGPL, MIT, BSD, Apache-2.0, proprietary firmware where Ubuntu ships it).
Their copyright files are kept inside the image under `/usr/share/doc/<package>/copyright`.

**Source availability (GPL).** Corresponding source for the Ubuntu packages is published by Ubuntu
(<https://archive.ubuntu.com/ubuntu/>, <https://launchpad.net/ubuntu>). Two packages are added to the image from the Ubuntu
archive at build time (`earlyoom`, `systemd-zram-generator`); their versions are recorded in the build manifest. The source of all
HSCL1-owned components is this repository. If you need a specific source package and cannot get it from Ubuntu, open an issue.

## Third-party components referenced by this repository

| Component | Use | Licence | Notes |
|---|---|---|---|
| Kubuntu / Ubuntu 26.04 | image base | various (mainly GPL/LGPL) | Canonical and Ubuntu are trademarks of Canonical Ltd. |
| KDE Plasma / Frameworks / Qt 6 | desktop | GPL/LGPL/LGPLv3 (Qt) | |
| Calamares | installer | GPL-3.0-or-later | |
| llama.cpp (pinned release b12130, downloaded on demand) | local inference | MIT | not shipped in the ISO; sha256 pinned in `ai/backends/llama.json` |
| Model weights in `ai/catalog/models.json` | downloaded by the user on request | per model (the catalogued ones: Apache-2.0 as reported by Hugging Face) | never bundled; abliterated variants carry a warning; licences must be re-checked before each addition |
| earlyoom | OOM guard | MIT | from the Ubuntu archive |
| systemd-zram-generator | zram swap | MIT | from the Ubuntu archive |
| mdBook | builds the handbook | MPL-2.0 | build-time tool |

Entries marked "not confirmed" in the HCS Coder catalogue stay gated in the UI until the licence is verified.

## Trademarks and endorsement

HSCL1 is not endorsed by Canonical, the KDE or Kubuntu projects, Offensive Security or the Tails project. No Apple, Microsoft,
Omarchy, Kali or Tails artwork is used. Whether the name "Kubuntu"/"Ubuntu" in the project description and the unmodified
base packages comply with Canonical's trademark and IP policy for derivative distributions has **not yet been reviewed**; this is
tracked in [`KNOWN_LIMITATIONS.md`](KNOWN_LIMITATIONS.md).
