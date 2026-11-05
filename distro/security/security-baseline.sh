#!/bin/sh
# HSCL1 first-boot security baseline: firewall deny-incoming / allow-outgoing, then enable. Idempotent.
# `UFW` is overridable for tests. Never disables AppArmor, Secure Boot or any other protection.
set -eu
ufw="${UFW:-ufw}"
"$ufw" default deny incoming
"$ufw" default allow outgoing
"$ufw" --force enable
mkdir -p "${HSCL_STATE_DIR:-/var/lib/hscl}"
: > "${HSCL_STATE_DIR:-/var/lib/hscl}/security-baseline.done"
