# Genesis research ledger (sources checked, append only)

| Date | Question | Source | Result | Status |
|---|---|---|---|---|
| 2026-11-07 | Default Python on Ubuntu 26.04 | packages.ubuntu.com `python3-defaults` (resolute) | 3.14.3-0ubuntu2 | ANSWERED |
| 2026-11-07 | Wheels for numpy/qiskit on CPython 3.14 manylinux | `pip download --only-binary=:all:` | all present, 62 MB | ANSWERED (measured) |
| 2026-11-07 | CQ-HECS 5.0.0 release assets and hashes | `gh release view v5.0.0`, `sha256sums.txt` | wheel 373,941 B, hash matches our pin | ANSWERED |
| 2026-11-07 | Is python3-venv in the base image | `dpkg-query --admindir` on the pristine root | no | ANSWERED (measured) |
| 2026-11-07 | CQ-HECS CLI health probe | real run of the 5.0.0 wheel | `version` is a subcommand, `--version` is not an option | ANSWERED (measured) |
| 2026-11-07 | Calamares recovery-key module | web search (one round) | none found; `luksbootkeyfile` adds a keyfile slot | PARTIAL (no confirming source for a custom step) |
| 2026-11-07 | Ubuntu 26.04 packages for solvers, Lean, Tauri 2 | `apt-cache policy` in the Ubuntu 26.04.1 WSL distribution | kissat 4.0.3-2, cadical 2.1.3-2, drat-trim 0.0~git20240428, elan 4.1.2-3.1ubuntu1, libwebkit2gtk-4.1-0 2.52.6; no lean4 package | ANSWERED (measured) |
| 2026-11-07 | Do SATLUTION (2509.07367) and GaloisSAT (2603.28796) exist | web search (arXiv records) | both exist; GaloisSAT authors report 8.41x (SAT) and 1.29x (UNSAT) on SAT Competition 2024; no independent replication found | ANSWERED (existence), claims UNVERIFIED |
| 2026-11-07 | RLAF (ICLR 2026) and AESAT (IJCAI 2026) | not re-checked | masterplan cites them; not verified by me | UNVERIFIED |
| 2026-11-07 | Foundry MCP tools and generation interface | `server/foundry/mcp_server.py` in the shallow clone | protocol 2025-06-18; tools machine_scan, machine_budget, models_list, datasets_*, vram_status, train_plan, eval_compare, gguf_quantize; no generation tool; generation internal in `runtime/llama_server.py` | ANSWERED (read from code) |
| 2026-11-07 | CQ-HECS SAT surface | shallow clone | `sat.py`, `sat_external.py`, `drat.py`, `omniwave/`, `mcp_server.py` present | ANSWERED (files exist; APIs not yet read) |
