#!/usr/bin/env bash
# Chroot customisation hook for the live rootfs. Called by scripts/remaster-iso.sh with ROOTFS set.
# PoC scope: point Kubuntu's Plasma look-and-feel defaults at the HSCL1 Midnight wallpaper.
set -Eeuo pipefail
: "${ROOTFS:?ROOTFS must point to the unpacked live root filesystem}"

n=0
for d in "$ROOTFS"/usr/share/plasma/look-and-feel/org.kubuntu*.desktop/contents/defaults; do
  [ -f "$d" ] || continue
  # Only touch the wallpaper key; keep a backup next to it.
  cp -n "$d" "$d.upstream"
  sed -i 's/^Image=Kubuntu$/Image=HSCL1Midnight/' "$d"
  n=$((n + 1))
done
echo "010-hscl-defaults: patched $n look-and-feel defaults"
