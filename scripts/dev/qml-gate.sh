#!/usr/bin/env bash
# Qt/QML gate: run the QML unit tests and lint every shipped QML file.
#
# Why this exists: until 2026-11-09 no QML test executed on the development host at all
# (`qmltestrunner` was not on PATH), so QML changes were only eyeballed. The binary lives in
# /usr/lib/qt6/bin on Ubuntu 26.04 even when `qmltestrunner6` is not linked into PATH.
#
# Policy for qmllint: exit codes are useless (it returns 0 even for syntax errors), so the
# output is parsed. `[syntax]` and `Error:` lines fail the gate. Warnings are counted per pool:
# the Control Center must stay at **zero**, the Plasma wallpaper plugin has a documented allowance
# because qmllint cannot resolve the Plasma/Kirigami/KCM QML modules on a host without them
# (docs/AUTONOMOUS_QUEUE.md, Q-19).
set -Eeuo pipefail

here="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$here"

find_qt() { # name -> absolute path or empty
  local name="$1" c
  for c in "/usr/lib/qt6/bin/$name" "$(command -v "${name}6" || true)" "$(command -v "$name" || true)"; do
    if [ -n "$c" ] && [ -x "$c" ]; then
      printf '%s\n' "$c"
      return 0
    fi
  done
  return 1
}

runner="$(find_qt qmltestrunner || true)"
lint="$(find_qt qmllint || true)"
if [ -z "$runner" ] || [ -z "$lint" ]; then
  echo "qml-gate: qmltestrunner/qmllint not installed (install qt6-declarative-dev-tools)" >&2
  exit 3
fi

export QT_QPA_PLATFORM="${QT_QPA_PLATFORM:-offscreen}"
export PATH="/usr/lib/qt6/bin:${PATH}"

run_suite() {
  echo "== qmltestrunner: $1"
  "$runner" -input "$1"
}

run_suite tests/qml_plugin
run_suite apps/control-center/tests/qml

# The C++ side of the Control Center (the CLI allowlist) had no gate at all until 2026-11-11: the Miner page was
# silently refused by `CliBackend::isAllowed` and only ever showed its error banner. Build and run the backend test
# when cmake and the Qt6 development files are present; skip with a reason otherwise (the gate must not depend on
# packages the host may not have).
if command -v cmake >/dev/null && [ -f /usr/lib/x86_64-linux-gnu/cmake/Qt6Quick/Qt6QuickConfig.cmake ]; then
  cc_build="${TMPDIR:-/tmp}/hscl-cc-build"
  rm -rf "$cc_build"
  if cmake -S apps/control-center -B "$cc_build" -DCMAKE_BUILD_TYPE=Release >/dev/null 2>&1 \
     && cmake --build "$cc_build" --target tst_backend -j"$(nproc)" >/dev/null 2>&1; then
    echo "== tst_backend (Control Center CLI allowlist)"
    ( cd "$cc_build" && QT_QPA_PLATFORM=offscreen ./tst_backend ) || exit 1
  else
    echo "qml-gate: could not build tst_backend (Qt6 dev files incomplete?)" >&2
    exit 1
  fi
else
  echo "qml-gate: tst_backend skipped (cmake or Qt6 dev files missing)"
fi

mapfile -t cc_files < <(find apps/control-center/qml -name '*.qml' -type f | sort)
mapfile -t wp_files < <(find packages/debian/hscl-desktop/usr/share/plasma/wallpapers/org.hcs.hscl1.rain \
  -name '*.qml' -type f | sort)
if [ "${#cc_files[@]}" -eq 0 ]; then
  echo "qml-gate: no QML files found" >&2
  exit 2
fi

# Two pools, because only one of them is our own code that can be fixed by editing it.
#
#   control-center  our application, plain QtQuick.Controls: the budget is 0 and must stay 0. The last 20 were
#                   fixed on 2026-11-13 (Q-19): `required property` for the model roles, `pragma ComponentBehavior:
#                   Bound` so delegates may reference the enclosing page's ids, and one local `qmllint disable`
#                   for the C++ context property `cli`, which no linter can resolve.
#   rain plugin     a Plasma wallpaper. qmllint cannot resolve `org.kde.plasma.plasmoid` (WallpaperItem),
#                   `org.kde.kirigami` or `org.kde.kcmutils` on a host without the Plasma QML modules, and each
#                   unresolved type cascades into `unqualified`/`missing-property` noise. The allowance is the
#                   measured count with those modules absent; lower it when the modules are installed, never
#                   raise it to make a red run green.
lint_area() { # name dir budget reason
  local name="$1" dir="$2" budget="$3" reason="$4" out warnings errors
  local -a files
  mapfile -t files < <(find "$dir" -name '*.qml' -type f | sort)
  out="$("$lint" "${files[@]}" 2>&1 || true)"
  warnings="$(printf '%s\n' "$out" | grep -c '^Warning:' || true)"
  errors="$(printf '%s\n' "$out" | grep -cE '^Error:|\[syntax\]' || true)"
  echo "qmllint: $name, $warnings warnings, $errors errors (budget $budget)"
  if [ "$errors" -ne 0 ]; then
    printf '%s\n' "$out" | grep -E '^Error:|\[syntax\]' >&2
    exit 1
  fi
  if [ "$warnings" -gt "$budget" ]; then
    echo "qml-gate: $name has $warnings lint warnings, over the budget of $budget. $reason" >&2
    printf '%s\n' "$out" | grep '^Warning:' | sed -E 's/^Warning: //' | sort | uniq -c | sort -rn | head -15 >&2
    exit 1
  fi
}

lint_area "control-center" apps/control-center/qml "${QML_CC_WARN_BUDGET:-0}" \
  "Our own QML must lint clean; fix the binding or suppress that single line with a reason."
lint_area "rain wallpaper" packages/debian/hscl-desktop/usr/share/plasma/wallpapers/org.hcs.hscl1.rain \
  "${QML_WP_WARN_BUDGET:-129}" \
  "These are cascades from the Plasma/Kirigami/KCM QML modules not being installed here - install them to lower it."
