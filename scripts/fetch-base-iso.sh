#!/usr/bin/env bash
# Download the official Kubuntu 26.04.1 amd64 ISO and verify checksum + signature.
# Usage: scripts/fetch-base-iso.sh [DEST_DIR]   (default: ~/hscl1-build/upstream)
set -Eeuo pipefail

dest="${1:-$HOME/hscl1-build/upstream}"
base="https://cdimage.ubuntu.com/kubuntu/releases/26.04/release"
iso="kubuntu-26.04.1-desktop-amd64.iso"

for c in curl sha256sum gpg df; do
  command -v "$c" >/dev/null || { echo "missing command: $c" >&2; exit 2; }
done
mkdir -p "$dest"
cd "$dest"
free_kb=$(df --output=avail -k . | tail -n 1)
[ "$free_kb" -gt 20000000 ] || { echo "need >= 20 GB free in $dest" >&2; exit 2; }

curl -fsS -O "$base/SHA256SUMS"
curl -fsS -O "$base/SHA256SUMS.gpg"
curl -fL -C - --retry 2 -O "$base/$iso"

grep -F " *$iso" SHA256SUMS | sed 's/ \*/  /' > "$iso.sha256"
sha256sum -c "$iso.sha256"

# Signature: needs the Ubuntu CD Image Automatic Signing Key in the local keyring.
if gpg --verify SHA256SUMS.gpg SHA256SUMS 2>sig.log; then
  echo "GPG signature OK"
else
  echo "GPG signature NOT verified - see $dest/sig.log (import the Ubuntu CD signing key, fingerprint 843938DF228D22F7B3742BC0D94AA3F0EFE21092)" >&2
  exit 3
fi
echo "base ISO verified: $dest/$iso"
