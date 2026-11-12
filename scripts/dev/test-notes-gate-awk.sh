#!/usr/bin/env bash
# Prove the new image-gate assertion before a build has to: it must pass without the line and fail with it.
set -u
AWK='/^- show:/{s=1;next} /^- exec:/{s=0} s && /^  - notesqml$/{f=1} END{exit f}'
mk() { printf -- '- show:\n%s- exec:\n' "$1"; }

mk '  - welcome
  - partition
' > /tmp/g_off.conf
mk '  - welcome
  - notesqml
  - partition
' > /tmp/g_on.conf

for f in /tmp/g_off.conf /tmp/g_on.conf; do
  awk "$AWK" "$f"
  rc=$?
  case "$f:$rc" in
    /tmp/g_off.conf:0) echo "ok    $f -> exit 0 (step disabled, gate passes)" ;;
    /tmp/g_on.conf:1)  echo "ok    $f -> exit 1 (step wired, gate fails)" ;;
    *) echo "FAIL  $f -> exit $rc (unexpected)"; exit 1 ;;
  esac
done
rm -f /tmp/g_off.conf /tmp/g_on.conf
