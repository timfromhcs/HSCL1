#!/usr/bin/env bash
# Installs the single-source files from distro/security into $STAGE. Env: STAGE, ROOT.
set -Eeuo pipefail
: "${STAGE:?}" "${ROOT:?}"
install -D -m 0644 "$ROOT/distro/security/sysctl.d/90-hscl.conf" "$STAGE/etc/sysctl.d/90-hscl.conf"
install -D -m 0755 "$ROOT/distro/security/security-baseline.sh" "$STAGE/usr/lib/hscl/security-baseline.sh"
install -D -m 0644 "$ROOT/distro/security/systemd/hscl-security-baseline.service" "$STAGE/usr/lib/systemd/system/hscl-security-baseline.service"
ln -sf /usr/lib/systemd/system/hscl-security-baseline.service "$STAGE/etc/systemd/system/multi-user.target.wants/hscl-security-baseline.service"
