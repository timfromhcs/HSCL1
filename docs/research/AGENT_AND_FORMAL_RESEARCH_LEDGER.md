# Agent, formal-verification and rigorous-numerics research ledger

Source: Unified Master `AGENTS_HCS_UNIFIED_SELF_HEALING_RESEARCH_MASTER_2026-11-08.md`, parts IV and V. Evidence policy of that contract: rank sources, record dates,
label `ABSTRACT ONLY` when only an abstract was read. Review date 2026-11-08, read through the Firecrawl MCP (search excerpts and abstract pages).

| Source | Verified | Read depth | What it supports here | What it does not |
|---|---|---|---|---|
| VeRO: A Harness for Agents to Optimize Agents (Ursekar et al.), arXiv 2602.22480, ICML 2026 (accepted), v4 2026-06-02; code `github.com/scaleapi/vero` | yes, arXiv abstract and ICML poster page | ABSTRACT ONLY | Discipline for agent changes: versioned snapshots, budget-controlled evaluation, structured traces, fixed evaluation procedures | A claim that our agent got better; no immutable evaluation set exists in this project yet |
| FIRE-Bench (Wang et al. and others), arXiv 2602.02905, ICML 2026 | yes | ABSTRACT ONLY; the ICML lay summary says current agents get less than half of the rediscoveries right and answer inconsistently across runs | Known-result rediscovery before novelty (the contract's workflow) | General reliability of any agent; benchmark is machine-learning research findings, not physics or SAT |
| Goedel-Prover-V2 (ICLR 2026), arXiv 2508.03613 | yes | ABSTRACT ONLY | Pattern: formal checker feedback, self-correction, test-time exploration. Reported on MiniF2F: 8B at 84.6% pass@32; 32B flagship 88.1% pass@32, 90.4% with self-correction | That a local 8B model reproduces this on a Radeon 680M; no Lean toolchain is installed here |
| FormalMATH, OpenReview `mGzeNcMGFu` | exists; described as a large Lean4 benchmark of 5,560 problems | search excerpt only; **the contract's "28.31% Pass@32" figure was not confirmed** (the excerpt was cut off) | Reminder that informal fluency is not a machine-checked proof | Do not quote 28.31% until the paper is read |
| SWE-Compass, SWE-bench Science, Autonomous Science Bench, the 17 October 2026 lifecycle survey | **not searched** | NOT READ | - | Nothing may rely on them yet |
| FLINT/Arb ball arithmetic, LeanCert | **not searched** | NOT READ | Candidates for optional rigorous-numerics adapters (HCSEASYMATH decision D12) | - |
| Vulkan 1.4 memory and compute contracts | not re-read; HCSUDA already measures its own device | - | - | - |

## Consequences for the plans

- HCSEASYMATH: an optional Lean 4 worker behind a separate tool boundary with pinned toolchain and mathlib commit; Lean kernel acceptance counts as proof evidence only for
  the exact statement and environment. Rigorous numerics through Arb/FLINT as an optional adapter. Both are `PLANNED`, neither is installed, neither enters the ISO
  (see `docs/research/HCSEASYMATH_DECISIONS.md` D11, D12).
- Agent process: the self-improvement discipline of VeRO (versioned harness, fixed evaluation, traces, no editing of the evaluator by the candidate) applies to any future change
  of the scheduler or agent configuration. Until an immutable evaluation task set exists, no claim of agent improvement is made.
- Research claims in this repository carry a source, a retrieval date and a read depth. An abstract is not a result.
