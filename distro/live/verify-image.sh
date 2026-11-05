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
