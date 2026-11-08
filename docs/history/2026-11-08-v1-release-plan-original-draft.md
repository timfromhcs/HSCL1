# HSCL1 v1.0.0 Release Plan — From Current State to Stable Release

**Date:** 2026-11-08
**Current Branch:** `codex/autonomous-wave1` at `a74d086` (W2-6 MINER-1 documents done)
**Main Branch:** `main` at `bbb98dd` (merged PR #36)
**Open PR:** #37 (CI running — HCSUDA ubuntu-latest + cargo audit in progress)

---

## Executive Summary

This plan maps the remaining work from the current state (W2-6 complete) to **HSCL1 v1.0.0 stable release** per the governing contracts in `AGENTS.md` and the Master Ledger. The path follows the Master priority order P0-P14 and the Wave 2 execution order W2-7 through W2-9, then the release hardening track (P14/O-track).

**Key constraint:** One heavy job at a time (VM + ISO build OR local AI GPU OR HCSUDA logits). All gates must pass with evidence — no fake completion.

---

## Current State Summary

| Track | Status | Evidence |
|-------|--------|----------|
| **P0 (Baseline sync)** | IN PROGRESS | PR #29 landed; CQ-HECS clean clone suite 2759/0/110 on `hcspnp/integration`; HCSPNP_BASELINE.md audit parts 1-10 complete |
| **P1 (Studio guard)** | DONE LOCALLY | 19 adversarial tests on `hcspnp/studio-guard`; needs owner approval to push (B-P1) |
| **P2 (hscl cqhecs status)** | DONE, PR PENDING | 12 tests; `cargo test -p hscl` green; PR pending CI |
| **P4/P5 (NPBENCH)** | SLICES 1-6 DONE | NPBENCH-1 through 6 complete (134 + 13 + 26 + 26 + 24 + tests); `forge check` passes |
| **P12 (HCSUDA + HCSEASYMATH)** | IN FLIGHT | HCSUDA H3c-3b PAUSED; HCSEASYMATH `simplify` + `solve` DONE (PR #37); `plot` NEXT (W2-7) |
| **W2-6 MINER-1** | **DONE** | ADR + 4 schemas (event, heartbeat, batch, ack); all validate; `forge check` passes; committed `a74d086` |
| **Scheduler** | DESIGN + CODE DONE | `scripts/selfheal/` with 14 tests, 3 mutations; row rotation (W2-4) done (22 tests, 6 mutations) |
| **HCSEASYMATH gate** | GREEN | 244 passed in WSL (just verified) |

---

## Remaining Work — Ordered by Master Plan

### W2-7: HCSEASYMATH One-Page UI (Light Slot) — **NEXT**
**Master P12 / Ledger Row 23**
- **Files:** `apps/hcseasymath/` (API, page, operations), `scripts/hcseasymath_gate.sh`
- **Gate:** `bash scripts/hcseasymath_gate.sh` (WSL, hash-locked venv)
- **Scope:** Wire all 6 operations (`differentiate`, `integrate`, `evaluate`, `simplify`, `solve`, `plot`) in the single-page UI served by the API. Status and warnings must be shown **verbatim** from the engine (no sanitization). Plot renders data as SVG polyline — no image claim.
- **Dependency:** PR #29 merged (done); lock free
- **Acceptance:** All 6 operations reachable in UI; `status` + `warnings` verbatim; `plot` renders SVG data; gate green

### W2-8: Heavy Slot — Pick Exactly One (Ledger Row 5)
**Choose one; others stay PLANNED until this completes.**

| Option | Description | Gate |
|--------|-------------|------|
| **HCSUDA H3c-3b** | Real Qwen3 layers, tied head, logits vs llama-server | `hcsuda` gates |
| **ISO Rebuild + QEMU Boot** | Full remaster from v1 artifact, boot UEFI+BIOS, verify desktop | `scripts/test-iso-qemu.sh` + visual QA |
| **Local AI Vulkan Verification** | Bonsai-9B on Radeon 680M with measured tok/s, KV cache, memory | `hscl ai detect` + benchmark |

**Decision rule:** Pick the one that unblocks the most downstream work. HCSUDA H3c-3b is the current paused candidate (ledger row 5). ISO rebuild is gated on v1 stable anyway (row 24). Local AI vulkan is a measurement, not a release gate.

### W2-9: Release Hygiene (Ledger Row 7, partial)
**Master P14 / Ledger Rows 7, 8, 24+**
- **Dependabot review:** #1-#4 reviewed locally, PR pending (checkout 7.0.1, upload-artifact 7.0.2, sha2 0.11.1, thiserror 2.0.21) — needs merge
- **Release manifest:** Prepare `release/manifest.json`, `SHA256SUMS` script, release-notes template
- **ISO v1 stable:** Gated on ALL v1 release gates (AGENTS.md 14.2) — **not started**, needs free heavy slot

---

## Detailed Phase Plan

### Phase A: HCSEASYMATH UI Completion (W2-7) — **Immediate**
```
1. Extend page.py HTML to include all 6 operation forms (currently only differentiate)
2. Extend page.py JS to call each /api/v1/symbolic/<op> endpoint
3. Render status, warnings, checks, exactness, assumptions verbatim
4. Plot: render samples as SVG polyline (no image claim)
5. Run gate: bash scripts/hcseasymath_gate.sh
6. Commit + push; await CI green
```
**Estimated:** 1-2 iterations. Light slot — no VM, no heavy compute.

### Phase B: Heavy Slot Execution (W2-8) — **After Phase A green**
```
Option A (HCSUDA H3c-3b) — if chosen:
  1. Resume hcsuda H3c-3b logits comparison against llama-server
  2. Run hcsuda gates
  3. Record JSON logits comparison
  4. Commit + push

Option B (ISO Rebuild) — if chosen:
  1. scripts/remaster-iso.sh from tagged v1 artifact (not dev tree)
  2. scripts/test-iso-qemu.sh (UEFI + BIOS)
  3. Visual QA: desktop, keyboard, network
  4. Generate screenshots, serial logs
  5. Commit artifacts to release/

Option C (Local AI Vulkan) — if chosen:
  1. hscl ai detect --json
  2. hscl ai setup --backend vulkan
  3. Benchmark with measured tok/s, KV, memory
  4. Record in CLAIMS.md
```
**Only ONE at a time.** Resource rule enforced.

### Phase C: Release Hardening (P14 / O-track) — **After heavy slot + all gates green**
```
1. Merge Dependabot #1-#4 (reviewed, ready)
2. Generate release/manifest.json from actual build
3. Generate SHA256SUMS + detached signature (if signing key available)
4. Build v1.0.0 ISO from clean tag
5. Full VM matrix: QEMU UEFI, QEMU BIOS, VirtualBox UEFI
6. Install test: LUKS2 + non-encrypted
7. hscl doctor, security status, lab status, ai detect on installed system
8. SBOM (SPDX), package manifest, build manifest
9. Tag v1.0.0, GitHub Release with assets
10. Vercel deploy (if credentials available)
11. Update website download metadata to point to real release
```
**Gates (AGENTS.md 14.2) — ALL must pass:**
- [ ] ISO builds from repository scripts
- [ ] ISO hash + manifest from actual artifact
- [ ] Boots QEMU UEFI
- [ ] Secure Boot status tested + documented
- [ ] Live desktop starts + usable
- [ ] Graphical installer starts
- [ ] Disposable VM install completes
- [ ] Installed VM reboots to desktop
- [ ] LUKS2 install/unlock tested
- [ ] Default desktop, launcher, dock, Control Center function
- [ ] EN/DE/FR critical UI coverage complete
- [ ] hscl doctor truthful
- [ ] Host APT: no Kali repo
- [ ] Security Lab containers: no unsafe defaults
- [ ] Privacy claims match test evidence
- [ ] No critical/high unmitigated vulns in HSCL1 code
- [ ] README + guides match release
- [ ] SBOM, checksum, signature instructions exist
- [ ] GitHub Release asset links work
- [ ] Vercel production build succeeds
- [ ] Known limitations published

---

## Resource Constraints & Scheduling

| Constraint | Rule |
|------------|------|
| **Heavy job** | Exactly one at a time: VM/ISO, GPU inference, or HCSUDA training |
| **VM disks** | `C:\AI\vmtest\` only (NVMe). Never `E:\` (USB) |
| **Secrets** | Never printed. Use credential store / CI secrets |
| **forge check** | Before every commit (pytest, WSL changed tests, bash -n, shellcheck, secret scan) |
| **Cron loop** | 2-minute ping → take first non-DONE/BLOCKED row whose dependency is met |
| **Three-fix rule** | Three meaningful fixes per failure, then BLOCKED with reproducer |

---

## Dependency Graph

```
W2-7 (HCSEASYMATH UI) ──────► Gate green
       │
       ▼
W2-8 (Heavy Slot: ONE of HCSUDA/ISO/AI) ──────► Gate green
       │
       ▼
W2-9 (Release Hygiene: Dependabot, manifest, v1 gates) ──────► All gates green
       │
       ▼
v1.0.0 TAG + RELEASE
```

---

## Immediate Next Action

**W2-7: HCSEASYMATH One-Page UI** — extend `apps/hcseasymath/backend/hcseasymath/api/page.py` to expose all 6 operations with verbatim status/warnings. Run gate in WSL. This is a light slot task (no VM, no GPU).

---

## Evidence Tracking

All evidence goes to:
- `docs/BUILD_LOG.md` — engineering record with status vocabulary
- `docs/CLAIMS.md` — capability matrix with test references
- `docs/KNOWN_LIMITATIONS.md` — honest gaps
- `artifacts/` — screenshots, serial logs, JSON reports (not in git)
- GitHub Release assets — ISO, SHA256SUMS, manifest, SBOM, release notes

---

## Cron Loop Contract (2 minutes)

Per Master Ledger section 2 and Unified Master 17.2:
1. **OBSERVE** — fetch current repo state, CI status, ledger
2. **CLASSIFY** — find first row in Section 5 not DONE/BLOCKED with met dependency
3. **HYPOTHESIS** — what minimal change advances it
4. **PRE-REGISTER** — write intent to BUILD_LOG
5. **CHEAPEST EXPERIMENT** — run targeted test
6. **SMALLEST PATCH** — apply fix
7. **TARGETED VERIFY** — re-run that test
8. **SUBSYSTEM VERIFY** — run affected suite
9. **FULL GATE** — `forge check`
10. **RECORD** — update BUILD_LOG, CLAIMS, ledger
11. **COMMIT** — with Co-Authored-By
12. **PUSH/PR** — only where authorised

**Never weaken a gate. Green gate + real failure = gate is incomplete.**