#!/usr/bin/env bash
# Chroot customisation hook for the live rootfs. Called by scripts/remaster-iso.sh with ROOTFS set.
# PoC scope: make the HSCL1 Midnight wallpaper the default of Kubuntu's Plasma look-and-feel packages
# (desktop layout script, look-and-feel defaults) and of the screen locker. Fails loudly if nothing matched.
set -Eeuo pipefail
: "${ROOTFS:?ROOTFS must point to the unpacked live root filesystem}"

patched=0
patch_file() { # file sed-expression
  local f="$1" expr="$2"
  [ -f "$f" ] || return 0
  cp --update=none "$f" "$f.upstream"
  sed -i "$expr" "$f"
  if cmp -s "$f" "$f.upstream"; then return 0; fi
  patched=$((patched + 1))
}

for lnf in "$ROOTFS"/usr/share/plasma/look-and-feel/org.kubuntu*.desktop/contents; do
  wp=HSCL1Midnight
  case "$lnf" in *org.kubuntulight.desktop*) wp=HSCL1Light ;; esac
  patch_file "$lnf/defaults" "s/^Image=Kubuntu\$/Image=$wp/"
  # layout scripts use either ".../Kubuntu" or ".../Kubuntu#day-night"
  patch_file "$lnf/layouts/org.kde.plasma.desktop-layout.js"     "s#file:///usr/share/wallpapers/Kubuntu\(\#day-night\)\?#file:///usr/share/wallpapers/$wp#"
done
patch_file "$ROOTFS/usr/share/kubuntu-default-settings/kf5-settings/kscreenlockerrc" \
  's#file:///usr/share/wallpapers/Kubuntu/\#day-night#file:///usr/share/wallpapers/HSCL1Midnight#g'

# Make the HCS Hybrid Desktop the default look-and-feel (the Kubuntu settings file names the package)
patch_file "$ROOTFS/usr/share/kubuntu-default-settings/kf5-settings/kdeglobals"   's/^LookAndFeelPackage=org.kubuntu.desktop$/LookAndFeelPackage=org.hcs.hscl1.desktop/; s/^DefaultDarkLookAndFeel=.*/DefaultDarkLookAndFeel=org.hcs.hscl1.desktop/'

echo "010-hscl-defaults: patched $patched files"
[ "$patched" -ge 8 ] || { echo "expected to patch at least 8 files" >&2; exit 1; }
