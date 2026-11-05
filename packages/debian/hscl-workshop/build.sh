#!/usr/bin/env bash
# Mode fix-ups only. Workshop has no enable symlinks on purpose: udev starts it when a hypervisor port appears.
set -Eeuo pipefail
: "${STAGE:?}"
chmod 0755 "$STAGE/usr/lib/hscl/workshop/evidence.sh"
