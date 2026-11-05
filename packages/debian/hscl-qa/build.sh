#!/usr/bin/env bash
# Mode fix-ups and the enable symlink. Env: STAGE.
set -Eeuo pipefail
: "${STAGE:?}"
chmod 0755 "$STAGE/usr/lib/hscl/qa/run.sh"
mkdir -p "$STAGE/etc/systemd/system/graphical.target.wants"
ln -sf /usr/lib/systemd/system/hscl-qa.service "$STAGE/etc/systemd/system/graphical.target.wants/hscl-qa.service"
