#!/usr/bin/env bash
# Sandbox check for the palette lines in the live-image hook (no real image involved).
set -u
root=$(mktemp -d)
mkdir -p "$root/usr/share/kubuntu-default-settings/kf5-settings" "$root/etc/skel/.config"
printf '[General]\nLookAndFeelPackage=org.kubuntu.desktop\n' > "$root/usr/share/kubuntu-default-settings/kf5-settings/kdeglobals"
printf '[General]\n' > "$root/etc/skel/.config/kdeglobals"
ROOTFS="$root" bash /mnt/e/hcslinux222/distro/live/hooks/010-hscl-defaults.sh >/tmp/hook-sandbox.log 2>&1
echo "hook exit=$? (13-file assertion is expected to fail in the sandbox)"
echo '--- kubuntu defaults ---'; grep -n 'ColorScheme\|widgetStyle' "$root/usr/share/kubuntu-default-settings/kf5-settings/kdeglobals"
echo '--- skel ---'; grep -n 'ColorScheme\|widgetStyle' "$root/etc/skel/.config/kdeglobals"
rm -rf "$root"
