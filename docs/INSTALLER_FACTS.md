# Installer facts (measured in a booted live image)

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
  Argon2; Calamares failing with more than one LUKS volume). *Whether the installed system actually boots and unlocks is not yet tested (P2.4).*
- `showNotEncryptedBootMessage: false`: the installer does not warn that `/boot` is unencrypted. HSCL1 must show its own, localised explanation
  (P2.1) - until then this is an honest gap in the installer UX.
- `settings.conf` runs `luksbootkeyfile` in the exec sequence. **Risk to check in P2.4:** with an unencrypted `/boot`, a LUKS keyfile that ends up inside the
  initramfs would let anyone with disk access unlock the root. Gate: after the encrypted install, `lsinitramfs /boot/initrd.img-*` contains no keyfile,
  `/etc/crypttab` names no key file for the root volume, and boot asks for the passphrase.
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
