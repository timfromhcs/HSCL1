#!/usr/bin/env bash
# Build an HSCL1-owned .deb from packages/debian/<name>/ (a ready-made tree with DEBIAN/control).
# Usage: scripts/build-deb.sh <name> <outdir> [--bin /path/to/hscl]
set -Eeuo pipefail

name="${1:-}"; out="${2:-}"
[ -n "$name" ] && [ -n "$out" ] || { echo "usage: $0 <name> <outdir> [--bin PATH]" >&2; exit 2; }
shift 2
bin=""
while [ $# -gt 0 ]; do
  case "$1" in
    --bin) bin="${2:?--bin needs a path}"; shift 2 ;;
    *) echo "unknown argument: $1" >&2; exit 2 ;;
  esac
done
command -v dpkg-deb >/dev/null || { echo "missing dpkg-deb" >&2; exit 2; }

root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
src="$root/packages/debian/$name"
[ -f "$src/DEBIAN/control" ] || { echo "no such package tree: $src" >&2; exit 2; }
version="$(tr -d '\n' < "$root/VERSION")"

stage="$(mktemp -d)"
trap 'rm -rf "$stage"' EXIT
cp -a "$src/." "$stage/"
sed -i "s/^Version:.*/Version: ${version//-/\~}/" "$stage/DEBIAN/control"

# Generated, not committed: wallpaper from design tokens.
if [ -d "$stage/usr/share/wallpapers" ] || [ "$name" = "hscl-base" ]; then
  python3 "$root/scripts/gen-wallpaper.py" \
    "$stage/usr/share/wallpapers/HSCL1Midnight/contents/images/1920x1080.png" 1920 1080 >/dev/null
fi
if [ -n "$bin" ]; then
  install -D -m 0755 "$bin" "$stage/usr/bin/hscl"
fi
printf '{"product":"HSCL1","version":"%s","credit":"Made with love by hcsmedia","channel":"pre-alpha"}\n' \
  "$version" > "$stage/usr/share/hscl/release.json"
chmod 0755 "$stage/DEBIAN"
find "$stage" -type d -exec chmod 0755 {} +
mkdir -p "$out"
dpkg-deb --root-owner-group --build "$stage" "$out/${name}_${version//-/\~}_amd64.deb" >/dev/null
echo "$out/${name}_${version//-/\~}_amd64.deb"
