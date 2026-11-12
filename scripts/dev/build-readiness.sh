#!/usr/bin/env bash
# Read-only readiness check for the ISO build inside WSL.
set -u
echo "== base ISO =="
ls -l "$HOME"/hscl1-build/upstream/*.iso 2>/dev/null | head -3 || echo "MISSING base ISO"
echo "== disk =="
df -h "$HOME" | tail -1
echo "== pristine cache =="
if [ -d "$HOME/hscl1-build/work/pristine" ]; then du -sh "$HOME/hscl1-build/work/pristine"; else echo "no pristine cache (first build will unpack)"; fi
echo "== memory =="
awk '/MemAvailable/ {print "MemAvailable MB:", int($2/1024)}' /proc/meminfo
echo "== tools =="
for c in xorriso mksquashfs unsquashfs dpkg-deb cargo python3 lrelease sha256sum; do
  if command -v "$c" >/dev/null 2>&1; then echo "ok      $c"; else echo "MISSING $c"; fi
done
echo "== out dir =="
ls -1 "$HOME"/hscl1-build/out/*.iso 2>/dev/null | tail -4 || echo "no ISOs in out/"
echo "== git HEAD in the repo checkout used by the build =="
if [ -d /mnt/e/hcslinux222/.git ]; then
  git -C /mnt/e/hcslinux222 rev-parse --short HEAD 2>/dev/null || echo "cannot read HEAD over 9p"
fi
