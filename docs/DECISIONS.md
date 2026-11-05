# Decision records

## ADR-001 Image pipeline: scripted remaster of the official Kubuntu ISO (2026-11-05) - ACCEPTED
Context: AGENTS.md 2.6/7.2 asks for a PoC before committing. Result: the remastered Kubuntu 26.04.1 ISO boots under
UEFI and BIOS to a live Plasma desktop and launches the shipped installer (Calamares). Boot structure is replayed from the
original El Torito/GPT metadata. Secure Boot result pending (see BUILD_LOG).
Decision: keep the remaster pipeline; `livecd-rootfs` and Debian `live-build` remain fallbacks only.
Consequences: every branding change needs an in-image assertion (the first wallpaper patch was silently ineffective).
The installer is Calamares, so branding goes through `/etc/calamares/branding`.

## ADR-002 First stable release is v2.0.0 (2026-11-05) - ACCEPTED (user-directed)
The owner asked for "v2 stable". All AGENTS.md v1.0.0 gates apply to v2.0.0; failing a critical gate yields `v2.0.0-rc.N`.

## ADR-003 VM test host: Windows QEMU + WHPX (2026-11-05) - ACCEPTED
WSL has no /dev/kvm. WHPX boots in ~2 min; it lacks SMM, so Secure Boot tests use TCG.

## ADR-004 One main ISO with an opt-in, inert Workshop (2026-11-05) - ACCEPTED (owner request)
Context: earlier rule "no QA channel in release images" produced two ISOs and slow iteration. The owner wants one ISO with
install, live and QA functions plus an API/MCP for VM screenshots and an in-ISO mode to render the current state into a new
installer ISO ("respin").
Decision: package `hscl-workshop` ships in the main ISO and is **inert by default** (no enabled unit, no socket unit, no TCP
listener, no token baked in). It starts only when a hypervisor provides the virtio port `hscl.qa` / `hscl.api` (udev) or the
user runs `sudo hscl workshop enable`. Its API has a finite operation set (no arbitrary shell), allow-listed paths, a
session token. `verify-image.sh` fails the build if Workshop is enabled or exposes a socket; the ISO manifest attests
`workshop_default: disabled`; `make_release.py` refuses an ISO without that attestation.
Consequences: Workshop is documented in the threat model and limitations; respin output is labelled a development snapshot.
This replaces the earlier "no QA in release" rule.
