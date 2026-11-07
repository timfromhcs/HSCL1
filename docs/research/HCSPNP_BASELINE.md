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
| CQ-HECS test suite (clean shallow clone of `30c7f14` in WSL ext4, Python 3.14.4, qiskit 2.6.2, numpy 2.5.4, qiskit-aer 0.18.2, stim 1.16.0, python-sat 1.9.dev21) | **2739 passed, 1 failed, 110 skipped, 1 deselected** in 176 s wall, 460 MB peak RSS. The failure is `tests/test_sha_bridge.py::test_rate_limit` (a second test of that file fails intermittently): a real, platform-dependent defect, see the next row. Skips: 4 need `qiskit-ibm-runtime` (not installed), several need the native `_cq_hecs_core` (not built), others are Windows/PowerShell only; one skips because python-sat is installed | `/usr/bin/time -v`, `pytest -rs` log |
| Defect found by that run (upstream, not fixed on `main`) | The hardware bridge (`cqhecs/hardware/bridge.py`) answers early rejections (404, 403, 405, 429) of a POST without reading the request body. On Linux the server then closes a socket that still holds unread data, the kernel sends a TCP RST, and the client sometimes loses the response: after the 30-per-window limit the 31st request gets 429, later ones alternate between 429 and `RemoteDisconnected`. A local fix (drain the declared body, bounded by `MAX_BODY`, before the early reply) makes the file pass 16/16 three times in a row and the whole suite pass (**2740 passed, 0 failed, 110 skipped**, 177 s, 457 MB peak); it exists only on the local branch `hcspnp/early-reply-drains-body` and is **not pushed** (decision P10) | reproduction script, codes list `[200 x30, 429, 'RemoteDisconnected', 429, ...]` |
| Host | Windows 11, Ryzen 7 7735HS, Radeon 680M, WSL Ubuntu 26.04.1 (Python 3.14.4) | earlier baseline |
| Heavy jobs running | none during this review | process list |
