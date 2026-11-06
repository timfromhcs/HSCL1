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

# Per-package generator: packages/debian/<name>/build.sh runs with STAGE, ROOT, VERSION set and may create
# generated (not committed) files such as wallpapers and logos. It is not shipped.
if [ -f "$stage/build.sh" ]; then
  STAGE="$stage" ROOT="$root" VERSION="$version" bash "$stage/build.sh"
  rm -f "$stage/build.sh"
fi
if [ -n "$bin" ]; then
  install -D -m 0755 "$bin" "$stage/usr/bin/hscl"
fi
if [ "$name" = "hscl-base" ]; then
  mkdir -p "$stage/usr/share/hscl"
  printf '{"product":"HSCL1","version":"%s","credit":"Made with love by hcsmedia","channel":"pre-alpha"}
'     "$version" > "$stage/usr/share/hscl/release.json"
fi
chmod 0755 "$stage/DEBIAN"
# drvfs/NTFS checkouts report 0777; dpkg requires maintainer scripts within 0555..0775 and sane file modes
for f in preinst postinst prerm postrm; do [ -f "$stage/DEBIAN/$f" ] && chmod 0755 "$stage/DEBIAN/$f"; done
chmod 0644 "$stage/DEBIAN/control"
# Normalise every payload file by CONTENT, never by the checkout's modes (NTFS/drvfs checkouts report 0777 for everything, which
# would ship world-writable files): scripts with a shebang and ELF binaries are 0755, everything else 0644; directories 0755.
while IFS= read -r -d '' f; do
  if [ "$(head -c 2 "$f")" = '#!' ] || [ "$(head -c 4 "$f" | od -An -tx1 | tr -d ' \n')" = '7f454c46' ]; then
    chmod 0755 "$f"
  else
    chmod 0644 "$f"
  fi
done < <(find "$stage" -type f ! -path "$stage/DEBIAN/*" -print0)
find "$stage" -type d -exec chmod 0755 {} +
mkdir -p "$out"
dpkg-deb --root-owner-group --build "$stage" "$out/${name}_${version//-/\~}_amd64.deb" >/dev/null
echo "$out/${name}_${version//-/\~}_amd64.deb"
