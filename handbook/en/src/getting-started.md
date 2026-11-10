# Getting started

## Try it in a virtual machine

Use QEMU with UEFI firmware (OVMF/edk2) or legacy BIOS. Tested settings (pre-alpha):

| Setting | Value |
|---|---|
| Memory | 4 GB |
| CPUs | 4 |
| Graphics | standard VGA, no 3D |
| Network | user-mode (NAT) |

The live desktop appears after about two minutes on an accelerated host. Choose **Try or Install HSCL1** in the boot menu.

## Installing

The installer is **HSCL1 Installer**, a branded Calamares. It needs a disk you are willing to erase:
**use a disposable virtual disk.**

- **Unencrypted install:** verified with **4 GB** RAM (ESP + ext4 root, finishes with "All done").
- **LUKS2 encrypted install:** give the VM **8 GB** RAM. A 6 GB attempt panicked once; 8 GB is the documented figure.
- The system partition is encrypted with LUKS2 and you type the passphrase at every boot. The EFI partition and a
  separate `/boot` stay readable without it. There is **one** passphrase and **no recovery key**: if you forget it,
  the data cannot be recovered.

The installer writes to the disk you select. It does not offer a verified dual-boot setup, and it has not been
tested on physical hardware.
