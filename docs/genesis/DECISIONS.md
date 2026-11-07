# Genesis decisions (ADR log, append only; HSCL1's own decisions stay in `docs/DECISIONS.md`)

## G-ADR-001 Companion file, not a replacement (2026-11-07) - ACCEPTED
`AGENTS_HCS_GENESIS.md` is read as a companion to `AGENTS.md`; where they differ, `AGENTS.md` wins. The companion file stays untracked (owner's file). Plan: `docs/superpowers/plans/2026-11-07-genesis-parallel.md`.

## G-ADR-002 The CQ-HECS runtime lives in the user's data directory (2026-11-07) - ACCEPTED
Default venv: `$XDG_DATA_HOME/hscl/cqhecs/venv`, not `/opt/hscl/venvs/cqhecs`. Why: Genesis 2.2 allows a user-managed environment where the app has write/update needs; Genesis 2.5 forbids a privileged helper for something the user's account can do; a root-owned `/opt` venv would need one. Consequence: nothing about the runtime is in the system image; removal never touches user data.

## G-ADR-003 python3-venv is recommended, not required (2026-11-07) - ACCEPTED
The base live image has Python 3.14 but not `python3-venv` (checked in the pristine root of the base ISO). A hard dependency breaks `dpkg -i` in `scripts/remaster-iso.sh`. `install-runtime` detects the missing module (exit 8) and says what to install.

## G-ADR-004 Pins are for CPython 3.14 only (2026-11-07) - ACCEPTED
`requirements-cp314.txt` is hash-pinned for CPython 3.14 / manylinux x86_64, the base image's interpreter. Other Python versions are refused (exit 5) instead of silently resolving other wheels. Revisit when the base moves.

## G-ADR-005 Work from fresh upstream checkouts, not the stale local clone (2026-11-07) - ACCEPTED
`E:\QHCS\CQ-HECS` is at 2.1.0; GitHub `main` is 5.0.0. Reading and measuring uses shallow clones under `C:\AI\work\`; the user's clone is not touched.
