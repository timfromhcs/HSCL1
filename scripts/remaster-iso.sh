#!/usr/bin/env bash
# Remaster the verified Kubuntu 26.04.1 ISO into an HSCL1 pre-alpha ISO (Phase 2 proof of concept).
#
# Runs on an Ubuntu 26.04 builder (WSL2 or VM). Uses sudo only for unsquashfs/chroot/mksquashfs
# on a script-owned work directory. Never touches host disks.
#
# Usage: scripts/remaster-iso.sh --out ISO [--base-iso ISO] [--work DIR] [--fast] [--force]
set -Eeuo pipefail

root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
base="$HOME/hscl1-build/upstream/kubuntu-26.04.1-desktop-amd64.iso"
work="$HOME/hscl1-build/work"
out=""; fast=0; force=0
while [ $# -gt 0 ]; do
  case "$1" in
    --base-iso) base="${2:?}"; shift 2 ;;
    --work) work="${2:?}"; shift 2 ;;
    --out) out="${2:?}"; shift 2 ;;
    --fast) fast=1; shift ;;
    --force) force=1; shift ;;
    -h|--help) sed -n '2,9p' "$0"; exit 0 ;;
    *) echo "unknown argument: $1" >&2; exit 2 ;;
  esac
done
[ -n "$out" ] || { echo "--out is required" >&2; exit 2; }
[ "$(id -u)" -ne 0 ] || { echo "do not run as root; the script calls sudo where needed" >&2; exit 2; }
for c in xorriso mksquashfs unsquashfs dpkg-deb sudo sha256sum python3 cargo; do
  command -v "$c" >/dev/null || { echo "missing command: $c" >&2; exit 2; }
done
[ -f "$base" ] || { echo "base ISO not found: $base (run scripts/fetch-base-iso.sh)" >&2; exit 2; }
if [ -e "$out" ] && [ "$force" -ne 1 ]; then echo "refusing to overwrite $out (use --force)" >&2; exit 2; fi
mkdir -p "$work" "$(dirname "$out")"
free_kb=$(df --output=avail -k "$work" | tail -n 1)
[ "$free_kb" -gt 40000000 ] || { echo "need >= 40 GB free in $work" >&2; exit 2; }

version="$(tr -d '\n' < "$root/VERSION")"
rootfs="$work/rootfs-build"
cleanup() { :; }
trap cleanup EXIT

echo "== Plan =="
echo "base ISO : $base"
echo "work dir : $work"
echo "output   : $out"
echo "version  : $version  compression: $([ "$fast" -eq 1 ] && echo zstd-fast || echo xz)"

echo "== Verify base ISO checksum against upstream-signed SHA256SUMS =="
( cd "$(dirname "$base")" && sha256sum -c "$(basename "$base").sha256" )

echo "== Build hscl binary + HSCL1 packages =="
CARGO_TARGET_DIR="$work/target" cargo build --release --manifest-path "$root/Cargo.toml" -q
debdir="$work/debs"; rm -rf "$debdir"; mkdir -p "$debdir"
"$root/scripts/build-deb.sh" hscl-base "$debdir" --bin "$work/target/release/hscl" >/dev/null
"$root/scripts/build-deb.sh" hscl-branding "$debdir" >/dev/null
"$root/scripts/build-deb.sh" hscl-handbook "$debdir" >/dev/null
"$root/scripts/build-deb.sh" hscl-desktop "$debdir" >/dev/null
"$root/scripts/build-deb.sh" hscl-security "$debdir" >/dev/null
"$root/scripts/build-deb.sh" hscl-control-center "$debdir" >/dev/null
ls -l "$debdir"/*.deb

echo "== Unpack live root filesystem (fresh) =="
sudo rm -rf "$rootfs"
mkdir -p "$work/iso-files"
xorriso -osirrox on -indev "$base" -extract /casper/filesystem.squashfs "$work/iso-files/filesystem.squashfs" 2>/dev/null
sudo unsquashfs -f -d "$rootfs" "$work/iso-files/filesystem.squashfs" >/dev/null

echo "== Customise =="
sudo mkdir -p "$rootfs/tmp/hscl-debs"
sudo install -m 0644 "$debdir"/*.deb "$rootfs/tmp/hscl-debs/"
sudo chroot "$rootfs" sh -c 'dpkg -i /tmp/hscl-debs/hscl-base_*.deb /tmp/hscl-debs/hscl-branding_*.deb /tmp/hscl-debs/hscl-handbook_*.deb /tmp/hscl-debs/hscl-desktop_*.deb /tmp/hscl-debs/hscl-security_*.deb /tmp/hscl-debs/hscl-control-center_*.deb'
sudo rm -rf "$rootfs/tmp/hscl-debs"
sudo env ROOTFS="$rootfs" bash "$root/distro/live/hooks/010-hscl-defaults.sh"
echo "== Verify branding inside the image (fails the build if anything is missing) =="
sudo bash "$root/distro/live/verify-image.sh" "$rootfs"

echo "== Re-squash =="
new_sq="$work/iso-files/filesystem.new.squashfs"; sudo rm -f "$new_sq"
if [ "$fast" -eq 1 ]; then
  sudo mksquashfs "$rootfs" "$new_sq" -comp zstd -Xcompression-level 3 -b 131072 -noappend -quiet
else
  sudo mksquashfs "$rootfs" "$new_sq" -comp xz -b 131072 -Xbcj x86 -noappend -quiet
fi
sudo chown "$(id -u):$(id -g)" "$new_sq"

echo "== Patch boot menu label and checksum list =="
xorriso -osirrox on -indev "$base" -extract /boot/grub/grub.cfg "$work/iso-files/grub.cfg" \
  -extract /md5sum.txt "$work/iso-files/md5sum.txt" 2>/dev/null
chmod u+w "$work/iso-files/grub.cfg" "$work/iso-files/md5sum.txt"
sed -i 's/Try or Install Kubuntu/Try or Install HSCL1 (pre-alpha)/; s/"Kubuntu (safe graphics)"/"HSCL1 (safe graphics)"/' "$work/iso-files/grub.cfg"
sq_md5="$(md5sum "$new_sq" | cut -d' ' -f1)"; cfg_md5="$(md5sum "$work/iso-files/grub.cfg" | cut -d' ' -f1)"
sed -i "s#^[0-9a-f]\{32\}  ./casper/filesystem.squashfs\$#$sq_md5  ./casper/filesystem.squashfs#; s#^[0-9a-f]\{32\}  ./boot/grub/grub.cfg\$#$cfg_md5  ./boot/grub/grub.cfg#" "$work/iso-files/md5sum.txt"
grep -q "$sq_md5" "$work/iso-files/md5sum.txt" || { echo "md5sum.txt update failed" >&2; exit 1; }

echo "== Build ISO (replaying upstream boot structure) =="
rm -f "$out"
xorriso -indev "$base" -outdev "$out" -volid "HSCL1 ${version} amd64" \
  -boot_image any replay \
  -map "$new_sq" /casper/filesystem.squashfs \
  -map "$work/iso-files/grub.cfg" /boot/grub/grub.cfg \
  -map "$work/iso-files/md5sum.txt" /md5sum.txt \
  -commit 2>&1 | grep -vE '^(xorriso : UPDATE|Writing: )' | tail -n 12

echo "== Result =="
ls -l "$out"
sha256sum "$out" | tee "$out.sha256"
