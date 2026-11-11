# Running HSCL1 in a virtual machine

These are the settings the automated tests use. Everything on this page was measured in a VM;
nothing here is a statement about physical hardware (see [`HARDWARE_COMPATIBILITY.md`](HARDWARE_COMPATIBILITY.md)).

## Tested settings

| Setting | Value |
|---|---|
| Hypervisor | QEMU 11.1 on Windows with WHPX; QEMU with KVM on Linux; software emulation (TCG) where no accelerator was available |
| Firmware | UEFI (OVMF/edk2) — the default; legacy BIOS (SeaBIOS) also reached the desktop |
| Memory | 4 GB for an unencrypted install; **8 GB** for a LUKS2 install (a 6 GB run panicked once) |
| CPUs | 4 |
| Display | standard VGA, software rendering; HSCL1 detects it and turns animations and blur off |
| Network | user-mode (NAT) with a virtio NIC; no port forwarding is needed |
| Install disk | one empty 40 GB virtio disk in qcow2, created for the test only |
| Medium | the hybrid ISO attached as a CD-ROM |

## Quick start with the harness

The repository ships a harness that boots the ISO, clicks through the live prompt, dismisses the
Welcome Center and writes evidence (screenshots, a result JSON and optionally an in-guest report):

```console
$ python scripts/qemu_boot_test.py HSCL1-<version>-amd64.iso artifacts/boot-try \
    --firmware uefi --try-live --dismiss-welcome --mem 4096
```

Useful options:

| Option | Effect |
|---|---|
| `--firmware bios` | boot with SeaBIOS instead of OVMF |
| `--secure-boot` | boot the OVMF Microsoft-key variant — the guest still reports the actual state |
| `--disk PATH --disk-size 40G` | attach (and create) a disposable qcow2 for an install test |
| `--steps FILE.json` | run a scenario (`wait`, `keys`, `type`, `click`, `dclick`, `shot`) after the desktop appears |
| `--qa-out FILE` | attach the `hscl.qa` virtio port and write the machine-readable in-guest report |
| `--qmp-port N` | pin the QMP port; the default `0` lets the OS pick a free one |
| `--no-mem-guard` | skip the "VM size + 1.5 GB free" check (do not use it on a busy host) |

## Plain QEMU commands

Linux with KVM:

```console
$ qemu-system-x86_64 -enable-kvm -m 4096 -smp 4 \
    -bios /usr/share/ovmf/OVMF.fd \
    -cdrom HSCL1-<version>-amd64.iso \
    -vga std -device virtio-net-pci,netdev=net0 -netdev user,id=net0
```

Windows with WHPX (the harness builds an equivalent command, including the `q35` machine type and
UEFI variables):

```powershell
& "C:\Program Files\qemu\qemu-system-x86_64.exe" -machine q35 -accel whpx,kernel-irqchip=off `
  -m 4096 -smp 4 -vga std `
  -drive file=HSCL1-<version>-amd64.iso,media=cdrom,readonly=on `
  -device virtio-net-pci,netdev=net0 -netdev user,id=net0
```

## Install test on a disposable disk

```console
$ python scripts/qemu_boot_test.py HSCL1-<version>-amd64.iso artifacts/install-test \
    --firmware uefi --try-live --dismiss-welcome --disk artifacts/vdisks/t.qcow2 --disk-size 40G \
    --steps tests/visual/scenarios/install-normal.json
```

Then boot the disk **without** the ISO and log in:

```console
$ python scripts/qemu_boot_test.py "" artifacts/installed-boot \
    --disk artifacts/vdisks/t.qcow2 --boot-wait 40 --login-password '<the password you typed>'
```

Never attach a disk that contains data you care about: the installer erases the disk it is given, and
the harness has no undo.

## Encrypted install

Use 8 GB and the same flow, then unlock the disk at the boot prompt:

```console
$ python scripts/qemu_boot_test.py "" artifacts/luks-boot --disk artifacts/vdisks/luks.qcow2 \
    --unlock-passphrase '<the passphrase>' --unlock-first-wrong
```

`--unlock-first-wrong` types a wrong passphrase first and captures the refusal, which is the part of
the LUKS2 claim that is easy to fake and therefore worth recording.

## Troubleshooting

| Symptom | Cause | Fix |
|---|---|---|
| `refusing to start: N MB free, need M MB` | host memory is held by WSL or another VM | `wsl --shutdown`, close the other VM, or raise the host's free memory |
| `Failed to find an available port` in `qemu.log` | another QEMU already owns QMP 4444 | use `--qmp-port 0` (default) or an explicit free port |
| Black screen for minutes | no hardware acceleration or 3 GB or less RAM | check `-accel whpx`/`-enable-kvm`; give the VM 4 GB |
| Installer window disappears | the intermittent startup fault (Q-61) | the shipped launcher retries; read `/tmp/hscl-calamares.log` in the guest |
| `Secure Boot: unknown` in `hscl doctor` | the firmware has Secure Boot off | expected; the signed components are in the ISO, but acceptance is untested |

The harness refuses to start without the memory headroom, and it exits non-zero when the desktop is
not reached, so a failed run cannot be mistaken for a quiet success.
