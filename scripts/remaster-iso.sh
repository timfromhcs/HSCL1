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
export PATH="$HOME/.cargo/bin:$PATH"

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
  for m in dev sys proc; do mountpoint -q "$merged/$m" 2>/dev/null && sudo umount "$merged/$m" || true; done
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
for p in hscl-branding hscl-handbook hscl-desktop hscl-security hscl-control-center hscl-workshop hscl-memory hscl-cqhecs; do
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
# The overlay upper dir becomes the ROOT directory of the squashfs (and of every installed system, Calamares copies it): it must be root:root 0755.
# Created as the build user it made "/" owned by uid 1000 on installed systems (found 2026-11-06, a local privilege-escalation primitive).
sudo rm -rf "$ovl"; sudo install -d -o root -g root -m 0755 "$ovl" "$ovl/up" "$ovl/wk" "$merged"
sudo mount -t overlay overlay -o "lowerdir=$pristine,upperdir=$ovl/up,workdir=$ovl/wk" "$merged"
sudo mkdir -p "$merged/tmp/hscl-debs"
sudo install -m 0644 "$debdir"/*.deb "$merged/tmp/hscl-debs/"
sudo chroot "$merged" sh -c 'dpkg -i /tmp/hscl-debs/*.deb'
sudo rm -rf "$merged/tmp/hscl-debs"
sudo env ROOTFS="$merged" bash "$root/distro/live/hooks/010-hscl-defaults.sh"
echo "== Verify the image (fails the build if anything is missing or Workshop is not inert) =="
sudo bash "$root/distro/live/verify-image.sh" "$merged"

echo "== Rebuild the live initrd (the boot splash theme lives in it) =="
# The ISO's /casper/initrd is built by the upstream image pipeline and would still show the upstream boot splash. Rebuilding it in the
# customised root (same casper hooks, same tools) puts the HSCL1 splash into the live boot. Checked below, and by a boot test.
for m in proc sys dev; do sudo mount --bind "/$m" "$merged/$m"; done
kver="$(ls "$merged"/boot/vmlinuz-* | sed 's#.*/vmlinuz-##' | sort -V | tail -n 1)"
[ -n "$kver" ] || { echo "no kernel found in the image" >&2; exit 1; }
sudo rm -rf "$merged/tmp/initrd-out"; sudo mkdir -p "$merged/tmp/initrd-out"
# The upstream live initrd carries conf/conf.d/default-boot-to-casper.conf (BOOT=casper unless set), added by its image pipeline. Without
# it the initrd boots like an installed system and drops to the initramfs shell (seen in r2, 2026-11-06). The file exists ONLY while the
# initrd is built: left in the squashfs it would make every installed system try to boot from casper.
conf_snip="$merged/etc/initramfs-tools/conf.d/default-boot-to-casper.conf"
printf 'if [ -z "$BOOT" ]; then
    export BOOT=casper
fi
' | sudo tee "$conf_snip" >/dev/null
sudo chroot "$merged" update-initramfs -c -k "$kver" -b /tmp/initrd-out
sudo rm -f "$conf_snip"
sudo chroot "$merged" lsinitramfs "/tmp/initrd-out/initrd.img-$kver" | tee "$work/initrd.list" >/dev/null || { echo "cannot list the new initrd" >&2; exit 1; }
for m in dev sys proc; do sudo umount "$merged/$m"; done
new_initrd="$work/iso-files/initrd.main"
sudo cp "$merged/tmp/initrd-out/initrd.img-$kver" "$new_initrd"; sudo chown "$(id -u):$(id -g)" "$new_initrd"
sudo rm -rf "$merged/tmp/initrd-out"
for need in hscl1-logo.plymouth scripts/casper conf/conf.d/default-boot-to-casper.conf; do
  grep -q "$need" "$work/initrd.list" || { echo "new initrd lacks $need" >&2; exit 1; }
done
if grep -q 'kubuntu-logo' "$work/initrd.list"; then echo "new initrd still carries the upstream boot splash" >&2; exit 1; fi
[ "$(stat -c %s "$new_initrd")" -gt 30000000 ] || { echo "new initrd is suspiciously small" >&2; exit 1; }

xorriso -osirrox on -indev "$base" -extract /boot/grub/grub.cfg "$work/iso-files/grub.cfg" \
  -extract /md5sum.txt "$work/iso-files/md5sum.base.txt" 2>/dev/null
chmod u+w "$work/iso-files/grub.cfg" "$work/iso-files/md5sum.base.txt"

new_sq="$work/iso-files/filesystem.main.squashfs"; sudo rm -f "$new_sq"
# Squash resources are tunable: the host reaped the build three times while all cores and 1 GB of buffers were in use on a 19.8 GB machine
# (WSL page cache from the large output file counts against free memory). Defaults are deliberately modest.
sq_procs="${HSCL_SQUASH_PROCS:-3}"
sq_mem="${HSCL_SQUASH_MEM:-512M}"
echo "== Re-squash (bounded memory: $sq_procs processors, $sq_mem buffers) =="
if [ "$fast" -eq 1 ]; then
  sudo mksquashfs "$merged" "$new_sq" -comp zstd -Xcompression-level 3 -b 131072 -noappend -quiet -processors "$sq_procs" -mem "$sq_mem"
else
  sudo mksquashfs "$merged" "$new_sq" -comp xz -b 131072 -Xbcj x86 -noappend -quiet -processors "$sq_procs" -mem "$sq_mem"
fi
# awk must read all input: an early `exit` closes the pipe, unsquashfs gets SIGPIPE and pipefail aborts the build (seen 2026-11-06, exit 141)
root_owner="$(sudo unsquashfs -n -lls "$new_sq" 2>/dev/null | awk '$NF=="squashfs-root" && !done {print $2; done=1}')"
[ "$root_owner" = "root/root" ] || { echo "squashfs root directory is owned by ${root_owner:-unknown}, expected root/root" >&2; exit 1; }
sudo chown "$(id -u):$(id -g)" "$new_sq"

echo "== Patch boot menu label and checksum list =="
cfg="$work/iso-files/grub.main.cfg"; md5="$work/iso-files/md5sum.main.txt"
cp "$work/iso-files/grub.cfg" "$cfg"; cp "$work/iso-files/md5sum.base.txt" "$md5"
sed -i 's/Try or Install Kubuntu/Try or Install HSCL1 (pre-alpha)/; s/"Kubuntu (safe graphics)"/"HSCL1 (safe graphics)"/' "$cfg"
ird_md5="$(md5sum "$new_initrd" | cut -d' ' -f1)"
sq_md5="$(md5sum "$new_sq" | cut -d' ' -f1)"; cfg_md5="$(md5sum "$cfg" | cut -d' ' -f1)"
sed -i "s#^[0-9a-f]\{32\}  ./casper/filesystem.squashfs\$#$sq_md5  ./casper/filesystem.squashfs#; s#^[0-9a-f]\{32\}  ./boot/grub/grub.cfg\$#$cfg_md5  ./boot/grub/grub.cfg#" "$md5"
sed -i "s#^[0-9a-f]\{32\}  ./casper/initrd\$#$ird_md5  ./casper/initrd#" "$md5"
grep -q "$ird_md5" "$md5" || { echo "md5sum.txt initrd update failed" >&2; exit 1; }
# Live user and host name: casper takes the first word of /cdrom/.disk/info, lower-cased, as FLAVOUR (and with it USERNAME and HOST) unless
# FLAVOUR is set in casper.conf. Setting FLAVOUR in casper.conf broke the overlay boot (r5, 2026-11-06: "cow format specified as overlay and no
# support found"; the same image with the r4 initrd booted), so the supported route is this file. md5sum.txt lists it and must follow.
disk_info="$work/iso-files/disk-info"
printf 'HSCL1 %s (Ubuntu 26.04.1 base) - Release amd64 (%s)\n' "$version" "$(date -u +%Y%m%d)" > "$disk_info"
info_md5="$(md5sum "$disk_info" | cut -d' ' -f1)"
sed -i "s#^[0-9a-f]\{32\}  ./.disk/info\$#$info_md5  ./.disk/info#" "$md5"
grep -q "$info_md5  ./.disk/info" "$md5" || { echo "md5sum.txt .disk/info update failed" >&2; exit 1; }
grep -q "$sq_md5" "$md5" || { echo "md5sum.txt update failed" >&2; exit 1; }

echo "== Build ISO (replaying upstream boot structure) =="
rm -f "$out"
xorriso -indev "$base" -outdev "$out" -volid "HSCL1 ${version} amd64" \
  -boot_image any replay \
  -map "$new_sq" /casper/filesystem.squashfs \
  -map "$new_initrd" /casper/initrd \
  -map "$disk_info" /.disk/info \
  -map "$cfg" /boot/grub/grub.cfg \
  -map "$md5" /md5sum.txt \
  -commit 2>&1 | grep -vE '^(xorriso : UPDATE|Writing: )' | tail -n 12
# The check above only looked at the file we meant to map. Prove it is what the finished ISO contains (a missing -map once shipped the
# upstream boot splash while every gate was green).
xorriso -osirrox on -indev "$out" -extract /casper/initrd "$work/iso-files/initrd.check" 2>/dev/null
cmp -s "$work/iso-files/initrd.check" "$new_initrd" || { echo "the ISO does not contain the rebuilt initrd" >&2; exit 1; }
rm -f "$work/iso-files/initrd.check"
echo "ok    ISO /casper/initrd is the rebuilt initrd (md5 $ird_md5)"
xorriso -osirrox on -indev "$out" -extract /.disk/info "$work/iso-files/disk-info.check" 2>/dev/null
cmp -s "$work/iso-files/disk-info.check" "$disk_info" || { echo "the ISO does not contain the HSCL1 .disk/info" >&2; exit 1; }
[ "$(cut -d' ' -f1 "$work/iso-files/disk-info.check" | tr '[:upper:]' '[:lower:]')" = "hscl1" ] || { echo ".disk/info first word is not HSCL1" >&2; exit 1; }
rm -f "$work/iso-files/disk-info.check" "$disk_info"
echo "ok    ISO /.disk/info starts with HSCL1 (casper flavour: live user and host hscl1)"
rm -f "$new_sq" "$new_initrd"
sha256sum "$out" | tee "$out.sha256"
dirty=0
[ -z "$(git -C "$root" status --porcelain 2>/dev/null)" ] || dirty=1
python3 "$root/scripts/write_iso_manifest.py" "$out" "$version" 0 "$base_sha" \
  "$(git -C "$root" rev-parse HEAD 2>/dev/null || echo unknown)" "$dirty"

echo "== Result =="
ls -l "$out"
