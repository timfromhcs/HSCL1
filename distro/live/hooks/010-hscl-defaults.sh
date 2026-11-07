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

# Installer: use the HSCL1 Calamares branding and name the desktop entry after the product
patch_file "$ROOTFS/etc/calamares/settings.conf" 's/^branding: *kubuntu$/branding: hscl1/'
patch_file "$ROOTFS/usr/share/applications/kubuntu-calamares.desktop" \
  '/^\(Name\|GenericName\)\(\[[^]]*\]\)\?=/ s/Kubuntu 26\.04/HSCL1/; /^\(Name\|GenericName\)\(\[[^]]*\]\)\?=/ s/Kubuntu/HSCL1/'

patch_file "$ROOTFS/usr/share/applications/calamares-launch-oem.desktop"   '/^\(Name\|GenericName\)\(\[[^]]*\]\)\?=/ s/Kubuntu 26\.04/HSCL1/; /^\(Name\|GenericName\)\(\[[^]]*\]\)\?=/ s/Kubuntu/HSCL1/'

# Login screen: derive an HSCL1 SDDM theme from the installed Kubuntu one (QML stays upstream), HSCL1 artwork and avatar
sddm="$ROOTFS/usr/share/sddm/themes"
if [ -d "$sddm/kubuntu" ]; then
  rm -rf "$sddm/hscl1"
  cp -a "$sddm/kubuntu" "$sddm/hscl1"
  rm -f "$sddm/hscl1/preview.png" "$sddm/hscl1/"kubuntu_*.png
  install -m 0644 "$ROOTFS/usr/share/wallpapers/HSCL1Midnight/contents/images/1920x1080.png" "$sddm/hscl1/background.png"
  install -m 0644 "$ROOTFS/usr/share/hscl/brand/hscl1-mark-dark.svg" "$sddm/hscl1/default-logo.svg"
  cat > "$sddm/hscl1/theme.conf" <<'CONF'
[General]
showlogo=hidden
showClock=true
logo=/usr/share/sddm/themes/hscl1/default-logo.svg
type=image
color=#0e1117
fontSize=10
background=/usr/share/sddm/themes/hscl1/background.png
needsFullUserModel=false
CONF
  sed -i 's/^Name=.*/Name=HSCL1/; /^Name\[/d; s/^Comment=.*/Comment=HSCL1 login theme/; /^Comment\[/d' "$sddm/hscl1/metadata.desktop"
  printf '[Theme]
Current=hscl1
' > "$ROOTFS/etc/sddm.conf.d/30-hscl1.conf"
fi
# GRUB menu entries of installed systems are named after GRUB_DISTRIBUTOR (default: lsb_release -i -s = "Ubuntu").
# DISTRIB_ID in /etc/lsb-release stays unchanged on purpose: unattended-upgrades and other tools key their origin patterns on it.
patch_file "$ROOTFS/etc/default/grub" 's/^GRUB_DISTRIBUTOR=.*/GRUB_DISTRIBUTOR=HSCL1/'

# Upstream flavour marketing and artwork that must not stay visible (Welcome Center page with a donation call, installer slideshow of the
# old branding directory, tour/donate graphics, bug avatar). The HSCL1 welcome page comes from the hscl-branding package.
rm -f "$ROOTFS/usr/share/plasma/plasma-welcome/extra-pages/01-Kubuntu.qml"
rm -rf "$ROOTFS/etc/calamares/branding/kubuntu"
rm -f "$ROOTFS/usr/share/kubuntu-default-settings/kubuntu_donate.svg" "$ROOTFS/usr/share/kubuntu-default-settings/kubuntu_tour.svg"       "$ROOTFS/usr/share/plasma/avatars/kubuntu-bug.png"
# Global-theme, desktop-theme and panel-layout entries still list the upstream flavour by name in System Settings: rename the visible
# names (Ids stay, other settings reference them).
for md in "$ROOTFS"/usr/share/plasma/look-and-feel/org.kubuntu*.desktop/metadata.json           "$ROOTFS"/usr/share/plasma/desktoptheme/kubuntu*/metadata.json           "$ROOTFS"/usr/share/plasma/layout-templates/org.kubuntu.desktop.defaultPanel/metadata.json; do
  patch_file "$md" 's/Kubuntu/HSCL1 Classic/g'
done
# Start-menu icons of the upstream flavour: same file names, HSCL1 mark inside (the panel and themes refer to these names)
mark="$ROOTFS/usr/share/hscl/brand/hscl1-mark-dark.svg"
if [ -f "$mark" ]; then
  for d in "$ROOTFS"/usr/share/plasma/desktoptheme/kubuntu*/icons; do [ -d "$d" ] && gzip -9 -n -c "$mark" > "$d/start.svgz"; done
  start_icon="$ROOTFS/usr/share/icons/breeze/places/16/start-here-kubuntu.svg"
  if [ -e "$start_icon" ]; then install -m 0644 "$mark" "$start_icon"; fi
  rm -f "$ROOTFS/usr/share/icons/breeze/places/16/start-here-kubuntu.svgz"
fi

# Installer welcome page: no upstream donation link (HSCL1 has no donation page)
patch_file "$ROOTFS/etc/calamares/modules/welcome.conf" 's#^showDonateUrl:.*#showDonateUrl: false#'
# Upstream website launchers must not appear in the application menu
rm -f "$ROOTFS/usr/share/applications/org.kubuntu.web.home.desktop" "$ROOTFS/usr/share/applications/org.kfocus.web.howtos.desktop"
patch_file "$ROOTFS/usr/share/applications/org.kubuntu.restore-desktop-links.desktop" 's/Re-create Kubuntu.s default desktop links/Re-create the default desktop links/'
# SDDM theme derived from the upstream one: description and id (author/copyright lines stay: they are attribution, see docs/BRAND.md)
if [ -f "$sddm/hscl1/metadata.desktop" ]; then
  sed -i 's/^Description=.*/Description=HSCL1 login theme (based on the Breeze SDDM theme)/; s/^Theme-Id=.*/Theme-Id=hscl1/' "$sddm/hscl1/metadata.desktop"
fi
# Live session user and host name: do NOT touch /etc/casper.conf. Setting FLAVOUR there made the live initrd fail with
# "cow format specified as overlay and no support found" (r5, 2026-11-06). casper derives the names from the first word of
# /cdrom/.disk/info, which scripts/remaster-iso.sh sets to "HSCL1" on the medium.

# Default avatar of new users
rm -f "$ROOTFS/etc/skel/.face"
install -m 0644 "$ROOTFS/usr/share/hscl/brand/hscl1-mark-256.png" "$ROOTFS/etc/skel/.face"
ln -sf .face "$ROOTFS/etc/skel/.face.icon"

patch_file "$ROOTFS/etc/calamares/modules/oemid.conf" 's/^batch-identifier: kubuntu-/batch-identifier: hscl1-/'

# Partition/filesystem names that end up on the installed disk
patch_file "$ROOTFS/etc/calamares/modules/partition.conf" 's/"kubuntu_boot"/"hscl1_boot"/; s/"kubuntu_2604"/"hscl1_root"/'
# With encryption, /boot stays unencrypted (docs/INSTALLER_FACTS.md); Calamares has a translated message for exactly that.
patch_file "$ROOTFS/etc/calamares/modules/partition.conf" 's/^showNotEncryptedBootMessage:.*/showNotEncryptedBootMessage: true/'

# Replace upstream marketing shortcuts on the live desktop with HSCL1 entries
rm -f "$ROOTFS/etc/skel/Desktop/org.kfocus.web.howtos.desktop" "$ROOTFS/etc/skel/Desktop/org.kubuntu.web.home.desktop"
ln -sf /usr/share/applications/hscl-handbook.desktop "$ROOTFS/etc/skel/Desktop/hscl-handbook.desktop"
ln -sf /usr/share/applications/hscl-control-center.desktop "$ROOTFS/etc/skel/Desktop/hscl-control-center.desktop"

echo "010-hscl-defaults: patched $patched files"
[ "$patched" -ge 13 ] || { echo "expected to patch at least 13 files" >&2; exit 1; }
