# Subplan S1-S: AREX-style agent runner, AI API, abliterated-model policy, updates/freeze, stress tests

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
- [ ] Tests with a scripted fake `Chat`: stops on `finish`; stops at `max_rounds`; a refused tool is logged and the loop continues; `log` is called once per round
- [ ] Implement; commit

### Task D1: serve-spec generator (prints, never executes)
**Files:** Create `cli/hscl/src/serve.rs`; `hscl ai serve --print`; `docs/CLI.md` row (drift test enforces).
**Interfaces:** `pub fn serve_argv(o: &ServeOpts) -> anyhow::Result<Vec<String>>`; `ServeOpts { model: PathBuf, port: u16, ctx: u32, router_dir: Option<PathBuf>, models_max: Option<u32>, metrics: bool }`.
- [ ] Failing tests: default argv has `--host 127.0.0.1`, passes the key by file or env (never the key text), no `--metrics`, no `--tools`, no `--webui-mcp-proxy`; port < 1024 rejected; router dir must lie inside the model storage path; fuzz of paths (traversal, spaces, option smuggling)
- [ ] Implement; commit

### Task D4 (S6): HTTP client `hscl agent run` against the local server, tested with a loopback stub server.

## Track E - abliterated-model policy
### Task E1: delta-card gate
**Files:** Create `ai/model-catalog/delta-card.schema.json`, `scripts/check_delta_cards.py`, `tests/unit/test_delta_cards.py`.
**Interfaces:** every catalog entry with `abliterated: true` references a card with `refusal_rate`, `tool_overcall_rate`, `kl_vs_stock`, `measured_by` (`own` or `third-party`), `date`; the gate fails on a missing field or when a shipped entry has only a third-party card.
- [ ] Failing tests: missing field; third-party-only shipped entry; valid card passes
- [ ] Implement; fix existing catalog entries honestly; commit

## Track F - updates and image freeze
- [ ] F1 honesty gate: a test fails when README/docs/website say "atomic", "boot into snapshot" or "immutable" outside an explicit negation allow-list
- [ ] F2 (S4) `packages/debian/hscl-snapshots`: apt hook active only on a btrfs root, depends on `snapper`; VM test on a btrfs install (MEASURE: Calamares creates `@` and `@home`)
- [ ] F3 (S5) minimal `systemd-sysext` image: merge/unmerge in the VM, `SYSEXT_LEVEL` match test

## Track G - stress and fault tests
- [ ] G1 `scripts/stress_vm.sh`: refuses unless `HSCL_IN_DISPOSABLE_VM=1` and `/etc/hscl-vm-marker` exist; runs `stress-ng --klog-check --metrics-brief`, `fio` randrw 1 GiB, `memtester 256M 1`; writes JSON to `artifacts/stress/`. Tests with fake binaries on PATH: refuses without marker; writes summary; tool failure gives non-zero exit; shellcheck clean
- [ ] G2 (S2) QEMU `blkdebug` cases under `tests/vm/blkdebug/`: injected EIO at the Nth write must make the installer fail safely
- [ ] G3 proptest round trips for `redact.rs`, `toolcall.rs`, `hw.rs`; scheduled workflow for time-boxed `cargo-fuzz` and `cargo-mutants -f` on parsers
- [ ] G4 (S2) `autopkgtest` for `hscl-base` (`hscl version --json`, completions present)

## Track H - desktop resilience (S2 image)
- [ ] `verify-image.sh` checks `systemd-oomd` enabled and monitoring user slices, `zram-tools` zstd config, documented PSI thresholds; boot-time numbers before/after (MEASURE, no claim without numbers)

## Order
D2 -> D3 -> D1 -> E1 -> F1 -> G1 -> G3, then in S2: H, G2, G4; S4: F2; S5: F3; S6: D4.
