# Troubleshooting

Everything here refers to behaviours that were observed on a real artifact, or to a command that
exists in `hscl`. Where a cause is unknown, it says so. Physical hardware is untested — see
[`KNOWN_LIMITATIONS.md`](KNOWN_LIMITATIONS.md) before blaming the system for a driver problem.

## First three commands

```console
$ hscl doctor                 # 6 checks: arch, memory, apparmor, firewall, apt sources, Secure Boot, theme
$ hscl status                 # kernel, memory, session type
$ hscl logs collect           # redacted bundle for a report (writes a file, never uploads)
```

`hscl doctor` exits non-zero when a check fails, so it is scriptable. A `[SKIP]` line is not a pass:
`secure-boot` is skipped when the firmware has no SecureBoot variable, which is exactly what a test VM
shows.

## Boot

| Symptom | Likely cause | What to do |
|---|---|---|
| Live session never reaches the desktop | fewer than ~3 GB RAM; the live ISO unpacks into RAM | give the VM 4 GB, or boot the installed system instead |
| "Please unlock disk luks-…" and the passphrase is rejected | wrong passphrase, or a non-US keyboard layout at that prompt | the prompt shows the layout (`US`); retype carefully, check Caps Lock |
| Unlock succeeds, then a black screen | GPU/driver or Wayland session failure | switch to a TTY (Ctrl+Alt+F3), log in, `journalctl -b -p err`, then `hscl logs collect` |
| Boot stops after GRUB | missing or damaged initrd | boot the live medium, mount the system, `update-initramfs -u -k all` inside a chroot |
| Firmware refuses to boot the USB stick | Secure Boot enabled | the signed components are present but acceptance is **untested**; do not disable Secure Boot permanently just to try a pre-alpha |

## Installer

| Symptom | Cause | Fix |
|---|---|---|
| The wizard disappears a few seconds after it opens | intermittent startup kill (Q-61): roughly 1 start in 6–12, no OOM, no core | the shipped launcher retries up to three times and logs to `/tmp/hscl-calamares.log`; start it again |
| The wizard never appears at all | it is a separate process started with `sudo` | run `sudo -b /usr/bin/calamares-launch-normal` from a terminal and watch the output |
| The disk is not listed | no disk attached, or the disk is claimed by RAID/Intel RST | attach an empty disk, or switch the firmware from RAID to AHCI |
| The encrypted install panics mid-write | observed once at 6 GB RAM | use **8 GB** for a LUKS2 install; the unencrypted install is fine at 4 GB |
| "An existing installation was found" but nothing is there | the disk has a leftover partition table | erase the disk from the live session, or pick another disk — do not proceed if you are unsure which disk it is |

The installer erases the disk you select. If you are not certain which device that is, stop: boot the
live session and check with `lsblk -o NAME,SIZE,MODEL,SERIAL`.

## Desktop

| Symptom | Cause | Fix |
|---|---|---|
| Desktop icon labels are slanted (0.1.5 and older) | Plasma draws a **symlink** desktop entry in italics (`font.italic: model.isLink`) | fixed in the tree (real files); in 0.1.5 the labels of the three seeded icons remain italic |
| An orange "!" badge sits on a desktop icon | Plasma marks a launcher **without the executable bit** as untrusted | fixed in the tree (entries installed `0755`); an existing system can run `chmod +x ~/Desktop/*.desktop` |
| A two-line label wraps left of its icon | upstream FolderView centres the text in the cell, not under the icon (Q-60) | cosmetic, no supported knob shipped yet; the "Label width" setting in *Desktop and Wallpaper → Icons* is the closest upstream control |
| Kate looks light although the shell is dark | a custom `katerc` or a colour scheme that is not Breeze Dark | `hscl appearance theme set HCSMidnight`; the image ships `/etc/skel/.config/katerc` with Breeze Dark |
| The Control Center does not open | its binary or QML is missing, or the CLI it shells out to is not installed | run `hscl-control-center` in a terminal and read the error; `hscl doctor` reports a missing theme |
| The Welcome Center opens on KDE's page | upstream: the intro pages are compiled into `plasma-welcome` | cosmetic; the HSCL1 page is one of the dots (Q-45) |

## Network, audio, Bluetooth

These are **unverified** on real hardware. On a VM they work through the emulated device.

```console
$ nmcli device status          # is the interface managed?
$ nmcli connection show
$ hscl security firewall status
```

- No Wi-Fi networks at all: the radio may be firmware-less (many Broadcom/Realtek parts need a
  proprietary blob). Nothing in HSCL1 installs firmware automatically.
- Audio silent: `wpctl status`, then check the default sink. In a VM, the emulated HDA device must be
  attached.
- Bluetooth: the service is enabled but no radio has been tested.

## Memory and performance

```console
$ hscl memory status           # RAM, zram, AI budget
$ hscl low-vram status         # caps animations/blur on weak GPUs
$ zramctl                      # compressed swap device
$ systemctl status earlyoom    # last-resort OOM handler
```

The live session runs from a RAM-backed overlay, so a 4 GB VM with a large install target can run out
of memory. Do not lower `earlyoom`'s limits to "make it fit"; give the VM more RAM.

## Security Lab

| Symptom | Cause | Fix |
|---|---|---|
| `hscl lab run` refuses an image | only digest-pinned references are accepted (`name@sha256:<64 hex>`), or a local `localhost/name:tag` produced by `hscl lab commit` | pull with the digest, or commit first |
| `podman: NOT installed` in `hscl privacy status` | the lab is opt-in | install `podman` and run `hscl lab setup`; nothing in the image does it for you |
| A tool inside the container cannot use raw sockets | `run` defaults to `--network=none` and drops capabilities | that is deliberate; use a VM profile for tools that need the host network |

## Reporting a bug

```console
$ hscl report --output /tmp/hscl-report.json
$ hscl logs collect
```

`hscl report` redacts user, host, MAC and private IP addresses by default; `--include-sensitive` is
the only way to include them, and it says so in the output. Attach the two files, the artifact hash
(`sha256sum` of the ISO or `HSCL1_*` from `/etc/os-release`) and the exact command.
