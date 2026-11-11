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

ensure_key() { # file section key value  (sets a key even when the file does not carry it yet)
  local f="$1" sec="$2" key="$3" val="$4"
  [ -f "$f" ] || return 0
  cp --update=none "$f" "$f.upstream"
  if grep -q "^${key}=" "$f"; then
    sed -i "s|^${key}=.*|${key}=${val}|" "$f"
  elif grep -q "^\[${sec}\]$" "$f"; then
    sed -i "/^\[${sec}\]$/a ${key}=${val}" "$f"
  else
    printf '\n[%s]\n%s=%s\n' "$sec" "$key" "$val" >> "$f"
  fi
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
# ... and give new users the HCS palette for widget apps (Dolphin, Konsole, Kate). Without this the live/in-
# stalled session kept Kubuntu's light Breeze palette: Plasma shell dark, Qt apps light (visual QA 2026-11-09).
# The Kubuntu default file carries [General] but no ColorScheme key at all, so this must *ensure* the key
# rather than sed-replace it (the first attempt changed nothing and the image gate caught it).
ensure_key "$ROOTFS/usr/share/kubuntu-default-settings/kf5-settings/kdeglobals" General ColorScheme HCSMidnight
ensure_key "$ROOTFS/usr/share/kubuntu-default-settings/kf5-settings/kdeglobals" KDE widgetStyle Breeze
# New and live users are created from /etc/skel, which Plasma reads before any look-and-feel is applied.
# The file does not necessarily exist in the base image, so create it first.
skel_kdeglobals="$ROOTFS/etc/skel/.config/kdeglobals"
mkdir -p "$(dirname "$skel_kdeglobals")"
[ -f "$skel_kdeglobals" ] || : > "$skel_kdeglobals"
ensure_key "$skel_kdeglobals" General ColorScheme HCSMidnight
ensure_key "$skel_kdeglobals" KDE widgetStyle Breeze
# Desktop icon labels (visual audit 2026-11-10): every capture shows oblique (italic) icon labels. The cause is
# not the font: Plasma's FolderItemDelegate sets `font.italic: model.isLink`, so a desktop entry that is a
# **symlink** is always drawn in italics. The image has 314 Noto font files and no Lato, so "Noto Sans" is the
# correct family to pin; the icon entries themselves are installed as real files below instead of symlinks.
ensure_key "$skel_kdeglobals" Fonts desktopFont "Noto Sans,10,-1,5,50,0,0,0,0,0"

# Kate does not inherit the Plasma palette on its own: the application chrome follows its own "ColorScheme" and
# the editor area follows the KSyntaxHighlighting theme, and the live session opened with a light window inside
# the dark shell (Q-53, `docs/img/showcase/14_app_kate.png`). Give new and live users an explicit dark default
# instead of documenting the exception. Breeze Dark ships with the image.
cat > "$ROOTFS/etc/skel/.config/katerc" <<'KATERCR'
[UiSettings]
ColorScheme=Breeze Dark

[KTextEditor Renderer]
Color Theme=Breeze Dark
Auto Color Theme Selection=false
KATERCR
chmod 0644 "$ROOTFS/etc/skel/.config/katerc"

# Installer: use the HSCL1 Calamares branding and name the desktop entry after the product
patch_file "$ROOTFS/etc/calamares/settings.conf" 's/^branding: *kubuntu$/branding: hscl1/'
# The welcome module's network probe runs inside ModuleManager::checkRequirements() at startup and made
# Calamares crash in a VM (KCrash log 2026-11-10: "Application 'calamares' crashing... crashRecursionCounter = 2"
# right after initViewSteps/checkRequirements, then KCrash SIGKILLed the process). The image installs offline,
# so storage/ram/power/root stay as checks and the network probe goes.
patch_file "$ROOTFS/etc/calamares/modules/welcome.conf" '/^        - internet$/d'
patch_file "$ROOTFS/usr/share/applications/kubuntu-calamares.desktop" \
  '/^\(Name\|GenericName\)\(\[[^]]*\]\)\?=/ s/Kubuntu 26\.04/HSCL1/; /^\(Name\|GenericName\)\(\[[^]]*\]\)\?=/ s/Kubuntu/HSCL1/'
# Calamares' Qt Quick UI crashed intermittently in VMs while building its first view (KCrash after the requirement
# check, `qrc:/ui/MainPage.qml`), and KCrash then SIGKILLed it. The wrapper sets QT_QUICK_BACKEND=software, which
# removes that crash class; the installer UI is simple enough that software rendering costs nothing.
patch_file "$ROOTFS/usr/share/applications/kubuntu-calamares.desktop" \
  's#^Exec=sudo /usr/bin/calamares-launch-normal$#Exec=sudo /usr/bin/hscl-calamares#'

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
# Open the Welcome Center on the HSCL1 page. Measured 2026-11-11 on rc8: `plasma-welcome --help` documents
# `--pages <pages>` ("comma-delimited list of page(s) by internal name"), and the internal name is the file stem in
# extra-pages, so `--pages 01-HSCL1` opened the HSCL1 page as the only page (artifacts/boot-welcome-name). Without
# it the first thing a new user sees is Plasma's built-in "Welcome to KDE" page with the Konqi mascot.
patch_file "$ROOTFS/usr/share/applications/org.kde.plasma-welcome.desktop" 's/^Exec=plasma-welcome$/Exec=plasma-welcome --pages 01-HSCL1/'
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
# Notes page (disk encryption explained, en/de/fr via lang/*.qm): a QML view step shown before the partition page. The page file lives in
# the hscl-branding package; here the module config is created and the step is inserted into the show sequence.
if [ -f "$ROOTFS/etc/calamares/settings.conf" ]; then
  printf -- '---\n# where to look for notesqml.qml: the branding directory only\nqmlSearch: branding\n' > "$ROOTFS/etc/calamares/modules/notesqml.conf"
  patch_file "$ROOTFS/etc/calamares/settings.conf" '0,/^  - partition$/s//  - notesqml\n  - partition/'
fi
# With encryption, /boot stays unencrypted (docs/INSTALLER_FACTS.md). Calamares has a message for that, but it was NOT seen in the automatic
# erase+encrypt path of the dev2 image (only the config value is verified); an HSCL1 explanation is still an open gap.
patch_file "$ROOTFS/etc/calamares/modules/partition.conf" 's/^showNotEncryptedBootMessage:.*/showNotEncryptedBootMessage: true/'

# Replace upstream marketing shortcuts on the live desktop with HSCL1 entries
rm -f "$ROOTFS/etc/skel/Desktop/org.kfocus.web.howtos.desktop" "$ROOTFS/etc/skel/Desktop/org.kubuntu.web.home.desktop"
# Plasma draws a desktop entry that is a symlink in italics (`FolderItemDelegate.qml: font.italic: model.isLink`),
# so the two HSCL1 entries are installed as real copies rather than links. Same launcher, upright label.
rm -f "$ROOTFS/etc/skel/Desktop/hscl-handbook.desktop" "$ROOTFS/etc/skel/Desktop/hscl-control-center.desktop"
for entry in hscl-handbook hscl-control-center; do
  install -m 0644 "$ROOTFS/usr/share/applications/$entry.desktop" "$ROOTFS/etc/skel/Desktop/$entry.desktop"
done

echo "010-hscl-defaults: patched $patched files"
[ "$patched" -ge 13 ] || { echo "expected to patch at least 13 files" >&2; exit 1; }
