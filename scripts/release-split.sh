#!/usr/bin/env bash
# Split a large image into parts that fit GitHub's per-file release limit (2 GiB) and write SHA256SUMS.
#
# Usage: scripts/release-split.sh IMAGE OUTDIR [PART_MIB]      (default part size: 1900 MiB)
# Output: OUTDIR/IMAGE.part000, .part001, ... and OUTDIR/SHA256SUMS with one line per part AND one line for the whole image.
# Rejoin and verify with scripts/release-join.sh. Environment PART_BYTES overrides the size (tests only).
set -Eeuo pipefail

img="${1:-}"; out="${2:-}"; mib="${3:-1900}"
[ -f "$img" ] && [ -n "$out" ] || { echo "usage: $0 IMAGE OUTDIR [PART_MIB]" >&2; exit 2; }
case "$mib" in ''|*[!0-9]*) echo "PART_MIB must be a number" >&2; exit 2 ;; esac
[ "$mib" -le 1950 ] || { echo "PART_MIB must be at most 1950 (GitHub limit is 2 GiB per file)" >&2; exit 2; }
bytes="${PART_BYTES:-$((mib * 1024 * 1024))}"
name="$(basename "$img")"
mkdir -p "$out"
if ls "$out/$name".part* >/dev/null 2>&1; then echo "refusing to overwrite existing parts in $out" >&2; exit 2; fi

split -b "$bytes" -d -a 3 "$img" "$out/$name.part"
{
  ( cd "$out" && sha256sum "$name".part* )
  ( cd "$(dirname "$img")" && sha256sum "$name" )
} > "$out/SHA256SUMS"
echo "wrote $(ls "$out/$name".part* | wc -l) part(s) and $out/SHA256SUMS"
