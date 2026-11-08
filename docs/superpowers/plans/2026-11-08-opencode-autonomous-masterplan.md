# OpenCode autonomous masterplan (2026-11-08, session 2)

> Status: **ACTIVE**. Written by the OpenCode agent that took over after the Claude Code sessions.
> This file is an *execution plan*, not a second priority list: the single order stays
> `2026-11-08-selfheal-masterplan.md` section 3 (Master P0-P14). Everything here is a task under one of
> those P numbers and cites the ledger row it continues.
>
> Precedence unchanged: root `AGENTS.md` -> owner instructions -> code and reproducible tests -> the
> ecosystem contracts (`AGENTS_HCS_ECOSYSTEM_MASTER_2026-11-07.md`,
> `AGENTS_HCS_UNIFIED_SELF_HEALING_RESEARCH_MASTER_2026-11-08.md`,
> `AGENTS_HSCL1_BITAXE_MINER_RESEARCH_BRIDGE_MASTER_2026-11-08.md`) -> this plan.

## 1. Audit: where the previous agent stopped

Read-only reconnaissance before any edit: `git fetch --all --prune`, `gh pr list`, `gh release list`,
`gh run list`, the sub-repositories, `docs/BUILD_LOG.md` (818 lines), the live ledger
`2026-11-08-selfheal-masterplan.md`, `docs/CLAIMS.md`, and the code under `apps/hcseasymath/`,
`cli/hscl/src/`, `scripts/`.

**Repository state at handover (2026-11-08T00:03Z):**

| Item | State |
|---|---|
| `timfromhcs/HSCL1` `main` | `3a32d56`, then PR #36 merged in this session -> `bbb98dd` |
| Open PRs | only #36 (`codex/miner-plans`, 16/16 checks green); merged in this session |
| Releases | `v0.1.0-alpha.0`, `v0.1.1-alpha.0`, `v0.1.2-alpha.0` - all prereleases, unsigned |
| CI | last 8 runs green (main, branch, PR) |
| Branches | `codex/*` work branches, Dependabot branches (its own PRs were applied by hand in #33; the branches were deleted with the merge) |
| Sub-repositories | `CQ-HECS` `30c7f14` (2026-11-02), `hcs-foundry` `cfea6fa`, `hcs-discovery-studio` `fdd6ccb` - all unchanged since early November; `HCSPNP` is 404 and must not be created |
| Local CQ-HECS clone (WSL) | `~/src/CQ-HECS`, branch `hcspnp/integration` at `5ed3d2e` (guard + early-reply fix, **local only**) |
| Local HSCL1 WSL clone | `~/hscl1-src` at `2b65013` - **stale**, not the build source of truth any more; the Windows tree is |

**Where the work stopped:** the previous session finished MINER-0 (reading the miner contract,
verifying its claims, recording decisions M1-M7) and merged it as PR #36. The live ledger's next
actions were, in order: row 1 (read the listed CQ-HECS solver files in full, P0), row 2
(Studio guard, **done locally, blocked on owner approval to push**, B-P1), row 3 (`hscl cqhecs
status`, **done, PR merged** as part of #31), row 4 (Track E M2 remainder: simplify, solve, plot,
warm worker), row 5 (HCSUDA H3c-3b, **paused**, needs a free heavy slot), row 8 (durable scheduler,
**design note only, no code**), rows 11-13 (MINER-0 done, MINER-1 planned, MINER-2+ owner-blocked).

**Verified in this session before touching anything:** the HCSEASYMATH gate from the Windows tree
in WSL passes (`bash scripts/hcseasymath_gate.sh` -> `143 passed, 1 warning in 14.76s`), so the
documented "143 tests" is reproducible right now.

## 2. How the previous agent worked (so this session keeps the same standard)

Observed from the log, not assumed:

- Probe before implementing: call the real API/tool first (`llama-server --help`, `gh api`,
  `sp.integrate` behaviour) and let the probe decide the design.
- Tests first, with a red state shown; mutation checks to prove a test actually guards something.
- Smallest patch, targeted verify, subsystem verify, full gate (`python scripts/forge.py check`),
  then log, then commit. Three attempts per failure, then `BLOCKED` with a reproducer.
- Honest status vocabulary only: PLANNED, IMPLEMENTED, TESTED, VM-VERIFIED, HARDWARE-VERIFIED,
  EXPERIMENTAL, BLOCKED. A green unit test is not a booted image.
- Defects found in the agent's own gates and docs are fixed as defects (three real examples in the
  log: a summary reading keys the harness never writes, a menu section pointing at missing files,
  the provider-specific redaction bug found by property tests).
- Resource discipline: one heavy job at a time, VM disks on `C:\AI\vmtest`, no secrets printed.

This session keeps all of it and adds one thing the previous sessions did not have: a durable,
unprivileged loop (section 5) instead of a session-only ping.

## 3. Research answers to the open questions (read 2026-11-08)

| Question (source in the ledgers) | Answer | Consequence |
|---|---|---|
| SAT Competition **2026** resource limits and proof rules (open part of conflict C4; the 2026 rules page could not be retrieved earlier) | Main track: 300-600 instances, **5000 s**, **32 GB**, PAR-2 scoring, **certificates required in both SAT and UNSAT cases**, run on HoreKa/NHR@KIT (76-core Xeon Platinum 8368). Parallel: **1000 s wall clock**, one `m6i.16xlarge` (64 vCPU / 256 GB). Cloud: **200 s**, 100 x `m6i.4xlarge` (16 vCPU / 64 GB) with MPI/SSH. Experimental track for solvers whose techniques cannot yet emit certificates; AI-generated/AI-tuned sub-tracks carry the same limits and no main prizes. Source: `https://satcompetition.github.io/2026/tracks.html`, read 2026-11-08. | C4's limit gap is closed. A benchmark contract in HSCL1 must use **32 GB / 5000 s / PAR-2** as the main-track reference and must not present a run without a proof as an UNSAT result. The 2026 competition is already over (slides and `scores.csv` published 2026-07-23), so no deadline pressure exists. |
| SymPy `solve` output shape and reliability (needed for the `solve` operation) | Official guidance: `solve(..., dict=True)` for a consistent list-of-mappings shape; `solveset` is the newer univariate API and returns sets (`FiniteSet`, `ConditionSet`, intervals) with an explicit domain; the docs themselves show that `solve` can miss roots without `check=False` and can return `[]` for solvable equations (open issue #25849 with 1.14.0). Source: SymPy 1.14.0 docs "Solvers", "Solveset", "Solving Guidance", read 2026-11-08. | Plan changed: implement `solve` on `solveset` (univariate, explicit domain) **plus** substitution back into the original equation for every returned root, and mark `partial`/`unresolved` instead of returning an unverified set. Do not use `solve()` as the primary engine. |
| Lean 4 rigorous numerics (decision D12, "not searched" in the agent/formal ledger) | `LeanCert` (github `alerad/leanbound`) implements verified interval arithmetic for Lean 4 with an executable certificate checker and a proved soundness theorem; Lean 4.31.0 was released 2026-06-13. Source: GitHub README and lean-lang.org release notes, read 2026-11-08. | D12 stays **PLANNED**: the adapter is real work (toolchain pin, mathlib commit, certificate format) and does not belong before P0-P4. The ledger row can now name the concrete candidate instead of "not searched". |
| Repository override of the snapshot in the miner contract (C12) | Re-checked live: HSCL1 `main` is `bbb98dd` after this session's merge; `CQ-HECS`/`foundry`/`discovery` unchanged. | The contract's snapshot is stale again; the live ledger's section 1 is authoritative. |

Not researched on purpose: anything that needs an owner decision (CQ-HECS push, signing keys,
hardware contact, DE/FR native review, production deployment). A web search cannot grant those.

## 4. The plan for this session

Order follows the live ledger (lowest P first, dependency met, one heavy job at a time). "Light"
means no VM, no ISO build, no local model run.

### Wave 0 - reconcile and arm (this batch)

| ID | Master | Work | Gate |
|---|---|---|---|
| W0-1 | P0 | Merge PR #36 (green) | done: `bbb98dd` |
| W0-2 | P0 | This plan, the live-ledger rows, `BUILD_LOG.md`, C4 closure | `forge check` |
| W0-3 | P4 | Arm the 2-minute loop (section 5) | first tick observed |

### Wave 1 - Track E M2 remainder (P12, light, no owner needed)

| ID | Work | Detail | Gate |
|---|---|---|---|
| W1-1 | `simplify` operation | `sp.simplify` + an **equivalence check** against the input at rational sample points (same grading idea as the antiderivative check); `ok` only when the result is verified equivalent; `partial` when only numerically checked; never claim a size reduction that `count_ops` contradicts | new tests + gate |
| W1-2 | `solve` operation | `solveset` on an equation `lhs = rhs` for one variable, explicit domain; every element of a `FiniteSet` substituted back (`|f(root)|` exact or numerically tiny); `ConditionSet`/`ImageSet`/intervals -> `unresolved` or `partial`, never `ok` with a guessed list; complex roots reported as such | new tests + gate |
| W1-3 | `plot` data (only if 1-2 land green) | server-side sampling of `y = f(x)` on a bounded grid with an explicit point cap and a discontinuity policy; returns **data**, not an image claim | new tests + gate |
| W1-4 | Warm worker (only if 1-3 land green) | keep one child alive between requests with the same limits; measure the latency win instead of assuming it | latency numbers in the ledger |

Not in Wave 1: ODE lab, microprice, spintronics, Macaulay2 (each has a named blocker B4-B6 or a
later milestone).

### Wave 2 - durable scheduler (P4, ledger row 8, light)

Implement the design note `docs/research/SELFHEAL_SCHEDULER_DESIGN.md` exactly: one tick, global
lock with stale takeover, heavy-job lock, wall timeout below the interval, dry-run default,
atomic state file, three-failure rule, JSONL log. Tests are the seven listed in the note; they are
written first. Unprivileged, per-user state directory, never in the repository.

Why here: it is the honest version of the loop this session runs ad hoc, and it is a
`scripts/selfheal/` default lock group with no conflict.

### Wave 3 - P0 audit row 1 (light, read-only)

Read the files listed in ledger row 1 in the local CQ-HECS clone (`sat.py`, `sat_external.py`,
`drat.py`, `unified.py`, `sat_separator.py`, `omniwave/*`, `studio/app.py`, `provenance.py`,
`mcp_server.py`, `src/sat_solver.cpp`) and fill `HCSPNP_BASELINE.md` with a gap list carrying file
and line references. Read-only: no change to that repository, no push (B-P1 stays open).

### Wave 4 - MINER-1 documents (light, docs only)

ADR (receiver location, runtime, port choice with a conflict check, pairing) and schema drafts
`hcs.miner.event.v1`, `hcs.miner.heartbeat.v1`, `hcs.miner.batch.v1`, `hcs.miner.ack.v1` under
`docs/miner/`. No receiver code, no device contact, no firmware change (M2/M4/M5).

### Wave 5 - NP benchmark harness (owner request, light; P4/P5, ledger rows 16-21)

Added by the owner's instruction in the running session (2026-11-08): research NP-hard and "hardest"
problems on the web, find out how to build them as code benchmarks, adapt the plans, build them in and
try to build solvers. This does not reorder P0-P14: the work sits inside **P4** (one benchmark control)
and **P5** (benchmark corpus). The research and its limits are in `docs/research/NP_BENCHMARK_RESEARCH.md`.

| Step | Row | Work | Done when |
|---|---|---|---|
| W5-1 | 16 | SAT slice: strict DIMACS, generators with known answers, independent model and RUP verifiers, CDCL and WalkSAT baselines, runner with PAR-2 | **DONE**: 40 tests, 8 mutations red-then-reverted |
| W5-2 | 17 | Suite manifest, CLI, JSON report, light default suite | **DONE**: 13 tests, 7 mutations |
| W5-3 | 18 | Colouring, clique, Hamiltonian cycle (known-answer generators, independent verifiers, exact and greedy solvers) | **DONE**: 26 tests, 12 mutations |
| W5-4 | 19 | TSP and knapsack / subset sum | **NEXT**: tests + sweep |
| W5-5 | 20 | DRAT checker, optional external adapters, differential parser test vs CQ-HECS (read-only) | test report |
| W5-6 | 21 | Beyond NP: small exact #SAT and QBF tools | later |

Rules that carry over: a solver answer is never evidence (verifier or checked proof, otherwise `UNKNOWN`);
a contradiction with a known answer is a recorded `disagreement`; an unavailable solver is `unavailable`
(no silent fallback); pure Python solvers are baselines and the reports never call them competitive;
no licence-unclear tool (Concorde, LKH, OR-Tools: not confirmed) is bundled or called before a licence check.

### Not in this session (blocked or heavy)

| Item | Why not now |
|---|---|
| P1 push to `timfromhcs/CQ-HECS` | owner approval B-P1 |
| MINER-2+ firmware, flashing, device probes | owner approval M4, hardware |
| ISO build + VM boot/install gates | heavy; one at a time; host memory 20 GB total |
| HCSUDA H3c-3b (real Qwen3 layers, logits vs llama-server) | heavy; needs the free heavy slot |
| Release, tag, signing, Vercel production | owner-only (keys, deployment) |

## 5. The loop this session runs (2-minute heartbeat)

Mechanism: a **one-shot background wake** (`Start-Sleep 120` then a sentinel line) that completes
and notifies this agent; on every wake the agent performs exactly one ledger step, records it, and
arms the next wake. This is the local "monitored shell output" pattern with a one-shot heartbeat
instead of a `while` loop, because a never-ending background process produces no completion
notification in this harness.

Contract for every tick:

1. **Read** the loop state file `artifacts/loop/state.json` (outside Git history content, ignored
   path) and the live ledger section 5.
2. **Pick** the first row that is not DONE/BLOCKED, whose dependency is met, and whose work fits a
   light slot; never start a heavy job while another heavy job runs.
3. **Act**: smallest verifiable step. Tests first for code.
4. **Verify**: targeted test, then the relevant gate.
5. **Record**: `BUILD_LOG.md` entry, ledger row state, artifact paths.
6. **Commit and push** on the work branch; open or update a PR only for coherent batches.
7. **Arm** the next 120 s wake.

Hard rules for the loop: no force-push, no history rewrite, no merge without green CI, no release,
no cross-repository push, no secrets, no destructive disk operations, no weakening of a gate.
Three failed attempts on one row -> `BLOCKED` with the reproducer, then move to the next row.
The loop stops when the owner says so; it must never run as root and never on its own authority
extend to owner-only items.

## 6. Owner decisions still needed (unchanged, not guessed)

1. Push the CQ-HECS guard + bridge fix and open the PR there (**B-P1**).
2. Signing keys for tags/checksums, and the licence for a future public `hcsuda` repository.
3. Physical hardware boot session (Secure Boot firmware acceptance, suspend, Wi-Fi, audio).
4. DE/FR native review of user-facing strings.
5. Production deployment of the website.
6. Whether the durable scheduler may be enabled as a user-level scheduled task (choice of
   Task Scheduler vs cron) after its tests are green.

## 7. Evidence rules for this session's claims

- "done" means the gate for that item ran in this session and its exit code is recorded.
- The ICSE-style honesty rule from the previous sessions stays: a unit test is not a VM result, a
  schema is not a receiver, a design note is not a scheduler.
- Every claim added to `docs/CLAIMS.md` names the artifact or the command that produced it.
