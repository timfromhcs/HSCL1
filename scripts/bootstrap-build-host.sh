#!/usr/bin/env bash
# Install the packages the HSCL1 image build needs on an Ubuntu 26.04 builder (WSL2 or VM).
# Usage: scripts/bootstrap-build-host.sh        (uses sudo; never touches disks)
set -Eeuo pipefail
[ "$(id -u)" -ne 0 ] || { echo "run as a normal user; sudo is used where needed" >&2; exit 2; }
pkgs=(
  xorriso squashfs-tools debootstrap dpkg-dev mtools jq
  qemu-system-x86 qemu-utils ovmf swtpm
  shellcheck shfmt
  build-essential cmake ninja-build
  qt6-base-dev qt6-declarative-dev qt6-declarative-dev-tools qt6-tools-dev qt6-l10n-tools
  qml6-module-qtquick qml6-module-qtquick-controls qml6-module-qtquick-layouts qml6-module-qtquick-window
  qml6-module-qttest qml6-module-qtqml-workerscript qml6-module-qtquick-templates
  python3 python3-pytest
)
sudo apt-get update
sudo DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends "${pkgs[@]}"
echo "Also needed (not in apt): Rust via rustup (see rust-toolchain.toml) and mdBook: cargo install mdbook --locked --version 0.4.52"
