# LIVE MASTER LEDGER (self-heal masterplan v7) — execution index for all tracks

> Status: **ACTIVE**. This file is the one live index (Ecosystem Master section 8.5). Track plans hold detail and must not
> carry their own competing priority lists. Last reconciled: **2026-11-08**, after landing PR #31 (`49673ab`) and reading the Unified Master of the same day (section 0, item 3b).
> A cron ping (every 2 minutes, session-only) only prompts: *take the first row of section 5 that is not DONE/BLOCKED and whose
> dependency is met*. It is never a pause.

## 0. Governing contracts and precedence

1. Root `AGENTS.md`, safety/security rules, explicit owner decisions (highest).
2. Source code and reproducible tests; then `docs/CLAIMS.md`, `docs/BUILD_LOG.md`, `docs/KNOWN_LIMITATIONS.md`, capability matrices.
3. **`AGENTS_HCS_ECOSYSTEM_MASTER_2026-11-07.md`** (owner companion, untracked): the single **priority list P0-P14**, the loop (section 8), file locks (8.6),
   benchmark contract (9), definition of done (16). Companions it builds on: `AGENTS_HCSPNP_HSCL1_LATEST.md`, `AGENTS_HCSEASYMATH_HSCL1_FIRST.md`.
3b. **`AGENTS_HCS_UNIFIED_SELF_HEALING_RESEARCH_MASTER_2026-11-08.md`** (owner companion, untracked, 3278 lines; it embeds the 7 November Ecosystem Master as Appendix A): fresh
   snapshot, six-layer architecture, the HCS Physics sub-track (parts III), the research evidence policy (part IV), the **update-before-next-work contract** (17.2), failure and
   rollback rules (19), lock groups (20) and the scheduler model (21). It keeps P0-P14 as the only order (section 27). Its root `AGENTS.md` blob
   (`88a8a9cc...`, 113402 bytes) was checked: identical to this repository's.
3c. **`AGENTS_HSCL1_BITAXE_MINER_RESEARCH_BRIDGE_MASTER_2026-11-08.md`** (owner companion, untracked, 2392 lines): the Miner Research Bridge (Bitaxe / ESP-Miner telemetry into HSCL1, datasets, SAT research). Treated as a **sub-track under this one order** (decision M1 in `docs/research/MINER_BRIDGE_RESEARCH_LEDGER.md`); its P0-P16 are MINER-0..16, not new priorities.
4. Track plans: `2026-11-08-hcspnp-plan.md` (Track P), `2026-11-08-hcseasymath-plan.md` (Track E), `2026-11-07-masterplan-hcsuda-to-v1.md`
   (HCSUDA gates, threat model, honesty rules; **its "HCSUDA first" ordering is superseded**, see C1).
5. Older notes and research.

The owner files above stay untracked until the owner decides otherwise.

## 1. Repository snapshot (re-fetched 2026-11-08; never reuse yesterday's)

| Repository | `main` | Notes | Command |
|---|---|---|---|
| `timfromhcs/HSCL1` | `49673ab` (merge of PR #31; PRs #29, #30, #31 all merged) | working branch `codex/hscl1-v1` is ahead of `main` by the HCSEASYMATH integrate commit and this reconciliation; open PRs: Dependabot #1-#4 only | `git fetch --all --prune`, `gh pr list --state open` |
| `timfromhcs/CQ-HECS` | `30c7f14` (2026-11-02), Apache-2.0 | 34 branches besides `main`: **31 behind, 0 equal, 0 ahead, 3 diverged** (`agent/v4-studio-mfit2-sat` 7/100, `claude/beautiful-rubin-3hcoym` 1/125, `claude/vigilant-ritchie-mscxry` 1/78); no open PRs; none merged or deleted by us | `gh api repos/timfromhcs/CQ-HECS/compare/main...<branch>` |
| `timfromhcs/hcs-foundry` | `cfea6fa` (2026-11-02) | not inspected beyond the SHA | `gh api repos/timfromhcs/hcs-foundry/commits/main` |
| `timfromhcs/hcs-discovery-studio` | `fdd6ccb` (2026-11-04) | separate product; not inspected | same |
| `timfromhcs/HCSPNP` | 404 | not a repository; never create it | `gh api repos/timfromhcs/HCSPNP` |
| local CQ-HECS clone (WSL `~/src/CQ-HECS`) | branches `hcspnp/early-reply-drains-body` (1 commit), `hcspnp/studio-guard` (2 commits) and `hcspnp/integration` (both merged), **local only, no push**, based on `30c7f14` | bridge fix alone 2740 / 0 / 110; `hcspnp/integration` (both) 2759 / 0 / 110 | `git -C ~/src/CQ-HECS branch -vv` |

## 2. Loop (Master 8.1, unchanged in spirit)

OBSERVE -> CLASSIFY -> HYPOTHESIS -> PRE-REGISTER -> CHEAPEST EXPERIMENT -> SMALLEST PATCH -> TARGETED VERIFY -> SUBSYSTEM VERIFY -> FULL GATE ->
RECORD -> REVIEW -> COMMIT -> PUSH/PR (only where authorised). Three meaningful fixes per failure, then `BLOCKED` with the reproducer. Never weaken
a gate; a green gate followed by a real failure means the gate is incomplete (example 2026-11-08: the Rust doc-command test; forge now covers it).
Resource rule: one heavy job at a time, VM disks on `C:\AI\vmtest`, no secrets printed, `forge check` before every commit.

## 3. Priority map (Master P0-P14 -> our work)

| Master | Meaning | State | Our IDs / evidence |
|---|---|---|---|
| **P0** | sync and freeze the real baseline | **IN PROGRESS**: PR #29 landed, snapshot refreshed, clean-clone CQ-HECS suite recorded; **open: read the listed SAT files in full, supersede stale docs** | `docs/research/HCSPNP_BASELINE.md`, section 1 here |
| **P1** | make the Studio safe and usable | **PATCH TESTED LOCALLY, not pushed**: 19 adversarial tests (red against `main`), guard on `hcspnp/studio-guard`, each guard proven by mutation, browser-verified, combined suite 2759 / 0 / 110 on `hcspnp/integration`; patches in `artifacts/hcspnp/cqhecs-patches/`; **needs owner approval to leave the machine (B-P1)** | P-M1a (2) |
| P2 | single HSCL1 command and launch path | PLANNED, lock needed | P-S1 `hscl` status wrapper, then P-M1b (blocked on P1 + a pinned release) |
| P3 | trust / proof UX | PLANNED | P-M2 |
| P4 | one benchmark and debugging control | PARTIAL | `scripts/forge.py` has two conditional steps (`hcseasymath (WSL)`, `doc commands (cargo)`); structured benchmark runner not started |
| P5 | classification, portfolio, benchmark corpus | PLANNED | P-M3 (+ corpus manifest proposal) |
| P6-P11 | smart cubing, XNF/parity, HCSUDA BCP, streaming, tensor #SAT, GNN/RLAF | PLANNED (research, after P0-P4) | P-M4..P-M7, P-M5; no code |
| **P12** | HCSUDA inference track + HCSEASYMATH completion | IN FLIGHT, slots only | Track E (M1 done); HCSUDA H3c-3b paused |
| P13 | QBF/TQBF | later | Q |
| *sub-track* | HCS Physics (not P15, not a new priority list) | **PHYS-0 DONE** (research ledger + integrator experiment, no code); PHYS-1 only after P0-P4 and the CPU reference gate | `docs/research/HCSPHYSICS_RESEARCH_LEDGER.md` |
| P14 | release hardening | later | P-M9, O-track |

## 4. Locks (Master 8.6 format: `LOCK: track - paths - owner - reason - start SHA`)

Shared groups: `cli/hscl/`; `apps/control-center/`; `packages/debian/`; `distro/live/verify-image.sh`; `scripts/remaster-iso.sh`, `scripts/forge.py` and shared CI
workflows; schemas/provenance interfaces; HCSUDA planner/capability contracts.

Default lock groups added by the Unified Master (20.3): `scripts/selfheal/` (does not exist yet), `apps/hcseasymath` API/schema/worker, a future `apps/hcsphysics`.

- **No lock held.** Released: `LOCK: E - apps/hcseasymath/ (core/symbolic.py, core/engine.py, api/app.py, schemas) - agent - integrate operation and graded derivative check - a82b7a5`; taken without a written line (same gap as C6), released when its PR merges. Released: `LOCK: P - cli/hscl/ (main.rs, new cqhecs.rs), docs/CLI.md - agent - read-only CQ-HECS status wrapper (Master P2, row 3) - a82b7a5`, released when its PR merged.
- Released: `LOCK: E - scripts/forge.py, .github/workflows/ci.yml (+ tests/unit/test_forge.py) - agent - hcseasymath gate step and CI job, doc-command step - 37d2f6d`;
  taken without being written down (a gap), released when PR #29 merged as `4bdcb2f`. From now on a lock line is written **before** editing these files.

## 5. Next actions (Master 17.9: owner, files, test command, dependency, state, evidence)

| # | Master | Action | Files / owner | Test command | Depends on | State | Evidence target |
|---|---|---|---|---|---|---|---|
| 1 | P0 | Read in full: `sat.py`, `sat_external.py`, `drat.py`, `unified.py`, `sat_separator.py`, `omniwave/{bcp,gpu,engine,learned}.py`, `studio/app.py`, `provenance.py`, `mcp_server.py`, `src/sat_solver.cpp` (section 23.1 questions); fill the gap list | read-only in the local clone; Repo Auditor | n/a (report) | - | **NEXT** | `HCSPNP_BASELINE.md` gap list with file and line references |
| 2 | P1 | Studio guard (tests first, then patch): **done locally**. Files: `cqhecs/studio/app.py`, `cqhecs/studio/static/app.js`, `tests/test_studio_security.py` (new), `tests/test_studio.py` (helpers send the token) | local clone branch `hcspnp/studio-guard`; Solver Engineer | `~/venvs/cq/bin/python -m pytest -q tests/test_studio_security.py` then the full suite | row 1 not required | **DONE locally; waiting for owner (B-P1) before any push** | `HCSPNP_BASELINE.md` |
| 3 | P2 | `hscl cqhecs status`: read-only, wraps `hscl-cqhecs doctor --json`, fixed argv, bounded time and output | `cli/hscl/src/cqhecs.rs`, `main.rs`, `docs/CLI.md` | `cargo test -p hscl` (Windows and WSL) | lock free | **DONE (PR pending CI)** | 12 tests; real launcher checked in both states |
| 4 | P12 | Track E M2: **integrate done locally** (`unresolved` honest, derivative check graded symbolic / numeric / partial); open: evaluate, simplify, solve, plot, warm worker | `apps/hcseasymath/` | `bash scripts/hcseasymath_gate.sh` | PR #29 (done) | IN PROGRESS | 134 tests; gate E6 partly |
| 5 | P12 | HCSUDA H3c-3b: real Qwen3 layers, tied head, logits vs llama-server | `hcsuda/` | per `hcsuda` gates | free heavy slot (no VM, no solver run) | PAUSED | logits comparison JSON |
| 6 | P4/P5 | Benchmark corpus manifest proposal (families, hashes, seeds), `hcs.run.v2` reuse | docs first | link and command validation | rows 1, 2 | PLANNED | proposal document |
| 7 | P0 | Review Dependabot #1-#4 one by one (MSRV, lockfile, action SHA pins, permissions); review notes only, no batch merge | `.github/`, `Cargo.lock` (locks apply) | full CI | lock free | **DONE locally, PR pending** | Dependabot #1-#4 reviewed one by one, applied together on a branch off current main (their bases were old). #1 checkout 4.2.2->7.0.1 (SHA 3d3c42e5 = tag v7.0.1; v5 Node 24, v6 separate credential file, v7 blocks fork PRs for pull_request_target/workflow_run: none used here). #2 upload-artifact 4.6.2->7.0.2 (SHA cf430e03 = tag v7.0.2; v6 Node 24 / runner >= 2.327.1, v7 ESM + `archive` input: only name/path/if-no-files-found used). #3 sha2 0.10->0.11.1 and #4 thiserror 1->2.0.21: each tested alone and combined on main: fmt, clippy -D warnings, 209 tests pass (WSL). hcsuda workspace still on sha2 0.10 / thiserror 1 (not touched). Dependabot PRs close when this lands. |
| 8 | P4 | Durable scheduler under `scripts/selfheal/` (Master 21): one tick, global lock, heavy-job lock, wall timeout below the interval, state in a user directory, unprivileged; today's 2-minute ping is session-only and not that scheduler | `scripts/selfheal/`, `scripts/forge.py` (lock) | dry-run first | rows 1-3 | **design note DONE** (`docs/research/SELFHEAL_SCHEDULER_DESIGN.md`), code PLANNED | tests listed in the note first |
| 9 | sub-track | PHYS-0: research ledger and integrator check | `docs/research/HCSPHYSICS_RESEARCH_LEDGER.md`, `docs/research/hcsphysics/integrator_check.py` | `python docs/research/hcsphysics/integrator_check.py` | - | **DONE** | orders, symplecticity and drift measured; no engine code |
| 11 | sub-track | MINER-0: read the Miner Bridge contract, verify its repository claims, record decisions M1-M7 (`docs/research/MINER_BRIDGE_RESEARCH_LEDGER.md`) | docs only | link and claim check | - | **DONE** (ESP-Miner heads, ahead/behind, partition table and RLAF abstract verified; 22 sources NOT READ; no device contact) | ledger file |
| 12 | sub-track | MINER-1: ADR (receiver location, runtime) and schema drafts for event, heartbeat, batch, ACK; then a receiver with a **simulated device** only | `docs/miner/`, later `cli/hscl`, `services/` (locks) | schema validation tests | rows 1-3, P0-P4 | PLANNED; schemas may start as docs, code waits for the core gates | ADR + schemas |
| 13 | sub-track | MINER-2+: firmware branch, device probe, flashing, backup, ESP-Miner / CQ-HECS PRs | other repositories and hardware | - | owner approval (M4) | **BLOCKED on owner** | - |
| 10 | sub-track | PHYS-1 entry gate: numerical-method spec reviewed by the owner, scene and evidence schema extending `hcs.run.v2`, CPU reference for pendulum and Kepler | docs and schemas first | per the ledger gate | owner review, P0-P4 | BLOCKED on owner review | - |

Order rule: lowest P-number first, dependency met, one heavy job at a time. Rows 1-3 are light; row 5 is the only heavy one.

### 5b. Update before the next work (Unified Master 17.2) - the closing checklist of every batch

1. exact changed files and commits; 2. commands with exit codes; 3. pass/fail/skip counts with skip reasons; 4. raw artifact paths; 5. `BUILD_LOG.md`; 6. the owning track plan and research ledger; 7. claims, limitations, architecture or decision record if affected; 8. this table; 9. release the lock; 10. only then pick the next row. A batch that cannot finish this stops at a stable checkpoint and does the update first.

## 6. HCSUDA and product ledger (carried forward, evidence in `BUILD_LOG.md`)

| ID | Item | State | Evidence / next action |
|---|---|---|---|
| H2a-d | tiled f32/f16/int8 GEMM, softmax/layernorm/rmsnorm, RoPE, coopmat | TESTED, hardware-verified (one iGPU) | `hcsuda/benchmarks/amd-radeon-680m/*.json`, `hcsuda/docs/MEASURED.md`; planner picks verified paths from selftest evidence |
| H3a/b | GGUF header reader; 7-type dequantisation | TESTED; checked on real models | bit-equal to official `gguf` on fixtures |
| H3c-1/2/3a | CPU block, GPU block (<=256 tokens), Qwen3-style layer on CPU | TESTED / hardware-verified vs CPU | err 1.85e-6, 4.6e-7, 1.9e-6; correctness kernels, not tuned |
| H3c-3b | real layers + logits vs llama.cpp | PAUSED (row 5) | - |
| O2 | alpha gaps: recovery key, /boot text, brand OCR, shortcuts, egress audit, upgrade persistence, SOURCE_OFFER, Secure Boot firmware acceptance | PLANNED | `docs/KNOWN_LIMITATIONS.md` |

## 7. Track E - HCSEASYMATH (Master P12; detail in `2026-11-08-hcseasymath-plan.md`)

| ID | Item | State | Evidence |
|---|---|---|---|
| E-M0 | research ledger, decisions D1-D10, blockers B1-B8, test matrix, integration page | DONE | `docs/research/HCSEASYMATH_*.md` |
| E-M1 | allow-list parser, exact derivative, isolated worker, loopback API with Host/Origin/token, hash-locked cp314 lock, forge step, CI job | **DONE - PR #29 merged `4bdcb2f`, 16/16 CI checks** (B3 answered: `setup-python` 3.14 works on `ubuntu-latest`) | `apps/hcseasymath/`, 112 tests |
| E-M2 | operations beyond differentiate | **integrate and evaluate done** (143 tests; `unresolved` honest; graded derivative check; evaluate refuses symbolic/hostile values and reports undefined points as `unresolved`); simplify, solve, plot, warm worker open | row 4 |
| E-M3..M13 | see the plan | PLANNED | - |

## 8. Track P - HCSPNP (Master P0-P11; detail in `2026-11-08-hcspnp-plan.md`)

HCSPNP is a feature family of CQ-HECS and HSCL1, not a product or repository.

| ID | Item | State | Evidence / next action |
|---|---|---|---|
| P-M0 | audit | **IN PROGRESS**: investigation (repos, web, crawl) done; clean-clone suite **2739 passed / 1 failed / 110 skipped** (177 s, 460 MB peak); one real defect found (hardware bridge answers early POST rejections without reading the body -> TCP RST -> lost 429), local fix: suite **2740 / 0 / 110**; full file reading open (row 1) | `HCSPNP_BASELINE.md`, `HCSPNP_DECISIONS.md` |
| P-M1a | upstream fixes in the local clone, tests first, not pushed: (1) bridge early-reply fix **committed** (`hcspnp/early-reply-drains-body`), (2) Studio guard **tested** (`hcspnp/studio-guard`, request-desync fix included) | DONE locally | B-P1 before any push |
| P-S1 | `hscl cqhecs status` | **DONE** locally, PR pending CI (row 3) | next in this chain: typed `hscl mcp` tool (lock needed), Control Center card, `studio` only after P1 ships |
| P-M1b | launcher `studio`, desktop entry opens it | BLOCKED on the guarded Studio in a pinned CQ-HECS release | decisions P2/P3 |
| P-M2..M9, Q | see the plan | PLANNED | - |

## 9. Reconciliation notes (conflicts found, resolution by authority and recency)

| # | Conflict | Resolution |
|---|---|---|
| C1 | `2026-11-07-masterplan-hcsuda-to-v1.md` orders "HCSUDA first, then HSCL1"; the Ecosystem Master (newer, ecosystem-level) orders P0-P14 with HCSUDA inference at P12 | Master ordering wins. The HCSUDA masterplan keeps its gates (H-G*, L*/C*), honesty rules and threat model. Banner added to that file |
| C2 | Master rule 17 ("no automatic merge or release unless a later explicit owner instruction") vs the standing instruction in the cron prompt and the first request ("main merge ... nur bei gruenem CI") | Interpreted as that explicit owner instruction: merge **only** when all CI checks are green, merge commit, never force; no release, no tag. Reported in every summary. Cross-repo pushes (CQ-HECS, Foundry, Discovery Studio) remain forbidden without owner approval (Master rule 16 = decision P10) |
| C3 | Master 8.5: do not copy one mutable priority list into many files; `2026-11-08-hcspnp-plan.md` had its own order table | Replaced there by a pointer to section 3/5 of this ledger |
| C4 | Ledger and plans cited SAT Competition 2025 proof rules; Master cites 2026 | Re-crawled: the 2026 output page states the same rule (proofs to `proof.out`, checked by dpr-trim, GRAT or VeriPB; verified LRAT/LPR via cake). Resource limits on the 2026 rules page were **not retrievable** (empty answer) |
| C5 | Master snapshot lists the branch as 4 commits ahead with PR #29 open | Now merged; section 1 shows the new `main` |
| C7 | The Unified Master (written at ~00:15) still lists PR #30 as open and PR #29 as the latest merge | Both are merged now (`49673ab`); section 1 shows the current state. The Master's own caution (a proposal in an open PR is not a merged rule) is why the ledger names the merge SHAs |
| C8 | The Unified Master ends with a 2-minute scheduler design (an OS cron entry running a `cron_tick.py` wrapper); this session's ping is a Claude Code session job | Different things. The ping is session-only, dies with the session and is not the durable scheduler; the durable one is row 8 and does not exist. Neither may run as root |
| C9 | A new domain (physics) tempts a P15 | Refused by the Master (section 27): it is a sub-track recorded under the one order, started as research only |
| C10 | The Miner contract numbers its priorities P0-P16 | Renamed MINER-0..16 under one order (M1); the Master's P0-P14 win |
| C11 | The Miner contract plans a network listener and device contact; root `AGENTS.md` forbids silent telemetry and broad privilege | Receiver off by default, opt-in pairing, private LAN bind (M3); no device contact until the owner authorises it (M4, M5) |
| C12 | The Miner contract's snapshot (HSCL1 `4bdcb2f`, no open PRs) is older than `3a32d56` | Ledger section 1 is the current state; contract facts re-checked where cheap (research ledger section 1) |
| C6 | `forge.py` and `ci.yml` are lock groups; Track E edited them without a written lock | Documented in section 4; rule now followed |

## 10. Owner-only items (not guessed)

Approval to open pull requests in `timfromhcs/CQ-HECS` (B-P1); HCSUDA licence and a public `hcsuda` repo; signing keys; physical hardware boot session; legal review;
DE/FR native review; production website deployment; repository settings (secret scanning, branch rules); creating `timfromhcs/hcseasymath`.
