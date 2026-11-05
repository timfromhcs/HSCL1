#!/usr/bin/env bash
# Build the trilingual HSCL1 handbook (mdBook) into OUTDIR/{en,de,fr}.
# Usage: scripts/build-handbook.sh OUTDIR
set -Eeuo pipefail
out="${1:?usage: $0 OUTDIR}"
root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
command -v mdbook >/dev/null || { echo "missing mdbook (cargo install mdbook --locked)" >&2; exit 2; }
for lang in en de fr; do
  mdbook build "$root/handbook/$lang" -d "$out/$lang"
done
