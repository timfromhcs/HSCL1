#!/usr/bin/env bash
# Builds the offline handbook into $STAGE/usr/share/doc/hscl-handbook/{en,de,fr}. Env: STAGE, ROOT.
set -Eeuo pipefail
: "${STAGE:?}" "${ROOT:?}"
bash "$ROOT/scripts/build-handbook.sh" "$STAGE/usr/share/doc/hscl-handbook" >/dev/null
printf '<!doctype html><meta charset="utf-8"><title>HSCL1 Handbook</title><ul><li><a href="en/">English</a></li><li><a href="de/">Deutsch</a></li><li><a href="fr/">Français</a></li></ul>\n' \
  > "$STAGE/usr/share/doc/hscl-handbook/index.html"
chmod 0755 "$STAGE/usr/bin/hscl-handbook"
