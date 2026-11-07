# HCSEASYMATH execution plan (Track E)

> Status: **ACTIVE** from 2026-11-08. Written after reading the owner contract
> `AGENTS_HCSEASYMATH_HSCL1_FIRST.md` (untracked, 2141 lines) and after three research
> rounds, recorded in `docs/research/HCSEASYMATH_RESEARCH_LEDGER.md`.
>
> **Authority.** Root `AGENTS.md` wins. `2026-11-07-masterplan-hcsuda-to-v1.md` keeps ordering
> authority for HCSUDA work; `2026-11-08-selfheal-masterplan.md` is the live ledger and now
> carries Track E rows. This file only adds the HCSEASYMATH steps and the reasons for their order.

## 0. Ordering decision

The owner asked for the new plans to be followed before further work. So:

1. **Track E runs first.** Its M1 is light (Python, tests, no VM, no model, no GPU).
2. **HCSUDA H3c-3b is paused**, not dropped. It needs one heavy CPU run plus a local
   llama-server comparison, which must not overlap with anything else (owner rule: one heavy
   thing at a time). It resumes in a free slot, for example while Track E waits on CI.
3. Small HCSUDA hygiene (docs, evidence) may interleave; heavy HCSUDA work may not.
4. Nothing from Track E touches `hcsuda/`. HCSEASYMATH does not write its own GGUF reader or
   model runtime (contract 2.2); it will call HCSUDA only through the planner contract, later (M8).

## 1. What the research changed (full detail in the ledger and DECISIONS D1-D10)

| Change | Reason |
|---|---|
| Python **3.14**, cp314 hash-pinned wheels, gates in WSL Ubuntu 26.04.1 | OS ships 3.14; all 34 needed packages resolve as wheels (numpy 2.5.4, scipy 1.18.1, sympy 1.14.0, fastapi 0.162.2, pydantic 2.14.3) |
| No Python MCP SDK; extend Rust `hscl mcp` | contract 2.2; SDK is on a new 2.x major; CVE-2025-66416 below 1.23.0 |
| Own AST parser, never `sympify`/`parse_expr` on text | SymPy docs: `parse_expr` uses `eval`, avoid string input |
| Worker subprocess with timeout and memory cap for every operation | an in-process CAS call cannot be stopped safely |
| `Host`/`Origin` validation + per-launch token on the loopback API | DNS rebinding is the named attack on local servers |
| 2D plots default, Three.js 0.187 only optional | VM rendering unmeasured; WebGL2 fallback is software |
| Weighted mid is a labelled proxy, not the micro-price | Stoikov: limit of expected mid-prices, a martingale |
| Open research gaps become blockers B3-B8 | exact M2 `Tor` call, Stoikov estimator text, LLG convention, Lean sizes, CI Python 3.14, VM WebGL2 |

## 2. Milestones and their next concrete steps

| M | Deliverable | Gate | State |
|---|---|---|---|
| **M0** | Baseline, research ledger, decisions, blockers, test matrix, integration page, AGENTS proposal; HCSUDA doc drift reconciled | docs exist, every fact has a source, `forge check` OK | **DONE** (this commit) |
| **M1** | `apps/hcseasymath/` foundation: allow-list parser, exact derivative, worker with limits, loopback API with Host/Origin/token, hash-pinned lock | E1-E5 | **NEXT** |
| M2 | Math Studio MVP: evaluate, simplify, integrate (`unresolved` honest), solve, plot 1D/2D, history | E6 | PLANNED |
| M3 | ODE lab (`solve_ivp`, `y' = -k y` vs exact, abs+rel error) | E7 | PLANNED |
| M4 | Microprice proxy and macrospin demo with unit contracts | after B5, B6 | PLANNED |
| M5 | Homological algebra proof of concept, Macaulay2 cross-check | after B4 | PLANNED |
| M6 | `hscl math`, typed MCP tools, local storage | E8 | PLANNED |
| M7 | Frontend polish, Control Center card | UX gates | PLANNED |
| M8 | HCSUDA adapter | planner evidence matches device | PLANNED |
| M9 | `hscl-hcseasymath` package | E9 | PLANNED |
| M10 | dev ISO integration and VM acceptance | E10 | PLANNED |
| M11-M13 | RC integration, extraction, standalone repo (owner permission) | contract 14.5 | PLANNED |

### M1 in order (tests first at every step)

1. `apps/hcseasymath/pyproject.toml` (`requires-python >= 3.14`), `backend/hcseasymath/core/expression_ast.py`.
   Tests: accepts the documented grammar (`+ - * / **`, parentheses, numbers, symbols, allow-listed functions
   `sin cos tan exp log sqrt`); refuses the hostile corpus (D4) with `invalid_input`; Hypothesis fuzz never raises
   anything but the typed error.
2. `core/limits.py` (node/depth/literal caps) and `jobs/worker.py` (subprocess, timeout, `RLIMIT_AS`).
   Test: a deliberately non-terminating operation is killed inside the limit.
3. `core/symbolic.py`: `differentiate`. Test: `x**3 - 3*x**2 + 2*x` -> `3*x**2 - 6*x + 2`, checked by an
   independent numeric derivative at sample points, result schema `hcseasymath.result.v1`, deterministic run id.
4. `api/app.py`: `/api/v1/health`, `/api/v1/capabilities`, `/api/v1/symbolic/differentiate`; `Host`/`Origin`/token checks (E5).
5. `tools/make_lock.py`: turn `pip install --report` output into a `--hash` requirements lock; E3 in a fresh 3.14 venv in WSL.
6. End-to-end: start the real server, call, stop, assert no listener (E4).
7. Hook the WSL gate into `scripts/forge.py` only for changed paths under `apps/hcseasymath/`, so unrelated work stays fast.
8. Update the ledger, BUILD_LOG and CLAIMS; one PR; merge on green CI.

## 2a. Place in the Ecosystem Master (added 2026-11-08)

Track E is Master **P12**. M1 was Master P0 step 2 and is merged (PR #29, `4bdcb2f`, 16/16 checks; the CI job `HCSEASYMATH (Python 3.14, hash-locked)` passed, which
answers blocker B3). Priority order across tracks is kept only in `2026-11-08-selfheal-masterplan.md` (sections 3 and 5); do not copy it here.
Master section 13 asks for the same local-API protections and killable workers that M1 implements, and names the allow-list parser as a standing rule.

## 2b. Coordination with Track P (HCSPNP) - added 2026-11-08

Shared HSCL1 files (`cli/hscl/`, `apps/control-center/`, `distro/live/verify-image.sh`, `scripts/remaster-iso.sh`, `packages/debian/`) are edited
by one track at a time (lock rule P9, `2026-11-08-hcspnp-plan.md`). M1 touched none of them (`apps/hcseasymath/`, `scripts/forge.py`,
`scripts/hcseasymath_gate.sh`, `.github/workflows/ci.yml`, `tests/unit/test_forge.py`). M6 (`hscl math`, MCP tools) and M7 (Control Center card)
need the lock; Track P's `hscl cqhecs status` slice goes first because it is small and already specified. M1 state: merged.

## 3. Loops and limits

The self-heal loop of `2026-11-08-selfheal-masterplan.md` applies unchanged. The contract's six loops (A-F)
map onto it: A build repair, B mathematical correctness, C numerical stability, D UX, E performance, F packaging.
Three attempts per distinct failure, then `BLOCKED` with the reproducer. A mathematical test is never relaxed to
get a pass; a tolerance may only change with a written reason in `MATHEMATICAL_CONTRACTS.md`.

## 4. Owner-only items (unchanged)

Standalone repo creation and licence, signing keys, physical hardware, legal review, DE/FR native review.
