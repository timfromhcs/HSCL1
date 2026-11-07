# Known limitations (truthful list)

Status of this document: maintained with every phase. Last update: 2026-11-06 (research round, release `0.1.2-alpha.0`).

HSCL1 is **pre-alpha**. Nothing below has been tested on physical hardware. Rows are corrected whenever an earlier status turns out to
be stale - a limitation list that lags behind reality is a false claim in the other direction.

| Area | Status | Limitation |
|---|---|---|
| Bootable ISO | VM-VERIFIED (pre-alpha) | A remastered ISO boots to the HCS desktop in QEMU (UEFI, BIOS, Secure-Boot firmware). Not tested on physical hardware; not published; no release signatures yet. |
| Secure Boot | partially verified | The image boots under OVMF Secure-Boot firmware with Microsoft keys. The Secure Boot state inside the guest has not been read yet, so no Secure Boot claim is made. |
| Installer | VM-VERIFIED (pre-alpha) | Upstream Kubuntu Calamares **3.3.14** (from `resolute-updates`) installs to a 40 GiB virtual disk; the installed system boots and logs in. Offline install works. **Not done:** installer fault injection, branding of every Calamares page, dual-boot, physical disks. Two upstream defects are documented below. |
| LUKS2 | VM-VERIFIED (pre-alpha) | Automated Erase-disk + Encrypt install on a disposable disk; installed system boots, wrong passphrase is rejected, correct one reaches the desktop; `aes-xts-plain64`/`argon2id`, no keyfile in `crypttab`, initrd or `/`; marker passphrase absent from the scanned logs. **Not done:** recovery-key flow, TPM-backed unlock (not offered), Secure Boot combined with encryption, `/boot` and the initrd are unencrypted and not integrity-protected. |
| `hscl` CLI | TESTED (unit) | Implemented: `version`, `about`, `status`, `system info`, `security status`, `ai detect`, `doctor`. Not yet run on an installed HSCL1 system. |
| Security Lab | PLANNED | No container tooling exists yet. Kali tools will only ever run in isolated rootless containers or VMs. |
| Privacy mode | PLANNED | HSCL1 is **not Tails** and makes no anonymity claim. |
| Local AI | partially verified | Hardware detection, model catalogue, download with sha256 check and a CPU chat completion with one 2B model are verified on the builder. Vulkan/GPU, MTP and TurboQuant are NOT verified. |
| Hardware | none verified | No device is listed as supported. |
| Languages | partial | Handbook (EN/DE/FR) and Control Center strings (EN/DE/FR) exist; installer, boot menu and desktop defaults are still English/Kubuntu. |
| Test environment | note | `/dev/kvm` is present in the WSL2 build lab since 2026-11-06 (earlier plan text said otherwise), but the automated install gates still run under WHPX/TCG for Secure Boot coverage, so they remain slow. |
| Trademarks | rules encoded, human review pending | `docs/TRADEMARKS.md` + `scripts/check_trademarks.py` enforce the mechanical part of OffSec's policy (symbol + attribution sentence on first mention, no modified/combined mark, no mark in a domain name) and forbid Kali/Tails logos and "HSCL1 Tails"/"HSCL1 Kali Edition" wording. Legal review of the derivative-distribution naming and of Canonical's IP policy is still **owner work**. |
| Window tiling | PLANNED (honest wording) | KWin does not persist custom tile layouts (KDE bug 466019) and loses them on monitor changes. HSCL1 plans reviewed **presets** written into `kwinrc` and re-applied after a monitor change, but neither the presets nor a layout subcommand exist yet (plan W5.5) - until they do, nothing in the desktop offers "saved layouts". |
| Flatpak | not installed by default | The base does not ship Flatpak (Canonical asked the flavours to stop). It is a documented opt-in switch in the Control Center; any Flatpak application is the user's own choice and its sandbox is not verified by us. |
| Installer, multiple encrypted disks | upstream defect, not worked around | Calamares 3.3.14 is reported not to finish when more than one LUKS device is involved. HSCL1 will refuse and explain rather than pretend; the fault-injection gate records the behaviour. |
| Installer, unreachable apt source | upstream defect, mitigated by testing | Calamares can crash in the software-db step when a source is unreachable (LP #2143847). The offline install is the primary tested path. |
| Virtual-machine screenshot share | unverified | The WSL2 host kernel has the 9p client (`/proc/filesystems` shows `nodev 9p`), but the virtio transport and the guest-side mount have not been proven yet; the visual-QA harness falls back to virtiofs or serial-console capture. |
| Neural Lab | PLANNED | No demo, Game Studio or workspace exists yet. Scope is deliberately small (neural cellular automaton, tiny-net trainer, toy frame predictor, grammar-validated game specs); nothing here is a neural game engine, and GameNGen/Genie 3 scale is out of reach on this hardware. |
| Release signing | not in place | Releases carry SHA256SUMS only; no signing key exists yet. |
| Network contacts inherited from the base | disclosed, not changed | With a network present, the installer contacts `networkcheck.kde.org` (connectivity check) and `geoip.ubuntu.com` (mirror choice); the installed system keeps the base defaults: time sync against `ntp.ubuntu.com` (chrony), package archives at `archive.ubuntu.com`, and the update-manager release check at `changelogs.ubuntu.com`. HSCL1 adds no telemetry of its own. Whether and how to replace these defaults is an open policy decision. |
| Live session names | VM test pending | The live session user and host name come from the first word of `/.disk/info` on the medium, which the image build sets to `HSCL1` (casper turns it into `hscl1`). Setting `FLAVOUR` in `/etc/casper.conf` instead broke the live boot (dev image r5) and is not used. Verified only after the VM test of the build that contains it. |
