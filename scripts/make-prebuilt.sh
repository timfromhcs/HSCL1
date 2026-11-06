#!/usr/bin/env bash
# Turn an installed (OEM) qcow2 into a publishable prebuilt image: credential scan first, then compress + manifest.
# Runs on the Linux/WSL builder. Reads the source image only (converted to a temporary raw copy, mounted read-only).
#
# Usage: scripts/make-prebuilt.sh SRC.qcow2 OUT.qcow2 --allow-user NAME [--secret TEXT] [--force]
# Result: OUT.qcow2 (compressed) and OUT.qcow2.manifest.json with credential_scan = "clean".
# Exit 1 and NO output image when the scan finds anything.
set -Eeuo pipefail

src=""; out=""; force=0
allow=(); secrets=()
while [ $# -gt 0 ]; do
  case "$1" in
    --allow-user) allow+=(--allow-user "${2:?}"); shift 2 ;;
    --secret) secrets+=(--secret "${2:?}"); shift 2 ;;
    --force) force=1; shift ;;
    -h|--help) sed -n '2,8p' "$0"; exit 0 ;;
    -*) echo "unknown option: $1" >&2; exit 2 ;;
    *) if [ -z "$src" ]; then src="$1"; elif [ -z "$out" ]; then out="$1"; else echo "too many arguments" >&2; exit 2; fi; shift ;;
  esac
done
[ -n "$src" ] && [ -n "$out" ] && [ ${#allow[@]} -gt 0 ] || { echo "usage: $0 SRC.qcow2 OUT.qcow2 --allow-user NAME ..." >&2; exit 2; }
[ -f "$src" ] || { echo "no such image: $src" >&2; exit 2; }
case "$src$out" in *.qcow2*.qcow2) ;; *) echo "both paths must end in .qcow2" >&2; exit 2 ;; esac
[ ! -e "$out" ] || [ "$force" -eq 1 ] || { echo "refusing to overwrite $out (use --force)" >&2; exit 2; }
for c in qemu-img losetup sudo python3 sfdisk sha256sum; do command -v "$c" >/dev/null || { echo "missing command: $c" >&2; exit 2; }; done

root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
tmp="$(mktemp -d "${TMPDIR:-/tmp}/hscl-prebuilt.XXXXXX")"
mnt="$tmp/mnt"; mkdir -p "$mnt"
loopdev=""
cleanup() {
  mountpoint -q "$mnt" && sudo umount "$mnt" || true
  [ -z "$loopdev" ] || sudo losetup -d "$loopdev" || true
  rm -rf "$tmp"
}
trap cleanup EXIT

echo "== Convert a temporary raw copy (source stays untouched) =="
qemu-img convert -O raw "$src" "$tmp/disk.raw"
loopdev="$(sudo losetup --find --show --read-only --partscan "$tmp/disk.raw")"
sleep 1
# shellcheck disable=SC2024  # the redirect target is our own temp directory
sudo sfdisk -J "$loopdev" > "$tmp/ptable.json"

echo "== Find and mount the root filesystem read-only =="
rootpart=""
for part in "${loopdev}"p*; do
  fs="$(sudo blkid -o value -s TYPE "$part" 2>/dev/null || true)"
  case "$fs" in ext4|btrfs|xfs) if sudo mount -o ro,noload "$part" "$mnt" 2>/dev/null || sudo mount -o ro "$part" "$mnt" 2>/dev/null; then
      if [ -d "$mnt/etc" ] && [ -d "$mnt/usr" ]; then rootpart="$part"; break; fi
      sudo umount "$mnt"; fi ;; esac
done
[ -n "$rootpart" ] || { echo "no root filesystem found in $src" >&2; exit 1; }
echo "root partition: $rootpart"

echo "== Credential scan =="
scan_status="clean"
if ! sudo python3 "$root/scripts/scan_credentials.py" "$mnt" "${allow[@]}" "${secrets[@]}"; then scan_status="findings"; fi
dpkg_count="$(grep -c '^Package:' "$mnt/var/lib/dpkg/status" || true)"
hscl_ver="$(sed -n 's/^HSCL1_VERSION="\(.*\)"/\1/p' "$mnt/usr/lib/os-release" || true)"
kernel="$(ls "$mnt/boot" | sed -n 's/^vmlinuz-//p' | sort -V | tail -n 1)"
sudo umount "$mnt"; sudo losetup -d "$loopdev"; loopdev=""

if [ "$scan_status" != "clean" ]; then
  echo "REFUSED: credential scan has findings; no prebuilt image written." >&2
  exit 1
fi

echo "== Compress =="
rm -f "$out"
qemu-img convert -c -O qcow2 "$src" "$out"
vsize="$(qemu-img info --output=json "$out" | python3 -c 'import json,sys;print(json.load(sys.stdin)["virtual-size"])')"
python3 - "$out" "$vsize" "$hscl_ver" "$kernel" "$dpkg_count" "$tmp/ptable.json" "$scan_status" "${allow[1]}" <<'PY'
import hashlib, json, sys, datetime
from pathlib import Path
out, vsize, ver, kernel, pkgs, ptable, scan, user = sys.argv[1:9]
p = Path(out)
h = hashlib.sha256()
with p.open("rb") as f:
    for c in iter(lambda: f.read(1 << 20), b""):
        h.update(c)
m = {
    "product": "HSCL1", "artifact": p.name, "hscl1_version": ver, "kernel": kernel, "dpkg_packages": int(pkgs),
    "image_bytes": p.stat().st_size, "image_sha256": h.hexdigest(), "virtual_bytes": int(vsize),
    "partition_table": json.loads(Path(ptable).read_text())["partitiontable"],
    "credential_scan": scan, "first_boot": "OEM user setup (account '%s' is replaced at first boot)" % user,
    "built_utc": datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
}
Path(out + ".manifest.json").write_text(json.dumps(m, indent=2) + "\n")
print("manifest:", out + ".manifest.json")
PY
ls -l "$out"
