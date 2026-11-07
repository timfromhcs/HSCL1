# LIVE MASTER LEDGER (self-heal masterplan v7) — execution index for all tracks

> Status: **ACTIVE**. This file is the one live index (Ecosystem Master section 8.5). Track plans hold detail and must not
> carry their own competing priority lists. Last reconciled: **2026-11-08**, after landing PR #29 (`4bdcb2f`).
> A cron ping (every 2 minutes, session-only) only prompts: *take the first row of section 5 that is not DONE/BLOCKED and whose
> dependency is met*. It is never a pause.

## 0. Governing contracts and precedence

1. Root `AGENTS.md`, safety/security rules, explicit owner decisions (highest).
2. Source code and reproducible tests; then `docs/CLAIMS.md`, `docs/BUILD_LOG.md`, `docs/KNOWN_LIMITATIONS.md`, capability matrices.
3. **`AGENTS_HCS_ECOSYSTEM_MASTER_2026-11-07.md`** (owner companion, untracked): the single **priority list P0-P14**, the loop (section 8), file locks (8.6),
   benchmark contract (9), definition of done (16). Companions it builds on: `AGENTS_HCSPNP_HSCL1_LATEST.md`, `AGENTS_HCSEASYMATH_HSCL1_FIRST.md`.
4. Track plans: `2026-11-08-hcspnp-plan.md` (Track P), `2026-11-08-hcseasymath-plan.md` (Track E), `2026-11-07-masterplan-hcsuda-to-v1.md`
   (HCSUDA gates, threat model, honesty rules; **its "HCSUDA first" ordering is superseded**, see C1).
5. Older notes and research.

The owner files above stay untracked until the owner decides otherwise.

## 1. Repository snapshot (re-fetched 2026-11-08; never reuse yesterday's)

| Repository | `main` | Notes | Command |
|---|---|---|---|
| `timfromhcs/HSCL1` | `4bdcb2f` (merge of PR #29) | working branch `codex/hscl1-v1` equals `main` plus local doc edits; open PRs: Dependabot #1-#4 only | `git fetch --all --prune`, `gh pr list --state open` |
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
| P14 | release hardening | later | P-M9, O-track |

## 4. Locks (Master 8.6 format: `LOCK: track - paths - owner - reason - start SHA`)

Shared groups: `cli/hscl/`; `apps/control-center/`; `packages/debian/`; `distro/live/verify-image.sh`; `scripts/remaster-iso.sh`, `scripts/forge.py` and shared CI
workflows; schemas/provenance interfaces; HCSUDA planner/capability contracts.

- **No lock held.**
- Released: `LOCK: E - scripts/forge.py, .github/workflows/ci.yml (+ tests/unit/test_forge.py) - agent - hcseasymath gate step and CI job, doc-command step - 37d2f6d`;
  taken without being written down (a gap), released when PR #29 merged as `4bdcb2f`. From now on a lock line is written **before** editing these files.

## 5. Next actions (Master 17.9: owner, files, test command, dependency, state, evidence)

| # | Master | Action | Files / owner | Test command | Depends on | State | Evidence target |
|---|---|---|---|---|---|---|---|
| 1 | P0 | Read in full: `sat.py`, `sat_external.py`, `drat.py`, `unified.py`, `sat_separator.py`, `omniwave/{bcp,gpu,engine,learned}.py`, `studio/app.py`, `provenance.py`, `mcp_server.py`, `src/sat_solver.cpp` (section 23.1 questions); fill the gap list | read-only in the local clone; Repo Auditor | n/a (report) | - | **NEXT** | `HCSPNP_BASELINE.md` gap list with file and line references |
| 2 | P1 | Studio guard (tests first, then patch): **done locally**. Files: `cqhecs/studio/app.py`, `cqhecs/studio/static/app.js`, `tests/test_studio_security.py` (new), `tests/test_studio.py` (helpers send the token) | local clone branch `hcspnp/studio-guard`; Solver Engineer | `~/venvs/cq/bin/python -m pytest -q tests/test_studio_security.py` then the full suite | row 1 not required | **DONE locally; waiting for owner (B-P1) before any push** | `HCSPNP_BASELINE.md` |
| 3 | P2 | `hscl` status wrapper: read-only, wraps `hscl-cqhecs doctor --json`, typed, no shell; docs only name it after it exists | `cli/hscl/` (takes LOCK P) | `cargo test -p hscl` | lock free | PLANNED | Rust tests + doc-command test green |
| 4 | P12 | Track E M2: evaluate / simplify / integrate (`unresolved` stays honest) / solve / plot, warm worker | `apps/hcseasymath/` | `bash scripts/hcseasymath_gate.sh` | PR #29 (done) | PLANNED | gate E6 |
| 5 | P12 | HCSUDA H3c-3b: real Qwen3 layers, tied head, logits vs llama-server | `hcsuda/` | per `hcsuda` gates | free heavy slot (no VM, no solver run) | PAUSED | logits comparison JSON |
| 6 | P4/P5 | Benchmark corpus manifest proposal (families, hashes, seeds), `hcs.run.v2` reuse | docs first | link and command validation | rows 1, 2 | PLANNED | proposal document |
| 7 | P0 | Review Dependabot #1-#4 one by one (MSRV, lockfile, action SHA pins, permissions) | `.github/`, `Cargo.lock` (locks apply) | full CI | lock free | PLANNED | per-PR notes |

Order rule: lowest P-number first, dependency met, one heavy job at a time. Rows 1-3 are light; row 5 is the only heavy one.

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
| E-M2..M13 | see the plan | PLANNED | row 4 above |

## 8. Track P - HCSPNP (Master P0-P11; detail in `2026-11-08-hcspnp-plan.md`)

HCSPNP is a feature family of CQ-HECS and HSCL1, not a product or repository.

| ID | Item | State | Evidence / next action |
|---|---|---|---|
| P-M0 | audit | **IN PROGRESS**: investigation (repos, web, crawl) done; clean-clone suite **2739 passed / 1 failed / 110 skipped** (177 s, 460 MB peak); one real defect found (hardware bridge answers early POST rejections without reading the body -> TCP RST -> lost 429), local fix: suite **2740 / 0 / 110**; full file reading open (row 1) | `HCSPNP_BASELINE.md`, `HCSPNP_DECISIONS.md` |
| P-M1a | upstream fixes in the local clone, tests first, not pushed: (1) bridge early-reply fix **committed** (`hcspnp/early-reply-drains-body`), (2) Studio guard **tested** (`hcspnp/studio-guard`, request-desync fix included) | DONE locally | B-P1 before any push |
| P-S1 | HSCL1 status wrapper | PLANNED (row 3) | - |
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
| C6 | `forge.py` and `ci.yml` are lock groups; Track E edited them without a written lock | Documented in section 4; rule now followed |

## 10. Owner-only items (not guessed)

Approval to open pull requests in `timfromhcs/CQ-HECS` (B-P1); HCSUDA licence and a public `hcsuda` repo; signing keys; physical hardware boot session; legal review;
DE/FR native review; production website deployment; repository settings (secret scanning, branch rules); creating `timfromhcs/hcseasymath`.
