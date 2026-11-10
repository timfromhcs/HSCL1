#!/usr/bin/env bash
# Sandbox check for the palette lines in the live-image hook (no real image involved).
# Case 1: kdeglobals carries [General] but no ColorScheme (the real Kubuntu default).
# Case 2: /etc/skel has no kdeglobals at all (the real base image) - the hook must create it.
set -u
root=$(mktemp -d)
mkdir -p "$root/usr/share/kubuntu-default-settings/kf5-settings"
printf '[General]\nLookAndFeelPackage=org.kubuntu.desktop\n' > "$root/usr/share/kubuntu-default-settings/kf5-settings/kdeglobals"
ROOTFS="$root" bash "$(dirname "$0")/../../distro/live/hooks/010-hscl-defaults.sh" > "$root/hook.log" 2>&1
echo "hook exit=$? (the 13-file assertion is expected to fail in the sandbox)"
echo '--- kubuntu defaults ---'; grep -n 'ColorScheme\|widgetStyle' "$root/usr/share/kubuntu-default-settings/kf5-settings/kdeglobals" || true
echo '--- skel ---'; grep -n 'ColorScheme\|widgetStyle' "$root/etc/skel/.config/kdeglobals" || echo 'MISSING'
rc=0
grep -q '^ColorScheme=HCSMidnight$' "$root/usr/share/kubuntu-default-settings/kf5-settings/kdeglobals" || rc=1
grep -q '^ColorScheme=HCSMidnight$' "$root/etc/skel/.config/kdeglobals" || rc=1
[ $rc -eq 0 ] || { echo '--- hook log (for the failure) ---'; tail -20 "$root/hook.log"; }
rm -rf "$root"
echo "sandbox result: $([ $rc -eq 0 ] && echo PASS || echo FAIL)"
exit $rc
