#!/usr/bin/env bash
# Show the Secure Boot section of the in-guest report from the KVM run.
set -u
r="$HOME/sb-test/hscl1-report.txt"
if [ ! -f "$r" ]; then
  echo "no report yet"
  ls -la "$HOME/sb-test" 2>/dev/null | head -12
  exit 0
fi
echo "== report size: $(wc -c < "$r") bytes"
awk '/^== secure-boot ==/{p=1} p&&/^== /&&!/^== secure-boot ==/{p=0} p' "$r" | head -8
echo "== os-release name"
awk '/^== os-release ==/{p=1;next} p&&/^== /{p=0} p' "$r" | grep -E '^(NAME|PRETTY_NAME|HSCL1_VERSION)=' | head -3
