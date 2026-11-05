# Known limitations (truthful list)

Status of this document: maintained with every phase. Last update: Phase 1 (2026-11-05).

HSCL1 is **pre-alpha**. Nothing below has been tested on physical hardware.

| Area | Status | Limitation |
|---|---|---|
| Bootable ISO | PLANNED | No HSCL1 ISO exists yet. Only the upstream Kubuntu ISO has been downloaded and verified. |
| Secure Boot | PLANNED | Unknown until a remastered image is booted with OVMF Secure Boot. No claim is made. |
| Installer | PLANNED | Upstream Kubuntu Calamares is the candidate. No HSCL1 install has been performed. |
| LUKS2 | PLANNED | Not tested. TPM-backed unlock is not offered. |
| `hscl` CLI | TESTED (unit) | Implemented: `version`, `about`, `status`, `system info`, `security status`, `ai detect`, `doctor`. Not yet run on an installed HSCL1 system. |
| Security Lab | PLANNED | No container tooling exists yet. Kali tools will only ever run in isolated rootless containers or VMs. |
| Privacy mode | PLANNED | HSCL1 is **not Tails** and makes no anonymity claim. |
| Local AI | PLANNED | Only hardware *detection* exists; GPU acceleration is never reported as verified without a smoke test. |
| Hardware | none verified | No device is listed as supported. |
| Languages | PLANNED | EN/DE/FR coverage not yet implemented in any UI. |
| Test environment | note | No `/dev/kvm` in the development WSL2 instance, so VM tests use software emulation (slow). |
