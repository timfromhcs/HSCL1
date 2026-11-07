# Plan: HSCL1 gates and the HCS-Genesis companion track, run in parallel (2026-11-07)

Source: `AGENTS_HCS_GENESIS.md` (untracked companion file in the repo root, read in full 2026-11-07). `AGENTS.md` stays the parent contract; where the two differ, `AGENTS.md` wins and the difference is recorded here.

## Observed facts that change the companion file's assumptions
| Genesis file says | Checked 2026-11-07 | Consequence |
|---|---|---|
| HSCL1 README says `0.1.2-alpha.0` | `VERSION` is `0.1.3-alpha.0` | use the files, not the quoted snapshot |
| agent credentials had no push permission | `gh` is logged in as `timfromhcs`, `viewerPermission: ADMIN` on HSCL1 and CQ-HECS | pushing is *possible*; it is still **not done without the owner asking** (AGENTS.md 13, Genesis 13.3) |
| three repos to inspect | CQ-HECS clone exists at `E:\QHCS\CQ-HECS` (clean, `main`, last merge PR #4); **no local hcs-foundry clone** (only the data dir `C:\Users\hcsme\.hcs-foundry`); both repos readable via `gh` | Phase 0 reads CQ-HECS locally and Foundry via `gh`; no write to either repo |
| Foundry binds 127.0.0.1:8770 and supervises one llama-server | this PC already runs its own llama-server on :8080 (Bonsai-9B, autostart) | the Genesis adapter must call Foundry's API, not start a second server; the :8080 server is not Foundry's |

## Two tracks, at most two local agents at once
**Track A: HSCL1 release gates (current, unchanged priority).**
1. Finish the LUKS install on the exact 0.1.3-alpha.0 ISO: wrong passphrase refused, right one unlocks, desktop reached. (Running now; disk on NVMe.)
2. In-guest evidence without the Workshop: decide between a temporary opt-in of the Workshop in a *test* image or reading results from the guest through screenshots only. Do not enable the Workshop in the release image (Workshop-inert gate).
3. Rebuild once for the branding-version fix (`5356d5b`) and anything else queued; verify the new artefact; only then re-run the gates on it.
4. G10 (brand OCR) and G11 (finding recorded: no shortcut bindings exist; decide whether to implement AGENTS.md 4.5 or keep it PLANNED).

**Track B: Genesis companion, in this order, each phase gated by its own exit criteria.**
- **B0 Baseline and claims audit (read-only, cheap, can run beside A):** write `docs/genesis/BASELINE.md`, `RESEARCH_LEDGER.md`, `DECISIONS.md`, `BLOCKERS.md`, `TEST_MATRIX.md` in the HSCL1 repo (separate from `docs/DECISIONS.md`). Record CQ-HECS and Foundry SHAs, versions, ports, MCP tools, licences, CI state, from the clone and from `gh`. Label every planned capability implemented/experimental/planned/blocked.
- **B1 Contracts and packaging spike:** JSON schemas (capabilities, runs, provenance, evidence, reports) with fixtures; **one** Debian package shell, `hscl-cqhecs` first because the clone exists and the Python install is the supported surface. Build twice from clean sources, install/uninstall in a disposable environment, no network in maintainer scripts, no service enabled, venv under `/opt/hscl/venvs/`, user data under XDG. Add a test, then the package, then the launcher entry.
- **B2 and later** (CQ-HECS full integration, Foundry, Genesis MVP, science slices): not started before B1 exits. The first scientific slice is chosen after B0; none of the whole-human claims in Genesis 0.3 may appear anywhere.

## Rules carried over, in one place
- No model weights, datasets or training stacks in the ISO; packages are small shells (Genesis 2.1, 3.1).
- Nothing autostarts in the live session; services bind loopback; no shell/exec MCP tool (Genesis 2.5, 7.3).
- ISO size, boot RAM and offline behaviour are measured before and after any package is added to `scripts/remaster-iso.sh`.
- Repair loop: at most three focused attempts per failure hypothesis (matches Genesis 11.2 and AGENTS.md 15.2).
- Evidence log: Genesis wants `docs/genesis/EXECUTION_LOG.md`; HSCL1 keeps `docs/BUILD_LOG.md`. Genesis entries go in the former, HSCL1 gate evidence in the latter; no duplicates.
- Local only for sub-agents; heavy RAM jobs (QEMU, llama-bench) one at a time; VM disks on `C:\AI\vmtest`.

## What is explicitly not done now
- No push, no PR, no merge (owner has not asked; `gh` could do it).
- No change to CQ-HECS or Foundry repos.
- `AGENTS_HCS_GENESIS.md` is not committed (it is the owner's file); it stays untracked until the owner decides.
