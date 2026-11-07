# Genesis test matrix (what is actually exercised, 2026-11-07)

| Component | Test | Where it ran | Status |
|---|---|---|---|
| `hscl-cqhecs` control, payload, desktop entry, launcher rules | `tests/unit/test_pkg_cqhecs.py` (16) | Windows (Git-Bash), Linux (WSL, Ubuntu 26.04) | TESTED |
| `hscl-cqhecs` image gates (paired with `verify-image.sh`) | `tests/unit/test_cqhecs_in_image.py` (3) | Windows, WSL | TESTED (the gate itself runs only inside a build) |
| `install-runtime` against the network on Python 3.14.4 | manual run, `docs/genesis/EXECUTION_LOG.md` | WSL Ubuntu 26.04.1 | VERIFIED once, not an HSCL1 image |
| Debian package build and throwaway install/remove | `scripts/build-deb.sh`, `dpkg --root` | WSL | VERIFIED once |
| Package inside the ISO | `scripts/remaster-iso.sh` + `verify-image.sh` | dev build `0.1.3-dev2` (in progress) | PLANNED |
| Package on an installed HSCL1 / booted guest | none yet | - | NOT VERIFIED |
| Adapters, API, MCP, science slices | none | - | PLANNED |
