#!/usr/bin/env bash
# Assert that HSCL1 branding really is present inside an unpacked live rootfs (AGENTS.md: no silent patches).
# Usage: verify-image.sh ROOTFS     Exit 0 only if every check passes.
set -Eeuo pipefail
root="${1:?usage: verify-image.sh ROOTFS}"
fail=0
check() { # description, command...
  local d="$1"; shift
  if "$@" >/dev/null 2>&1; then echo "ok    $d"; else echo "FAIL  $d"; fail=1; fi
}
sudo_cat() { sudo cat "$@"; }

check "os-release NAME=HSCL1"             grep -q '^NAME="HSCL1"' "$root/usr/lib/os-release"
check "os-release keeps ID=ubuntu"        grep -q '^ID=ubuntu$' "$root/usr/lib/os-release"
check "os-release HSCL1_VERSION set"      grep -q '^HSCL1_VERSION="[0-9]' "$root/usr/lib/os-release"
check "original os-release diverted"      test -f "$root/usr/lib/os-release.ubuntu"
check "/etc/os-release resolves to ours"  grep -q '^NAME="HSCL1"' "$root/etc/os-release"
check "/etc/issue branded"                grep -q 'HSCL1' "$root/etc/issue"
check "hscl CLI installed"                test -x "$root/usr/bin/hscl"
check "release marker"                    test -f "$root/usr/share/hscl/release.json"
for w in HSCL1Midnight HSCL1Light HSCL1Nord HSCL1Aurora; do
  check "wallpaper $w"                    test -s "$root/usr/share/wallpapers/$w/contents/images/1920x1080.png"
done
check "logo mark svg"                     test -s "$root/usr/share/hscl/brand/hscl1-mark-dark.svg"
check "logo wordmark svg"                 test -s "$root/usr/share/hscl/brand/hscl1-wordmark-dark.svg"
check "hicolor icon hscl1 (scalable)"     test -s "$root/usr/share/icons/hicolor/scalable/apps/hscl1.svg"
check "About logo configured"             grep -q 'hscl1-mark' "$root/etc/xdg/kcm-about-distrorc"
check "look-and-feel wallpaper default"   grep -q '^Image=HSCL1Midnight$' "$root/usr/share/plasma/look-and-feel/org.kubuntu.desktop/contents/defaults"
check "layout script wallpaper"           grep -q 'wallpapers/HSCL1Midnight' "$root/usr/share/plasma/look-and-feel/org.kubuntu.desktop/contents/layouts/org.kde.plasma.desktop-layout.js"
check "screen locker wallpaper"           grep -q 'HSCL1Midnight' "$root/usr/share/kubuntu-default-settings/kf5-settings/kscreenlockerrc"
if grep -rIl --exclude='*.upstream' -e 'wallpapers/Kubuntu' "$root/usr/share/plasma/look-and-feel" "$root/usr/share/kubuntu-default-settings" 2>/dev/null | grep -q .; then
  echo "FAIL  stale Kubuntu default wallpaper reference remains"; fail=1
else
  echo "ok    no stale Kubuntu default wallpaper reference"
fi
[ "$fail" -eq 0 ] && echo "verify-image: all checks passed" || echo "verify-image: FAILED"
exit "$fail"
