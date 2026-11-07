# SELF-HEAL MASTERPLAN v6 — 24 h long-horizon run (started 2026-11-07 evening)

> Status: ACTIVE. Ordering authority is still `2026-11-07-masterplan-hcsuda-to-v1.md`
> (HCSUDA first, then HSCL1 to stable). This file adds: the measured resume state, the
> autonomous loop contract, the cron ping, and a ledger that is updated after every green batch.

## 0. Where the previous agent stopped (measured 2026-11-07)

- Previous session died mid-H2 (cli did not compile); repaired and committed as `e157bc0`.
- `origin/main` held a squash of PR #22 (H0/H1). Branch merged with `main` in `70bbf09`
  (conflicts resolved keeping the branch: it is a strict superset), pushed.
- No open PR for the branch; 4 Dependabot PRs (#1-#4) open, not ours.
- Gates this session: `cargo fmt/clippy -D warnings/test --all` in `hcsuda/` = 41 passed;
  `hcsuda selftest` PASS (saxpy, triad, gemv, gemm, softmax, layernorm, rmsnorm on Radeon 680M);
  `python scripts/forge.py check` OK (pytest 267 s, bash -n, shellcheck, secret scan).
- Release artefact `0.1.3-alpha.0` ISO exists and is boot/install/LUKS VM-verified (narrow); open
  alpha gaps: recovery key, /boot text, brand OCR (G10), shortcuts (G11 nothing bound), egress (P18),
  upgrade persistence (P19), SOURCE_OFFER (P22), Secure Boot firmware acceptance (G6).

## 1. Loop contract (every cron ping, every batch)

OBSERVE → CLASSIFY → HYPOTHESIS → cheapest EXPERIMENT → smallest FIX + test that fails without it →
VERIFY (targeted → subsystem → gate) → RECORD (ledger + BUILD_LOG) → commit → push.
Max 3 attempts per failure, then BLOCKED with evidence. Never weaken a gate. Local worker output is a hint.
Resource rules (owner memory): one heavy job at a time (no VM with a local model), VM disks on
`C:\AI\vmtest`, secrets never printed, `forge check` before commit.
The 2-minute cron is a ping, never a pause.

## 2. Ledger (update in place; a box needs a path or command as evidence)

| ID | Item | State | Evidence / next action |
|---|---|---|---|
| L-0 | Branch pushed and merged with main | DONE | `70bbf09` on origin |
| H2a | GEMM f32 tiled, softmax, layernorm, rmsnorm | TESTED, hardware-verified | `hcsuda/docs/MEASURED.md` |
| H2b | rope kernel + oracle | TESTED, hardware-verified | 3 oracle tests; selftest `rope` err 2.98e-7 vs tol 4.2e-5, deterministic (`hcsuda/benchmarks/amd-radeon-680m/selftest.json`); `Op::Rope` in the planner |
| H2c | int8 dot-product GEMM (`dotPacked4x8EXT`, i32 accumulate) | TESTED, hardware-verified | tiled kernel bit-equal (incl. tail shape), 1.38x faster than f32 tiled in the same run (0.195 vs 0.269 ms); untiled was 2.1x slower; planner now picks it from selftest evidence (`hcsuda plan gemm i8`) |
| H2d | f16 GEMM, cooperative-matrix GEMM | f16 storage GEMM TESTED + hardware-verified; coopmat PLANNED | f16: odd-shape error 0, 0.257 ms vs f32 0.27-0.38 ms (bimodal, cause unknown); next: coopmat 16x16x16 |
| H3 | GGUF reader, tiny transformer | PLANNED | after H2 |
| O-PR | PR to main, CI green, merge | PR #23 MERGED (`48a949c`, 14/14 green) | next batch: new PR from this branch |
| O2 | alpha gaps (see §0) | PLANNED | recovery key flow design first (host-only) |
| DOC | README/KNOWN_LIMITATIONS match artefact | PLANNED | update only with evidence |

## 3. Owner-only items (not guessed)

HCSUDA licence, public `hcsuda` repo, signing keys, physical hardware boot, legal review,
DE/FR native review, production website deploy, repository settings.
