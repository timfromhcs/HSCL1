# HCSEASYMATH baseline (measured 2026-11-08)

Every row has a command or path. Nothing here is carried over from the contract's snapshot.

| Fact | Value | How observed |
|---|---|---|
| Repository | `timfromhcs/HSCL1`; working branch `codex/hscl1-v1` at `4f4e61b`; `origin/main` at `c261f90` (merge of PR #27) | `git rev-parse --short origin/main HEAD` |
| Version | `0.1.3-alpha.0` | `VERSION` |
| HCSUDA | H2 complete and merged (PRs #23-#25), H3a-H3c-3a merged or pushed (PRs #26, #27, `4f4e61b`): GGUF reader, dequantisation (7 types), CPU transformer block and Qwen3-style layer, GPU block | `docs/BUILD_LOG.md`, `hcsuda/benchmarks/amd-radeon-680m/selftest.json` |
| HCSUDA doc drift | `hcsuda/README.md`, `hcsuda/docs/CAPABILITY_MATRIX.md` and the 2026-11-07 masterplan section 12 still listed H2 as planned; reconciled in this session from the evidence above | `git diff` of the reconciliation commit |
| Local gates | `python scripts/forge.py check`: pytest, `bash -n`, shellcheck (WSL), secret scan - OK on the last commit | `artifacts/forge/20261107-223922/summary.json` |
| Host | Windows 11, Ryzen 7 7735HS, Radeon 680M, ~24 GB shared RAM | root `CLAUDE.md`, `hcsuda caps` |
| Host Python / Node | Python 3.13.13, Node 22.23.1, npm 11.21.1 | `python --version`, `node --version` |
| Linux gate host | WSL "Ubuntu" = 26.04.1 LTS, Python 3.14.4, `python3.14-venv` 3.14.4-1ubuntu0.2 installed | `wsl.exe -e bash -c 'cat /etc/os-release; python3 --version'` |
| Optional tools | `macaulay2` candidate 1.25.11+ds-4 in resolute (not installed); Lean not installed | `apt-cache policy macaulay2` in WSL |
| Reference package pattern | `packages/debian/hscl-cqhecs/` (launcher, desktop entry, hash-pinned wheels, no autostart) - to be read in full at milestone M9, not copied blindly | contract 1.5 |
| Heavy jobs running during this session | none besides short GPU selftests; no VM, no local model server | process list, memory rule "one heavy thing at a time" |
| Untracked owner files | `AGENTS_HCSEASYMATH_HSCL1_FIRST.md`, `AGENTS_HCSUDA_HCSWAVER_UNIFIED_MASTERPLAN.md`, `AGENTS_HCSWAVER_MASTERPLAN.md`, `AGENTS_HCS_GENESIS.md` | `git status` |
