#!/usr/bin/env bash
# Show where the qmllint warnings come from: per directory, per file and per message.
set -u
here="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$here"
lint=/usr/lib/qt6/bin/qmllint
CC=apps/control-center/qml
WP=packages/debian/hscl-desktop/usr/share/plasma/wallpapers/org.hcs.hscl1.rain
mapfile -t files < <(find "$CC" "$WP" -name '*.qml' -type f | sort)
out="$("$lint" "${files[@]}" 2>&1 || true)"
printf '%s\n' "$out" > "${TMPDIR:-/tmp}/qml-lint.out"

echo "== warnings per area"
for area in "$CC" "$WP"; do
  n=$(grep '^Warning:' "${TMPDIR:-/tmp}/qml-lint.out" | grep -c -- "$area/" || true)
  printf '%6s  %s\n' "$n" "$area"
done

echo
echo "== warnings per file"
grep '^Warning:' "${TMPDIR:-/tmp}/qml-lint.out" \
  | sed -E 's/^Warning: //' \
  | sed -E 's/^([^:]+):[0-9]+:[0-9]+: .*/\1/' \
  | sort | uniq -c | sort -rn

echo
echo "== warnings per message"
grep '^Warning:' "${TMPDIR:-/tmp}/qml-lint.out" \
  | sed -E 's/^Warning: [^:]+:[0-9]+:[0-9]+: //' \
  | sort | uniq -c | sort -rn

echo
echo "== total"
grep -c '^Warning:' "${TMPDIR:-/tmp}/qml-lint.out" || true
