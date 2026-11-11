# Installing HSCL1

**Status: pre-alpha.** HSCL1 has only been installed in virtual machines. Nothing in this guide has
been verified on physical hardware, and no USB stick has been booted. Treat every step on a real
machine as untested, and **never** point the installer at a disk that holds data you need.

For the tested virtual-machine path see [`VM_GUIDE.md`](VM_GUIDE.md); the installer's own facts
(Calamares version, module behaviour, the two upstream defects) are in
[`INSTALLER_FACTS.md`](INSTALLER_FACTS.md).

## What you need

| Item | Minimum | Notes |
|---|---|---|
| CPU | x86_64 | UEFI recommended; BIOS boot also reached the desktop in a VM |
| RAM (live session) | 4 GB | the live ISO unpacks a squashfs into RAM; below ~3 GB the session dies |
| RAM (encrypted install) | 8 GB | a 6 GB LUKS run panicked once in a VM; the unencrypted install succeeded at 4 GB |
| Disk | 40 GB | 64 GB or more is comfortable; the whole disk is used |
| Medium | 6 GB USB stick | the ISO is ~4.7 GB (xz) |

## Write the ISO to a USB stick

Do this on a **spare** stick. Every tool below erases the selected device without asking twice.

1. Download the ISO and `SHA256SUMS` from the [release page](https://github.com/timfromhcs/HSCL1/releases)
   and verify the digest before writing anything:
   ```console
   $ sha256sum -c SHA256SUMS --ignore-missing
   ```
   The release ships the ISO split into parts; `scripts/release-join.sh` verifies and rejoins them.
2. **Windows:** use a writer that supports raw/DD mode (for example Rufus or balenaEtcher) and select
   the stick explicitly. If the tool offers "ISO mode" and "DD mode", choose **DD mode**: the image is
   a hybrid ISO.
3. **Linux:** the safe graphical route is a writer such as GNOME Disks or KDE's ISO writer. The command
   line is faster and more dangerous:
   ```console
   $ lsblk -o NAME,SIZE,MODEL,TRAN     # find the stick: it must NOT be your system disk
   $ sudo dd if=HSCL1-<version>-amd64.iso of=/dev/sdX bs=8M status=progress oflag=sync
   $ sync
   ```
   Replace `/dev/sdX` with the **whole device**, never a partition such as `/dev/sdX1`. A wrong letter
   destroys the wrong disk.
4. **macOS:** `diskutil list` to identify the device, `diskutil unmountDisk /dev/diskN`, then `dd` as
   above with `/dev/rdiskN`.

## Boot the stick

1. Open the firmware boot menu (usually F12, F11, F9 or Esc during power-on) and pick the USB device.
2. With Secure Boot enabled the firmware may refuse the image: the ISO carries signed shim/GRUB/kernel
   components, but **a boot with Secure Boot enabled has not been demonstrated** — the test firmware
   ran with Secure Boot off. Do not disable Secure Boot permanently just to try this; use a VM instead.
3. The boot menu offers a live session and the installer. "Try HSCL1" starts the live desktop.

## The installer

HSCL1 uses its own branded Calamares: **HSCL1 Installer**. The pages are Welcome → Location →
Keyboard → Customize → Notes → Partitions → Users → Summary → Install → Finish.

- **Notes** explains encryption before you choose a disk. Read it: there is **one passphrase and no
  recovery key**. If you forget it, the data cannot be recovered.
- **Partitions** offers *Erase disk* and *Manual partitioning*. There is no verified "install
  alongside another system" path; dual-boot is untested, and the installer will not preserve an
  existing EFI system partition for you.
- **Erase disk** writes to the disk you select. Check the model, size and device name on the page
  before continuing; the summary page repeats them.
- **Users** asks for a full name, a username, a hostname and a password. There is no cloud account and
  no telemetry.
- With **Encrypt system** ticked, the system partition becomes LUKS2 (Argon2id). The EFI partition and
  a separate `/boot` stay readable without the passphrase; they are not integrity-protected.
- **Install** writes the system. Do not close the window; a cancelled or killed install may leave a
  half-written disk.

The installer has an intermittent startup fault: in roughly one start in five to twelve it is killed
within the first seconds while building its first page. The shipped launcher retries up to three times
and writes to `/tmp/hscl-calamares.log`. If the wizard disappears, start it again — and if it keeps
disappearing, report it with that log (see [`KNOWN_LIMITATIONS.md`](KNOWN_LIMITATIONS.md), Q-61).

## After the first boot

1. Unlock the disk with the passphrase you chose (encrypted installs only).
2. Log in with the user you created.
3. Open a terminal and run:
   ```console
   $ hscl doctor
   ```
   Six checks should pass; the Secure Boot line reports what the firmware actually does instead of
   claiming success.
4. Read `hscl privacy status` and `hscl security status` before relying on either mode — they report
   the real state (swap, core dumps, automounted disks, Tor) rather than a promise.

## Recovery

- Forgot the passphrase: the data is gone. There is no recovery key.
- The system boots but the desktop does not: switch to a TTY (Ctrl+Alt+F3), log in, and read
  `journalctl -b -p err`.
- The live session still works from the stick; use it to copy data off an installed disk before
  attempting repairs.
- `hscl recovery status` and `hscl logs collect` produce a redacted report for a bug report.

## What this guide does not cover

Physical hardware validation, USB boot, Secure Boot acceptance, dual-boot with Windows, RAID, Intel
RST/VMD, TPM-backed unlocking, and suspend/resume are **not verified**. See
[`KNOWN_LIMITATIONS.md`](KNOWN_LIMITATIONS.md) and [`HARDWARE_COMPATIBILITY.md`](HARDWARE_COMPATIBILITY.md).
