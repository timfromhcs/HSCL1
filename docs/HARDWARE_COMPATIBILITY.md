# Hardware compatibility

**No physical hardware has been verified.** This page exists so that the absence of evidence is
visible instead of implied by a compatibility list. Do not read the tables below as support
statements; read the "Status" column.

## Verified

| Component | Status | Evidence |
|---|---|---|
| QEMU/KVM and QEMU/WHPX virtual machines | `VM-VERIFIED` | live desktop, installation, LUKS2 unlock, in-guest QA report, Security Lab chain — see `BUILD_LOG.md` |
| OVMF/edk2 UEFI firmware | `VM-VERIFIED` | boots to the desktop at 4 GB |
| Legacy BIOS (SeaBIOS) | `VM-VERIFIED` | boots to the desktop |
| Secure Boot firmware | **NOT verified** | the ISO carries signed shim/GRUB/kernel components, but every test ran with Secure Boot **off**; the guest reports "This system doesn't support Secure Boot" |

## Not verified — expect problems

| Area | Why it is listed |
|---|---|
| Wi-Fi and Bluetooth | no radio was ever exercised; firmware packages are inherited from the base and untested |
| Suspend, resume, hibernation | never tested; the live session does not support hibernation by design |
| NVIDIA proprietary drivers | require module signing with Secure Boot and were never installed on hardware |
| Hybrid graphics / external GPUs | untested; `hscl graphics detect` reads sysfs but has not been validated on real devices |
| Printers and scanners | untested |
| Touchpads, touchscreens, pen input | untested |
| Cameras, fingerprint readers | untested |
| Thunderbolt, USB4, docking stations | untested |
| RAID, Intel RST/VMD | unsupported and untested; the installer sees one disk |
| TPM-backed disk unlocking | not offered; passphrase LUKS2 only |
| Secure Boot acceptance | not demonstrated (see above) |
| USB media boot | not demonstrated; the ISO is hybrid but only booted as a virtual CD |
| Dual boot with Windows | not tested; the installer does not offer a verified alongside-installation path |

## What "supported" would require

A device may only be listed as supported after, on that exact model:

1. the ISO boots to the live desktop with the firmware in its default configuration;
2. the installer completes on a disposable disk and the installed system reboots;
3. audio, network, display, suspend/resume and the input devices work after the reboot;
4. the results are recorded here with the model, firmware version and date.

Anything else is "it booted on someone's machine", which is not a compatibility claim.

## Reporting

`hscl hw detect` prints the inventory the project needs (CPU features, GPUs, memory, firmware and
Secure Boot state) without root. `hscl report` writes a support file with user, host, MAC and private
IP redacted. Attach that instead of a screenshot of the whole system.
