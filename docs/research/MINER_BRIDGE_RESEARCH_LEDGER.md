# Miner Research Bridge: research ledger and decisions (MINER-0)

Source contract (owner companion, untracked, 2392 lines): `AGENTS_HSCL1_BITAXE_MINER_RESEARCH_BRIDGE_MASTER_2026-11-08.md`. Review date 2026-11-08.
Status: **MINER-0 = reading, verification and planning only. No receiver, schema, firmware change, device contact or dataset exists.** Status vocabulary as in the root `AGENTS.md`.

## 1. Facts verified today (GitHub API, read-only)

| Claim of the contract | Checked | Result |
|---|---|---|
| `timfromhcs/ESP-Miner` master `21f543c...` | `gh api` | **confirmed** (`21f543cbd3abd151338815f5accd1687775ecd6d`); repo public; last push 2026-11-02 |
| Branch `feat/timsminer-sha-research-mode` head `07de7e4...`, 8 ahead / 0 behind, 22 files | `gh api compare` | **confirmed** (head `07de7e463a1d2f4203ddb904ab06fe960273f2cc`, ahead 8, behind 0, 22 files). CI results of that branch not re-read |
| Branches `docs/readme-logo`, `release/v4.0.2` | branch list | present; no open PR in the fork |
| Partition table leaves no free data partition (nvs 0x6000, factory 4M, www 3M, ota_0 4M, ota_1 4M, otadata, coredump 64K) | read `partitions.csv` | **consistent** with the contract's constraint: no flash spool without an approved partition change (contract P15) |
| Upstream `bitaxeorg/ESP-Miner` PRs #2055, #2058, #2060, #2063 open; #2082 draft; #2072 (IDF 6.0.3) merged 2026-11-02 | `gh pr view` | **confirmed**. #2063 title is "Stratum driver abstraction" |
| HSCL1 `main` `4bdcb2f` | `gh api` | **stale**: main is `3a32d56` now (PRs #29-#35 merged since) |
| RLAF paper (Toenshoff and Grohe, arXiv 2505.16053): GNN variable weights and polarities in one pass, GRPO, solver cost as reward, "more than 2x speed-up in some cases" | arXiv abstract | **confirmed at abstract level (ABSTRACT ONLY)**; evidence for guidance hints, not for proofs or for SHA-256 |

Not checked (NOT READ): the other 22 sources of the contract's section 14 (Nature Communications heuristics paper, arXiv 2603.07176, SATzilla, SAT Competition 2026 pages, the SHA SAT papers, Stratum V2 specification, ESP-IDF NVS and wear-levelling pages, OpenTelemetry log model). Nothing may rely on them yet.
Not done: **no contact with `192.168.178.61` or `.66`** (contract task 7 allows read-only GET only; it is not needed for MINER-0), no ESP-Miner AGENTS/README/docs read beyond the file list, no CI re-read, no check of CQ-HECS module APIs.

## 2. Decisions

| ID | Decision | Why | Proof | Status |
|---|---|---|---|---|
| M1 | The bridge is a **sub-track under the one order** (Master section 27), not a new priority list. The contract's P0-P16 are renamed MINER-0..MINER-16 and map to the live ledger; the Master order (P0-P14) wins on conflict | Two numbering schemes would create the conflict the Master forbids | ledger rows reference MINER-n | IN FORCE |
| M2 | Allowed now: documents, an ADR and **schema drafts** (`hcs.miner.event.v1`, heartbeat, batch, ACK). Not allowed yet: receiver code, firmware branch, any device contact, dataset or training | Contract section 16 task order and milestone ("safe receiver with authenticated 30-second heartbeat and one durable test event"); the live order puts the core gates first | no `services/` or `cli/` change in this batch | PLANNED |
| M3 | Receiver is a **headless service in the existing Rust workspace** behind `hscl miner ...`, off by default, binding one private LAN interface, opt-in pairing, no internet exposure | Contract 2.1, 3.4, 3.5; root `AGENTS.md` rule 9 (no silent telemetry) and rule 7 (no broad root execution) | ADR + tests with a simulated device before any firmware work | PLANNED |
| M4 | **Everything in `timfromhcs/ESP-Miner` and `timfromhcs/CQ-HECS` (branches, PRs, flashing, merging the research branch) needs explicit owner approval** | Master rule 16 / decision P10 apply to every repository outside HSCL1; flashing hardware is irreversible | owner message | BLOCKED on owner |
| M5 | Device contact rule if ever authorised: GET only, exactly two addresses, identity by MAC + hostname + board + ASIC, stop on mismatch; IP alone is never identity | Contract 3.1/3.2 and stop conditions | recorded probe report with MACs redacted | PLANNED |
| M6 | Neural output is **advisory input to solvers**, never proof authority; UNSAT claims need an independent checker (existing DRAT checker in CQ-HECS); reduced-round SHA results never become claims about full-round SHA-256 or Bitcoin | Contract 7.x, 18 lines 16-17; same rule as the CQ-HECS evidence policy | checker-verified labels only | IN FORCE |
| M7 | The contract's own 2-minute development cron is **not** the session ping and not the durable scheduler (ledger row 8); neither runs as root, neither flashes, probes devices or trains | Conflict C8 | design note `SELFHEAL_SCHEDULER_DESIGN.md` | IN FORCE |

## 3. Conflicts and gaps (also in the live ledger)

- Contract snapshot is older than reality (HSCL1 `4bdcb2f` vs `3a32d56`). Refresh at task start, as the contract itself demands.
- The contract's priority numbers collide with the Master's (M1). Its HCSUDA mention ("host-side compute where supported") must follow the HCSUDA capability matrix, not assume GPU support.
- Receiver port `8765` is a proposal: no conflict check done on this host or against the HSCL1 firewall convention.
- TLS pinning on the ESP32-S3 is unmeasured; the contract forbids a silent downgrade to plain HTTP. No measurement exists.
- Backup: the contract says the WLAN backup is app-partition only; a full-chip backup procedure is unverified. No flashing before a verified private backup.
