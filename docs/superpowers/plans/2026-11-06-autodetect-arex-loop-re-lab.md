# Subplan S1-R: Autodetect v2, AREX-style improvement loop, reverse-engineering lab

> **Reconciled 2026-11-08:** The current OS release execution plan is
> [v1 release plan](2026-11-08-v1-release-plan.md); ecosystem priorities and evidence
> remain in the [live master ledger](2026-11-08-selfheal-masterplan.md).
> See [the per-plan audit](../../PLAN_INDEX.md) for current continuation notes.
> Older snapshots, release ladders and competing next-task orders below are historical;
> preserve the domain specifications and gates. Root `AGENTS.md` and later owner
> instructions govern conflicts. Model assistance for this continuation is local only;
> no Qwen Mythos/cloud inference.


> **For agentic workers:** REQUIRED SUB-SKILL: superpowers:executing-plans. Checkboxes = progress. Parent: `2026-11-06-masterplan-resume-s1.md`.

**Goal:** (A) a measurable propose-measure-reflect-revise loop for our own self-healing work, (B) offline modalias-based hardware/driver autodetect, (C) a documented, legally bounded workflow to understand single undocumented parts.

**Architecture:** A reuses existing gates as the verifiable feedback; B extends `cli/hscl/src/hw.rs` (sysfs, fixture-tested); C is documentation + one capture helper, no vendor code in the repo.

**Tech Stack:** Rust (hw.rs), Python (loop recorder, tests), udev hwdb, usbmon/Wireshark.

**Spec:** `docs/research/2026-11-06-arex2-autodetect-reverse-engineering.md`.

## Global Constraints
- Everything offline and read-only by default; redaction on (`redact.rs`); uploads never default.
- No claim about driver availability without the package actually existing in the pinned archive.
- RE only on hardware the owner owns, for interoperability; no vendor firmware/decompiled code in Git; legal wording = owner item.
- A MEASURE item stays MEASURE until a run on the machine gives a number.

## Review Focus
- A modalias with unusual characters/very long strings must not break parsing or JSON output.
- Machine with no `/sys` entries (container/CI) must yield an empty, valid report, not an error.
- Loop recorder must never store secrets or absolute user paths (reuse `scan_credentials.py` rules).
- Hybrid-GPU laptop: two display devices must both be listed, with the one driving the panel marked only if sysfs says so.
- Quirk table entry that matches nothing must not be reported as "applied".

---

## Track A - AREX-style loop for our own work (pattern, not the 27B model)

### Task A1: Round recorder
**Files:** Create `scripts/round_log.py`, `tests/unit/test_round_log.py`; Produces `artifacts/auto-loop/rounds.jsonl`
**Interfaces:** `record_round(task: str, round_no: int, score: dict[str, float|int], action: str, reflection: str, path: Path) -> dict` appends one JSON line with keys `task, round, score, action, reflection, ts`; rejects secrets (uses `scan_credentials` patterns) and absolute home paths.
- [x] Failing tests first (collection error), then `scripts/round_log.py`: valid JSON line, increasing rounds per task, planted token / private key / bearer / password and personal paths refused, numeric score, capped text (13 tests incl. exec-bit)
- [x] Implemented; committed

### Task A2: Improvement report
**Files:** Create `scripts/round_report.py` (+ test)
**Interfaces:** `summarise(path: Path) -> dict` returns per task `best_round`, `delta_first_to_last`, `stalled` (no score gain for 3 rounds => stop rule from the plan).
- [x] `scripts/round_report.py` with 8 tests (improving, stalled after 3 rounds since best, 2 rounds not stalled, lower-is-better, regression, missing key, malformed line, exit code 3); documented in `docs/DEV_LOOP.md`
- [ ] Rule: three stalled rounds => write BLOCKER into BUILD_LOG (existing stop rule), not a fourth retry

### Task A3 (later, S6): optional AI bundle candidate
- [ ] G39 check for AREX-Turbo: official GGUF or a conversion that the pinned llama.cpp accepts; licence text Apache-2.0 + Qwen base notice; eval on our own held-out prompts; decide ship / do not ship. Not before the pinned build is probed (Task B0 of `ai`).

## Track B - Autodetect v2 (modalias first)

### Task B1: Collect modaliases
**Files:** Modify `cli/hscl/src/hw.rs`; Test in same file (fixture trees)
**Interfaces:** `pub struct Modalias { pub bus: String, pub path: String, pub value: String }`; `pub fn modaliases(root: &Path) -> Vec<Modalias>` walks `sys/bus/{pci,usb,platform,acpi,i2c}/devices/*/modalias`; values longer than 512 bytes or with control characters are dropped and counted.
- [x] Failing tests: pci+usb fixture returns both sorted; missing `sys` returns empty; control chars/oversized dropped; output stable (2026-11-07, 8 tests incl. render summary)
- [x] Implement; `Report` gets `modaliases` + `dropped_modaliases`; `hscl hw detect --json` shows them (redaction: no serial numbers; USB `serial` file never read). DONE 2026-11-07: fixture-testet, USB-`serial` wird nachweislich nie gelesen, leere modaliases zaehlen nicht als verworfen; Textausgabe zeigt Zaehler je Bus

### Task B2: Quirk table + hwdb
**Files:** Create `hw-quirks/README.md`, `hw-quirks/*.toml` (empty seed), `scripts/gen_hwdb.py`, `packages/debian/hscl-base/usr/lib/udev/hwdb.d/` generated at build, `tests/unit/test_gen_hwdb.py`
**Interfaces:** `gen_hwdb.render(entries: list[dict]) -> str` produces hwdb text (`modalias-pattern` line + indented `KEY=value` lines); validates patterns (`^[a-z0-9]+:[A-Za-z0-9*?:._-]+$`), rejects unknown keys.
- [ ] Failing tests: valid entry renders exact text; bad pattern/key rejected; duplicate pattern rejected
- [ ] Implement; packaging postinst runs `systemd-hwdb update` (MEASURE: image test that `systemd-hwdb query` returns the key)

### Task B3: Driver hints
**Files:** Modify `hw.rs` (+ `hscl hw drivers`), Test fixtures
**Interfaces:** `pub fn driver_hints(mods: &[Modalias], ubuntu_drivers: Option<&str>) -> Vec<Hint>` where `ubuntu_drivers` is the text of `ubuntu-drivers list`; a Hint has `device, package, source ("ubuntu-drivers"|"quirk"|"none")`.
- [x] Failing tests with captured `ubuntu-drivers list` text (nvidia example) and without the tool (all `none`, no error) - DONE 2026-11-07 as the apt-index route
- [x] Implement; docs row in `docs/CLI.md` (drift test enforces). DONE 2026-11-07: `hw::parse_packages_modaliases`, `modality_matches`, `suggest`, `licence_class`, `load_package_modaliases` + `hscl hw suggest [--root DIR] [--json]`, 8 Rust tests + 3 Python gate tests; live run on this host prints "No apt package index found" and installs nothing. Not used yet: `ubuntu-drivers devices` as an oracle (the research round showed both paths exist; the index route needs no external tool, which is why it is first)

### Task B4: Local-only probe export
- [ ] `hscl hw export --output PATH` writes the redacted JSON (no serials, MACs, hostnames); never uploads; test asserts planted serial/MAC are absent

## Track C - Reverse-engineering lab (documentation + helper)

### Task C1: Policy and workflow
**Files:** Create `docs/RE_LAB.md`
- [ ] Contents: scope (own hardware, interoperability, no distribution of vendor code/firmware), clean-room split (observer writes protocol notes, implementer writes code from notes), tools (`usbmon`+Wireshark, `lsusb -v`, `acpidump`+`iasl` for ACPI tables, Ghidra only where the licence allows), what is stored (`docs/re/<device>.md` protocol notes, captures stay outside Git), EU art. 6 / C-13/20 summary with "not legal advice, owner decides"
- [ ] Gate: `scripts/check_trademarks.py`-style test that the doc contains the four required sections (scope, clean-room, storage, legal note)

### Task C2: Capture helper (read-only)
**Files:** Create `scripts/re_capture.sh` (+ shellcheck + test with a fake `modprobe`)
- [ ] Loads `usbmon` only after an explicit `--yes`, prints how to start Wireshark, never writes into the repository; test: without `--yes` it prints usage and exits 2

## Order
B1 -> B3 -> B2 -> A1 -> A2 -> C1 -> C2 -> B4. Each task: test first, red, minimal code, cargo/pytest/forge green, commit, BUILD_LOG line, RSI reflection.
