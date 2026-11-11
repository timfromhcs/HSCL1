# Known limitations

- Pre-alpha: nothing has been tested on physical hardware. Everything below was measured in virtual machines
  (UEFI, QEMU/KVM or WHPX).
- The release artefacts are **not signed**; only SHA-256 checksums are published.
- Secure Boot has not been verified for HSCL1 images.
- The installer occasionally dies 2-3 s after it starts (roughly one start in six to twelve) and is then restarted
  by `/usr/bin/hscl-calamares`. On images without that wrapper, start it again - the next attempt usually works.
- `hscl` (version, status, doctor, themes, wallpapers, privacy status, lab commands, AI detection) and the Control
  Center (Overview, Appearance, Security, Miner, About) are implemented. The Security Lab and the Privacy workflow
  are **command-line workflows**, not separate desktop modes.
- The Security Lab runs tools in rootless Podman containers. GUI tools, wireless/USB passthrough and disposable VM
  profiles are not provided.
- The Privacy mode is **not Tails**: there is no verified network kill switch and no encrypted persistent storage.
- The Welcome Center shows only the HSCL1 page when it is opened from the menu; what an installed system does at
  the first login has not been verified.
- A desktop icon with a two-line name wraps its second line to the left of the icon centre.
- German and French follow the English structure chapter by chapter.
