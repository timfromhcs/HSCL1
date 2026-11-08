# Subplan S1-S: AREX-style agent runner, AI API, abliterated-model policy, updates/freeze, stress tests

> **Reconciled 2026-11-08:** The current OS release execution plan is
> [v1 release plan](2026-11-08-v1-release-plan.md); ecosystem priorities and evidence
> remain in the [live master ledger](2026-11-08-selfheal-masterplan.md).
> See [the per-plan audit](../../PLAN_INDEX.md) for current continuation notes.
> Older snapshots, release ladders and competing next-task orders below are historical;
> preserve the domain specifications and gates. Root `AGENTS.md` and later owner
> instructions govern conflicts. Model assistance for this continuation is local only;
> no Qwen Mythos/cloud inference.


> **For agentic workers:** REQUIRED SUB-SKILL: superpowers:executing-plans. Parent: `2026-11-06-masterplan-resume-s1.md`. Research: `docs/research/2026-11-06-four-round-loop-arex-api-updates-stress.md`.

**Goal:** turn the four-round research into testable tasks.
**Architecture:** all new code is host-testable first (Rust CLI + Python scripts); VM/image gates come in S2/S3/S6.
**Tech Stack:** Rust (clap), Python/pytest, bash + shellcheck, QEMU.

## Global Constraints
- Local only: loopback bind, no telemetry, no web tools by default.
- Model files are data, never executed; abliterated models never in the ISO.
- No claim of atomic updates or boot-into-snapshot; no claim copied from a model card without our own measurement.
- A task without a failing test first is not started.

## Review Focus
- The API key must never appear in logs, `ps`, JSON reports or `hscl report` (redaction test).
- The agent runner must stop at the round budget even if the model never calls `finish`.
- A tool outside the allow-list (e.g. `bash`, `visit`) is refused and recorded, never executed.
- A malformed or truncated XML tool call is a recorded error: no crash, no execution.
- The stress script must refuse to run outside a disposable VM.

## Track D - AI API and agent runner

### Task D2: AREX-protocol parser (first)
**Files:** Create `cli/hscl/src/toolcall.rs`; register in `main.rs`.
**Interfaces:** `pub enum Call { Tool { name: String, args: serde_json::Value }, Finish { answer: String } }`; `pub fn parse(text: &str, allow: &[&str]) -> Result<Vec<Call>, ParseError>`; `ParseError::{Incomplete, UnknownTool(String), Duplicate(String), TooLarge, Nested}`. Accepts `<tool_call>` blocks with a JSON body or `<function=NAME><parameter=KEY>VAL</parameter></function>`; body limit 64 KiB.
- [x] Failing tests first (8 of 10 red), then implemented: JSON form; XML form; unknown tool refused; truncated block gives `Incomplete`; nested gives `Nested`; duplicate parameter; oversize; 20000-string fuzz never panics (cargo test 128 passed)
- [x] fmt, clippy, test; commit. NOTE: `#![allow(dead_code)]` in `toolcall.rs` is temporary and must be removed in D4 when `hscl agent run` uses the module

### Task D3: runner loop with round budget
**Files:** Create `cli/hscl/src/agent.rs`.
**Interfaces:** `pub trait Chat { fn complete(&mut self, msgs: &[Msg]) -> anyhow::Result<String>; }`, `pub trait Tools { fn run(&mut self, name: &str, args: &serde_json::Value) -> anyhow::Result<String>; }`, `pub fn run(chat: &mut dyn Chat, tools: &mut dyn Tools, goal: &str, max_rounds: u32, log: &mut dyn FnMut(&Round)) -> Outcome`, `Outcome::{Finished(String), BudgetExhausted}`.
- [x] Tests with a scripted fake `Chat` (4, red first): stops on `finish`; stops at `max_rounds`; a refused tool is logged and never reaches `Tools`; results capped at 64 KiB; `log` once per round
- [x] Implemented in `cli/hscl/src/agent.rs` (cargo test 132 passed, clippy clean); `#![allow(dead_code)]` to be removed in D4

### Task D1: serve-spec generator (prints, never executes)
**Files:** Create `cli/hscl/src/serve.rs`; `hscl ai serve --print`; `docs/CLI.md` row (drift test enforces).
**Interfaces:** `pub fn serve_argv(o: &ServeOpts) -> anyhow::Result<Vec<String>>`; `ServeOpts { model: PathBuf, port: u16, ctx: u32, router_dir: Option<PathBuf>, models_max: Option<u32>, metrics: bool }`.
- [x] 8 tests, red first (6 failed against the stub): default argv carries the measured settings (`-ctk q8_0 -ctv q4_0 -c 4096 -rea off --reasoning-format deepseek -cram 1024 --sleep-idle-seconds 600 -np 1`), key only via `--api-key-file`, `--metrics` only when asked, ports < 1024 and contexts outside 512..262144 refused, model must be a `.gguf` inside the model storage (traversal, other roots, leading `-`, control characters, shell metacharacters refused), router mode with `--models-dir` inside storage and at most 2 resident models, 5000-case seeded fuzz never yields `--tools`/MCP-proxy/`--api-key`/foreign host
- [x] Implemented `cli/hscl/src/serve.rs` + `hscl ai serve [MODEL] [--port] [--ctx] [--api-key-file] [--router-dir] [--models-max] [--metrics]` (prints the command, never executes; `-t` deliberately omitted so llama.cpp uses the physical core count); doc row in `docs/CLI.md` (drift test green); cargo test 140 passed, clippy -D warnings clean; manual run: valid command printed, `/etc/passwd.gguf` and port 80 refused. Windows test fix: expected paths are built with `join`, not literal `/`

### Task D4 (S6): HTTP client `hscl agent run` against the local server, tested with a loopback stub server.

## Track E - abliterated-model policy
### Task E1: delta-card gate
**Files:** Create `ai/model-catalog/delta-card.schema.json`, `scripts/check_delta_cards.py`, `tests/unit/test_delta_cards.py`.
**Interfaces:** every catalog entry with `abliterated: true` references a card with `refusal_rate`, `tool_overcall_rate`, `kl_vs_stock`, `measured_by` (`own` or `third-party`), `date`; the gate fails on a missing field or when a shipped entry has only a third-party card.
- [x] 22 tests (red first): unmeasured / own / third-party cards valid; missing card, orphan card, bad `measured_by`, missing or out-of-range numbers, booleans as numbers, missing evidence file, non-https third-party source, non-null numbers on an unmeasured card, bad date, and an abliterated id or file name found in `distro/` or `packages/` are all errors; plain models need no card; the schema file lists the same required fields as the checker; the real repository passes
- [x] Implemented `scripts/check_delta_cards.py` (`--report`), `ai/catalog/delta-card.schema.json`, `ai/catalog/delta-cards.json` (path corrected: the catalog lives in `ai/catalog/`). Honest state of the real catalog: **6 abliterated models, 0 measured by us, 0 third-party, 6 unmeasured**; none appears in `distro/` or `packages/`. Not done: showing "unmeasured" in `hscl ai model info` / `list` (small follow-up)

## Track F - updates and image freeze
- [x] F1 honesty gate: `scripts/check_update_claims.py` + 25 tests (red first). Flags "atomic", "immutable" (also DE `atomar`/`unveränderlich`, FR `atomique`/`immuable`) and "boot into a snapshot" in README, `docs/` (not `docs/research`, `docs/superpowers`), `handbook/` and `website/` unless the same clause negates it (not, no, never, without, nicht, kein, pas, jamais, ...). Negation after the term counts ("booting into a snapshot is not available"); a negation in another clause does not ("Atomic updates, no downtime" is flagged). Real repository: no hits, and a test proves the gate scans README, docs and website (more than 20 files). Limitation: the check is word-based, a creative phrasing ("updates that never half-apply") is not caught
- [ ] F2 (S4) `packages/debian/hscl-snapshots`: apt hook active only on a btrfs root, depends on `snapper`; VM test on a btrfs install (MEASURE: Calamares creates `@` and `@home`)
- [ ] F3 (S5) minimal `systemd-sysext` image: merge/unmerge in the VM, `SYSEXT_LEVEL` match test

## Track G - stress and fault tests
- [x] G1 `scripts/stress_vm.sh`: refuses unless `HSCL_IN_DISPOSABLE_VM=1` and `/etc/hscl-vm-marker` exist; runs `stress-ng --klog-check --metrics-brief`, `fio` randrw 1 GiB, `memtester 256M 1`; writes JSON to `artifacts/stress/`. Tests with fake binaries on PATH: refuses without marker; writes summary; tool failure gives non-zero exit; shellcheck clean. DONE 2026-11-07: `scripts/stress_vm.sh`, 8 tests written first (`tests/unit/test_stress_vm.py`), shellcheck -S warning clean. Real run still MC: fio/stress-ng/memtester are not installed on this host; the gate needs the disposable VM (S2)
- [ ] G2 (S2) QEMU `blkdebug` cases under `tests/vm/blkdebug/`: injected EIO at the Nth write must make the installer fail safely
- [x] G3 proptest round trips for `redact.rs`, `toolcall.rs`, `hw.rs`; scheduled workflow for time-boxed `cargo-fuzz` and `cargo-mutants -f` on parsers
      DONE 2026-11-07: 13 `prop_` cases in the three modules (proptest, dev-dependency only) + `fuzz/` crate with two
      libFuzzer targets that `#[path]`-include the shipped files + `.github/workflows/fuzz.yml` (weekly/dispatch,
      `-max_total_time=300`, PROPTEST_CASES=20000, cargo-mutants on both parsers). The properties found a real defect:
      `redact` replaced user then host one after the other, so a short host rewrote the marker (`[[redacted]dacted]`);
      now one pass over the input, documented marker limitation. Not run so far: a real `cargo fuzz` run (needs nightly,
      CI only) and G3b prototype: splitting the crate into lib+bin so the targets link normally instead of `#[path]`
- [ ] G4 (S2) `autopkgtest` for `hscl-base` (`hscl version --json`, completions present)

## Track H - desktop resilience (S2 image)
- [ ] `verify-image.sh` checks `systemd-oomd` enabled and monitoring user slices, `zram-tools` zstd config, documented PSI thresholds; boot-time numbers before/after (MEASURE, no claim without numbers)

## Order
D2 -> D3 -> D1 -> E1 -> F1 -> G1 -> G3, then in S2: H, G2, G4; S4: F2; S5: F3; S6: D4.
