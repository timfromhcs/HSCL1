# Known limitations (truthful list)

Status of this document: maintained with every phase. Last update: Phase 1 (2026-11-05).

HSCL1 is **pre-alpha**. Nothing below has been tested on physical hardware.

| Area | Status | Limitation |
|---|---|---|
| Bootable ISO | VM-VERIFIED (pre-alpha) | A remastered ISO boots to the HCS desktop in QEMU (UEFI, BIOS, Secure-Boot firmware). Not tested on physical hardware; not published; no release signatures yet. |
| Secure Boot | partially verified | The image boots under OVMF Secure-Boot firmware with Microsoft keys. The Secure Boot state inside the guest has not been read yet, so no Secure Boot claim is made. |
| Installer | PLANNED | Upstream Kubuntu Calamares is the candidate. No HSCL1 install has been performed. |
| LUKS2 | PLANNED | Not tested. TPM-backed unlock is not offered. |
| `hscl` CLI | TESTED (unit) | Implemented: `version`, `about`, `status`, `system info`, `security status`, `ai detect`, `doctor`. Not yet run on an installed HSCL1 system. |
| Security Lab | PLANNED | No container tooling exists yet. Kali tools will only ever run in isolated rootless containers or VMs. |
| Privacy mode | PLANNED | HSCL1 is **not Tails** and makes no anonymity claim. |
| Local AI | PLANNED | Only hardware *detection* exists; GPU acceleration is never reported as verified without a smoke test. |
| Hardware | none verified | No device is listed as supported. |
| Languages | partial | Handbook (EN/DE/FR) and Control Center strings (EN/DE/FR) exist; installer, boot menu and desktop defaults are still English/Kubuntu. |
| Test environment | note | No `/dev/kvm` in the development WSL2 instance, so VM tests use software emulation (slow). |
