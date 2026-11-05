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
