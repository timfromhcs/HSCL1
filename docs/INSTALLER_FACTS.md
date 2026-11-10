# Installer facts (measured in a booted live image)

## RAM: 4 GB for the plain install, 8 GB for the encrypted one (2026-11-10)

Measured on `HSCL1-installer-fix` (`3e8ebce1…`), QEMU/WHPX, UEFI, disposable 40 GB qcow2:

| Install | RAM | Result |
|---|---|---|
| erase disk, ext4, no encryption | 4 GB | "All done", disk boots, `hscl doctor` 6 passed / 0 failed / 1 skipped |
| erase disk, LUKS2 | 6 GB | **kernel panic mid-write** (`Attempted to kill init! exitcode=0x0000000b`), one observation |
| erase disk, LUKS2 | 8 GB | "All done", disk unlocks and boots |

The 6 GB panic was not reproducible at 8 GB, and the same scenario had finished at 6 GB on an earlier candidate, so
this is documented as a RAM requirement rather than a hard defect. `scripts/dev/detect_panic.py DIR` flags the
purple crash frame, and the VM harness reports `panic_suspects` for every run.

Source: read-only probes in a QEMU/WHPX VM booting `HSCL1-dev-p2.iso` (sha256 `0eb7acb77f5dfd31ac9246b7a46a4cd7816c80cab214e5df46c535968be263ff`,
commit 3d89a43), evidence `artifacts/probe-baseline2/probe.json` (not in git). Date 2026-11-06. Nothing here was installed to a disk; these are
configuration facts, not an installation test.

## Calamares (Kubuntu 26.04 package, files under `/etc/calamares`)

`modules/partition.conf` in the image (the `hscl1_*` labels are ours, the structure is Kubuntu's):

```yaml
efiSystemPartition: "/boot/efi"
enableLuksAutomatedPartitioning: true
luksGeneration: luks2
userSwapChoices: [none, file]
initialSwapChoice: file
showNotEncryptedBootMessage: false
defaultFileSystemType: "ext4"
availableFileSystemTypes: ["ext4","btrfs","xfs"]
partitionLayout:
    - name: "hscl1_boot"      # unencrypted /boot, only present when encryption is chosen
      filesystem: ext4
      noEncrypt: true
      onlyPresentWithEncryption: true
      mountPoint: "/boot"
      size: 4G
    - name: "hscl1_root"
      filesystem: unknown
      mountPoint: "/"
      size: 100%
```

What this means (and what it does not prove):

- The automated "erase disk + encrypt" path already produces the layout the plan wants: ESP, a 4 GiB **unencrypted `/boot`**, one **LUKS2** root,
  swap as a **file** (so there is exactly one LUKS volume). This avoids the two failures reported for Kubuntu 26.04 (encrypted `/boot` + signed GRUB without
  Argon2; Calamares failing with more than one LUKS volume). *Update 2026-11-07: tested for one install of 0.1.3-alpha.0 in a VM - it boots, refuses a wrong passphrase and unlocks with the right one (BUILD_LOG, 'LUKS install on the exact 0.1.3-alpha.0 artefact').*
- `showNotEncryptedBootMessage: false` (stock). Since 2026-11-07 the live hook sets it to `true` and `verify-image.sh` checks the file. **Observed on the `0.1.3-dev2` image (VM, screenshots in `artifacts/dev2-installer/`): in the automatic "Erase disk + Encrypt system" path the setting has no visible effect** - no dialog on `Next`, no text on the Partitions page or the Summary. It probably applies to manual partitioning only (not verified). So the installer still does not explain the unencrypted `/boot` in the default path; a custom explanation (and a recovery-key explanation, AGENTS.md 6.3) remains an open gap. The setting is left on because it is harmless, tested as configuration, and may matter in the manual path.
- `settings.conf` runs `luksbootkeyfile` in the exec sequence. **Risk to check in P2.4:** with an unencrypted `/boot`, a LUKS keyfile that ends up inside the
  initramfs would let anyone with disk access unlock the root. Gate: after the encrypted install, `lsinitramfs /boot/initrd.img-*` contains no keyfile,
  `/etc/crypttab` names no key file for the root volume, and boot asks for the passphrase.
  **Result for that one install (offline read of the test disk, no passphrase used):** the unencrypted `/boot` holds `initrd.img-7.0.0-30-generic` (93,926,537 bytes); `lsinitramfs | grep -i keyfile` is empty; the `cryptroot/crypttab` inside the initramfs reads `luks-<uuid> UUID=<uuid> none` (passphrase prompt, no key file); the root LUKS2 header (read directly from the partition) has **exactly one keyslot** (argon2id, 688,611 KiB memory, time 4, 4 CPUs, 64-byte key, `aes-xts-plain64`, sector 512) and no tokens. So no keyfile slot was added and none is in the initramfs. Not covered: whether `/crypto_keyfile.bin` exists inside the encrypted root, other installs (btrfs, swap choices), and low-RAM machines (the Argon2id memory cost of about 672 MiB was chosen on a 4 GB VM; a small machine may fail to unlock).
- Manual partitioning is still available in the stock config; the plan documents only the automated path as supported.

## GRUB / Secure Boot chain in the image

| Item | Value |
|---|---|
| GRUB | 2.14 (`grub-install 2.14-2ubuntu2.1`), signed package `grub-efi-amd64-signed 1.215+2.14-2ubuntu1`, `shim-signed 1.59+15.8-0ubuntu2` |
| EFI files on the ISO | `/EFI/boot/bootx64.efi` (shim), `grubx64.efi`, `mmx64.efi` |
| Signed GRUB contents (grep counts) | `luks2` 1, `cryptodisk` 10, `pbkdf2` 4, **`argon` 0** -> GRUB can open LUKS2 only with PBKDF2 keyslots; irrelevant while `/boot` is unencrypted |
| GRUB modules available in the image | `luks`, `luks2`, `cryptodisk`, `argon2`, `pbkdf2` (the `argon2` module exists as a file but is not inside the signed binary) |
| Secure Boot state in this VM | not enabled (firmware without Secure Boot); this is not a Secure Boot test (see P2.7) |

## Other measured facts used by the plan

- 304 files owned by `hscl-*` packages were checked in the booted image: **0** group- or world-writable (P1.2).
- Diversions in place: KDE Connect autostart and D-Bus service (originals under `/usr/share/hscl/diverted/`), branding files.
- Podman candidates could not be read: the guest's apt package lists are stale/empty (71 days). Package availability must be checked on the builder (P4.0).
