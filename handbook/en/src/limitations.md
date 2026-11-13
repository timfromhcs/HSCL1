# Known limitations

- Pre-alpha: nothing has been tested on physical hardware. Everything below was measured in virtual machines
  (UEFI, QEMU/KVM or WHPX).
- The release artefacts are **not signed**; only SHA-256 checksums are published.
- Secure Boot is read inside the guest (`mokutil --sb-state`, `hscl doctor`), but a positive Secure-Boot boot has
  not been demonstrated: this host cannot enter SMM under WHPX or WSL/KVM. No Secure-Boot claim is made.
- The installer's startup crash (a segfault in the notes step while the progress tree painted it) is fixed since
  0.1.8. `/usr/bin/hscl-calamares` still restarts a wizard that dies within its first minute, as a precaution.
- `hscl` (version, status, doctor, themes, wallpapers, privacy status, lab commands, AI detection) and the Control
  Center (**eleven read-only pages**: Overview, Appearance, Security, Privacy, Security Lab, Local AI, Updates &
  Recovery, Developer, Language & Region, Miner, About) are implemented. Applying a theme is the only action the
  panel performs; everything that changes the system stays on the command line. The Security Lab and the Privacy
  workflow are still **command-line workflows**, not separate desktop modes.
- The Security Lab runs tools in rootless Podman containers. GUI tools, wireless/USB passthrough and disposable VM
  profiles are not provided.
- The Privacy mode is **not Tails**: there is no verified network kill switch and no encrypted persistent storage.
- The Welcome Center opens the HSCL1 page when it is launched from the menu; a fresh install logs in to the bare
  HSCL1 desktop, because the state file is pre-seeded so the KDE tour does not appear.
- Two-line desktop icon labels are centred under their icon (measured within 1 px); the earlier note about a
  left-shifted second line was an impression from the rendered image, not a measurement.
- German and French follow the English structure chapter by chapter.
