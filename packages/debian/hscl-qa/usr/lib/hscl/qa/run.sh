#!/bin/sh
# Collect evidence for the VM test harness. Output goes to QA_OUT (default: the virtio port hscl.qa).
# Read-only: it only reads system state. Sections are "== name ==" followed by command output.
QA_OUT="${QA_OUT:-/dev/virtio-ports/hscl.qa}"
[ -e "$QA_OUT" ] || exit 0

section() { # name command...
  name="$1"; shift
  printf '== %s ==\n' "$name"
  if command -v "$1" >/dev/null 2>&1; then "$@" 2>&1; else echo "unavailable: $1"; fi
  echo
}

# Wait (bounded) for the desktop session so user-level checks are meaningful.
i=0
while [ "$i" -lt "${QA_WAIT:-240}" ] && ! pgrep -x plasmashell >/dev/null 2>&1; do
  i=$((i + 1)); sleep 1
done
sleep "${QA_SETTLE:-20}"

user="$(ps -o user= -C plasmashell 2>/dev/null | head -n 1 | tr -d ' ')"
{
  printf '== hscl-qa ==\nversion=1\nplasmashell_user=%s\n\n' "${user:-none}"
  section os-release cat /usr/lib/os-release
  section hscl-status hscl status --json
  section hscl-doctor hscl doctor --json
  section secure-boot mokutil --sb-state
  section apparmor aa-status --enabled
  section ufw ufw status verbose
  section listening ss -tulnH
  section failed-units systemctl --failed --no-legend
  section sysctl sysctl kernel.kptr_restrict kernel.dmesg_restrict fs.protected_symlinks
  section look-and-feel-packages ls /usr/share/plasma/look-and-feel
  if [ -n "$user" ] && command -v runuser >/dev/null 2>&1; then
    section user-lookandfeel runuser -l "$user" -c "kreadconfig6 --file kdeglobals --group KDE --key LookAndFeelPackage"
    section user-colorscheme runuser -l "$user" -c "kreadconfig6 --file kdeglobals --group General --key ColorScheme"
    section user-shortcuts-overview runuser -l "$user" -c "kreadconfig6 --file kglobalshortcutsrc --group kwin --key Overview"
    section user-panels runuser -l "$user" -c "grep -c plugin= ~/.config/plasma-org.kde.plasma.desktop-appletsrc"
  fi
  echo "== end =="
} > "$QA_OUT"
