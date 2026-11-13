#!/usr/bin/env bash
# Prove the Control Center lint ratchet is real: one unqualified access must turn the gate red.
set -u
here="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$here"
probe=apps/control-center/qml/ZzProbe.qml
trap 'rm -f "$probe"' EXIT
cat > "$probe" <<'QML'
import QtQuick

Item {
    Repeater {
        model: ["a", "b"]
        delegate: Text { text: modelData }
    }
}
QML
if bash scripts/dev/qml-gate.sh > /tmp/qml-gate-probe.log 2>&1; then
  echo "FAIL: the gate stayed green with an unqualified access in the Control Center"
  exit 1
fi
if grep -q 'control-center has 1 lint warnings' /tmp/qml-gate-probe.log; then
  echo "ok    the gate fails with 1 warning in the Control Center (budget 0)"
else
  echo "FAIL: the gate was red for another reason:"
  tail -20 /tmp/qml-gate-probe.log
  exit 1
fi
