#!/usr/bin/env bash
# Print only the Control Center warnings, one per line (file:line:col  message).
set -u
here="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$here"
mapfile -t files < <(find apps/control-center/qml -name '*.qml' -type f | sort)
/usr/lib/qt6/bin/qmllint "${files[@]}" 2>&1 | grep '^Warning: ' | sed -E 's/^Warning: apps\/control-center\/qml\///'
