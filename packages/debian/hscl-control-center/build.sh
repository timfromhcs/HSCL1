#!/usr/bin/env bash
# Builds the Qt app and installs it into $STAGE (prefix /). Needs cmake, ninja and Qt 6 dev packages
# (scripts/bootstrap-build-host.sh). Env: STAGE, ROOT.
set -Eeuo pipefail
: "${STAGE:?}" "${ROOT:?}"
b="$(mktemp -d)"
trap 'rm -rf "$b"' EXIT
cmake -S "$ROOT/apps/control-center" -B "$b" -G Ninja -DCMAKE_BUILD_TYPE=Release -DCMAKE_INSTALL_PREFIX=/ >/dev/null
cmake --build "$b" >/dev/null
DESTDIR="$STAGE" cmake --install "$b" >/dev/null
