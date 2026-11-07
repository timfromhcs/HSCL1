#!/usr/bin/env bash
# Gate for apps/hcseasymath on Linux (WSL Ubuntu 26.04 or CI): build a venv from the hash lock,
# check it, run the tests. The venv lives in the user's cache and is rebuilt when the lock changes.
set -Eeuo pipefail

root=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
app="$root/apps/hcseasymath"
cache="${XDG_CACHE_HOME:-$HOME/.cache}/hcsem-gate"

if ! python3 -c 'import sys; sys.exit(0 if sys.version_info >= (3, 14) else 1)'; then
  echo "hcseasymath gate: python3 is $(python3 --version 2>&1); Python 3.14 is required (the OS interpreter)" >&2
  exit 3
fi

want=$(sha256sum "$app/requirements-test.lock" | cut -d' ' -f1)
have=$(cat "$cache/lock.sha256" 2>/dev/null || true)
if [ ! -x "$cache/venv/bin/python" ] || [ "$have" != "$want" ]; then
  echo "hcseasymath gate: building venv from requirements-test.lock"
  rm -rf "$cache/venv"
  mkdir -p "$cache"
  python3 -m venv "$cache/venv"
  "$cache/venv/bin/pip" install -q --disable-pip-version-check --require-hashes --only-binary=:all: \
    -r "$app/requirements-test.lock"
  printf '%s' "$want" >"$cache/lock.sha256"
fi

"$cache/venv/bin/pip" check
cd "$app"
PYTHONDONTWRITEBYTECODE=1 exec "$cache/venv/bin/python" -m pytest -p no:cacheprovider -o addopts= -q \
  -W error::SyntaxWarning
