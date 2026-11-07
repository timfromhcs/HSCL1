# HCSPNP execution plan (Track P)

> Status: **ACTIVE** from 2026-11-08. Written after the owner contract `AGENTS_HCSPNP_HSCL1_LATEST.md` (German, untracked)
> and a three-stage investigation (repositories, web search, crawl) recorded in `docs/research/HCSPNP_RESEARCH_LEDGER.md`.
>
> **Authority.** Root `AGENTS.md` wins, then source and tests, then `CLAIMS.md`/`BUILD_LOG.md`, then the contract, then this plan.
> The live ledger is `2026-11-08-selfheal-masterplan.md`; this file adds Track P steps and their order.
> Owner rule kept verbatim: *Reuse first. Measure second. Verify every claim. Integrate once.*

## 0. What the investigation changed

| Finding (evidence) | Effect on the plan |
|---|---|
| The desktop entry runs `hscl-cqhecs doctor` in a terminal; it never starts the Studio | P-M1 is not "polish": the launcher must be given a `studio` command, and the status must stay documented as it is until then |
| The Studio HTTP server has no Host/Origin/token check; POST routes start solver jobs | **Guard first, launcher second** (decision P2). Starting it from an icon would widen exposure |
| `python-sat 1.9.dev21` resolves for cp314; the OS runtime pin omits it | CaDiCaL becomes an optional, confirmed, hash-pinned step (P4), not a default |
| SAT Competition 2025 checks proofs with dpr-trim, GRAT or VeriPB | The in-repo DRAT checker stays an independent check, never a competition claim (P5) |
| RLAF injects variable weights and polarities; abstract-only evidence | Learned guidance is a branching hint, opt-in, baseline preserved (P6) |
| `T_dense`/`T_sparse` are theory without a checker | No "proof-checked count" claim for any tensor backend (P7) |
| CQ-HECS suite never run from a clean checkout here; docs contradict `pyproject.toml` on Python 3.14 | P-M0 runs it and records the result before any code change |

## 1. Order across tracks (single source: the live ledger)

The priority list lives in **`2026-11-08-selfheal-masterplan.md` sections 3 and 5** and follows the Ecosystem Master P0-P14. This plan keeps only
the Track P detail below; it does not carry its own order. Locks follow the Master format (ledger section 4). Mapping of this plan's milestones:

| This plan | Master | Note |
|---|---|---|
| P-M0 audit | P0 | PR #29 landed, suite recorded; full file reading open |
| P-M1a upstream fixes (local, not pushed) | P1 | bridge early-reply fix committed locally; Studio guard next |
| P-S1 status wrapper | P2 | takes the `cli/hscl/` lock |
| P-M1b launcher `studio` + desktop entry | P2 | blocked until a guarded Studio is pinned |
| P-M2 proof UX | P3 | - |
| P-M3 #SAT separator | P5 | - |
| P-M4 learned guidance | P11 | - |
| P-M5 tensor counting | P10 | - |
| P-M6 streaming/storage | P9 | - |
| P-M7 HCSUDA | P8 | - |
| P-M8, P-M9 | P2 / P14 | - |
| Q | P13 | - |

## 2. Milestones (numbering follows the contract)

| M | Deliverable | Gate | State |
|---|---|---|---|
| **P-M0** | Audit: SHAs, files read, CQ-HECS suite result from a clean clone, gaps with file references, list of the first small PR's files | reproducible report in `HCSPNP_BASELINE.md`; contract task list ticked | **IN PROGRESS** (repo, web and crawl stages done; clone and suite run next) |
| P-M1 | Integrated run path: guarded Studio (upstream), launcher `studio`, desktop entry opens it, CPU-only, same data in CLI/Studio/JSON, `hcs.run.v2` export | clean VM starts CQ-HECS from HSCL1, solves SAT and UNSAT fixtures, exports a run card | PLANNED (P-M1a prepared locally, needs B-P1 to leave the machine) |
| P-M2 | Proof UX: trust level visible everywhere, checker failures and engine disagreements tested | no UI/API string calls an unchecked UNSAT "certified" | PLANNED |
| P-M3 | #SAT separator first-class: plan-only preflight, induced width, table budget, brute-force oracle, 64-bit overflow tests | exact counts on all small fixtures; refusal never yields a partial count | PLANNED |
| P-M4 | Learned guidance baseline: document JW and FeatureScorer, keep negative results, RLAF-style prototype opt-in | baseline reproduces without a model; verdict independent of the model | PLANNED |
| P-M5 | Tensor counting research: separator-to-factor-graph, exact CPU reference, path planning, comparison | a delimited class with a measured advantage, or a documented null result | PLANNED |
| P-M6 | Streaming and storage: streaming DIMACS, file-backed CNF, truncation recovery, explicit GPU staging | memory cap works; no zero-copy claim without hardware proof | PLANNED |
| P-M7 | Optional HCSUDA: concrete BCP kernel with CPU oracle, compare with CQ-HECS Vulkan BCP | same correctness, measured improvement on named hardware, or a reason not to ship | PLANNED |
| P-M8 | HSCL1 package and Control Center: update `hscl-cqhecs`, card, EN/DE/FR, live and installed VM tests | installed system opens the Studio, CPU fallback, visible proof status | PLANNED |
| P-M9 | Release hardening: schema freeze, clean checkout, SBOM/licences, claims matrix | only verified features in release notes | PLANNED |
| Q (later) | QBF/TQBF as a separate track after proof contracts stabilise | not started; PSPACE-completeness is not an NP result | PLANNED |

## 3. P-M0 task list (this is the next work)

1. `git clone https://github.com/timfromhcs/CQ-HECS` into WSL `~/src/` (ext4, not the USB drive); record the SHA.
2. venv with Python 3.14 from the repository's own dev extras; record package versions.
3. Run `pytest` (SAT and unified tests first, then the rest); record counts, skips with reasons, wall time, peak memory.
4. Read in full: `README.md`, `docs/UNIFIED_SOLVER.md`, `cqhecs/unified.py`, `sat.py`, `sat_external.py`, `drat.py`, `sat_separator.py`,
   `omniwave/learned.py`, `studio/app.py`, `provenance.py`, `mcp_server.py`; skim `src/sat_solver.cpp` against section 23.1 questions.
5. Fill `HCSPNP_BASELINE.md` (suite result) and update the gap list with file and line references.
6. Report: the files of the first small PR and the test command (contract "Ergebnisbericht vor Implementierung").

## 4. Rules that apply to every Track P change

- CPU-only must stay complete. HCSUDA/Vulkan only through capability detection and a CPU comparison.
- SAT models are re-checked against the unchanged original CNF. Counts are exact or `UNKNOWN`.
- One heavy job at a time (no VM together with a model or a long solver run).
- Tests first; a failing test is never weakened. Three attempts per failure, then `BLOCKED` with the reproducer.
- Claims only with logs, tests, hashes or a checker. The forbidden claims of contract section 0.2 stay forbidden.
