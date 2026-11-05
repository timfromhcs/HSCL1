#!/usr/bin/env bash
# Verify and rejoin a split image (see release-split.sh). Fails on ANY mismatch; never leaves a half-written image behind.
#
# Usage: scripts/release-join.sh DIR [--verify-only] [--force]
#   DIR must contain IMAGE.partNNN files and SHA256SUMS (as published in a release).
#   --verify-only  hash the concatenated stream without writing the joined file (used by CI: needs no second copy of the image)
#   --force        overwrite an existing joined image
set -Eeuo pipefail

dir="${1:-}"; shift || true
verify_only=0; force=0
for a in "$@"; do
  case "$a" in --verify-only) verify_only=1 ;; --force) force=1 ;; *) echo "unknown option: $a" >&2; exit 2 ;; esac
done
[ -d "$dir" ] || { echo "usage: $0 DIR [--verify-only] [--force]" >&2; exit 2; }
[ -f "$dir/SHA256SUMS" ] || { echo "missing $dir/SHA256SUMS" >&2; exit 2; }

# the whole-image line is the one that is not a .partNNN file
whole_line="$(grep -vE '\.part[0-9]{3}$' "$dir/SHA256SUMS" | tail -n 1)"
[ -n "$whole_line" ] || { echo "SHA256SUMS has no line for the whole image" >&2; exit 1; }
whole_sha="${whole_line%% *}"
name="${whole_line##* }"
name="${name#\*}"
case "$name" in */*|*..*|'') echo "unsafe image name in SHA256SUMS: $name" >&2; exit 1 ;; esac

echo "== verify parts"
parts_sums="$(mktemp)"; trap 'rm -f "$parts_sums" "${tmp:-}"' EXIT
grep -E '\.part[0-9]{3}$' "$dir/SHA256SUMS" > "$parts_sums"
[ -s "$parts_sums" ] || { echo "SHA256SUMS lists no parts" >&2; exit 1; }
( cd "$dir" && sha256sum -c "$parts_sums" )

# parts must be exactly the listed ones, in order, without gaps
mapfile -t listed < <(awk '{print $2}' "$parts_sums" | sed 's/^\*//' | sort)
for i in "${!listed[@]}"; do
  expect="$name.part$(printf '%03d' "$i")"
  [ "${listed[$i]}" = "$expect" ] || { echo "part sequence broken: expected $expect, found ${listed[$i]}" >&2; exit 1; }
done

echo "== join (${#listed[@]} parts)"
if [ "$verify_only" -eq 1 ]; then
  actual="$(cd "$dir" && cat "${listed[@]}" | sha256sum | cut -d' ' -f1)"
  [ "$actual" = "$whole_sha" ] || { echo "joined image hash mismatch" >&2; exit 1; }
  echo "OK (verify-only): $name sha256 $whole_sha"
  exit 0
fi

target="$dir/$name"
[ ! -e "$target" ] || [ "$force" -eq 1 ] || { echo "refusing to overwrite $target (use --force)" >&2; exit 2; }
tmp="$target.joining"
( cd "$dir" && cat "${listed[@]}" ) > "$tmp"
actual="$(sha256sum "$tmp" | cut -d' ' -f1)"
if [ "$actual" != "$whole_sha" ]; then rm -f "$tmp"; echo "joined image hash mismatch; nothing written" >&2; exit 1; fi
mv "$tmp" "$target"
echo "OK: $target sha256 $whole_sha"
