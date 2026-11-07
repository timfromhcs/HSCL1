# Plan: HCSWaver on HSCL1, folded into the two-track plan (2026-11-07)

Source: `AGENTS_HCSWAVER_MASTERPLAN.md` (untracked, owner's file, read 2026-11-07: sections 0-4, 12-14, 17-19 in full, the rest by heading). Parent contract stays `AGENTS.md`; Genesis companion plan: `docs/superpowers/plans/2026-11-07-genesis-parallel.md`.

## What HSCL1 owns here (and what it does not)
HCSWaver is a standalone application; HSCL1 owns only the integration: packages, launcher, `hscl` commands, a Control Center card, docs EN/DE/FR, image gates. It must not become a second SAT solver, a model warehouse, or run anything as root or at boot (masterplan 1.2, 13.1, 13.5). The standalone code lives in its own repository, which **does not exist yet** (`gh`: 404 for `timfromhcs/hcswaver`); creating it is an outward-facing act and waits for the owner's explicit go.

## Claims of the masterplan, checked 2026-11-07
| Masterplan says | Checked | Result |
|---|---|---|
| HSCL1 licence GPL-3.0-or-later | `LICENSE`, README badge | true |
| CQ-HECS 5.0.0, Apache-2.0, has a SAT subsystem and MCP | shallow clone `C:\AI\work\cq-hecs`: `sat.py`, `sat_external.py`, `drat.py`, `omniwave/`, `mcp_server.py`, wheel and `sha256sums.txt` in release v5.0.0 | true (APIs and failure semantics not yet read) |
| Foundry MCP over stdio, protocol 2025-06-18, tools machine_scan, machine_budget, models_list, datasets_*, vram_status, train_plan, eval_compare, gguf_quantize, no shell tool | `server/foundry/mcp_server.py` | true; **no text-generation tool in MCP**; generation exists internally (`runtime/llama_server.py` streams `/v1/chat/completions`, `gateway.py`) but is not exposed (masterplan 7.2 told us not to assume it) |
| Foundry licence MIT | `LICENSE` file | true (GitHub API says NOASSERTION) |
| HSCL1 README says 0.1.2-alpha.0 | `VERSION` | outdated: 0.1.3-alpha.0 |
| Ubuntu 26.04 packages for the dependency story | `apt-cache policy` in the Ubuntu 26.04.1 WSL distribution | `kissat` 4.0.3-2, `cadical` 2.1.3-2, `drat-trim` 0.0~git20240428, `elan` 4.1.2-3.1ubuntu1, `libwebkit2gtk-4.1-0` 2.52.6 (Tauri 2 target), `libayatana-appindicator3-1`, `cmake` 4.2.3, `libvulkan-dev`, `glslang-tools`. **No `lean4` package**: Lean toolchains come from `elan` over the network, so they are a first-run download on explicit user action, never in the ISO |
| Papers: SATLUTION 2509.07367, GaloisSAT 2603.28796, RLAF (ICLR 2026), AESAT (IJCAI 2026) | web search | the two arXiv records exist (GaloisSAT: authors report 8.41x on SAT and 1.29x on UNSAT instances of SAT Competition 2024, no independent replication found); RLAF and AESAT not re-verified by me |

## One family of science packages, shared adapters
`hscl-cqhecs` (built, in the dev2 image) is the CQ-HECS adapter base for both Genesis and HCSWaver. Same for the future Foundry adapter. Rule: HCSWaver and Genesis call these through their typed CLI/MCP contracts and never start their own llama-server or SAT stack (masterplan 1.2, 7.2; Genesis 1.3). Evidence vocabularies differ slightly (HCSWaver: PROPOSED/FORMALLY-VERIFIED, HSCL1: PLANNED); HSCL1 documents keep the HSCL1 words and map them.

## Order of work on the HSCL1 side
1. Done: `hscl-cqhecs` shell, runtime install from a pinned file, free-space and venv checks, image gates, dev2 image booted with 31 guest checks.
2. Now (docs only, no code): this plan, `docs/integrations/HCSWAVER.md` (status PLANNED), a **proposed** AGENTS.md section (`docs/integrations/HCSWAVER_AGENTS_SECTION.md`, awaiting the owner's approval to insert), Genesis ledger/decisions/blockers updated.
3. Next: read CQ-HECS `sat.py`/`sat_external.py`/`drat.py` and its MCP tools to fix the adapter contract from code (masterplan task 4); read Foundry's `runtime/llama_server.py` and `api/` for a real generation interface or record the gap (task 5).
4. Later, only after the standalone repository exists and a first vertical slice runs there: package design from the real `.deb` conventions, `hscl hcswaver` commands (read-only status/doctor first), Control Center card, handbook EN/DE/FR, VM install test (masterplan Phase 8, gate P8).

## Hard rules inherited, restated for this plan
No push, PR or merge without the owner asking (`gh` has ADMIN on HSCL1 and CQ-HECS, so this is a choice, not a limit). No model weights, Lean toolchains, solvers or benchmark sets in the ISO. Nothing autostarts in the live session, nothing listens until the user launches a workflow, loopback only, never root. No claim about P vs NP, GPU speed-ups or proofs without the checker and hardware evidence the masterplan demands.

## Open items that need the owner
- Create `timfromhcs/hcswaver` (public, under `timfromhcs`)? Not done.
- Approve inserting the proposed section into `AGENTS.md`.
- Licence for HCSWaver (masterplan suggests Apache-2.0 after a compatibility review; HSCL1 is GPL-3.0-or-later and must not receive GPL-incompatible code the other way round).
