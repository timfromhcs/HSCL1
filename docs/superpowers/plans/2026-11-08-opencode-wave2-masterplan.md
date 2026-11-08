# OpenCode autonomous Wave 2 masterplan (2026-11-08, session 3)

> **Reconciled 2026-11-08:** The current OS release execution plan is
> [v1 release plan](2026-11-08-v1-release-plan.md); ecosystem priorities and evidence
> remain in the [live master ledger](2026-11-08-selfheal-masterplan.md).
> See [the per-plan audit](../../PLAN_INDEX.md) for current continuation notes.
> Older snapshots, release ladders and competing next-task orders below are historical;
> preserve the domain specifications and gates. Root `AGENTS.md` and later owner
> instructions govern conflicts. Model assistance for this continuation is local only;
> no Qwen Mythos/cloud inference.


> Status: **ACTIVE** from 2026-11-08. Written by the OpenCode agent that continues PR #37.
> This file holds **no priority list of its own**. The single order stays
> `2026-11-08-selfheal-masterplan.md` section 3 (Master P0-P14) and section 5 (ledger rows). Every task
> below names the Master P number and the ledger row it continues, plus the exact command that must
> prove it. If a task here disagrees with the ledger, the ledger wins and this file is corrected.
>
> Precedence (unchanged): root `AGENTS.md` -> owner instructions -> code and reproducible tests ->
> the ecosystem contracts -> the live ledger -> this plan.

---

## 0. Why this file exists

The previous two sessions left a working loop but three loose ends that a fresh agent would otherwise
re-discover by hand:

1. **Unpushed work.** Slice 4 of the NP benchmark harness (TSP + knapsack, 26 tests) was staged on the
   Windows tree and never committed. It is committed as `617e1f8` and pushed in this session.
2. **Split branch line.** Slices 2-3 were pushed to `codex/npbench-wave5` while PR #37 tracks
   `codex/autonomous-wave1`. Both refs now carry the same head, so no work is stranded on a branch
   nobody reviews. Nothing was deleted and nothing was force-pushed.
3. **No written continuation plan.** The takeover plan (`2026-11-08-opencode-autonomous-masterplan.md`)
   ends at Wave 5 step W5-5 "NEXT" with no contract for what a *new* session does at 04:00.

This file is that contract: what to build, in which order, with which gate, and what to do when a gate
is red.

---

## 1. Handover snapshot (measured in this session, not remembered)

| Item | State | How it was measured |
|---|---|---|
| `timfromhcs/HSCL1` `main` | `bbb98dd` (merge of PR #36) | `git log --all --decorate` |
| Work branch | `codex/autonomous-wave1` | `git status -b` |
| Head before this session | `13ddbe2` (npbench slice 3), 2 commits ahead of origin | `git status -b` |
| Head after this session's first batch | `617e1f8` (npbench slice 4) | `git log --oneline -1` |
| Mirror branch | `codex/npbench-wave5` = `617e1f8` (same commit) | `git push origin HEAD:codex/npbench-wave5` |
| Open PR | **#37**, head `codex/autonomous-wave1`, `MERGEABLE`, 16/16 checks green at `ac26e69` | `gh pr view 37` |
| Releases | `v0.1.0-alpha.0`, `v0.1.1-alpha.0`, `v0.1.2-alpha.0` — prereleases, SHA256SUMS only, **unsigned** | `git tag`, `docs/KNOWN_LIMITATIONS.md` |
| CI | last runs green except two transient failures at 01:50 (fixed by the following push) | `gh run list` |
| Windows host | Python 3.14.6, `gh` 2.97.0 authenticated as `timfromhcs`, ADK/WSL2 with `Ubuntu` distribution (stopped) | `python --version`, `gh auth status`, `wsl -l -v` |
| Gate for the NP harness | `python -m pytest tests/unit/test_npbench_*.py -q` -> **105 passed in 22.88 s** | run in this session before committing `617e1f8` |
| Gate for the whole repo | `python scripts/forge.py check` (tests, WSL re-run of changed tests, `bash -n`, ShellCheck, secret scan) | `scripts/forge.py --help` |
| Local CQ-HECS clone | WSL `~/src/CQ-HECS`, branch `hcspnp/integration`, **local only**, push blocked by B-P1 | ledger row 1/2 |

**Nothing here is "pushed" that is not listed above. Nothing listed as unpushed is still unpushed.**

---

## 2. Inventory: what actually exists, with its real status word

Only evidence-backed rows. A status word is never upgraded here.

| Area | Path | Status | Evidence |
|---|---|---|---|
| NP benchmark harness, SAT | `tools/npbench/npbench/{cnf,gen_sat,proof,runner}.py`, `solvers/` | TESTED | 40 tests, 8 mutations |
| NP harness, suites + CLI + report | `suites.py`, `__main__.py` | TESTED | 13 tests, 7 mutations; light suite 16/16 |
| NP harness, graph families | `graph.py`, `gen_graph.py`, `graph_solvers.py`, `graph_runner.py` | TESTED | 26 tests, 12 mutations |
| NP harness, optimisation | `tsp.py`, `knap.py`, `*_solvers.py`, `opt_runner.py` | TESTED | 26 tests, 15 mutations |
| HCSEASYMATH operations | `apps/hcseasymath/` | TESTED | gate `scripts/hcseasymath_gate.sh` -> 244 passed at last run |
| Durable self-heal tick | `scripts/selfheal/tick.py`, `rows.json` | TESTED (Windows + WSL) | 14 tests, 3 mutations; **known gap: no row rotation** |
| `hscl` CLI | `cli/hscl/src/` | TESTED (unit) | `cargo test -p hscl` -> 209 passed; never run on an installed system |
| Bootable ISO | `artifacts/iso/`, `scripts/remaster-iso.sh` | VM-VERIFIED (pre-alpha) | QEMU UEFI/BIOS, LUKS2 install evidence in `artifacts/` |
| Secure Boot | — | **partially verified only** | signatures read (`scripts/sb_evidence.py`); firmware acceptance NOT proven |
| Security Lab | — | PLANNED | no container tooling |
| Privacy mode | — | PLANNED | no claim made |
| HCSPNP audit | `docs/research/HCSPNP_BASELINE.md` | IN PROGRESS | rows read: native solver, C ABI, certificate side, `sat.py` core; the rest unread |
| Miner bridge | `docs/research/MINER_BRIDGE_RESEARCH_LEDGER.md` | MINER-0 DONE, MINER-2+ BLOCKED | owner approval M4 |

---

## 3. Working style to preserve (observed, not invented)

These are the habits that produced the green gates above. They are binding for Wave 2.

1. **Probe before designing.** Call the real API, run the real tool, read the real file. The
   `evaluate`-over-HTTP defect was found by *probing the running server*, not by reading tests.
2. **Tests first, red shown.** A new test that never failed proves nothing. For every guard, mutate the
   code, watch the specific test go red, restore from a backup copy (byte compare), re-run green.
   **Never revert a mutation with `git checkout`** — that erased uncommitted work once (slice 3).
3. **Smallest patch, then widen.** Targeted test -> subsystem test -> full gate -> log -> commit.
4. **Three attempts per failing item**, then `BLOCKED` with a reproducer (command, output, environment).
5. **Honest vocabulary only:** PLANNED / IMPLEMENTED / TESTED / VM-VERIFIED / HARDWARE-VERIFIED /
   EXPERIMENTAL / BLOCKED. A unit test is not a VM result. A schema is not a receiver.
6. **A contradiction is data.** A solver answer that disagrees with a known answer is a recorded
   `disagreement` and a non-zero exit code, never a silent pass.
7. **No silent fallback.** An unavailable solver is `unavailable`. An unsupported check is
   `unsupported` and the verdict stays `UNKNOWN`.
8. **Resource discipline.** One heavy job at a time, VM disks only under `artifacts/` or `C:\AI\vmtest`,
   no secrets printed, no environment dump in logs.
9. **Docs are part of the change.** `BUILD_LOG.md`, the owning ledger row, `CLAIMS.md` where a claim is
   added, `KNOWN_LIMITATIONS.md` where a limit is found.

---

## 4. The loop (heartbeat + tick contract)

### 4.1 Heartbeat

A background shell prints a timestamped heartbeat every **120 s** into `artifacts/loop/heartbeat.log`
and into the session output. It is bounded (30 beats = 60 min) and re-armed when it completes, because
a `while ($true)` loop never completes and therefore never notifies this harness (the same reason the
previous session used a one-shot wake).

The heartbeat is **not** the durable scheduler. `scripts/selfheal/tick.py` is that, and it is not
registered with Task Scheduler or cron (owner decision, ledger row 15).

### 4.2 Tick contract (one tick = one bounded, verifiable unit)

```
READ     artifacts/loop/state.json + ledger section 5
PICK     lowest P number, dependency met, not DONE/BLOCKED, fits a light slot
ACT      smallest verifiable step; tests first for code
VERIFY   targeted test -> subsystem gate -> (forge check before commit)
RECORD   BUILD_LOG.md entry, ledger row state, artifact paths, CLAIMS.md if a claim was added
COMMIT   one coherent batch, descriptive message with the measured numbers
PUSH     work branch only; PR update only for a coherent batch
ARM      the next heartbeat
```

### 4.3 Loop state file (`artifacts/loop/state.json`, ignored by Git)

```json
{
  "loop": "hscl1-autonomous-wave2",
  "branch": "codex/autonomous-wave1",
  "pr": 37,
  "tick_interval_s": 120,
  "last_tick_utc": "<measured ISO-8601>",
  "row": 20,
  "step": "<what is in flight, in the ledger's words>",
  "done": ["..."],
  "next": ["..."],
  "blocked": ["B-P1", "signing keys", "hardware session", "DE/FR review", "production deploy", "MINER-2+ M4"]
}
```

### 4.4 Failure taxonomy and what each one triggers

| Class | Signal | Action |
|---|---|---|
| Code defect | deterministic red test | root cause first, smallest patch, re-run targeted then subsystem |
| Test defect | test passes under the mutation | rewrite the test, re-run the mutation |
| Gate defect | green gate, real failure later | fix the gate, add the missing check to `forge.py` |
| Environment | WSL stopped, tool missing, no network | retry twice with backoff, then record `BLOCKED` with the exact command |
| Upstream | package mirror stall, action deprecation | pin, document, do not work around silently |
| Flake | red then green with no change | record it; three flakes on one test = test defect |
| Owner-only | push to a foreign repo, signing, deploy | stop, record, keep the artifact local |

**Three distinct failed attempts on one row -> `BLOCKED` + reproducer + move on.** Never weaken a gate,
never skip an assertion, never disable AppArmor/firewall/Secure Boot to get green.

### 4.5 Stop conditions

Stop the loop and report when: all reachable rows are DONE or BLOCKED; a destructive action would be
needed without owner approval; the same row blocks three times; the working tree would need a
force-push; or the owner says stop.

---

## 5. Wave 2 task order

One heavy job at a time. "Light" = no VM, no ISO build, no local model run. Every row below already
exists in the live ledger; the numbers in brackets are the ledger row.

### W2-0 — reconcile and arm (this batch)

| Field | Value |
|---|---|
| Master / row | P0 / rows 14-21 bookkeeping |
| Work | commit slice 4, align both branch refs, this plan, ledger rows 20-21 refreshed, BUILD_LOG entry |
| Files | `docs/superpowers/plans/*`, `docs/BUILD_LOG.md`, `docs/superpowers/plans/2026-11-08-selfheal-masterplan.md` |
| Gate | `python scripts/forge.py check` (no code changed; the run also proves the tree is clean) |
| Done when | `git status` clean, CI green on the new head, ledger row 20 says IN PROGRESS with this file named |
| Risk | low; docs only |

### W2-1 — NPBENCH-5a: DRAT proof checker (row 20)

| Field | Value |
|---|---|
| Master | P4 (one benchmark control) / P5 (corpus) |
| Work | `tools/npbench/npbench/drat.py`: strict reader for the DRAT line format (`c` comments, optional `d` deletion prefix, integers terminated by `0`, no other tokens, caps before allocation), an active-clause database with deletion, **RUP checking per addition** against the active database by unit propagation, and a **typed refusal** for a step that is not RUP: `rat_unsupported` -> the overall verdict is `unknown` with a reason, never `UNSAT`. An empty clause ends the refutation; a proof that ends without one is `unknown` (`incomplete_proof`). |
| Integration | `runner.py` gains `verify_unsat: "rup" \| "drat"` so a solver record states **which** checker accepted its proof. A DRAT-accepted proof is never relabelled `verified=true` for the native solver (that stays a separate upstream finding). |
| Files + lock | `tools/npbench/` (default lock group, no shared group touched) |
| Tests first | `tests/unit/test_npbench_drat.py`: accept the CDCL baseline's own proofs for 40 random small formulas; a hand-written 3-step refutation; deletion actually removes a clause (a RUP step that only works without the deletion must fail); `c` lines ignored; missing final empty clause -> `unknown(incomplete_proof)`; a non-RUP step -> `rat_unsupported`; malformed lines (float, `0` in the middle, unterminated line, oversized literal, `d` without clause) refused with a typed error; a proof for the wrong CNF refused; caps enforced before allocation. |
| Gate | `python -m pytest tests/unit/test_npbench_drat.py -q` then all four npbench files; `forge check` before commit |
| Mutations (must go red) | RUP check accepts any clause; deletion ignored; empty clause not required; proof accepted for a different CNF; caps after allocation |
| Done when | tests green, mutations red-then-restored, shows real numbers in the BUILD_LOG, README + `CLAIMS.md` row updated, pushed |
| Risk | medium: DRAT includes RAT which is expensive. **Decision: RAT is not implemented in this slice** and is reported as `rat_unsupported`. This is stated in README, docstring, report schema and `KNOWN_LIMITATIONS.md` — the checker must never claim "DRAT-complete". |

### W2-2 — NPBENCH-5b: differential parser test against CQ-HECS (row 20)

| Field | Value |
|---|---|
| Master | P0 (audit) / P5 |
| Work | For each of the **seven input classes** where the audit found the CQ-HECS Python and native parsers disagree (`docs/research/HCSPNP_BASELINE.md`, audit row 1), a table-driven test that states, per class, what our strict parser does and what the CQ-HECS parser does. If the local clone is reachable, the CQ-HECS side runs for real (`~/src/CQ-HECS`, read-only, no edit, no push); otherwise the test is marked `skip` with the exact reason and the class table stays as documentation-only evidence. |
| Why the skip is allowed | The clone is a *local* artifact of another repository. A CI runner cannot have it. A skipped differential test is honest; a *fake* differential test that imports nothing would be a lie. |
| Gate | `python -m pytest tests/unit/test_npbench_diff.py -q` on the Windows host **and** in WSL when the clone exists |
| Done when | report in `HCSPNP_BASELINE.md` section "differential parser test" with the observed matrix and a per-class verdict |
| Risk | low; read-only on a foreign repo. Any *fix* there needs B-P1 and is out of scope. |

### W2-3 — NPBENCH-6: beyond NP, smallest honest slice (row 21)

| Field | Value |
|---|---|
| Master | P13 (later) — **do not start before W2-1/W2-2 are green** |
| Work | exact #SAT model counter for small formulas (DPLL with component caching, capped node budget), and a toy QBF checker for closed prenex CNF with `forall`/`exists` (2^n assignment walk, explicitly exponential, cap enforced). Both return `unknown` on budget exhaustion. |
| Tests | count equals brute force for 100 random small formulas; counter refuses a formula above the node cap with `unknown`; QBF checker agrees with brute force on all closed formulas with <= 3 variables; an open formula is refused as `malformed`, not guessed |
| Done when | tests green, limitations named (exponential, tiny sizes, no competitiveness claim) |
| Risk | medium: easy to over-claim. The word "counter" must never appear without "for small formulas" in the same sentence. |

### W2-4 — scheduler row rotation (row 15 follow-up, light)

| Field | Value |
|---|---|
| Master | P4 |
| Work | `scripts/selfheal/tick.py` always picks the first non-blocked row, so only `git-status` ever runs. Add round-robin by last-run timestamp, keep the three-failure rule, keep the blocking test. |
| Files | `scripts/selfheal/`, `tests/unit/test_selfheal_tick.py` (new default lock group) |
| Tests | rotation over three rows; a BLOCKED row is skipped by rotation too; state without a timestamp starts at the first row; the existing 14 tests stay green (Windows **and** WSL) |
| Done when | 15+ tests green on both platforms, design note updated, `forge check` green |
| Risk | low. Do **not** register the tick with Task Scheduler — owner decision. |

### W2-5 — HCSPNP audit completion (row 1, light, read-only)

| Field | Value |
|---|---|
| Master | P0 |
| Work | Read the remaining files listed in row 1 (`sat_separator.py`, `omniwave/*`, `provenance.py`, `mcp_server.py`, DPLL/counting/MaxSAT internals of `sat.py`) and fill the gap list with file+line references. |
| Gate | n/a (report); every claim carries `path:line` |
| Done when | `HCSPNP_BASELINE.md` has no row saying "not read" inside its scope, or the residue is explicitly named |
| Risk | low; read-only. No edit, no push (B-P1). |

### W2-6 — MINER-1 documents (row 12, docs only)

| Field | Value |
|---|---|
| Master | sub-track under P0-P4 |
| Work | ADR (receiver location, runtime, port choice with a conflict check, pairing) + schema drafts `hcs.miner.event.v1`, `heartbeat.v1`, `batch.v1`, `ack.v1` under `docs/miner/` |
| Gate | JSON-Schema validation of every example in the docs; no device contact, no listener |
| Done when | schemas validate, ADR names the open owner decisions (M3/M4) |
| Risk | none (documents). **Must not** create a listener or touch a device. |

### W2-7 — the one-page HCSEASYMATH UI (row 4 residue, light)

| Field | Value |
|---|---|
| Master | P12 |
| Work | The integration page calls only `differentiate`; wire `integrate`, `simplify`, `solve`, `evaluate`, `plot` (plot renders **data** as an SVG polyline in the page, no image claim from the server). |
| Gate | `bash scripts/hcseasymath_gate.sh` (WSL, hash-locked venv) |
| Done when | every operation is reachable from the page, the page states the honest limits (numeric vs symbolic verification), gate green |
| Risk | medium: a UI that silently drops `partial` warnings would turn an honest API dishonest. The page must show `status` and `warnings` verbatim. |

### W2-8 — heavy slot (not before 1-7): pick exactly one

| Candidate | Why it is heavy | Precondition |
|---|---|---|
| HCSUDA H3c-3b (real Qwen3 layers, logits vs `llama-server`) | GPU + model run | free heavy slot, local model present |
| ISO rebuild + QEMU UEFI/BIOS boot + install gate | ISO build, VM, 20 GB host RAM | free heavy slot, no other VM |
| Local AI Vulkan verification | model download/run | free heavy slot |

Only one of them, only after the light rows are green, and the result is recorded as
VM-VERIFIED / HARDWARE-VERIFIED only with the artifact path.

### W2-9 — release hygiene (owner-gated)

| Field | Value |
|---|---|
| Work | Nothing that needs a key. Prepare: `release/manifest.json` from real values, `SHA256SUMS` generation script check, release-notes template filled from `BUILD_LOG.md` |
| Blocked on | signing keys, production deployment, tag decision (owner) |
| Done when | a release checklist exists that a human can execute in one hour, with every command tested in dry-run |

---

## 6. Check matrix: which gate for which change

| Change touches | Mandatory checks before commit |
|---|---|
| `tools/npbench/**` | the four npbench test files; `python -m npbench run --suite light` smoke; `forge check` |
| `apps/hcseasymath/**` | `bash scripts/hcseasymath_gate.sh` (WSL, hash-locked venv); API tests |
| `cli/hscl/**` | `cargo fmt --all -- --check`, `cargo clippy --all-targets -D warnings`, `cargo test -p hscl` (Windows **and** WSL) |
| `hcsuda/**` | same three, inside `hcsuda/` |
| `apps/control-center/**` | `qmltestrunner` + `cmake --build` + `ctest` (Linux; CI covers it, record SKIPPED locally) |
| `scripts/**`, `distro/**`, `packages/**` | `bash -n`, ShellCheck; `python3 -m pytest tests -q` |
| `.github/workflows/**` | `forge check` + a green CI run on the pushed head; SHAs pinned |
| `docs/**` only | `forge check` (includes the Rust doc-command gate and the secret scan) |
| Anything before a push | `python scripts/forge.py check` — and a skipped step is reported as SKIPPED, not PASS |

A green local gate followed by a red CI is a **gate defect**: the missing check goes into `forge.py`.

---

## 7. Git, PR and release policy for this wave

- Branch: `codex/autonomous-wave1` (PR #37). Mirror push to `codex/npbench-wave5` keeps both refs equal;
  no branch is deleted.
- Never force-push, never rewrite pushed history, never delete tags or releases.
- Merge to `main` only when every CI check on the PR head is green (standing owner instruction), merge
  commit, never squash a foreign author's work.
- No release, no tag, no signing, no production deploy, no cross-repository push. Those are owner-only.
- One coherent batch per commit; the message names the measured numbers (tests, mutations, timings).

---

## 8. Evidence format for every batch

Every entry in `docs/BUILD_LOG.md` states, in this order:

1. what was built (files),
2. the exact command and exit code that proves it,
3. pass/fail/skip counts, with the reason for each skip,
4. the artifact path (report JSON, log, screenshot) if any,
5. the mutations performed and which test each one turned red,
6. what was **not** done, explicitly,
7. the new `disagreement`/`unsupported`/`unknown` cases if the change created any.

A batch that cannot fill this stops at a stable checkpoint and fills it before the next batch.

---

## 9. Owner-only items (unchanged, never guessed)

1. Push the CQ-HECS guard + bridge fix and open the PR there (**B-P1**).
2. Signing keys for tags/checksums; licence decision for a future public `hcsuda`.
3. Physical hardware boot session (Secure Boot acceptance, suspend, Wi-Fi, audio).
4. DE/FR native review of user-facing strings.
5. Production deployment of the website.
6. Whether the durable scheduler may be enabled as a user-level scheduled task.
7. MINER-2+ firmware work, device contact, flashing (M4/M5).

---

## 10. Risk register

| Risk | Impact | Mitigation |
|---|---|---|
| DRAT checker over-claims (RAT not implemented) | a wrong UNSAT verdict becomes "verified" | typed `rat_unsupported`, verdict `unknown`, stated in README/limits/CLAIMS |
| Differential test silently skipped in CI | the parser question looks answered | the skip is explicit with a reason; the class table stays as documentation |
| Mutation revert destroys uncommitted work | lost batch | revert from a backup copy + byte compare, never `git checkout` |
| Loop runs unattended and drifts from the ledger | priority inversion | every tick re-reads the ledger; `state.json` is rewritten each tick |
| Heavy job started twice | host OOM (20 GB total, no swap headroom) | one heavy job at a time, heavy lock file, VM disks outside the repo |
| PR grows without review | merge risk | coherent batches, CI green before merge, no release |
| A "NEXT" row is actually blocked | wasted ticks | the three-attempt rule and an explicit `BLOCKED` line with a reproducer |

---

## 12. Owner request (2026-11-08, session 3): a VM-usable HSCL1 image at v1 stable

**Status: PLANNED. Explicitly gated on v1 stable — it does not start before the v1 release gates are green,
and nothing about it may be reported as done earlier.**

What "usable in a VM with GUI, keyboard, internet and everything" means as testable requirements:

| Requirement | How it is proven | Status |
|---|---|---|
| Boots in a VM | QEMU/KVM UEFI (OVMF) and BIOS runs of the **released** artifact, `artifacts/` screenshots + serial log | PLANNED |
| GUI desktop | Plasma session reached, wallpaper, panel, dock, launcher open, one application started - screenshot per step | PLANNED |
| Keyboard input | keystrokes delivered into the guest (QEMU monitor `sendkey` / `-device usb-kbd`), text typed into a real field, layout switch tested for EN/DE/FR | PLANNED |
| Internet | guest reaches the network through user-mode NAT (`-netdev user`) and through a bridged setup; DNS, HTTP and HTTPS verified inside the guest; **no host-only claim** | PLANNED |
| Everyday work | browser opens a page, terminal runs a command, settings window opens, file manager shows the home directory | PLANNED |
| Deliverable | a documented VM path (qcow2 image **and/or** an ISO + a tested recipe), SHA256SUMS, a VM guide with exact QEMU and VirtualBox settings, and a known-limitations row stating what was not tested | PLANNED |
| Honesty | the image is derived from the released v1 artifact; a rebuilt image is not called "the release"; no GPU/3D-acceleration claim without measurement | PLANNED |

Hard rules for this item:

1. **No shortcut.** The VM image is built from the tagged v1 artifact (or from the same build inputs), never from a
   local dev tree that differs from the release.
2. **Disposable disks only.** Every VM test uses a throw-away qcow2 outside the repository; no physical disk, no
   user data.
3. **No credential leakage.** The image ships no account, no key, no token; first boot creates the user, or the
   documented default is credential-free with a forced password change.
4. **Secure Boot honesty.** If the v1 ISO does not prove firmware acceptance, the VM guide says so and does not
   imply it.
5. **Network scope.** Internet access is proven inside the guest; a "works everywhere" claim is never made - the
   tested combinations are listed.

Preconditions before it may start: v1 release gates from `AGENTS.md` section 14.2, a green CI on the release
commit, a signed-or-explicitly-unsigned artifact, and a free heavy slot. Until then this section stays a plan.

---

## 13. Definition of done for Wave 2

Wave 2 is done when, and only when:

- [ ] W2-1 DRAT checker: tests green, mutations red-then-restored, RAT limitation published
- [ ] W2-2 differential parser matrix recorded (or explicitly blocked with a reason)
- [ ] W2-4 rotation: tests green on Windows and WSL, design note updated
- [ ] W2-5 audit residue closed or named
- [ ] W2-3 beyond-NP slice green with its exponential limit stated
- [ ] W2-6 schemas validate (no listener, no device)
- [ ] W2-7 one-page UI covers every operation and shows status/warnings verbatim
- [ ] the v1-gated VM deliverable (section 12) is still PLANNED and named as such
- [ ] every batch has a `BUILD_LOG.md` entry with command + exit code
- [ ] PR #37 green and mergeable
- [ ] no claim in `CLAIMS.md` without an artifact behind it
- [ ] `KNOWN_LIMITATIONS.md` lists **RAT unsupported**, the differential-test skip condition and the
      scheduler rotation change

Anything not measurable above stays PLANNED and is listed in the final report as a gap.
