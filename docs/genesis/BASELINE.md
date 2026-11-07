# Genesis baseline (B0), observed 2026-11-07

Read-only. Nothing in CQ-HECS or hcs-foundry was modified, fetched into a working tree or pushed. Source: `AGENTS_HCS_GENESIS.md` plus the checks below.

| Repo | Where | Observed | Note |
|---|---|---|---|
| HSCL1 | `E:\hcslinux222`, branch `codex/hscl1-v1` | `VERSION` 0.1.3-alpha.0; HEAD 7e0bc41 at this time; GitHub `main` tree d8f6533; workflows `ci.yml`, `fuzz.yml`, `release.yml`; 40+ local commits not on `origin` | `gh`: ADMIN, public |
| CQ-HECS | local `E:\QHCS\CQ-HECS`, clean, `main` | **local clone is stale: HEAD 22fd300, `pyproject.toml` version 2.1.0, `requires-python >=3.9`, tag v2.1.0** | GitHub `main` is 30c7f14: **version 5.0.0, `requires-python >=3.11`**, Apache-2.0, pushed 2026-11-02. Work must start from a fresh checkout of GitHub `main` in a scratch directory (planned `C:\AI\work\cq-hecs`), not from the stale clone |
| hcs-foundry | **no local clone** (only data dir `C:\Users\hcsme\.hcs-foundry`) | GitHub `main` commit cfea6fa, latest tag v7.5.0, pushed 2026-11-02; top level has `server/`, `web/`, `site/`, `tools/`, `AGENTS.md`, `PLAN.md`, `HCS_FOUNDRY_LONG_HORIZON_AGENT.md` | GitHub reports the licence as `NOASSERTION` although a `LICENSE` file exists: licence status must be read from the file before any redistribution |

Discrepancies with the companion file: it quotes the SHAs `30c7f14...` (CQ-HECS) and `cfea6fa...` (Foundry) as "tree" ids; for these two they are the **commit** ids of `main` (CQ-HECS tree is the same value only by the file's wording, the API returned `30c7f14` for both commit and tree on CQ-HECS; verify before quoting in a manifest). HSCL1's quoted version 0.1.2 is outdated.

## Capability map (initial, from the companion file; nothing here is implemented in HSCL1 yet)
| Capability | Owner repo | State |
|---|---|---|
| CQ-HECS app shell package `hscl-cqhecs` | HSCL1 packaging, CQ-HECS source | PLANNED |
| Foundry app shell package `hscl-foundry` | HSCL1 packaging, Foundry source | PLANNED |
| Genesis (`apps/genesis/`, schemas, adapters, MCP) | HSCL1 subtree, later own repo | PLANNED |
| Large model weights, datasets, training stacks | user-installed on demand | NOT IN ISO, by rule |
| Scientific adapters (Boltz-2, OpenFold3, Evo 2, scLDM, OpenMM, PBPK ...) | Genesis | PLANNED, none verified |

## Next safe actions
1. Shallow-clone GitHub `main` of CQ-HECS and Foundry into scratch directories on `C:`; record exact SHAs, `pyproject` metadata, ports, MCP tools, licence files, CI results.
2. Decide the first package (`hscl-cqhecs`) only after reading its v5.0.0 install surface (Python >= 3.11 vs the base Python of Ubuntu 26.04).

## Fresh shallow clones (scratch, `C:\AI\work\`, not part of HSCL1) - 2026-11-07
| Item | CQ-HECS | hcs-foundry |
|---|---|---|
| HEAD | `30c7f1484af01cf71a8843cca56ff38786eeaf92` | `cfea6fab4ea4bd0ffb1517dc59e98a80f830096a` |
| Package | `cqhecs` 5.0.0, console script `cq-hecs = cqhecs.cli:main` | `hcs-foundry` 7.5.0 (`server/pyproject.toml`, layout `server/foundry`) |
| Python | `>=3.11` (classifiers 3.11-3.14) | `>=3.11` |
| Dependencies | numpy>=1.24, qiskit>=0.45; extras `sat`, `dev`, `benchmark` | see `server/pyproject.toml`; lock files `requirements-lock.txt`, `requirements-train-lock.txt` (training kept separate) |
| Licence file | Apache-2.0 (file and GitHub agree) | **MIT** ("Copyright (c) 2026 timfromhcs and hcsmedia"); GitHub shows `NOASSERTION`, so the file, not the API, is the source |
| CI | `ci.yml`, `nightly.yml`, `release.yml` | `ci.yml` |
| Notes | README in EN/DE/FR; native C++/CMake path needs Vulkan SDK (per companion file, not yet re-verified in the CMake file) | `cli.py` refuses a non-loopback host unless `allow_lan` is set (loopback-by-default is real in source); port 8770 appears only in a benchmark fixture, not yet confirmed as the service default |

Open: which Python the base image provides (Ubuntu 26.04 `python3`) versus `>=3.11` for both; whether `qiskit` has wheels there; install size of the CQ-HECS venv. These decide the shape of `hscl-cqhecs` and are the first B1 measurements.
