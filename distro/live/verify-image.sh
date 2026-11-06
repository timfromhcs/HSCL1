#!/usr/bin/env bash
# Assert that HSCL1 branding really is present inside an unpacked live rootfs (AGENTS.md: no silent patches).
# Usage: verify-image.sh ROOTFS [release]   Exit 0 only if every check passes.
#   (the optional second argument is accepted for compatibility and ignored)
set -Eeuo pipefail
root="${1:?usage: verify-image.sh ROOTFS [release]}"
fail=0
check() { # description, command...
  local d="$1"; shift
  if "$@" >/dev/null 2>&1; then echo "ok    $d"; else echo "FAIL  $d"; fail=1; fi
}
sudo_cat() { sudo cat "$@"; }

check "rootfs root directory is root:root 0755" test "$(stat -c %u:%g:%a "$root")" = "0:0:755"
check "os-release HSCL1_NAME_LONG (full product name)" grep -q '^HSCL1_NAME_LONG="Hypercharged Supreme Computing Layout 1"$' "$root/usr/lib/os-release"
check "hscl1 program (symlink to hscl)"  test "$(readlink "$root/usr/bin/hscl1")" = hscl
check "os-release NAME=HSCL1"             grep -q '^NAME="HSCL1"' "$root/usr/lib/os-release"
check "os-release keeps ID=ubuntu"        grep -q '^ID=ubuntu$' "$root/usr/lib/os-release"
check "os-release HSCL1_VERSION set"      grep -q '^HSCL1_VERSION="[0-9]' "$root/usr/lib/os-release"
check "original os-release diverted"      test -f "$root/usr/lib/os-release.ubuntu"
check "/etc/os-release resolves to ours"  grep -q '^NAME="HSCL1"' "$root/etc/os-release"
check "/etc/issue branded"                grep -q 'HSCL1' "$root/etc/issue"
check "original /etc/issue diverted"      test -f "$root/etc/issue.ubuntu"
check "handbook (en) installed"           test -s "$root/usr/share/doc/hscl-handbook/en/index.html"
check "handbook (de) installed"           test -s "$root/usr/share/doc/hscl-handbook/de/index.html"
check "handbook (fr) installed"           test -s "$root/usr/share/doc/hscl-handbook/fr/index.html"
check "handbook launcher"                 test -x "$root/usr/bin/hscl-handbook"
check "handbook desktop entry"            test -s "$root/usr/share/applications/hscl-handbook.desktop"
check "original kcm-about config diverted" test -f "$root/etc/xdg/kcm-about-distrorc.kubuntu"
check "HCS look-and-feel package"         test -s "$root/usr/share/plasma/look-and-feel/org.hcs.hscl1.desktop/metadata.json"
check "HCS top bar template"              test -s "$root/usr/share/plasma/layout-templates/org.hcs.hscl1.topbar/contents/layout.js"
check "HCS dock template"                 test -s "$root/usr/share/plasma/layout-templates/org.hcs.hscl1.dock/contents/layout.js"
check "HCS is the default look-and-feel"  grep -q '^LookAndFeelPackage=org.hcs.hscl1.desktop$' "$root/usr/share/kubuntu-default-settings/kf5-settings/kdeglobals"
check "sysctl hardening installed"        test -s "$root/etc/sysctl.d/90-hscl.conf"
check "security baseline service enabled" test -L "$root/etc/systemd/system/multi-user.target.wants/hscl-security-baseline.service"
check "autotune autostart at login"        grep -q '^Exec=hscl autotune$' "$root/etc/xdg/autostart/hscl-autotune.desktop"
check "KDE Connect daemon off by default"  grep -q '^Hidden=true$' "$root/etc/xdg/autostart/org.kde.kdeconnect.daemon.desktop"
check "KDE Connect D-Bus activation stubbed"   grep -q "^Exec=/bin/false$" "$root/usr/share/dbus-1/services/org.kde.kdeconnect.service"
check "control center binary"             test -x "$root/usr/bin/hscl-control-center"
check "control center QML"                test -s "$root/usr/share/hscl/control-center/qml/Main.qml"
check "control center de translation"     test -s "$root/usr/share/hscl/control-center/i18n/hscl-cc_de.qm"
check "control center fr translation"     test -s "$root/usr/share/hscl/control-center/i18n/hscl-cc_fr.qm"
check "control center desktop entry"      test -s "$root/usr/share/applications/hscl-control-center.desktop"
check "Calamares branding hscl1"          test -s "$root/etc/calamares/branding/hscl1/branding.desc"
check "Calamares logo"                    test -s "$root/etc/calamares/branding/hscl1/logo.png"
check "Calamares welcome image"           test -s "$root/etc/calamares/branding/hscl1/welcome.png"
check "Calamares slideshow"               test -s "$root/etc/calamares/branding/hscl1/show.qml"
check "Calamares uses hscl1 branding"     grep -q '^branding: *hscl1$' "$root/etc/calamares/settings.conf"
check "installer launcher renamed"        grep -q '^Name=Install HSCL1' "$root/usr/share/applications/kubuntu-calamares.desktop"
check "no Kubuntu installer launcher name" sh -c "! grep -E '^(Name|GenericName)(\\[[^]]*\\])?=.*Kubuntu' '$root/usr/share/applications/kubuntu-calamares.desktop'"
check "live desktop: no Kubuntu Focus link" test ! -e "$root/etc/skel/Desktop/org.kfocus.web.howtos.desktop"
check "live desktop: handbook link"       test -L "$root/etc/skel/Desktop/hscl-handbook.desktop"
check "root filesystem label is hscl1_root" grep -q '"hscl1_root"' "$root/etc/calamares/modules/partition.conf"
check "SDDM theme hscl1"                  test -s "$root/usr/share/sddm/themes/hscl1/Main.qml"
check "SDDM theme background"             test -s "$root/usr/share/sddm/themes/hscl1/background.png"
check "SDDM theme selected"               grep -q '^Current=hscl1$' "$root/etc/sddm.conf.d/30-hscl1.conf"
check "SDDM theme has no Kubuntu artwork" sh -c "! ls '$root'/usr/share/sddm/themes/hscl1/ | grep -i kubuntu_"
check "default avatar is the HSCL1 mark"  cmp -s "$root/etc/skel/.face" "$root/usr/share/hscl/brand/hscl1-mark-256.png"
check "OEM launcher renamed"              grep -q '^Name=Install HSCL1' "$root/usr/share/applications/calamares-launch-oem.desktop"
check "OEM batch id is hscl1-*"           grep -q '^batch-identifier: hscl1-' "$root/etc/calamares/modules/oemid.conf"
check "earlyoom installed"                test -x "$root/usr/bin/earlyoom"
check "zram generator installed"          test -x "$root/usr/lib/systemd/system-generators/zram-generator"
check "zram config"                       grep -q 'zram-size = min(ram / 2, 8192)' "$root/etc/systemd/zram-generator.conf"
check "earlyoom drop-in spares the shell" grep -q 'plasmashell' "$root/etc/systemd/system/earlyoom.service.d/90-hscl.conf"
check "AI memory slice"                   grep -q '^MemoryHigh=60%' "$root/usr/lib/systemd/system/hscl-ai.slice"
check "memory sysctl"                     grep -q 'vm.swappiness = 100' "$root/etc/sysctl.d/91-hscl-memory.conf"
check "hscl CLI installed"                test -x "$root/usr/bin/hscl"
check "release marker"                    test -f "$root/usr/share/hscl/release.json"
for w in HSCL1Midnight HSCL1Light HSCL1Nord HSCL1Aurora; do
  check "wallpaper $w"                    test -s "$root/usr/share/wallpapers/$w/contents/images/1920x1080.png"
done
check "design tokens installed"           test -s "$root/usr/share/hscl/themes/tokens.json"
for c in HCSMidnight HCSLight HCSNord HCSAurora; do
  check "colour scheme $c"                test -s "$root/usr/share/color-schemes/$c.colors"
done
check "app icon control center"           test -s "$root/usr/share/icons/hicolor/scalable/apps/hscl1-control-center.svg"
check "app icon handbook"                 test -s "$root/usr/share/icons/hicolor/scalable/apps/hscl1-handbook.svg"
check "rain wallpaper plugin"             test -s "$root/usr/share/plasma/wallpapers/org.hcs.hscl1.rain/contents/ui/main.qml"
check "rain wallpaper config schema"      test -s "$root/usr/share/plasma/wallpapers/org.hcs.hscl1.rain/contents/config/main.xml"
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
# Workshop (opt-in tools) must be present but inert: nothing enabled, no socket units, no baked-in token.
check "workshop evidence runner installed" test -x "$root/usr/lib/hscl/workshop/evidence.sh"
check "workshop udev rule installed"       test -s "$root/usr/lib/udev/rules.d/90-hscl-workshop.rules"
check "workshop is not enabled anywhere"   sh -c "! find '$root/etc/systemd/system' -name 'hscl-workshop*' | grep -q ."
check "workshop has no socket units"       sh -c "! find '$root/usr/lib/systemd/system' -name 'hscl-workshop*.socket' | grep -q ."
check "no workshop token baked in"         test ! -e "$root/etc/hscl/workshop.token"
# Package payload permissions: nothing shipped by an HSCL1 package may be world-writable or group-writable (a build on an NTFS checkout once produced 0777 everywhere).
bad_modes() {
  local l f
  for l in "$root"/var/lib/dpkg/info/hscl-*.list; do
    while IFS= read -r f; do
      [ -f "$root$f" ] && [ ! -L "$root$f" ] && [ -n "$(find "$root$f" -maxdepth 0 -perm /022)" ] && echo "$f"
    done < "$l"
  done
  return 0
}
check "hscl package files are not group/world-writable" bash -c "$(declare -f bad_modes); root='$root'; test -z \"\$(bad_modes)\""
check "diverted KDE Connect originals are outside scanned dirs" sh -c "! ls '$root'/etc/xdg/autostart | grep -q 'kdeconnect.daemon.desktop.'"
# Boot splash (W21): HSCL1 theme assembled by the hscl-branding postinst, selected as default, no upstream logo frames inside it
check "Plymouth theme hscl1-logo exists"       test -s "$root/usr/share/plymouth/themes/hscl1-logo/hscl1-logo.plymouth"
check "Plymouth theme has the pulse frames"    test -s "$root/usr/share/plymouth/themes/hscl1-logo/throbber-0032.png"
check "Plymouth theme keeps the dialog art"    test -s "$root/usr/share/plymouth/themes/hscl1-logo/entry.png"
check "Plymouth default is hscl1-logo"         test "$(readlink "$root/etc/alternatives/default.plymouth")" = /usr/share/plymouth/themes/hscl1-logo/hscl1-logo.plymouth
check "Plymouth theme has no Kubuntu text"     sh -c "! grep -ri kubuntu '$root/usr/share/plymouth/themes/hscl1-logo/'*.plymouth"
check "GRUB distributor is HSCL1"              grep -q '^GRUB_DISTRIBUTOR=HSCL1$' "$root/etc/default/grub"
check "no Kubuntu Welcome Center page"         test ! -e "$root/usr/share/plasma/plasma-welcome/extra-pages/01-Kubuntu.qml"
check "HSCL1 Welcome Center page"               grep -q 'Welcome to HSCL1' "$root/usr/share/plasma/plasma-welcome/extra-pages/01-HSCL1.qml"
check "old Calamares flavour branding removed"  test ! -e "$root/etc/calamares/branding/kubuntu"
check "no flavour donate/tour artwork"          sh -c "! ls '$root'/usr/share/kubuntu-default-settings/ | grep -E 'kubuntu_(donate|tour)'"
check "global themes renamed (no Kubuntu Name)" sh -c "! grep -E '\"Name\": *\"[^\"]*Kubuntu' '$root'/usr/share/plasma/look-and-feel/org.kubuntu*.desktop/metadata.json"
# Live session starter (owner-reported: the upstream "Try or Install Kubuntu" prompt blocked the boot with the flavour logo)
check "live starter is the HSCL1 one"         grep -q '^# HSCL1 live session starter' "$root/usr/libexec/start-kubuntu-live-env"
check "live starter does not run the prompt"  sh -c "! grep -E '^[^#]*kubuntu-installer-prompt' '$root/usr/libexec/start-kubuntu-live-env'"
check "live starter starts Plasma"            grep -q '^startplasma-wayland' "$root/usr/libexec/start-kubuntu-live-env"
check "live starter keeps the OEM branch"     grep -q 'calamares-launch-oem' "$root/usr/libexec/start-kubuntu-live-env"
check "original live starter diverted"        test -f "$root/usr/libexec/start-kubuntu-live-env.kubuntu"
# Visible upstream links and names found by the content scan (W24.6)
check "installer: no upstream donate link"      grep -q '^showDonateUrl: false$' "$root/etc/calamares/modules/welcome.conf"
check "no upstream website launcher (menu)"     test ! -e "$root/usr/share/applications/org.kubuntu.web.home.desktop"
check "no Kubuntu Focus launcher (menu)"        test ! -e "$root/usr/share/applications/org.kfocus.web.howtos.desktop"
check "SDDM theme id is hscl1"                  grep -q '^Theme-Id=hscl1$' "$root/usr/share/sddm/themes/hscl1/metadata.desktop"
check "SDDM theme description is HSCL1"         grep -q '^Description=HSCL1 login theme' "$root/usr/share/sddm/themes/hscl1/metadata.desktop"
check "live user is hscl1"                      grep -q '^export USERNAME="hscl1"$' "$root/etc/casper.conf"
check "live host is hscl1"                      grep -q '^export HOST="hscl1"$' "$root/etc/casper.conf"
check "casper FLAVOUR set (user/host honoured)" grep -q '^export FLAVOUR="HSCL1"$' "$root/etc/casper.conf"
[ "$fail" -eq 0 ] && echo "verify-image: all checks passed" || echo "verify-image: FAILED"
exit "$fail"
