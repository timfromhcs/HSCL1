# HCSPNP baseline (measured 2026-11-08)

Contract task: "update the repository table at every start". Every row has a command.

| Fact | Value | How observed |
|---|---|---|
| HSCL1 `origin/main` | `37d2f6d` at contract time (merge of PR #28); this working branch `codex/hscl1-v1` carries PR #29 (HCSEASYMATH M1) on top | `git log`, `gh pr list` |
| CQ-HECS `main` | `30c7f1484af01cf71a8843cca56ff38786eeaf92`, 2026-11-02 17:44 UTC, Apache-2.0, public, default branch `main` | `gh api repos/timfromhcs/CQ-HECS/commits/main`, `gh repo view` |
| HCSPNP repo | 404 | `gh api repos/timfromhcs/HCSPNP` |
| hcs-foundry | not inspected (the contract marks it optional) | - |
| CQ-HECS version | `cqhecs 5.0.0`, `requires-python >=3.11`; extras: `sat` (`python-sat>=1.8.dev0`), `dev`, `benchmark` | `pyproject.toml` |
| HSCL1 package state | `hscl-cqhecs` 0.0.0, `Architecture: all`, `Depends: hscl-base, python3 (>= 3.11)`, `Recommends: python3-venv`; runtime pinned to CPython 3.14; `python-sat` not included | `packages/debian/hscl-cqhecs/` |
| Desktop entry | `Exec=hscl-cqhecs doctor`, `Terminal=true` (status only; Studio is not started) | `.desktop` file |
| `hscl` CLI / MCP / Control Center | no CQ-HECS command, tool or card | `grep -rn cqhecs cli apps/control-center` returned nothing |
| Studio server | stdlib HTTP, 127.0.0.1, default port 8765, no Host/Origin/token | `cqhecs/studio/app.py` at `30c7f14` |
| HSCL1 local gates | `python scripts/forge.py check` OK incl. the `hcseasymath (WSL)` step | `artifacts/forge/20261107-230948/summary.json` |
| CQ-HECS test suite | **not yet run** from a clean checkout (P-M0 task) | - |
| Host | Windows 11, Ryzen 7 7735HS, Radeon 680M, WSL Ubuntu 26.04.1 (Python 3.14.4) | earlier baseline |
| Heavy jobs running | none during this review | process list |
