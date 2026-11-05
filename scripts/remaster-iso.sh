#!/usr/bin/env bash
# Remaster the verified Kubuntu 26.04.1 ISO into the HSCL1 main ISO (live + installer + opt-in Workshop tools).
#
# Runs on an Ubuntu 26.04 builder (WSL2 or VM). Uses sudo only for unsquashfs/mount/chroot/mksquashfs
# on a script-owned work directory. Never touches host disks.
#
# Usage: scripts/remaster-iso.sh --out ISO [--base-iso ISO] [--work DIR] [--fast] [--force]
#   --fast   quick zstd compression for development (default: xz)
#
# Engine: the pristine unpacked base filesystem is cached (keyed by the base ISO checksum) and customised through
# an overlayfs, so repeated builds skip the unpack; mksquashfs runs with bounded memory; a memory guard refuses
# to start when free memory is too low. There is a single output: the main ISO.
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
    -h|--help) sed -n '2,12p' "$0"; exit 0 ;;
    *) echo "unknown argument: $1" >&2; exit 2 ;;
  esac
done
[ -n "$out" ] || { echo "--out is required" >&2; exit 2; }
[ "$(id -u)" -ne 0 ] || { echo "do not run as root; the script calls sudo where needed" >&2; exit 2; }
for c in xorriso mksquashfs unsquashfs dpkg-deb sudo sha256sum python3 cargo mount; do
  command -v "$c" >/dev/null || { echo "missing command: $c" >&2; exit 2; }
done
[ -f "$base" ] || { echo "base ISO not found: $base (run scripts/fetch-base-iso.sh)" >&2; exit 2; }
if [ -e "$out" ] && [ "$force" -ne 1 ]; then echo "refusing to overwrite $out (use --force)" >&2; exit 2; fi

# Memory guard: a build that starves the host gets the whole session reaped.
avail_mb=$(awk '/MemAvailable/ {print int($2/1024)}' /proc/meminfo)
min_mb="${HSCL_MIN_FREE_MB:-3000}"
if [ "$avail_mb" -lt "$min_mb" ]; then
  echo "only ${avail_mb} MB memory available (need ${min_mb} MB). Close VMs/apps, run 'wsl --shutdown' from Windows," >&2
  echo "or lower HSCL_MIN_FREE_MB on purpose." >&2
  exit 2
fi
mkdir -p "$work" "$(dirname "$out")"
free_kb=$(df --output=avail -k "$work" | tail -n 1)
[ "$free_kb" -gt 30000000 ] || { echo "need >= 30 GB free in $work" >&2; exit 2; }

version="$(tr -d '\n' < "$root/VERSION")"
pristine="$work/pristine"
ovl="$work/overlay"; merged="$ovl/merged"
cleanup() {
  mountpoint -q "$merged" 2>/dev/null && sudo umount "$merged" || true
  sudo rm -rf "$ovl/up" "$ovl/wk" 2>/dev/null || true
}
trap cleanup EXIT

echo "== Plan =="
echo "base ISO : $base"
echo "work dir : $work   (memory available: ${avail_mb} MB)"
echo "output   : $out"
echo "version  : $version  compression: $([ "$fast" -eq 1 ] && echo zstd-fast || echo xz)"

echo "== Verify base ISO checksum against upstream-signed SHA256SUMS =="
( cd "$(dirname "$base")" && sha256sum -c "$(basename "$base").sha256" )
base_sha="$(cut -d' ' -f1 "$base.sha256")"

echo "== Build hscl binary + HSCL1 packages =="
CARGO_TARGET_DIR="$work/target" cargo build --release --manifest-path "$root/Cargo.toml" -q
debdir="$work/debs"; rm -rf "$debdir"; mkdir -p "$debdir"
"$root/scripts/build-deb.sh" hscl-base "$debdir" --bin "$work/target/release/hscl" >/dev/null
for p in hscl-branding hscl-handbook hscl-desktop hscl-security hscl-control-center hscl-workshop hscl-memory; do
  "$root/scripts/build-deb.sh" "$p" "$debdir" >/dev/null
done
# Third-party packages from the Ubuntu archive (signed by apt; MIT licensed): memory protection tools the image does not ship.
( cd "$debdir" && apt-get download earlyoom systemd-zram-generator >/dev/null )
ls -l "$debdir"/*.deb

echo "== Pristine root filesystem (cached by base ISO checksum) =="
if [ -d "$pristine/etc" ] && [ "$(cat "$work/pristine.key" 2>/dev/null)" = "$base_sha" ]; then
  echo "cache hit: $pristine"
else
  sudo rm -rf "$pristine"
  mkdir -p "$work/iso-files"
  xorriso -osirrox on -indev "$base" -extract /casper/filesystem.squashfs "$work/iso-files/filesystem.squashfs" 2>/dev/null
  sudo unsquashfs -f -d "$pristine" "$work/iso-files/filesystem.squashfs" >/dev/null
  rm -f "$work/iso-files/filesystem.squashfs"
  echo "$base_sha" > "$work/pristine.key"
fi

echo "== Customise through an overlay (the pristine tree is never modified) =="
sudo rm -rf "$ovl"; mkdir -p "$ovl/up" "$ovl/wk" "$merged"
sudo mount -t overlay overlay -o "lowerdir=$pristine,upperdir=$ovl/up,workdir=$ovl/wk" "$merged"
sudo mkdir -p "$merged/tmp/hscl-debs"
sudo install -m 0644 "$debdir"/*.deb "$merged/tmp/hscl-debs/"
sudo chroot "$merged" sh -c 'dpkg -i /tmp/hscl-debs/*.deb'
sudo rm -rf "$merged/tmp/hscl-debs"
sudo env ROOTFS="$merged" bash "$root/distro/live/hooks/010-hscl-defaults.sh"
echo "== Verify the image (fails the build if anything is missing or Workshop is not inert) =="
sudo bash "$root/distro/live/verify-image.sh" "$merged"

xorriso -osirrox on -indev "$base" -extract /boot/grub/grub.cfg "$work/iso-files/grub.cfg" \
  -extract /md5sum.txt "$work/iso-files/md5sum.base.txt" 2>/dev/null
chmod u+w "$work/iso-files/grub.cfg" "$work/iso-files/md5sum.base.txt"

new_sq="$work/iso-files/filesystem.main.squashfs"; sudo rm -f "$new_sq"
echo "== Re-squash (bounded memory) =="
if [ "$fast" -eq 1 ]; then
  sudo mksquashfs "$merged" "$new_sq" -comp zstd -Xcompression-level 3 -b 131072 -noappend -quiet -processors "$(nproc)" -mem 1G
else
  sudo mksquashfs "$merged" "$new_sq" -comp xz -b 131072 -Xbcj x86 -noappend -quiet -processors "$(nproc)" -mem 1G
fi
sudo chown "$(id -u):$(id -g)" "$new_sq"

echo "== Patch boot menu label and checksum list =="
cfg="$work/iso-files/grub.main.cfg"; md5="$work/iso-files/md5sum.main.txt"
cp "$work/iso-files/grub.cfg" "$cfg"; cp "$work/iso-files/md5sum.base.txt" "$md5"
sed -i 's/Try or Install Kubuntu/Try or Install HSCL1 (pre-alpha)/; s/"Kubuntu (safe graphics)"/"HSCL1 (safe graphics)"/' "$cfg"
sq_md5="$(md5sum "$new_sq" | cut -d' ' -f1)"; cfg_md5="$(md5sum "$cfg" | cut -d' ' -f1)"
sed -i "s#^[0-9a-f]\{32\}  ./casper/filesystem.squashfs\$#$sq_md5  ./casper/filesystem.squashfs#; s#^[0-9a-f]\{32\}  ./boot/grub/grub.cfg\$#$cfg_md5  ./boot/grub/grub.cfg#" "$md5"
grep -q "$sq_md5" "$md5" || { echo "md5sum.txt update failed" >&2; exit 1; }

echo "== Build ISO (replaying upstream boot structure) =="
rm -f "$out"
xorriso -indev "$base" -outdev "$out" -volid "HSCL1 ${version} amd64" \
  -boot_image any replay \
  -map "$new_sq" /casper/filesystem.squashfs \
  -map "$cfg" /boot/grub/grub.cfg \
  -map "$md5" /md5sum.txt \
  -commit 2>&1 | grep -vE '^(xorriso : UPDATE|Writing: )' | tail -n 12
rm -f "$new_sq"
sha256sum "$out" | tee "$out.sha256"
dirty=0
[ -z "$(git -C "$root" status --porcelain 2>/dev/null)" ] || dirty=1
python3 "$root/scripts/write_iso_manifest.py" "$out" "$version" 0 "$base_sha" \
  "$(git -C "$root" rev-parse HEAD 2>/dev/null || echo unknown)" "$dirty"

echo "== Result =="
ls -l "$out"
