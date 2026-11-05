# Known limitations (truthful list)

Status of this document: maintained with every phase. Last update: Phase 1 (2026-11-05).

HSCL1 is **pre-alpha**. Nothing below has been tested on physical hardware.

| Area | Status | Limitation |
|---|---|---|
| Bootable ISO | VM-VERIFIED (pre-alpha) | A remastered ISO boots to the HCS desktop in QEMU (UEFI, BIOS, Secure-Boot firmware). Not tested on physical hardware; not published; no release signatures yet. |
| Secure Boot | partially verified | The image boots under OVMF Secure-Boot firmware with Microsoft keys. The Secure Boot state inside the guest has not been read yet, so no Secure Boot claim is made. |
| Installer | VM-VERIFIED (earlier QA build) | Upstream Kubuntu Calamares installs to a 40 GiB virtual disk and the installed system boots (see `docs/CLAIMS.md`). Installer branding, LUKS2 and fault-injection are not done; no physical-disk install was ever performed. |
| LUKS2 | PLANNED | Not tested. TPM-backed unlock is not offered. |
| `hscl` CLI | TESTED (unit) | Implemented: `version`, `about`, `status`, `system info`, `security status`, `ai detect`, `doctor`. Not yet run on an installed HSCL1 system. |
| Security Lab | PLANNED | No container tooling exists yet. Kali tools will only ever run in isolated rootless containers or VMs. |
| Privacy mode | PLANNED | HSCL1 is **not Tails** and makes no anonymity claim. |
| Local AI | partially verified | Hardware detection, model catalogue, download with sha256 check and a CPU chat completion with one 2B model are verified on the builder. Vulkan/GPU, MTP and TurboQuant are NOT verified. |
| Hardware | none verified | No device is listed as supported. |
| Languages | partial | Handbook (EN/DE/FR) and Control Center strings (EN/DE/FR) exist; installer, boot menu and desktop defaults are still English/Kubuntu. |
| Test environment | note | No `/dev/kvm` in the development WSL2 instance, so VM tests use software emulation (slow). |
| Trademarks | review pending | Compliance of the derivative-distribution naming and the unmodified Ubuntu/Kubuntu base with Canonical's trademark and IP policy has not been reviewed. |
| Release signing | not in place | Releases carry SHA256SUMS only; no signing key exists yet. |
