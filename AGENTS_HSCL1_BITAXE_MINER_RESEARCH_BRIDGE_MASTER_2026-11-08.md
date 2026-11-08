# HSCL1 Miner Research Bridge — Master AGENTS Specification

**Revision:** 2026-11-08  
**Primary product:** `timfromhcs/HSCL1`  
**Firmware source:** `timfromhcs/ESP-Miner`  
**Research/solver consumer:** `timfromhcs/CQ-HECS` through HSCL1's existing integration boundary  
**Target devices:** the two explicitly known Bitaxe Ultra candidates at `192.168.178.61` and `192.168.178.66`; exact identity must be established at runtime  
**Target OS:** HSCL1, based on the existing Ubuntu/Kubuntu foundation, not a new independent desktop application  
**Operating mode:** miner continues normal mining while low-overhead telemetry and events are captured; bounded SHA research mode remains a separate, explicit, mining-paused mode  
**Priority:** P0 — create a reliable, safe, local-first data bridge from physical mining hardware into HSCL1's research, evidence, ML and SAT workflows  
**Credit:** Made with love by hcsmedia · timfromhcs

> **This is an implementation contract and a design derived from repository evidence. It is not evidence that the receiver, firmware changes, datasets, neural models, MCP actions, cron jobs or UI have already been implemented.** The agent must inspect current source and tests before making changes and must update this document's status ledger with real results.

---

# 0. THE CORRECT PRODUCT GOAL

The Bitaxe is not a separate product that HSCL1 merely monitors. It is a small, network-connected, physically operating research device that continuously supplies real-world mining, hashing, protocol, thermal, power, network, reliability and cryptographic-test observations to HSCL1.

**HSCL1 is the receiver, durable memory, analysis environment, training-data factory, experiment controller and research coordinator.** ESP-Miner is the field firmware and measurement source. CQ-HECS/HCSPNP consumes carefully prepared cryptographic and SAT workloads. HCSUDA supplies host-side compute where supported. Existing HSCL1 agent orchestration, evidence and plan systems coordinate the work.

The result should feel like one feature built into HSCL1:

- HSCL1 discovers only the two user-authorized candidate addresses or a previously paired device.
- It verifies which physical miner is at an address before assigning it a stable device identity.
- The miner checks every 30 seconds whether the HSCL1 receiver is reachable on the configured local port.
- Normal mining is not paused merely because HSCL1 is offline, rebooting, building, training or running a benchmark.
- The miner records compact, typed, low-overhead events and measurements, buffers them locally within strict resource limits, and uploads batches when HSCL1 is available.
- HSCL1 stores raw evidence safely, validates and normalizes events, derives datasets and benchmarks, and links every result to firmware, device, job, time, schema and model versions.
- Research agents use these observations to generate hypotheses, build controlled experiments, train and evaluate neural heuristics, benchmark SAT portfolios, and produce proposed improvements.
- Accepted model suggestions can be deployed as *advisory* or *bounded heuristic inputs* to CQ-HECS. They do not become truth or proof authority.
- The miner may receive a signed, versioned recommendation profile from HSCL1 for observation or human-approved operational tuning. It must never blindly accept arbitrary model-generated settings or code.

The crucial architecture is:

```text
┌────────────────────────────── HSCL1 OS ──────────────────────────────┐
│                                                                      │
│  Control Center / Miner Lab / CLI / Existing Agent & MCP Orchestration│
│                   │                                                  │
│                   ▼                                                  │
│  HCS Miner Receiver (local service, configured port, mDNS + pairing) │
│                   │                                                  │
│  ┌────────────────┼───────────────────────────────────────────────┐  │
│  ▼                ▼                 ▼                 ▼           │  │
│ Device Registry  Event Intake   Backup Vault     Live State        │  │
│  │                │                 │                 │           │  │
│  └────────────────┴─────────────────┴─────────────────┘           │  │
│                   ▼                                                  │
│  Immutable Evidence Store + Dataset Catalog + Feature Pipeline       │
│                   │                                                  │
│       ┌───────────┼─────────────┬──────────────────┐                 │
│       ▼           ▼             ▼                  ▼                 │
│   Miner QA    SHA Research   SAT/HCSPNP        Mining Optimizer      │
│   & Anomaly   & Replay       Solver Lab        (advisory)            │
│       │           │             │                  │                 │
│       └───────────┴─────────────┴──────────────────┘                 │
│                   ▼                                                  │
│       Evidence / Benchmarks / Models / Approved Recommendations       │
└───────────────────┬──────────────────────────────────────────────────┘
                    │ authenticated local Wi-Fi transfer
                    ▼
┌────────────────── Bitaxe / ESP-Miner ─────────────────────────────────┐
│ ASIC + ESP32-S3 · existing AxeOS API · event instrumentation          │
│ PSRAM queue · bounded flash spool only after partition approval       │
│ normal mining continues · heartbeat every 30 s · batch ACK/retry      │
│ existing SHA software oracle is optional and must not be confused     │
│ with inaccessible internal BM1366 ASIC round state                    │
└───────────────────────────────────────────────────────────────────────┘
```

## 0.1 Two connected but separate learning loops

There are two useful loops. Do not incorrectly collapse them into one.

### Loop A — make mining operation more reliable and efficient

Use actual telemetry to forecast and detect:

- hashrate stability and variance;
- power draw and energy efficiency;
- ASIC and regulator temperatures;
- fan response and thermal margins;
- Wi-Fi RSSI, DHCP/DNS recovery and pool latency;
- rejected, stale, duplicated or invalid shares;
- job-notification drops and queue stalls;
- memory pressure, allocation failures, reboot causes and long-term drift;
- frequency/voltage/power settings associated with stable operation.

The result is an evidence-backed report and, later, a bounded recommendation such as “this known profile is more stable at this measured room-temperature range”. It is **not** permission for an ML model to change voltage, frequency, fan policy, thermal limits, pool, wallet or network configuration without explicit owner approval. Existing hardware protection must always override any optimiser.

### Loop B — use real mining/hash observations to improve cryptographic research and SAT heuristics

The bridge supplies real, well-described hashing contexts and known outcomes. HSCL1 can derive:

- validated Bitcoin-style 80-byte header test cases where permitted;
- candidate nonce and target-verification records;
- known-answer SHA-256/SHA-256d vectors;
- software SHA-256 compression traces from the optional firmware oracle;
- reduced-round SHA-256 constraint instances generated on the host;
- controlled SAT/SMT/MILP/CP models with known witnesses or independently verified UNSAT results;
- solver telemetry, branching decisions, conflicts, propagations, restarts, cube sizes and proof-checking outcomes.

This can create realistic datasets for SAT guidance, hash-model testing and solver-portfolio research. It does **not** mean a neural network can replace the BM1366 nonce-search engine or that SAT is expected to outperform a hundreds-of-GH/s ASIC on full SHA-256 mining.

---

# PART I — AUDITED REALITY AND CURRENT REPOSITORY STATE

# 1. Repository snapshot checked on 8 November 2026

The agent must refresh all of this at task start. Branches, PRs, firmware and CI can change after this snapshot.

## 1.1 User-owned firmware repository

Repository: <https://github.com/timfromhcs/ESP-Miner>

Observed default branch is `master`. At the inspected snapshot:

- `master` head: `21f543cbd3abd151338815f5accd1687775ecd6d` (29 October 2026).
- There were four historical PRs in the fork, all closed/merged; no open PRs were returned.
- Latest merged PR #4 added the logo, README entry point and firmware deep-dive documentation.
- The fork advertises stable `v4.0.1-stable` and has `v4.0.2-rc1` merged into master but not represented as a published stable release in the README.
- Master already includes extensive networking recovery, power/thermal safety, memory headroom protection, OTA checks and evidence documentation.

The most important finding is a working, **unmerged feature branch**:

`feat/timsminer-sha-research-mode`

- Head: `07de7e463a1d2f4203ddb904ab06fe960273f2cc` (2 November 2026).
- GitHub comparison: **8 commits ahead, 0 behind** `master` at the checked time.
- Six observed CI/check results were successful: `Test Results`, `host-tests`, `build-and-test`, `build-research`, `frontend-test`, `build`.
- It is not merged into `master`; do not claim that master already contains it.

The eight feature-branch commits, from oldest to newest, are:

1. `1621dde` — optional on-device SHA oracle, bounded research API, running-app backup.
2. `288adb5` — reproducible CI artifact for the research variant.
3. `4f6c6a9` — CI action-pin typo correction.
4. `f30a8c8` — backup response headers receive independent storage.
5. `105d158` — streaming backup digest uses the repository's SHA implementation.
6. `941e4b0` — positive JSON prebuffer allocation fix.
7. `356b985` — research guard keyed to the actual paused/mining state.
8. `07de7e4` — same guarded research session can be driven from USB console.

### 1.1.1 What already exists on this branch

The branch adds or modifies:

- `main/research/research_sha.c/.h` — portable C SHA-256/SHA-256d implementation, incremental hashing, compression schedule, round tracing and JSON serialization;
- `main/research/research_guard.c/.h` — state machine, pairing token, identity, mining, thermal, power, job and time-budget checks;
- `main/http_server/research_api.c/.h` — bounded API routes for research state, capabilities, challenge/arm/pause/resume/cancel/disarm, SHA trace and digest;
- `main/http_server/backup_app.c/.h` — read-only download of the currently running application partition with a streamed SHA-256 digest;
- `main/research/research_console_parse.c/.h` — strict parser for the USB research console;
- `sdkconfig.research.defaults` — research-build configuration, 64-job budget, 900-second active-time budget, 65 °C ceiling and readable USB serial/JTAG console;
- `docs/RESEARCH_MODE.md`, `docs/WLAN_BACKUP.md` and CI/build updates;
- host test files for the SHA engine, guard and USB console.

The feature branch documentation states that the same C SHA code is compiled into firmware and host tests, and that a trace is shaped for `cqhecs.sha.round_trace.replay()` using `hcs.sha.trace.v1`. The trace is a **software computation** on the ESP32-S3. It is not internal ASIC state.

The guard requires a short-lived operator token, verified device identity, mining paused with no in-flight share, fresh/known thermal data and bounded job/runtime budgets. It refuses unknown thermal state. It does not alter pools, wallet, Wi-Fi configuration or OTA partitions.

The USB console is not a remote shell. It exposes named, parsed commands under the same guard, token and budget. It exists because the console line length is limited and trace output shares the USB log channel. The branch documentation says a 128-hex block must be uploaded as ordered chunks because long typed lines are truncated, and a trace dump temporarily silences unrelated log output to avoid interleaving.

### 1.1.2 What is not yet implemented by that branch

Do not mistake the feature branch for the requested end-to-end HSCL1 system. The following were **not found as implemented** in its eight-commit diff:

- no HSCL1 receiver service;
- no mDNS/DNS-SD service discovery between miner and HSCL1;
- no periodic 30-second receiver heartbeat;
- no device-to-host batch upload or acknowledgment protocol;
- no reliable offline upload queue;
- no device registry or pairing lifecycle managed by HSCL1;
- no persistent miner event spool with a reviewed partition layout;
- no structured event dataset exporter for jobs, shares, thermal, power and networking;
- no model-training pipeline or ML registry;
- no trained GNN/solver heuristic from miner data;
- no integrated HSCL1 Miner Lab card or CLI subcommands;
- no CQ-HECS dataset ingestion connector;
- no secure export of all NVS configuration secrets;
- no full-chip or NVS backup through the new WLAN backup endpoint.

The branch is a useful foundation. Extend it; do not throw it away or create a parallel firmware app.

## 1.2 Firmware API and data already available

The current AxeOS/ESP-Miner API exposes rich information in `/api/system/info`, `/api/system/asic`, `/api/system/statistics`, `/api/system/scoreboard`, `/api/system/logs`, and the live WebSocket routes. The repository OpenAPI schema documents, among other fields:

- board version, ASIC model, firmware version, IDF version, MAC, hostname and uptime;
- hash rate, rolling averages, expected hashrate and error percentage;
- accepted/rejected shares and rejection reasons;
- power, voltage, current, actual core voltage, frequency and fan readings;
- ASIC temperature, secondary temperature, VR temperature, thermal state and target;
- Wi-Fi status, RSSI, IP and AP mode;
- free internal heap, PSRAM, minimum free heap and largest allocation;
- pool protocol, endpoint, difficulty, response time and fallback selection;
- ASIC hash domains, ASIC count/model and ASIC error counter;
- notifications, work, dropped notifications, block height and statistics arrays.

The raw firmware logs are useful but must be handled carefully. The README explicitly documents that the `mining.authorize` request may expose credentials in INFO logs and that the log endpoint is readable to local-network clients. Treat raw logs as sensitive until redacted. A parser must never assume that the log ring is already safe to publish or train on.

## 1.3 Backup route limitations

The branch's `GET /api/system/backup/info` and `GET /api/system/backup/running-app` back up the **currently running application partition only**. The documentation explicitly excludes:

- bootloader;
- partition table;
- OTA metadata (`otadata`);
- NVS, including Wi-Fi/pool/wallet configuration;
- eFuses.

It is not a full-chip backup and does not restore configuration. It returns the exact running application partition bytes with size, partition, version and SHA-256 metadata. A host collector must preserve this scope label and must never call this a complete device backup.

The current master firmware API masks pool passwords in ordinary configuration responses. A complete private configuration backup therefore needs a separately designed, authenticated, one-shot export path or an explicitly verified out-of-band backup. Never infer that a masked API object is a full backup.

## 1.4 Current partition table — critical constraint

The inspected `partitions.csv` is:

```csv
# Name,      Type, SubType,   Offset,    Size, Flags
nvs,         data, nvs,       0x9000,    0x6000
phy_init,    data, phy,       0xf000,    0x1000
factory,     app,  factory,   0x10000,   4M
www,         data, spiffs,    0x410000,  3M
ota_0,       app,  ota_0,     0x710000,  4M
ota_1,       app,  ota_1,     0xb10000,  4M
otadata,     data, ota,       0xf10000,  8k
coredump,    data, coredump,          ,  64K
```

This layout has no named HCS telemetry partition. It already uses large app and web partitions. The physical flash capacity and any remaining unpartitioned range must be verified from the actual device and build. Never assume a few unused addresses are a safe data partition. Never repurpose `www`, `coredump`, NVS, an OTA slot or a factory image partition as a data spool.

**Phase 1 must use bounded RAM/PSRAM buffering and immediate HSCL1 upload.** A persistent flash spool is a later, separate design decision requiring verified flash capacity, a partition-table migration plan, rollback/recovery tests, wear-leveling and a full backup. Do not change the partition table in the first firmware feature PR.

## 1.5 User device identity evidence is inconsistent

At the current README snapshot, the two candidate units are described as:

| Candidate | Current README mapping | Board/ASIC | MAC identity in current README/evidence |
|---|---|---|---|
| `192.168.178.61` | `timsminer` | Board 201 / BM1366 | README's 2026-10-29 report identifies MAC ending `DD:3C` |
| `192.168.178.66` | `blackharkminer` | Board 201 / BM1366 | README's earlier evidence identifies MAC ending `99:80` |

Other historical evidence/report text in the repository has used the names and addresses inconsistently. Therefore, these rows are *candidate labels*, not runtime identity authority.

**Runtime identity rule:** query only `.61` and `.66` because the user explicitly named those two candidates; do not perform broad subnet scans. Read `/api/system/info` and `/api/system/asic` without writing anything. Verify `macAddr`, `hostname`, `boardVersion`, `ASICModel`, firmware version, IP and AP mode. Assign the host's internal device ID only after those fields are consistent with the approved registry. If a response does not match, mark `IDENTITY_MISMATCH` and stop. Never choose a device because its IP answered first.

## 1.6 Current fork is behind important upstream work

The official upstream project `bitaxeorg/ESP-Miner` had several open PRs at the inspected snapshot. Relevant examples include:

- #2063 Stratum driver abstraction;
- #2064 Stratum failover/session handling refactor;
- #2065 pool-session encapsulation;
- #2055 physical BOOT-button unlock for OTA and firmware activation;
- #2058 ASIC temperature-sensor-loss safety stop;
- #2060 stalled-fan safety detection;
- #2074 sensor read during overheat cooling;
- #2082 large coinbase-job support (draft at the inspected time, with a reported 512 KiB suffix and additional memory/log handling);
- #2062 pool ordering and reconnect optimization;
- #2061 SV2 certificate validity dates after an NTP-trusted clock.

These are not all equivalent in maturity or applicability. Some descriptions say build/QEMU tests passed but hardware validation is absent; #2055 reports a much broader physical validation record. Do not merge any of them blindly. Create a source-level compatibility table and cherry-pick/rebase only after reviewing dependencies, changed contexts, new bugs and the local test suite.

Upstream also merged the ESP-IDF 6.0.3 bump (#2072). The current fork's branch docs/build configuration say ESP-IDF 6.0.2. Validate the exact IDF version and dependency graph before importing upstream changes. Do not bump the toolchain just because a newer version exists.

## 1.7 Current HSCL1 repository snapshot

Repository: <https://github.com/timfromhcs/HSCL1>

Observed:

- `main` head: `4bdcb2f8ab628023ef85c3560b438024b90836eb` on 7 November 2026;
- no open PRs were returned by the latest PR query at the time of the second audit;
- root `AGENTS.md` blob was `88a8a9cc3fd25929a240619799b366bc8deff8fb` (113,402 bytes);
- HSCL1 already has Rust CLI (`cli/hscl`), `ai/`, `ai-shared/`, `apps/`, `hcsuda/`, `packages/`, `scripts/`, `tests/`, `docs/` and an existing agent/MCP configuration;
- the current architecture document marks the Control Center and privileged helper as planned, not shipped;
- the development loop includes `forge check`, a Linux/WSL parity gate, VM build/boot resource limits and a round-log anti-stall mechanism.

The receiver should be a **headless HSCL1 service first**, then an integrated Miner Lab/Control Center view. Do not invent a new OS, a second desktop shell, or a standalone unrelated mining application. The existing desktop may be incomplete; the data service and CLI must still be testable without the GUI.

## 1.8 CQ-HECS status and integration location

`timfromhcs/CQ-HECS` is the existing SAT/quantum-emulator research codebase. The host dataset processor should integrate through its existing Python APIs, solver portfolio, provenance and SAT Lab, not by reimplementing another solver inside firmware or HSCL1's receiver.

Use CQ-HECS source only after the current branch/main has been refreshed and the specific module APIs have been read. Preserve its existing `hcs.run.v2` provenance where applicable. The new miner dataset schemas are inputs to the existing experiment/evidence system, not a replacement run schema.

---

# PART II — PRODUCT ARCHITECTURE AND DATA FLOW

# 2. One direct HSCL1 product integration

Create one coherent HSCL1 feature named provisionally **HCS Miner Research Bridge**. The exact branding may be adjusted to match the current HSCL1 design tokens, but the engineering ownership is fixed.

## 2.1 Proposed HSCL1 code ownership

First inspect the actual repository layout and coding conventions. A proposed initial layout is:

```text
HSCL1/
├── apps/
│   └── miner-lab/                     # UI only after headless contracts are stable
├── services/
│   └── hcs-miner-ingest/              # local receiver/collector daemon (new if no fit exists)
├── ai/
│   └── ...                            # reuse current model/agent registry; no duplicate manager
├── ai-shared/
│   └── ...                            # shared typed agent/data contracts if an existing pattern fits
├── cli/
│   └── hscl                           # extend existing CLI with `hscl miner ...`
├── docs/
│   └── miner/
│       ├── ARCHITECTURE.md
│       ├── DATA_DICTIONARY.md
│       ├── THREAT_MODEL.md
│       ├── BACKUP_RESTORE.md
│       ├── DATASETS.md
│       ├── SAT_RESEARCH.md
│       ├── BENCHMARKS.md
│       └── BUILD_LOG.md
├── tests/
│   └── miner/                         # host-side integration/contract tests
└── scripts/
    ├── miner-doctor.*                 # only if it fits existing script conventions
    └── miner-fixture-generator.*
```

This is a proposed logical layout, not a claim that every directory exists. Do not create empty directories or duplicate services until code exploration demonstrates the appropriate owner. Prefer a single existing HSCL1 workspace/service pattern if one already fits.

**Prefer the existing Rust workspace and `hscl` CLI for the long-running receiver** if the repository's current service conventions support it. Python remains appropriate for data analysis, dataset generation, solver integration and training where existing libraries already live. Do not introduce a new runtime stack for the receiver unless there is a measured reason. The firmware remains ESP-IDF C.

## 2.2 Service responsibilities

The receiver daemon owns:

1. local interface binding and receiver health;
2. mDNS/DNS-SD advertisement and device discovery responses;
3. device pairing and identity registry;
4. authenticated ingest and idempotent acknowledgements;
5. live device state and heartbeat age;
6. bounded local queue/backpressure behavior;
7. immutable raw event and backup storage;
8. schema validation, deduplication and normalization;
9. dataset job creation and provenance;
10. export to CQ-HECS and other approved HCS research modules.

It does **not** own:

- ASIC scheduling, thermal control or mining job creation;
- wallet/pool selection;
- direct SAT solving;
- model training in the HTTP request path;
- arbitrary remote shell or code execution on the miner;
- firmware flashing without an explicit operator workflow.

## 2.3 Main data plane

```text
Miner event taps + periodic metrics
        │
        ▼
Firmware event normalizer
        │
        ├── high-priority safety/recovery events
        ├── job/share/protocol events
        ├── low-rate hardware telemetry
        └── optional research vectors
        │
        ▼
PSRAM bounded queue (sequence numbers, no heap growth loop)
        │
        ▼
30-second heartbeat + batch push when receiver is present
        │
        ▼
HSCL1 authenticated ingest API
        │
        ├── verify device pairing/signature/sequence/schema
        ├── deduplicate and acknowledge durable sequence range
        ├── write immutable raw batch
        ├── update live state projection
        └── schedule normalization/feature jobs
        │
        ▼
Dataset builder / benchmark harness / research agents
        │
        ├── mining reliability and efficiency models
        ├── SHA known-answer/replay/round trace datasets
        ├── reduced-round SHA SAT/SMT encodings
        ├── SAT branching / cube guidance datasets
        └── independently verified experiment evidence
```

Data ingestion and research execution are separate queues. A model training job must never block or delay live telemetry intake. A full disk must produce a clear `STORAGE_BACKPRESSURE` event and visible warning, not silently discard data.

---

# PART III — DEVICE DISCOVERY, PAIRING AND 30-SECOND HEARTBEAT

# 3. Find the miner on the local Wi-Fi safely

## 3.1 Candidate discovery order

1. Probe only `192.168.178.61` and `192.168.178.66` using read-only HTTP GET requests.
2. If the user has already paired a device and its IP changes, use its last known identity plus mDNS discovery for that specific device ID.
3. Support mDNS/DNS-SD only after the firmware advertises a service in a reviewed change. Candidate service type: `_hcs-miner._tcp.local.`; choose the final name after confirming ESP-IDF mDNS support and collision behavior.
4. Allow a manually configured endpoint when discovery is unavailable.
5. Never run a blind full-subnet scan, ARP sweep or port scan. Do not automatically select unknown Bitaxe/ESP devices.

## 3.2 Identity handshake

Read-only initial probe:

- `GET /api/system/info`;
- `GET /api/system/asic`;
- optionally `GET /api/system/statistics`, `/api/system/scoreboard` and `/api/system/logs` only after the device identity is confirmed and log privacy handling is in place.

Expected identity evidence fields:

- MAC address;
- hostname;
- board version;
- ASIC model;
- firmware version and AxeOS version;
- running partition;
- current IP;
- AP-mode flag;
- uptime/reset reason.

HSCL1 creates a stable `device_id` as a UUID or another opaque stable identifier during pairing. The device's MAC/hostname is identity evidence, not the primary database key. Do not derive a public identifier from a wallet, worker name, SSID or password.

Pairing states:

`DISCOVERED → IDENTITY_CHECKED → PAIRING_REQUIRED → PAIRED → ACTIVE`

Other states:

`IDENTITY_MISMATCH`, `UNREACHABLE`, `AUTH_FAILED`, `STALE`, `REVOKED`, `QUARANTINED`.

A device may upload only after `PAIRED`. `DISCOVERED` devices remain read-only.

## 3.3 Pairing protocol

A pairing ceremony must prove that the operator controls both HSCL1 and the physical miner.

Preferred initial method:

- HSCL1 shows a short-lived random pairing challenge and a local confirmation code.
- The physical device exposes the code through USB serial/log or an explicitly pressed hardware-button workflow supported by the board.
- The operator confirms the expected identity on HSCL1.
- Both sides derive or provision a per-device HMAC secret or keypair through a documented secure handoff.
- The secret is stored in the HSCL1 secret store, never in Git, training datasets, screenshots, crash logs or public reports.
- Pairing expires quickly and is single-use. Re-pairing or key rotation requires explicit owner action.

Do not rely on the existing six-digit research token as durable device authentication. The research token is documented as a speed bump and is not strong authentication if the same-LAN client can read the logs.

## 3.4 Receiver local port and protocol

Use a configurable port, with `8765` as the proposed default only after checking for conflicts and the HSCL1 firewall convention. Bind to the selected private LAN interface, not every interface by default. Provide a local-only health endpoint and a receiver status command.

Suggested versioned endpoints:

| Endpoint | Method | Purpose |
|---|---|---|
| `/v1/health` | GET | local receiver health for operator diagnostics |
| `/v1/pair/challenge` | POST | one-time device pairing challenge |
| `/v1/devices/{device_id}/heartbeat` | POST | 30-second device liveness and state summary |
| `/v1/devices/{device_id}/events` | POST | batch upload, idempotent by sequence range |
| `/v1/devices/{device_id}/backup-manifest` | POST | announce backup artifacts and hashes |
| `/v1/devices/{device_id}/backup-chunk` | POST | optional chunked artifact upload with resumable offsets |
| `/v1/devices/{device_id}/ack` | GET/POST | protocol-specific batch acknowledgement if separated from upload |
| `/v1/devices/{device_id}/commands` | GET | fetch only signed, typed, explicitly approved advisory commands |

Names may change to fit existing HSCL1 APIs. The versioning and semantics may not.

## 3.5 Security for the receiver

The existing ESP-Miner APIs are documented as plain HTTP without application authentication, protected only by a local-network check. The research API also uses the existing local-network guard. This is not acceptable for a new durable telemetry ingestion path.

New data transfer must use:

- TLS with a host certificate pinned during pairing, or a formally reviewed equivalent secure channel;
- request authentication (HMAC-SHA-256 or a per-device signing key) over canonical method, path, timestamp, sequence range and body digest;
- request freshness window and replay protection;
- unique monotonically increasing sequence numbers and boot IDs;
- bounded payload sizes and strict schema validation;
- per-device authorization scope;
- private-network firewall restriction;
- rate and body-size limits;
- secrets redaction before any logging;
- no port forwarding and no internet exposure.

If the ESP32-S3 TLS cost, available heap or current IDF build makes pinned TLS too costly, do not silently downgrade to unauthenticated HTTP. Produce measurements and compare a carefully reviewed local HMAC scheme plus network isolation. Any downgrade must be a documented decision with a threat model and owner approval.

## 3.6 Thirty-second heartbeat state machine

The miner initiates a heartbeat every 30 seconds while Wi-Fi is connected. Heartbeat interval is configurable but not faster than the validated default. Jitter the schedule slightly to avoid synchronized bursts if multiple devices are paired.

A heartbeat contains:

- device ID and boot ID;
- firmware version and source commit/build ID;
- monotonic uptime and wall-clock quality;
- current IP and Wi-Fi state;
- last acknowledged event sequence;
- pending queue depth and oldest pending age;
- current mining state (running/paused/research mode);
- compact resource/thermal summary;
- protocol/schema version.

The server responds with:

- `receiver_id`;
- acknowledged sequence watermark;
- accepted schema versions;
- receiver time and clock offset hint;
- batch size/flow-control budget;
- optional advisory policy version/hash;
- explicit pause or revoke state only where appropriate.

Device states:

`CONNECTED → RECEIVER_PRESENT → UPLOADING → ACKED`

and on failure:

`NO_RECEIVER → BUFFERING → RETRY_WAIT → DISCOVERY → RECEIVER_PRESENT`.

After three missed heartbeat acknowledgements, mark the receiver `STALE` on the device and continue mining. Do not pause mining, reboot the device or change its pool because HSCL1 is unavailable. Reconnect using exponential backoff with jitter, capped to a reasonable interval. Keep the 30-second heartbeat cadence as the normal liveness check; upload batches may be less frequent or coalesced according to bandwidth and queue state.

The HSCL1 UI should show a clear status:

- `LIVE` — authenticated heartbeat recent;
- `UPLOADING` — events in transfer;
- `BUFFERING` — device holds unacknowledged data;
- `STALE` — no heartbeat within threshold;
- `OFFLINE` — explicitly disconnected or not reachable;
- `QUARANTINED` — authentication/schema/identity problem.

---

# PART IV — FIRMWARE TELEMETRY AND EVENT MODEL

# 4. Observe the mining device without stealing work from the ASIC

The first firmware work should instrument existing state transitions and counters. Do not rewrite the mining scheduler or Stratum implementation merely to collect data.

## 4.1 Sampling schedule

| Signal | Default capture cadence | Method | Notes |
|---|---:|---|---|
| Liveness heartbeat | 30 s | device-initiated request | independent from metrics upload |
| System snapshot | 30 s | copy existing state | avoid calling slow or blocking functions in time-critical tasks |
| Hashrate and rolling averages | 30 s | sample existing counters | keep 1m/10m/1h metrics distinct |
| ASIC domain rates/errors | 30 s | existing ASIC state | preserve domain index and ASIC identity |
| Power/voltage/current | 30 s | existing measurements | include sensor validity and timestamp |
| ASIC/VR temperatures | 30 s | existing thermal state | unknown/stale readings are explicit, not `0` |
| Fan PWM/RPM | 30 s | existing fan controller state | include sensor-validity flags |
| Wi-Fi RSSI/IP/state | 30 s and state change | event + sample | don't over-poll Wi-Fi driver |
| Heap/PSRAM/min heap/max allocation | 30 s and threshold crossing | existing memory metrics | no large dynamic allocation in the telemetry path |
| Boot/reset/recovery events | event-driven | hook existing event transitions | always high-priority |
| Pool connect/disconnect/failover | event-driven | Stratum state machine | redact credentials and worker identifiers |
| Job/notify lifecycle | event-driven, bounded | existing Stratum handler | never store unlimited raw payloads |
| Share submitted/accepted/rejected | event-driven | existing submit/result path | capture reason class and latency |
| ASIC errors/reinitialization | event-driven + counter deltas | driver path | no per-nonce INFO logs |
| High-rate raw samples | opt-in lab mode only | measured sampling plan | disabled by default |

The user asked for richer data. Richer means meaningful typed measurements, event transitions, counters and correlations—not indiscriminately copying every packet or logging every nonce. Every event type must have a budget and a defined sampling policy.

## 4.2 Required event families

### Device lifecycle

- boot start/complete;
- identity initialized/verified;
- firmware version, build ID and partition;
- reset reason;
- configuration generation (not secrets);
- watchdog/reset/recovery events;
- task startup failure and hardware self-test result.

### Network and receiver

- Wi-Fi associated/disassociated;
- BSSID change (MAC may be treated as sensitive local metadata);
- RSSI bucket/change;
- DHCP start/lease/loss/timeout;
- DNS resolution success/failure and resolver class;
- gateway reachability result;
- Stratum TCP/TLS/Noise connection state;
- receiver discovery, heartbeat success/failure, upload retry and ACK;
- queue pressure, overflow, drop and recovery.

### Stratum/work pipeline

- protocol V1/V2 and connection/session generation;
- pool identity as a local opaque `pool_id`, not URL/user/password in the training record;
- job received, accepted, rejected, replaced, expired or stale;
- notify parse failure category;
- difficulty and version-rolling-mask changes;
- job queue depth and stale-job discard count;
- share candidate/validation/submission/acknowledgement;
- share result and rejection reason class;
- response and round-trip latency;
- fallback/failback and reconnect sequence.

The event model must tolerate upstream Stratum refactors (#2063–#2065) by placing telemetry hooks at stable, semantic boundaries rather than tying the bridge to one concrete task/function name.

### ASIC and power

- ASIC model, family and driver version;
- frequency requested and actual;
- nominal and measured core voltage;
- power/current/board voltage;
- chip and regulator temperatures;
- fan mode, PWM, tach readings and sensor validity;
- per-domain hashrate/error counts;
- ASIC init/reinit/communication errors;
- thermal throttle, power limit, hardware fault and safe stop.

### Software/quality/performance

- internal heap free/minimum/largest block;
- PSRAM free/minimum/largest block if available;
- allocation failure category;
- CPU utilization and task-level runtime only if measured without significant perturbation;
- log ring high-water mark and dropped-log count if available;
- loop/task latency and deadline misses for newly added telemetry work;
- firmware event queue depth and processing lag.

## 4.3 Never collect these in normal training telemetry

- Wi-Fi password or raw credentials;
- wallet/payout address;
- Stratum password, authorization string or worker username if it may contain a wallet;
- API tokens, pairing/HMAC keys, TLS private keys or OTA credentials;
- raw NVS contents;
- full coinbase transaction or scriptSig by default;
- raw logs before secret redaction;
- personal IP/MAC identifiers in any public/research-export dataset unless explicitly authorized;
- serial numbers, account names or local network metadata as public labels.

The private encrypted backup may hold secrets when explicitly requested. The research dataset must not.

## 4.4 Avoid hot-path instrumentation regressions

- Do not allocate variable-size JSON objects in ASIC result or Stratum hot paths.
- Do not perform disk writes, network calls, TLS, compression or model inference in mining tasks.
- Emit fixed-size event structs into a bounded queue.
- A lower-priority telemetry task performs serialization, compression and network upload.
- Use atomics/critical sections already accepted by FreeRTOS/ESP-IDF patterns; avoid long critical sections.
- Never log every nonce or every hash result at INFO.
- Use counters and histograms with bucketed latency; sample rare detailed events.
- If queue is full, preserve high-priority safety and state-transition events. Record overflow counts. Drop or coalesce low-priority repeated gauge samples according to a documented policy.
- Verify added stack, heap, PSRAM and task-priority cost on real hardware.

---

# PART V — HOST RECEIVER, STORAGE AND BACKUP

# 5. Durable, resumable data intake in HSCL1

## 5.1 Data contract

Every incoming record uses a versioned envelope. Suggested shape:

```json
{
  "schema": "hcs.miner.event.v1",
  "device_id": "opaque-stable-device-id",
  "boot_id": "random-per-boot-id",
  "sequence": 18293,
  "event_id": "stable-idempotency-key",
  "event_type": "share.accepted",
  "event_time_monotonic_ns": 187540000000,
  "event_time_utc": "2026-11-08T12:34:56.789Z",
  "clock_quality": "ntp_synced",
  "firmware": {
    "version": "v4.x-research",
    "source_sha": "actual-build-sha-or-unknown",
    "idf_version": "actual-idf-version"
  },
  "device": {
    "board": "201",
    "asic_model": "BM1366",
    "device_model": "Ultra"
  },
  "payload": {
    "job_ref": "opaque-job-id",
    "latency_ms": 108.4,
    "result": "accepted"
  },
  "privacy_class": "local_research",
  "integrity": {
    "body_sha256": "...",
    "signature": "..."
  }
}
```

This is illustrative; do not copy placeholders into a real event. `device_id` is assigned by HSCL1. Every payload schema requires a JSON Schema/Serde-equivalent validation definition and a compatibility policy.

Required semantics:

- `sequence` is monotonic within a `boot_id` and never reused;
- `event_id` makes delivery idempotent;
- `event_time_monotonic_ns` is the ordering anchor within one boot;
- wall time has an explicit quality flag (`ntp_synced`, `rtc_estimated`, `unknown`);
- device and firmware metadata is included without secret settings;
- missing values are null/unknown with a reason, never silently replaced by zero;
- schema version is explicit;
- body hash and authenticated request protect integrity and replay handling.

Align the semantic fields with the stable OpenTelemetry Logs Data Model where useful (`Timestamp`, `ObservedTimestamp`, `Severity`, `Body`, `Resource`, `Attributes`, `EventName`) rather than inventing opaque, untyped log blobs. Preserve firmware-specific fields as typed attributes.

## 5.2 Transport format

Prototype with bounded JSON/NDJSON to make debugging easy. Once schema is stable, benchmark CBOR or another compact binary format for MCU bandwidth and allocations. Use compression only on complete batches, after measuring CPU, memory and wire-size impact. The firmware must not compress each small record independently.

Recommended pipeline:

1. fixed-size event structs on device;
2. bounded batch assembled in lower-priority task;
3. serialize to JSON/CBOR;
4. optionally gzip/deflate for batches if the chosen IDF library is already available and memory headroom allows;
5. authenticate and send;
6. host validates and durably commits;
7. host ACKs sequence watermark and body hash;
8. device releases only acknowledged records.

Do not add Zstandard to ESP firmware without measuring binary size, peak memory and CPU. Host-side compression can use zstd on immutable sealed segments.

## 5.3 Append-only host storage

Use a local, versioned data root under HSCL1's data directory; exact OS paths and permissions must follow the current packaging model. Suggested logical structure:

```text
miner-data/
  registry/
    devices.sqlite
    pairing-metadata/               # key references only, no plaintext secrets
  raw/
    <device_id>/
      <date>/
        events-000001.ndjson.zst
        events-000002.ndjson.zst
        batch-manifests.jsonl
  backups-private/
    <device_id>/
      <date>/
        backup-manifest.json
        running-app.bin
        config.sealed
        api-snapshot.redacted.json
        logs.raw.sealed
  datasets/
    <dataset_id>/
      manifest.json
      schema.json
      train.parquet
      validation.parquet
      test.parquet
      data-quality.json
      lineage.json
  benchmarks/
    <campaign_id>/
      manifest.json
      raw-results.jsonl
      summary.json
      plots/
  models/
    registry.json
    <model_id>/
      manifest.json
      weights.safetensors-or-approved-format
      evaluation.json
      model-card.md
```

The path names are illustrative. The actual implementation should use HSCL1's existing data-directory policy and database conventions.

Rules:

- raw ingress is append-only and immutable after a batch is sealed;
- a batch is marked committed only after fsync/durable-write semantics appropriate to the host storage layer;
- the device receives ACK only after the raw data and its manifest are durably committed;
- repeated uploads are deduplicated by `device_id + boot_id + sequence/event_id + payload hash`;
- corrupted or schema-invalid batches are quarantined, never silently deleted;
- normalized data and derived datasets reference raw batch IDs;
- keep a catalog/index separate from large raw objects;
- use atomic temp-file → fsync → rename for manifest completion;
- disk quota and retention policy are configurable and visible;
- keep raw and normalized datasets separately identifiable;
- do not delete the only raw copy after dataset generation.

## 5.4 Storage policy and the user's “store as much as possible” goal

Store as much useful evidence as the device and PC can safely support, not unbounded noise.

On the miner:

- Phase 1: bounded RAM/PSRAM queue only, with clear high-water/drop counters;
- Phase 2: investigate a persistent flash spool only after a verified partition-map proposal and full recovery plan;
- never use NVS for high-frequency append-only telemetry;
- never write to OTA, app, bootloader, NVS, www or coredump areas as a makeshift log partition;
- never erase or format storage just because HSCL1 cannot connect;
- never delete unacknowledged events to make room without recording a loss interval and applying an approved overflow policy.

On HSCL1:

- store raw logs/evidence losslessly;
- compress closed raw segments losslessly (e.g. zstd) only after an immutable copy is committed;
- store structured normalized tables as Parquet/Arrow only after schema validation;
- keep a manifest with hashes and compression metadata;
- do not use lossy sampling for the raw archive;
- derived training sets may downsample with a documented selection algorithm and lineage;
- use a configurable size/retention budget with a warning before cleanup;
- default cleanup may delete regenerable caches but never the private backup, raw source evidence or a dataset referenced by a published experiment.

## 5.5 Backup workflow — do this before any firmware modification

A backup is a prerequisite, not a post-flash action.

### Read-only preflight

1. Discover `.61` and `.66` only, identify each separately.
2. Record all identity fields and the active partition.
3. Read current API snapshots: system info, ASIC, statistics, scoreboard, logs and relevant partition list.
4. Record running firmware version, build/date and source SHA if known.
5. Record pool slot ordering, protocol, endpoint, port, TLS flags, worker/payout identity and fallback selection to a **private** secret store. Ordinary API responses may mask passwords; record that limitation explicitly.
6. Record Wi-Fi SSID/BSSID only in the encrypted private config backup; never place Wi-Fi password in ordinary telemetry.
7. Record frequency, nominal/actual voltage, frequency/voltage profiles, power target, fan mode/minimum, temperature target, display and other tuning flags.
8. Download the running application image through the existing backup route if the research branch is built and route available.
9. Compare the download digest to the response header/info metadata.
10. Preserve prior OTA partition metadata and the current app partition's build identity. Do not overwrite the previous slot.
11. If a full-chip/USB backup is required, create it through the documented recovery process and verify it against the chip; do not infer full-chip completeness from the WLAN app backup.
12. Create a signed/hashed manifest and perform a restore-readiness check before proceeding.

### Private configuration export

Design a separate one-shot export path for sensitive NVS values. The current backup branch does not export NVS. Prefer:

- explicit physical-button confirmation (or the board's validated physical-presence mechanism);
- one-time challenge and short expiry;
- encryption to an HSCL1 public key or TLS-pinned receiver;
- explicit secret field allow-list;
- no public logs or normal HTTP debug body;
- secret-store ingestion directly into encrypted vault;
- verify the host can decrypt/read the backup before a firmware change;
- no secret in datasets or agent prompt context.

Do not raw-copy NVS flash bytes and call it a portable configuration export. NVS encoding/encryption and device-specific partition state matter. Export supported configuration values through a typed API or use a verified full-flash backup with a clear restore method.

### Backup manifest

Must record:

- device ID and verified identity evidence;
- timestamp and clock quality;
- firmware version/source SHA/IDF version;
- chip/board/partition layout and flash size if measured;
- artifact filenames, types, sizes, SHA-256 hashes and scopes;
- whether secrets are included and encrypted;
- which values are redacted;
- restore procedure and tested/unverified status;
- previous active and OTA partition labels;
- host software/schema version.

A backup without a manifest and verified digest is incomplete. A backup without a tested restore path is `BACKUP_CAPTURED_NOT_RESTORE_VERIFIED`.

## 5.6 No destructive configuration changes

The first rollout must be telemetry-only. It must not:

- reset NVS;
- erase flash;
- change SSID/password/BSSID;
- change pool or wallet/worker;
- change ASIC voltage/frequency/power limits;
- change fan/thermal safety thresholds;
- update bootloader or partition table;
- OTA-flash a device automatically;
- switch partitions automatically.

All such operations require a separate reviewed task, a verified private backup, a specific device identity, an explicit owner approval and a rollback plan.

---

# PART VI — DATASETS AND RESEARCH PREPARATION

# 6. Make the logs useful for training, not merely archived

Every dataset must have a manifest, schema, lineage, split strategy, data-quality report, target definition and leakage assessment. Dataset generation is deterministic and re-runnable.

## 6.1 Dataset families

### D1 — miner reliability events

Purpose: learn and detect network/ASIC/software failure patterns.

Features:

- event sequence and class;
- time since boot;
- link state/RSSI bucket;
- reconnect attempt/step/backoff;
- DHCP/DNS/gateway success/failure class;
- Stratum connection/session generation;
- job queue depth and stale job counters;
- memory pressure and heap minima;
- ASIC init/reinit state;
- thermal state and sensor validity.

Labels:

- stable;
- transient_network_loss;
- dhcp_failure;
- dns_failure;
- pool_timeout;
- stale_job_or_share;
- asic_reinit;
- thermal_trip;
- fan_or_sensor_fault;
- memory_pressure;
- watchdog_or_reset;
- unknown/unlabelled.

Do not train a predictor on labels generated by the same heuristic it is supposed to evaluate. Human/independent diagnostics and later outcomes must be distinguished from heuristic-generated pseudo-labels.

### D2 — mining-efficiency time series

Purpose: model safe operating efficiency and anomalies.

Features:

- frequency and actual frequency;
- nominal/actual core voltage;
- power/current/board voltage;
- ASIC and VR temperature;
- fan PWM/RPM;
- per-domain rate and error count;
- rolling hashrates and variance;
- accepted/rejected shares, target/difficulty and latency;
- Wi-Fi RSSI and pool response latency;
- uptime, firmware version and board identity.

Derived quantities:

Energy efficiency when rates and power units are valid:

\[
\text{J/TH} = \frac{P\;[\mathrm{W}]}{H\;[\mathrm{TH/s}]}
\]

For hashrate in GH/s:

\[
\text{J/TH} = \frac{1000\,P\;[\mathrm{W}]}{H\;[\mathrm{GH/s}]}
\]

Reject ratio over a window:

\[
r_{\mathrm{reject}} = \frac{\Delta R}{\Delta A + \Delta R}
\]

where `A` is accepted and `R` rejected, with explicit reset/wrap handling. Do not compare cumulative counters across resets without differencing by boot ID and reset events.

Labels/targets:

- expected hashrate range;
- stable thermal envelope;
- energy-efficiency estimate;
- anomaly probability;
- confidence interval and abstention reason.

No model may change frequency/voltage without an explicit operator-approved experiment profile and independent safety guard.

### D3 — Stratum/work lifecycle

Purpose: study job churn, protocol behavior, stale work and pool responsiveness.

Capture compact event semantics for:

- work/job arrival and replacement;
- job lifetime and queue age;
- difficulty changes;
- version rolling mask changes;
- job creation/parse/drop failure categories;
- share submission and response;
- share reject reason class;
- response latency and batching;
- failover/failback and session state.

Do not store credentials, full authorization messages, raw worker IDs or coinbase transaction data in this dataset.

### D4 — SHA known-answer and replay corpus

Purpose: validate SHA implementations, block parsing, nonce verification and round-trace replay.

Record:

- algorithm and variant (SHA-256 or SHA-256d);
- message/block bytes only where privacy policy permits;
- block size and padding metadata;
- IV/state identifier;
- full-round or reduced-round count;
- expected digest/trace hash;
- origin (NIST/FIPS known-answer, generated fixture, permitted mining header, device software trace);
- device/host implementation versions;
- independent verifier version and pass/fail.

Never label a software-generated trace as an ASIC-internal trace. The BM1366 internal round state is not exposed by the firmware research interface.

### D5 — reduced-round SHA SAT/SMT instances

Purpose: research constraint modelling and solver guidance.

The HSCL1 host generates exact bit-vector/CNF encodings from controlled fixtures. The miner contributes verified workload context, candidate nonce examples and optionally software traces. The PC performs the expensive model generation and solving.

Every instance manifest states:

- SHA variant and compression function model;
- exact number of rounds and whether feed-forward is included;
- message schedule and IV constraints;
- fixed/free message bits;
- target condition;
- encoding method and exact encoding version;
- variable/clause counts;
- expected SAT/UNSAT status if known;
- witness if SAT, independently checked;
- proof format and independently checked certificate if UNSAT;
- hardware and solver metadata;
- resource/time limit and timeout status.

Start with toy instances and low round counts; then increase complexity using a published experimental ladder. Never imply that the dataset is a full SHA-256 break or that the full Bitcoin mining search can be solved by SAT in practice.

### D6 — SAT solver event traces and branch decisions

Purpose: train a model to guide existing solvers.

Potential records:

- formula features (variables, clauses, literal count, clause-length histogram, variable degree, graph structure, XOR ratio, community features, width proxies);
- chosen solver and config;
- selected variable/polarity/branch score;
- propagation/conflict/restart/learned-clause counters;
- decision level and backtrack statistics;
- cube size/splitting tree;
- runtime, memory, timeout and proof-check result.

Only collect detailed per-decision traces when the solver instrumentation overhead is measured and controlled. Aggregate traces are the default for broad campaigns.

### D7 — benchmark corpus and model evaluation

Purpose: prevent cherry-picking and measure generalization.

Every benchmark family has a generator/source description, family ID, instance IDs, seeds and licensing/redistribution notes. Partition by problem family, source instance, device, mining job or session—not random rows from the same correlated stream.

## 6.2 Dataset split rules and leakage prevention

Required split strategies:

- train/validation/test by distinct instance family;
- leave-one-device-out when training across `.61` and `.66`;
- time-based holdout for telemetry;
- hold out firmware versions for robustness tests;
- group all records from one job/session/block into one split;
- no overlapping SHA block/nonce instances across splits unless explicitly labelled as a leakage stress test;
- do not tune hyperparameters on the hidden test split;
- publish a dataset manifest hash and split hash.

For repeated observations from the same physical conditions, use grouped splits to avoid a model merely memorizing a board, firmware, pool or time period.

## 6.3 Data-quality and privacy gates

Before training:

- schema validation passes;
- sequence gaps are counted and explained;
- duplicate records are removed by idempotency key;
- time ordering and clock quality are preserved;
- reset/counter wrap semantics are normalized;
- null/invalid sensor readings are not converted to zero;
- sensitive-field scanner passes;
- wallet/worker/SSID/password/API-token patterns are redacted or dataset quarantined;
- provenance links to raw immutable artifacts;
- dataset split leakage checks pass;
- class imbalance and sample count are reported;
- no train/test split is inferred from a filename alone.

---

# PART VII — SAT, SHA, NEURAL GUIDANCE AND RESEARCH

# 7. What the miner data can and cannot teach the SAT system

## 7.1 Accurate relationship between Bitcoin mining and SAT

Bitcoin-style proof of work evaluates double SHA-256 over an 80-byte block header with a changing nonce (and, depending on protocol/job, other fields such as version/time/extranonce-derived Merkle root). The ASIC is specialized to this repetitive hash evaluation. The firmware receives candidate nonce reports and validates/submits work according to its existing pipeline.

The miner's normal data does **not** contain every hash attempted by the ASIC. It contains aggregate rate/counter information, job events and candidate nonces/results reported by the chip/firmware. Do not claim to record all hash attempts.

The existing research branch's `research_sha.c` computes SHA in ordinary C on the ESP32-S3. It can create per-round traces for a supplied block, but it is not a register dump or internal round trace from BM1366. Its research guard pauses mining and enforces thermal/resource/time limits. Keep that bounded mode separate from normal mining telemetry.

A SAT solver is not expected to compete with the ASIC for the full 32-bit nonce search over full-round SHA-256d. The useful research questions are narrower and scientifically testable:

1. Can real mining job/header metadata produce a realistic stream of known-answer and target-check fixtures?
2. Can candidate nonce/digest pairs be independently replayed and verified on HSCL1?
3. Can reduced-round SHA bit-vector encodings be improved using observed structure and known traces?
4. Can learned branching heuristics improve existing SAT solvers on held-out cryptographic instances?
5. Can Cube-and-Conquer or XOR-aware solving exploit the specific bit-vector model structure?
6. Which model/solver portfolio is best for each formula class under a fixed budget?
7. Can the operational telemetry help HSCL1 recommend safer mining reliability/efficiency profiles separately from cryptanalysis?

## 7.2 Neural SAT guidance — primary research direction

The model should initially guide existing correct solvers rather than classify SAT/UNSAT as an authority.

Candidate outputs:

- variable ranking scores;
- polarity preferences;
- initial branching order;
- cube split-variable suggestions;
- solver/heuristic portfolio ranking;
- restart/phase heuristics where the solver API safely supports them.

Every suggestion is optional. Existing solver logic can ignore the suggestion. SAT model validation and UNSAT certificate checking remain independent.

### Research anchor A: RLAF / one-shot GNN guidance

Tönshoff & Grohe, ICLR 2026, “Learning from Algorithm Feedback: One-Shot SAT Solver Guidance with GNNs” describes assigning variable weights/polarities in one forward pass and training from solver computational cost using policy-gradient methods such as GRPO. This is a strong candidate for a controlled CQ-HECS experiment.

Implementation idea:

1. export CNF graph features from the existing CQ-HECS SAT pipeline;
2. run baseline solver without learned guidance;
3. run one-shot GNN-initialized scores with identical solver limits;
4. train on a train split using solver cost as reward;
5. validate on unseen families and larger instances;
6. compare mean runtime, PAR-2, solved count, nodes/conflicts, memory and timeouts;
7. reject a model that only improves one training distribution.

The published >2× results are not a promise for CQ-HECS or the Bitaxe-derived instances. Measure on the actual dataset families.

### Research anchor B: AutoModSAT / agentic heuristic discovery

Sun et al., Nature Communications 2026, “Discovering heuristics in a complex SAT solver with large language models” describes a modular CDCL solver with selected heuristic functions, presearch, prompt optimization and coder/evaluator/repairer agents. The useful design lesson is to search a constrained set of named heuristic seams, not ask an LLM to rewrite the entire solver.

Apply this only to modular, testable CQ-HECS heuristic hooks. Each candidate must:

- compile and pass unit tests;
- be semantically compared with existing candidates to avoid duplicate search;
- pass model/proof validation;
- be benchmarked on fixed, stratified datasets;
- run in a sandbox with a bounded iteration budget;
- remain experimental until generalization and resource cost are demonstrated.

### Research anchor C: initial branching-order learning

“Learning to Rank the Initial Branching Order of SAT Solvers” (2026, arXiv:2603.07176) reports gains on some random and pseudo-industrial sets but failure to speed up harder/industrial cases where dynamic CDCL heuristics quickly override the initial order. Therefore initial ordering is a cheap experiment, not a universal improvement. Record when the solver overwrites model suggestions and whether later decisions change.

### Research anchor D: explainability and concept learning

“Concept learning for algorithmic reasoning: Insights from SAT-solving GNNs” (Information Sciences, 2026) studies interpretable internal concepts from SAT GNNs. Use interpretability to debug whether the model is learning graph/constraint structure or accidental family/device identifiers. Compare a full model with a smaller teacher-student model only after it performs credibly on held-out families.

### Research anchor E: active-learning benchmark selection

Fuchs et al., “Active Learning for SAT Solver Benchmarking” (2025) proposes selecting benchmark instances that discriminate solver ranking while reducing benchmark effort. Use this to prioritize a representative mini-suite between full benchmark rounds. Never replace the fixed release benchmark suite with active selection alone; keep both a fixed gate corpus and an active exploratory corpus.

## 7.3 Cryptographic research and guardrails

Relevant research directions include:

- bit-vector/SAT encodings of reduced-round SHA-256 compression;
- differential path and message-modification constraints;
- XOR-aware propagation and cryptominisat-style Gaussian reasoning where appropriate;
- SAT/SMT/MILP/CP cross-formalism comparisons;
- neural differential distinguishers on round-reduced hash/permutation constructions;
- reduced-round cryptanalysis only, with explicit round counts and claims.

The current literature on SAT-based SHA-256 analysis reports attacks/preimages on reduced-round variants (for example, 17/18-round compression and weakened 19-round constructions in the cited work), while explicitly not demonstrating a full-round SHA-256 preimage or collision break. Neural differential distinguisher research on SHA-3-256/Ascon-Hash is relevant methodologically but is not a direct result against SHA-256.

For every claim, state:

- algorithm variant;
- number of rounds;
- compression vs complete hash;
- collision vs preimage vs differential trail vs distinguisher;
- chosen/fixed/free input conditions;
- time/data/memory complexity;
- success probability;
- independently verified result;
- whether the result generalizes to the deployed algorithm (usually it does not).

Never say “SHA-256 cracked”, “Bitcoin mining solved by AI” or “the ASIC exposes internal SHA rounds” unless there is direct, independently reviewed evidence meeting that exact claim.

## 7.4 Convert miner context into solver instances

Host pipeline example:

```text
permitted mining-job context / sanitized 80-byte header
        │
        ▼
exact Bitcoin header parser (endianness/field layout tests)
        │
        ▼
reference SHA256d implementation
        │
        ├── check known candidate nonce/digest/target
        ├── create known-answer fixtures
        └── create reduced-round compression instances
                 │
                 ▼
       bit-vector model + CNF encoder
                 │
                 ▼
       independent model checker / DRAT/LRAT checker
                 │
                 ▼
       CQ-HECS solver portfolio + learned guidance
                 │
                 ▼
       evidence package + benchmark report + dataset lineage
```

Do not generate CNF in the firmware. Firmware telemetry is the source of measurements and bounded vectors; HSCL1 owns expensive data processing and instance generation.

## 7.5 SAT instance portfolio and labels

Every generated problem is tagged with a family, source, generator SHA, seed, round count, model version, formula size, XOR/parity metrics and expected result class if known.

SAT result labels:

- `SAT_WITNESS_VERIFIED` — model checked independently;
- `UNSAT_PROOF_VERIFIED` — proof checked independently by an approved checker;
- `SAT_UNVERIFIED`;
- `UNSAT_UNVERIFIED`;
- `TIMEOUT`;
- `OOM`;
- `UNKNOWN`;
- `ENCODING_ERROR`.

Only the first two are valid final correctness labels. A model cannot use unverified solver output as a training target for “truth”. It may be used as a noisy heuristic target only if explicitly described and kept out of final correctness evaluation.

## 7.6 Cube-and-Conquer and XOR-aware experiments

Use a measurable progression:

1. run the existing solver portfolio baseline;
2. compute cheap instance features;
3. measure formula balance, graph structure, variable degrees and XOR density;
4. choose a bounded split strategy;
5. run cube workers in parallel with per-cube resource/time caps;
6. verify SAT models independently and aggregate UNSAT proofs where the checker/format supports it;
7. compare to no-cubing baseline and random split baseline;
8. evaluate learned split-variable ranking only after the deterministic split path is stable.

For SHA arithmetic, bit-vector addition introduces carry structure and XOR constraints. Test explicit XOR/CNF encodings against the baseline CNF encoding. Do not assume Gaussian elimination is always a win; measure cost, propagation, proof size and memory.

## 7.7 Mining feedback as model feedback — not false cryptanalysis

The mining telemetry can train models to predict operational outcomes and identify mining performance regressions. It is not automatically a labelled dataset for Boolean variable choices. SAT training labels must come from actual SAT solver traces and independently checked outcomes. Connect the domains via explicit experiment IDs and source manifests, not by conflating unrelated measurements.

---

# PART VIII — OPTIONAL RESEARCH MODE AND SAFE FEEDBACK TO THE MINER

# 8. The miner receives recommendations; HSCL1 owns learning

## 8.1 Separate normal mining from optional SHA research

Default state:

- miner hashes normally;
- collector samples and buffers telemetry;
- receiver upload runs at low priority;
- no research SHA computation competes with ASIC/mining tasks;
- no new solver or model runs on the ESP32-S3.

Optional research mode:

- operator explicitly pauses mining through existing safe pause API/USB console;
- no shares are in flight;
- device identity, thermal freshness and resource budgets pass;
- one short-lived token is required;
- job count and active time are bounded;
- research run produces a typed trace or digest;
- the trace is uploaded to HSCL1 and replayed independently;
- the research session disarms on unsafe state or budget expiry;
- mining resumes only through an explicit operator action, never automatically from a research handler.

The existing research guard and USB console are the baseline. Do not weaken their gates to make telemetry continuous. Telemetry must continue while normal mining is active; the SHA software oracle remains a separate controlled task.

## 8.2 Signed advisory profiles

HSCL1 may eventually publish a recommendation profile containing:

- model ID and model SHA-256;
- training dataset IDs and split hashes;
- input feature schema/version;
- target board/ASIC and firmware compatibility;
- prediction and confidence/uncertainty;
- allowed recommendation dimensions;
- prohibited parameter changes;
- valid-from/expiry and sequence number;
- recommendation provenance and evaluation metrics;
- explicit operator approval state.

The miner can:

- store a recommendation as read-only metadata;
- expose it in AxeOS/telemetry;
- return measured outcome data for a separately approved A/B test.

The miner cannot accept arbitrary shell code, raw model weights or untyped config patches from HSCL1. Model execution and training happen on HSCL1. A model profile never bypasses the thermal manager, power policy, OTA lock or human approval.

## 8.3 Safe future operational optimisation

If an operator explicitly chooses a tuning experiment, use this order:

1. select a known firmware and board profile;
2. capture a stable baseline (minimum 30–60 min, ideally repeated runs);
3. predeclare target metrics and safety limits;
4. change exactly one parameter family per experiment;
5. preserve the previous configuration as an encrypted restore point;
6. stop if thermal/power/sensor/network thresholds are violated;
7. measure hashrate, accepted/rejected shares, power, temperature, J/TH and uptime;
8. compare to baseline with confidence intervals and report environmental confounders;
9. require owner approval before making the profile persistent.

Never optimize hashrate alone. The objective should consider safe efficiency, share quality, reliability, temperature and operational availability.

---

# PART IX — MCP, CLI, AGENT TOOLS AND USER EXPERIENCE

# 9. One HSCL1 interface for the whole workflow

## 9.1 CLI commands

Extend the existing `hscl` CLI; do not create a second unrelated executable unless the current CLI architecture requires a separately packaged daemon.

Proposed commands:

```bash
hscl miner status
hscl miner discover --targets 192.168.178.61,192.168.178.66 --readonly
hscl miner probe <candidate>
hscl miner pair <candidate>
hscl miner devices
hscl miner health <device-id>
hscl miner telemetry <device-id> --since 1h
hscl miner logs <device-id> --redacted
hscl miner backup plan <device-id>
hscl miner backup capture <device-id> --dry-run
hscl miner backup verify <backup-id>
hscl miner receiver status
hscl miner receiver doctor
hscl miner dataset list
hscl miner dataset build <family> --dry-run
hscl miner dataset validate <dataset-id>
hscl miner sat generate <dataset-id> --rounds <N> --dry-run
hscl miner sat benchmark <campaign-id> --dry-run
hscl miner model list
hscl miner model evaluate <model-id>
hscl miner research report <device-id>
```

Any command that touches device configuration, exports secrets, pauses mining, reboots, changes partitions or flashes firmware must have a clearly named `--confirm`/interactive approval gate and a device identity re-check. Dry-run is the default for destructive or state-changing actions.

## 9.2 MCP integration

Register tools through HSCL1's existing agent/MCP architecture. Do not launch a second MCP service solely for mining unless a real isolation need is recorded.

Read-only tools:

- `miner.list_devices`
- `miner.discover_known_targets`
- `miner.probe_identity`
- `miner.get_status`
- `miner.get_telemetry`
- `miner.get_event_summary`
- `miner.get_receiver_status`
- `miner.list_backups`
- `miner.verify_backup_manifest`
- `miner.list_datasets`
- `miner.validate_dataset`
- `miner.run_sat_benchmark_dry_run`

Sensitive/approval-gated tools:

- `miner.begin_pairing`
- `miner.export_private_config`
- `miner.pause_mining`
- `miner.resume_mining`
- `miner.request_research_session`
- `miner.apply_recommendation`
- `miner.flash_firmware`
- `miner.change_pool_or_wallet`
- `miner.modify_voltage_frequency`

Do not expose these gated actions to unattended agent loops by default. Require a policy decision and a human confirmation.

## 9.3 Miner Lab UI in HSCL1

Add the feature to the existing HSCL1 design system and eventually Control Center. Use current tokens, typography, navigation, localization (EN/DE/FR), accessibility and window conventions.

### Overview page

- two known candidate cards, but only display a confirmed friendly name after identity verification;
- current device identity and firmware;
- receiver link state and last heartbeat;
- hashrate and rolling averages;
- power and J/TH;
- temperature/VR/fan state;
- accepted/rejected share trend;
- Wi-Fi RSSI and pool latency;
- queue depth and data-upload lag;
- last backup status.

### Telemetry page

- synchronized time-series charts;
- selectable 1m/10m/1h/day ranges;
- per-domain hashrate and error charts;
- power/voltage/frequency/temperature/fan correlations;
- share accepted/rejected and response-latency distribution;
- network recovery timeline;
- raw vs normalized distinction.

### Events / Logs page

- filter by category, severity, boot ID, job/session and firmware version;
- log redaction indicator and raw-private access control;
- event timeline with correlation IDs;
- sequence gaps and queue overflow as visible warnings;
- download sanitized evidence package.

### Backup page

- inventory of running app image, private config, snapshots, logs and full-flash backup;
- exact scope of each artifact;
- SHA-256 verification state;
- restore instructions and restore-tested status;
- backup encryption/secrets inclusion warning;
- no “complete” badge unless all required components have been captured and restore-tested.

### Research page

- dataset catalogue and source lineage;
- SHA fixture and trace viewer;
- reduced-round SHA instance generation settings;
- SAT/SMT solver comparisons;
- learned heuristic model version and evaluation;
- benchmark charts, timeouts and proof status;
- hypothesis and research ledger links.

### UX requirements

- never show a green “connected” state based solely on ping; require authenticated heartbeat;
- separate “device reachable” from “paired and trusted”;
- separate “backup captured” from “backup restore verified”;
- separate “solver returned UNSAT” from “UNSAT proof verified”;
- separate “AI recommendation” from “applied firmware config”;
- every destructive action shows target hostname, MAC suffix, IP, firmware and intended change;
- confirmation dialog explains rollback and recovery requirements;
- show unknown sensor values as unavailable, not zero;
- provide accessible labels, keyboard navigation, screen-reader semantics and contrast checks;
- capture screenshots in UI tests at desktop and constrained window sizes.

---

# PART X — TESTING, VERIFICATION AND BENCHMARKS

# 10. Test architecture — no physical flashing during ordinary CI

The receiver and firmware should be testable without a real miner. Real devices are a final acceptance layer, not a replacement for automated tests.

## 10.1 Firmware unit and host tests

Add tests for:

- event serialization and schema version;
- fixed-size event queue wraparound;
- priority preservation for safety events;
- low-priority gauge coalescing;
- sequence increments and boot-ID change;
- duplicate ACK handling;
- out-of-order upload response;
- reconnect/backoff and heartbeat state transitions;
- missing receiver does not pause mining or alter pools;
- buffer full and overflow counters;
- invalid signature/replay/wrong device identity;
- invalid/oversized body and malformed schema;
- no sensitive fields in standard telemetry;
- redaction behavior for log lines and authorization messages;
- low heap/PSRAM and allocation-failure path;
- telemetry task starvation/deadline handling;
- no telemetry event from interrupt context performs heap/network/disk work;
- research guard remains separate and unchanged for normal-mining path.

Run the existing simulation tests, QEMU/Unity tests, frontend tests, sanitizers and firmware builds on the actual supported ESP-IDF version. Keep upstream test behavior. Add regression fixtures before changing a discovered bug.

## 10.2 HSCL1 receiver contract tests

Test with a simulator and recorded fixtures:

- valid paired device;
- unknown device rejected;
- `.61`/`.66` identity swap/mismatch;
- duplicate sequence event;
- replayed heartbeat nonce/timestamp;
- missing sequence gap;
- duplicate batch with matching hash;
- same sequence but altered payload (integrity error);
- expired pairing token;
- revoked key;
- TLS pin mismatch;
- HMAC invalid;
- unsupported schema version;
- payload too large;
- slow upload and client disconnect;
- out-of-order chunks;
- host restart during upload;
- crash after raw write but before ACK;
- crash after ACK request but before fsync;
- full disk and quota exceeded;
- corrupted segment and recovery;
- mDNS unavailable and static endpoint fallback;
- firewall blocks incoming connection;
- receiver port already in use;
- host network moves between Wi-Fi interfaces;
- system sleep/resume and miner reconnection.

## 10.3 Backup and restore tests

For every device and firmware version:

- backup identity is correct;
- image size matches partition metadata;
- header and SHA-256 digest match;
- file can be read and its provenance is saved;
- secrets are encrypted at rest;
- no private field leaks into logs/datasets;
- configuration export completeness is explicit;
- full-chip backup scope is correct;
- restore instructions match exact board/flash/partition type;
- restore is tested on a lab unit or virtual/simulated image before claiming `RESTORE_VERIFIED`.

The WLAN running-app partition route alone cannot pass a “full backup” acceptance gate.

## 10.4 SAT and SHA verification

- FIPS/NIST known-answer SHA-256 vectors;
- SHA-256d genesis/block-header fixtures where licensed/source provenance is documented;
- padding boundary tests (0, 1, 55, 56, 63, 64, 65 bytes, multi-block);
- independent C/Python/reference implementation agreement;
- bit-exact reduced-round state comparisons;
- trace replay accepted unchanged by CQ-HECS;
- single-bit mutation causes verification failure;
- block header parser endian/serialization golden vectors;
- candidate nonce hash/target check against independent reference;
- CNF/bit-vector model SAT witness verification;
- UNSAT proof checker acceptance and mutation rejection;
- equivalence checks between alternative CNF/XOR encodings on small exhaustive instances.

A matching digest is useful evidence of byte-level agreement, not a proof that a physical ASIC exposed the same internal state.

## 10.5 Benchmark plan

### Firmware overhead baseline

Before and after each firmware change, measure on the same device and profile:

- hashrate 1m/10m/1h;
- accepted/rejected shares;
- power, current, voltage and J/TH;
- ASIC and VR temperatures;
- fan PWM/RPM;
- internal heap min/largest block;
- PSRAM free/minimum;
- Wi-Fi RSSI and pool response;
- boot-to-mining time;
- event queue high-water mark;
- telemetry CPU/task runtime;
- network bytes per minute;
- number of telemetry drops.

Declare the acceptance threshold before observing the result. A target of less than 1% mining performance perturbation from telemetry is a candidate gate, not an assumed fact; first measure the current baseline and choose a threshold based on repeatability.

### Receiver benchmarks

Measure:

- events/second accepted;
- bytes/event and bytes/batch;
- end-to-end latency;
- CPU/RAM per device;
- durable-write latency;
- compression ratio and CPU time;
- recovery after process restart;
- replay/duplicate throughput;
- disk use per device-hour/day.

### SAT benchmarks

Use fixed benchmark suites and the 2026 SAT Competition methodology where appropriate:

- solved-instance count;
- PAR-2 score;
- median and geometric mean runtime where meaningful;
- timeout/unknown/OOM rates;
- memory peak;
- proof size and proof-check time;
- split count and cube balance;
- propagation/conflict/decision counts;
- model inference overhead;
- hardware backend and software versions.

PAR-2 must be defined consistently: each unsolved instance contributes twice the time limit. Do not compare only mean solved-instance time because that hides timeouts.

### Long-duration stability

- 1-hour smoke test for every firmware build on physical hardware;
- 24-hour soak before calling the collector stable;
- 72-hour soak before a release-level reliability claim;
- forced AP/receiver unavailable windows;
- host reboot while device continues mining;
- Wi-Fi roaming/reconnect;
- queue pressure and offline backlog recovery;
- verify no reboot loop, no counter corruption and no secret leakage.

These are target test durations, not claims that they have already run.

## 10.6 Visual testing

- Playwright/UI automation for receiver dashboard and Miner Lab once UI exists;
- screenshot at 1280×720, 1920×1080 and compact 900×600 window;
- verify overflow, chart labels, empty/error/loading/offline states and accessibility;
- use deterministic synthetic data fixtures;
- no real IP, MAC, wallet or worker in golden screenshots;
- compare screenshot diffs and maintain an approved baseline;
- verify keyboard focus and screen-reader labels.

---

# PART XI — DEVELOPMENT, SELF-HEALING AND LONG-HORIZON AGENT LOOPS

# 11. One coordinated engineering loop

The agent must work in small, measurable iterations. Each tick has a single next action from the canonical priority ledger and records evidence.

```text
OBSERVE → RECONCILE → SELECT → PLAN → IMPLEMENT → TEST → MEASURE
        → VERIFY → DOCUMENT → UPDATE PLANS → CHECKPOINT → SELECT NEXT
```

## 11.1 Every tick begins with current reality

1. Check working tree status, branch, current HEAD and upstream tracking.
2. Fetch latest GitHub metadata for HSCL1 and ESP-Miner; read new commits, pushes, branches, PRs and CI results.
3. Check whether the research branch is still 8 commits ahead/0 behind; do not assume.
4. Refresh the official upstream ESP-Miner PRs relevant to Stratum, safety, OTA and hardware.
5. Read the current HSCL1 root `AGENTS.md`, current `docs/DEV_LOOP.md`, current PR/plan ledger and relevant source.
6. Verify whether a previous task changed the file layout or schema.
7. Compare every planned interface against current code before writing new code.
8. Reconcile the device identity registry and receiver status; never run destructive action.
9. Select exactly one bounded task.

## 11.2 Priority ledger

P0 — protect user/device data and freeze an accurate baseline.

P1 — build the HSCL1 local receiver and health endpoint with simulated devices; no firmware flash.

P2 — implement device registry, identity verification for only `.61` and `.66`, pairing protocol and revocation.

P3 — add 30-second heartbeat and authenticated batch upload on a firmware feature branch; existing mining continues when host is unavailable.

P4 — add bounded event schema and hot-path-safe firmware telemetry instrumentation.

P5 — implement immutable raw storage, sequence/idempotency, catalog and data-quality tooling.

P6 — implement read-only backup capture and verification; design private configuration export separately.

P7 — build sanitized mining/Stratum/ASIC/thermal/power/network datasets.

P8 — extend SHA fixtures and replay with mining-related known-answer data; separate software traces from ASIC observations.

P9 — build reduced-round SHA bit-vector/CNF dataset generation on HSCL1 host.

P10 — connect datasets to existing CQ-HECS SAT/solver APIs and provenance.

P11 — implement solver-trace collection and benchmark harness; validate learned guidance offline.

P12 — train/evaluate GNN/GRPO and algorithm-portfolio models on grouped splits; publish model cards.

P13 — add Miner Lab UI, charts, backups and research visualization to HSCL1.

P14 — develop signed advisory profiles and human-approved operational tuning; no autonomous voltage/frequency changes.

P15 — optional persistent miner flash spool only after partition-table, flash-capacity, wear-leveling and recovery approval.

P16 — production release, install packaging, device acceptance and 24/72-hour soak evidence.

Priority can be changed only after a new finding is written to the decision ledger with impact, risk, dependency and evidence.

## 11.3 Work division for parallel agents

Parallelize only where the interfaces are frozen and file ownership is non-overlapping.

| Agent | Scope | Owns | Must not edit concurrently |
|---|---|---|---|
| Principal/Coordinator | architecture, ledger, reviews, risk decisions | ADRs, master plan, task queue | firmware hot-path internals unless assigned |
| HSCL1 Receiver Engineer | service, API, storage | receiver service and its tests | ESP firmware |
| Firmware Engineer | queue, heartbeat, event taps | ESP-Miner feature branch files | receiver schema without coordination |
| Data Engineer | normalization, catalog, datasets | dataset pipeline and data contracts | device auth logic |
| Crypto/SAT Researcher | SHA instances, SAT encodings, proof checks | CQ-HECS integration branch | firmware hot-path files |
| ML Researcher | GNN/GRPO, portfolio, evaluation | model training/evaluation modules | baseline solver authority |
| UI/UX Engineer | Miner Lab and visual tests | UI module/design tests | receiver security and backup internals |
| QA/Security Engineer | threat model, fuzz, audit, test gates | test suites, security reports | unreviewed production behavior changes |

Every agent must report exact file ownership and current commit. Use file locks or a task ownership ledger. Do not have two agents rebase/modify the same source file concurrently.

## 11.4 Self-healing rules

When a test/build/benchmark fails:

1. capture exact command, exit code, environment and log;
2. classify it as source defect, test defect, infrastructure defect, environment drift, device/hardware defect or unknown;
3. reproduce in the smallest isolated target;
4. identify the owning module and probable cause;
5. create a regression test before or alongside the fix;
6. implement the smallest correction;
7. rerun local target tests;
8. rerun affected integration tests;
9. rerun full pre-merge suite;
10. update evidence, docs, relevant plans and decision record.

Limit a single root-cause repair to three materially different attempts. If no measurable improvement or a new understanding results after three attempts, set `BLOCKED`, preserve the artifacts and ask for human direction. Do not retry a failed command in a tight loop or simply increase timeouts until it passes.

No “self-healing” action may erase logs, reset NVS, flash a new image, change wallet/pool settings or disable thermal protection.

## 11.5 Two-minute development cron (optional, not a busy loop)

If the owner explicitly enables a local scheduler, use a systemd timer or cron firing every two minutes to start one **bounded development tick**. It is not the 30-second miner heartbeat and it is not a forever-running CPU loop.

Each tick:

- acquire one global lock;
- verify no other heavy build/VM/test process holds the same resource lock;
- refresh status/ledger and check incoming data;
- choose one next allowed task;
- execute only a short task within a per-tick time/resource budget;
- run focused tests;
- write a checkpoint/round log;
- update plans and next-action pointer;
- release lock.

Do not perform a full firmware build, ISO build, VM boot, model training, dataset regeneration or flash action every two minutes. Heavy operations enter their own bounded queue and run only when resources and policy permit. No firmware flashing, pool/wallet change, secret export, voltage/frequency tuning, merge or release from unattended cron.

Scheduler requirements:

- lock file with PID/start time and stale-lock recovery;
- maximum runtime and cancellation token;
- CPU/RAM/GPU/storage limits;
- no overlapping heavy tasks;
- stdout/stderr captured to private rotating logs;
- unique tick ID and result JSON;
- crash detection and checkpoint resume;
- max consecutive failure count;
- stop after repeated failure or a security alert;
- visible status and human stop command;
- all tools invoked through allow-listed typed commands, not arbitrary shell prompts.

Suggested tick result schema:

```json
{
  "schema": "hcs.selfheal.tick.v1",
  "tick_id": "generated-at-runtime",
  "main_sha": "actual-observed-sha",
  "selected_task": "one-ledger-task-id",
  "status": "checkpointed",
  "commands": [],
  "tests": [],
  "benchmarks": [],
  "plans_updated": [],
  "device_operations": [],
  "approval_required": false,
  "next_action": "actual-next-ledger-task",
  "resource_summary": {
    "wall_seconds": 0,
    "peak_rss_bytes": 0,
    "gpu_used": false,
    "heavy_lock": false
  }
}
```

The values must be real runtime values, not the example placeholders.

---

# PART XII — BUILD, RELEASE AND PHYSICAL DEVICE GATES

# 12. Build strategy

## 12.1 Firmware variant strategy

Start from the user's existing `feat/timsminer-sha-research-mode` branch after refreshing it against master and checking for new changes. Use a new integration branch for telemetry/receiver support; do not overwrite `master` or the research branch.

Proposed branch name:

`feat/hscl1-miner-telemetry-bridge`

The branch may be renamed to match the user's naming policy.

Keep separate build configurations:

- normal production firmware with low-overhead telemetry capability disabled or configured only after pairing;
- research firmware variant with existing SHA research guard and USB console;
- CI/simulator variant with mocks and no real credentials;
- device-specific release variants only when actual identity/MAC/BSSID/IP reservations are confirmed.

Do not bake a wallet, worker, pool password, Wi-Fi secret, personal IP or unique station MAC into a public binary artifact.

## 12.2 IDF/toolchain compatibility

The feature branch used ESP-IDF 6.0.2. Official upstream has merged a 6.0.3 bump after this branch. First establish the actual current build environment, lock file/components, build scripts and CI containers. Run a clean build under the exact baseline. If moving to 6.0.3 is desirable, make that a separate toolchain change with full before/after tests and release note.

## 12.3 CI gates

Firmware PR gates:

- format/lint;
- host C tests;
- ASan/UBSan host tests;
- QEMU/Unity tests;
- frontend tests;
- normal production firmware build;
- research variant firmware build;
- binary size and memory report;
- secret scan and forbidden configuration scan;
- license/dependency audit;
- schema compatibility tests;
- fuzz parser/event endpoint;
- simulator reconnect/offline/queue tests.

HSCL1 PR gates:

- Rust fmt/clippy/test;
- Python type/lint/unit tests where used;
- receiver contract and integration tests;
- database migration tests;
- schema validation;
- secret redaction and privacy tests;
- crash recovery/durable write tests;
- WSL/Linux parity as current `docs/DEV_LOOP.md` prescribes;
- CLI end-to-end tests;
- UI visual tests when present;
- package/systemd service smoke test;
- `hscl doctor` checks service and firewall state without requiring root.

CQ-HECS integration gates:

- existing solver test suite;
- model/witness checker;
- proof checker;
- dataset ingestion fixture;
- trace replay;
- solver portfolio baseline comparison;
- no regression in existing SAT/UNSAT verification semantics.

## 12.4 Physical deployment order

Physical flashing is a separate owner-approved release task. Before any flash:

1. refresh target identity via read-only API;
2. compare MAC/hostname/board/ASIC and explicit target name;
3. verify running firmware and partition metadata;
4. verify encrypted private config backup;
5. verify current app image backup digest;
6. verify previous OTA slot/recovery path;
7. validate build chip ID, project identity, board config, BSSID, IP and version;
8. inspect binary SHA-256 and build manifest;
9. verify OTA lock/button policy or explicit physical authorization;
10. request final owner confirmation naming the exact device and firmware hash;
11. upload once;
12. wait/poll boundedly and never resend on a dropped connection until state is known;
13. verify identity, firmware, partition, Wi-Fi, pool connection, accepted shares, safety sensors and logs;
14. monitor a declared smoke and sustained window;
15. restore original settings if the experiment requires it;
16. preserve all evidence and report actual result.

Do not flash both units at once. Start with the one whose identity and backup are fully verified. Do not switch target if the chosen address becomes unreachable; mark `TARGET_UNREACHABLE` and stop.

---

# PART XIII — RESEARCH QUESTIONS AND EXPERIMENT ROADMAP

# 13. Prioritized research questions

Each question becomes a ledger item with hypothesis, independent variable, dependent metrics, data, baseline, time/resource budget, expected result class and stop condition.

## 13.1 Telemetry and data quality

- Which firmware counters best predict a stale/rejected share before the pool rejects it?
- How much can queue depth/job age explain invalid job IDs and dropped notifications?
- Can a compact event timeline distinguish Wi-Fi association from actual usable gateway/DNS/Stratum readiness?
- Does per-domain hashrate imbalance correlate with temperature, voltage, UART errors or hardware faults?
- Can telemetry sampling remain statistically useful while staying under a measured CPU/RAM/network budget?
- What is the optimal batch size and compression setting on ESP32-S3 under a weak mesh link?
- Does sequence-based ACK recover all events after HSCL1 restarts, device reboots and partial transfer?

## 13.2 Miner operational ML

- Can a time-series model predict hashrate or thermal instability 1–5 minutes before a fault?
- Can anomaly detection identify a failing fan/sensor, unstable voltage, memory leak or pool reconnect cycle with few false alarms?
- Can a contextual model recommend stable frequency/voltage profiles using only measured board/ASIC conditions and verified settings?
- Does a model trained on `.61` generalize to `.66` (leave-one-device-out), or is it learning device identity?
- How robust is it across firmware versions, room temperature, Wi-Fi node and pool difficulty changes?

No model can be considered successful based only on one device and one mining session.

## 13.3 SHA and cryptographic modelling

- Do actual candidate nonce/share headers agree byte-for-byte with an independent SHA-256d host implementation?
- Can the optional firmware software oracle and host reference agree on all round trace fields?
- Which encoding of SHA message schedule/addition/XOR constraints gives the best solver performance at low round counts?
- Does XOR-aware propagation improve selected SHA reduced-round SAT instances?
- Can differential trail constraints prune the search space when validated against exact bit-vector semantics?
- Can GNN guidance improve initial branching, polarity or cube splitting on held-out hash families?
- Which instance families remain hard after model-guided search, and does the model generalize or merely memorize instance shapes?

## 13.4 Agentic solver improvement

- Can an LLM agent safely propose a local heuristic change inside one CQ-HECS extension seam?
- Can an evaluator detect semantic duplicates and redundant experiments?
- Can an independent proof/model checker reject false or incomplete solver results?
- Can active benchmark selection reduce the cost of exploratory search without hiding regressions on the fixed suite?
- Can automated repair loops improve code without accumulating complexity or harming unrelated formula families?

---

# PART XIV — RESEARCH REFERENCES AND ENGINEERING SOURCES

# 14. Source ledger to refresh before implementation

The following were located during the 8 November 2026 research pass. The agent must open the paper/specification and verify version/date before relying on it. This list is a starting bibliography, not a claim that every approach is SOTA for our exact workload.

## 14.1 SAT and learned solver guidance

1. **Tönshoff & Grohe, “Learning from Algorithm Feedback: One-Shot SAT Solver Guidance with GNNs,” ICLR 2026.** GNN variable weights/polarity, single-pass guidance, solver-cost reward and policy-gradient training.  
   <https://proceedings.iclr.cc/paper_files/paper/2026/hash/a04c50c0bd6937760a3b89ee10010c96-Abstract-Conference.html>  
   <https://arxiv.org/abs/2505.16053>
2. **Sun et al., “Discovering heuristics in a complex SAT solver with large language models,” Nature Communications 17, 9008 (17 July 2026).** Modular heuristic seams, presearch, coder/evaluator/repairer agents and evolutionary search.  
   <https://www.nature.com/articles/s41467-026-74949-2>
3. **“Learning to Rank the Initial Branching Order of SAT Solvers” (arXiv:2603.07176, March 2026).** Useful warning: gains vary by benchmark; dynamic CDCL may overwrite initial predictions, and difficult industrial instances may not speed up.  
   <https://arxiv.org/abs/2603.07176>
4. **“Neural approaches to SAT solving: Design choices and interpretability,” International Journal of Approximate Reasoning, March 2026.** Evaluation/design/interpretability of SAT GNN approaches.  
   <https://doi.org/10.1016/j.ijar.2025.109609>
5. **“Concept learning for algorithmic reasoning: Insights from SAT-solving GNNs,” Information Sciences, February 2026.** Interpretability and compact student network research.  
   <https://doi.org/10.1016/j.ins.2025.122754>
6. **Fuchs, Bach & Iser, “Active Learning for SAT Solver Benchmarking,” Journal of Automated Reasoning 69, 16 (23 June 2025).** Selective benchmark evaluation while retaining a fixed release suite.  
   <https://doi.org/10.1007/s10817-025-09729-6>
7. **SATzilla: Portfolio-based Algorithm Selection for SAT.** Foundational per-instance solver selection and empirical hardness modelling.  
   <https://new.aaai.org/Library/JAIR/Vol32/jair32-014.php>
8. **SAT Competition 2026 rules and benchmarks.** Uses PAR-2 and requires benchmark provenance; main-track submissions include new independently described instances.  
   <https://github.com/satcompetition/2026>  
   <https://satcompetition.github.io/2026/benchmarks.html>

## 14.2 SHA/cryptanalysis

9. **“Analysis of the cryptographic strength of the SHA-256 hash function using the SAT approach.”** Reports reduced-round logical cryptanalysis results and explicitly does not demonstrate a full-round SHA-256 break.  
   <https://ntv.ifmo.ru/en/article/23590/analiz_kriptograficheskoy_stoykosti_hesh-funkcii_SHA-256_pri_pomoschi_SAT-podhoda.htm>
10. **“Differential Cryptanalysis with SAT, SMT, MILP and CP: A Detailed Comparison for Bit-Oriented Primitives.”** Useful cross-formalism modelling/solver comparison.  
    <https://air.unimi.it/handle/2434/1019981>
11. **“Improved Differential Neural Distinguishers for SHA-3-256 and Ascon-Hash256,” Electronics 2026.** Relevant for neural distinguishers on sponge-based hash permutations; not a SHA-256 result.  
    <https://www.mdpi.com/2079-9292/15/18/4142>
12. **“Machine learning-aided differential-linear attacks with applications to DES and SPECK32/64,” 2025.** Shows the ML-cryptanalysis methodology on reduced-round ciphers; not a direct attack on Bitcoin SHA-256.  
    <https://doi.org/10.1007/s44443-025-00241-w>
13. **“Differential cryptanalysis with SAT, SMT” (IACR ePrint 2024/105).** Compare SAT/SMT/MILP/CP in differential probability/trail modelling.  
    <https://eprint.iacr.org/2024/105>

## 14.3 Protocol and firmware engineering

14. **Stratum V2 Mining Protocol specification.** Jobs, channels, search-space assignments and work protocol.  
    <https://stratumprotocol.org/specification/05-mining-protocol/>
15. **Stratum V2 protocol overview.** Mining, Job Declaration and Template Distribution separation.  
    <https://stratumprotocol.org/specification/03-protocol-overview/>
16. **Stratum V2 Job Declaration Protocol.** Custom work selection and miner/pool responsibilities.  
    <https://stratumprotocol.org/specification/06-job-declaration-protocol/>
17. **ESP-IDF NVS Encryption.** XTS-AES storage and key-partition/flash-encryption requirements.  
    <https://docs.espressif.com/projects/esp-idf/en/latest/esp32/api-reference/storage/nvs_encryption.html>
18. **ESP-IDF Wear Levelling API.** Sector-based flash erase limits and safety/performance modes.  
    <https://docs.espressif.com/projects/esp-idf/en/latest/esp32/api-reference/storage/wear-levelling.html>
19. **OpenTelemetry Logs Data Model.** Stable common semantic model for event records and machine-generated logs.  
    <https://opentelemetry.io/docs/specs/otel/logs/data-model/>
20. **ESP-Miner user fork.** Source of truth for current firmware, docs, evidence and feature branch.  
    <https://github.com/timfromhcs/ESP-Miner>
21. **ESP-Miner current research branch.** SHA oracle/research guard/backup/USB console foundation; refresh before use.  
    <https://github.com/timfromhcs/ESP-Miner/tree/feat/timsminer-sha-research-mode>
22. **HSCL1.** Existing OS, root AGENTS, CLI, HCSUDA, agent tools and integration surfaces.  
    <https://github.com/timfromhcs/HSCL1>
23. **CQ-HECS.** Existing SAT/quantum/solver/replay/provenance code.  
    <https://github.com/timfromhcs/CQ-HECS>

---

# PART XV — ACCEPTANCE CRITERIA AND RELEASE DEFINITION

# 15. What “working end-to-end” means

Do not mark the project complete until all required gates below pass.

## Gate A — source and backup safety

- latest HSCL1 and ESP-Miner sources audited;
- branch/PR/commit baseline saved;
- `.61` and `.66` probed read-only and verified by identity;
- private configuration and active app image backups captured;
- full-backup scope stated correctly;
- hashes verified;
- restore instructions and known gaps documented;
- no NVS erase/flash operation occurred.

## Gate B — HSCL1 receiver

- receiver starts/stops with HSCL1 service manager;
- configured local port is reachable from the same Wi-Fi/LAN;
- `hscl miner receiver doctor` reports interface, port, TLS/pairing and storage status;
- unknown device is rejected;
- paired device is accepted;
- invalid/replayed request is rejected;
- 30-second heartbeat changes device state and is visible;
- receiver restart does not lose acknowledged events;
- no receiver does not disrupt miner operation.

## Gate C — firmware telemetry

- typed snapshots and event taps implemented;
- no secrets in regular events;
- queue is fixed/bounded;
- network/disk/TLS not run from mining hot path;
- telemetry task is lower priority;
- CPU/RAM/PSRAM/throughput overhead measured;
- 24-hour soak completed before stable claim.

## Gate D — durable ingest and backup

- sequence ACK and idempotency work;
- reconnect/backlog uploads work;
- partial upload resumes correctly;
- raw immutable data stored with hashes;
- backup artifacts retain scope and verification state;
- private config encrypted;
- no training artifacts contain secrets;
- host storage full/permission failure has visible behavior.

## Gate E — datasets and solver integration

- data dictionary and dataset schemas are versioned;
- training/validation/test split and leakage report exist;
- raw lineage traceable;
- SHA fixtures independently pass;
- reduced-round encodings verified on small cases;
- CQ-HECS consumes datasets through the existing solver API;
- SAT models and UNSAT proofs are independently checked;
- fixed baseline benchmarks exist;
- learned model does not replace solver correctness.

## Gate F — ML models

- model card documents scope, training data, exclusions, limitations and calibration;
- held-out evaluation includes separate device/session/firmware families;
- baseline vs learned heuristic measured;
- inference overhead measured;
- model may abstain when out of distribution or low confidence;
- model suggestions are advisory and versioned;
- no automatic firmware tuning is enabled by default.

## Gate G — HSCL1 product quality

- CLI commands work;
- Miner Lab UI is integrated into the existing OS/control-center architecture;
- visual states include offline, stale, buffering, quarantined and identity mismatch;
- screenshots and visual regression tests exist;
- localization and accessibility pass;
- docs and `hscl doctor` include receiver/data status;
- installation package/service works on the actual supported HSCL1 target.

---

# PART XVI — FIRST EXECUTION PLAN FOR THE NEXT AGENT

# 16. First 25 tasks, in exact order

1. Read current HSCL1 root `AGENTS.md` and current development loop.
2. Read the current ESP-Miner root `AGENTS.md`, `GEMINI.md`, README, deep dive, research mode and WLAN backup docs.
3. Refresh latest branch heads, commits, PRs, upstream PR dependencies and CI.
4. Confirm whether `feat/timsminer-sha-research-mode` still exists and recalculate ahead/behind.
5. Compare `master` and research branch changed files; inspect the full diff, not only commit messages.
6. Read the current firmware API/OpenAPI schema and the exact telemetry fields already exposed.
7. Verify current target identity on `.61` and `.66` with read-only GET only; stop on mismatch.
8. Capture baseline snapshots and produce a redacted identity/telemetry report.
9. Create a private backup manifest; identify that the new WLAN backup is only the app partition.
10. Do not flash. Do not change NVS. Verify existing backup artifact/readiness only.
11. Audit HSCL1 root layout and choose the correct service/CLI pattern; write an ADR for the receiver location and runtime.
12. Draft `hcs.miner.event.v1`, heartbeat, batch and ACK schemas.
13. Implement receiver health endpoint with fake-device fixture first.
14. Implement device registry and identity verification tests.
15. Implement pairing flow and local key storage; test invalid/replay/revoke paths.
16. Implement event ingest with idempotent sequence watermark and durable raw write.
17. Implement mDNS or explicit endpoint discovery, after security review.
18. Implement `hscl miner receiver status/doctor` and list/probe commands.
19. Add firmware fixed-size event queue and 30-second heartbeat in a separate feature branch.
20. Add offline buffering and ACK release; prove mining continues with HSCL1 absent.
21. Add a small set of high-value event taps (boot/network/pool/job/share/thermal/ASIC fault).
22. Benchmark instrumentation overhead and compare against the pre-change baseline.
23. Build sanitizer/QEMU/host CI and run the physical smoke test only after all earlier gates pass.
24. Build first normalized dataset (mining reliability + efficiency) and SHA fixture dataset.
25. Connect a reduced-round SHA fixture family to existing CQ-HECS, establish exact SAT/UNSAT verification, and only then start model training.

The first milestone is **a safe receiver with authenticated 30-second heartbeat and one durable test event**, not a neural model, not an OTA flash and not a new GUI.

---

# PART XVII — STATUS LEDGER TEMPLATE

# 17. Keep this live ledger current

The agent updates this ledger after each milestone with exact paths, SHAs, tests and limitations.

| ID | Feature | Initial status | Evidence required to promote |
|---|---|---|---|
| MBR-001 | HSCL1 headless receiver | NOT IMPLEMENTED | service process + health endpoint + tests |
| MBR-002 | candidate device identity verification | NOT IMPLEMENTED IN HSCL1 | read-only API evidence and tests for `.61`/`.66` mismatch |
| MBR-003 | secure pairing | NOT IMPLEMENTED | pairing/key lifecycle and replay tests |
| MBR-004 | 30-second heartbeat | NOT IMPLEMENTED | real device heartbeat ACK and offline behavior |
| MBR-005 | event batch upload/ACK | NOT IMPLEMENTED | sequence/idempotency/disconnect tests |
| MBR-006 | PSRAM event queue | NOT IMPLEMENTED FOR THIS BRIDGE | fixed bounded queue tests and measured memory |
| MBR-007 | persistent device flash spool | BLOCKED / NOT APPROVED | flash map, partition proposal, wear-leveling and recovery proof |
| MBR-008 | host immutable raw event storage | NOT IMPLEMENTED | crash-safe write, hashes, duplicate/recovery tests |
| MBR-009 | complete private config backup | NOT IMPLEMENTED BY WLAN APP BACKUP | secure export path and restore validation |
| MBR-010 | running app image backup | IMPLEMENTED ON FEATURE BRANCH | route availability, exact digest and device verification |
| MBR-011 | standard telemetry events | PARTIALLY AVAILABLE AS API FIELDS | event instrumentation and schema tests |
| MBR-012 | training dataset builder | NOT IMPLEMENTED | manifests, splits, leakage and privacy checks |
| MBR-013 | SHA software oracle | IMPLEMENTED ON FEATURE BRANCH | fresh build, KAT tests and independent replay |
| MBR-014 | ASIC internal round trace | NOT AVAILABLE / DO NOT CLAIM | would require actual hardware interface evidence; current design states none |
| MBR-015 | reduced-round SHA SAT generator | HOST RESEARCH TASK | exact encoding fixtures and independent verification |
| MBR-016 | CQ-HECS ingestion | NOT IMPLEMENTED | integration tests and provenance link |
| MBR-017 | learned SAT branching guidance | EXPERIMENTAL FUTURE | held-out speedup with no correctness regression |
| MBR-018 | mining efficiency predictor | EXPERIMENTAL FUTURE | grouped, cross-device validation and calibration |
| MBR-019 | advisory recommendation profile | NOT IMPLEMENTED | signed/versioned profile and explicit approval |
| MBR-020 | Miner Lab UI | NOT IMPLEMENTED | integrated screens + visual/accessibility tests |
| MBR-021 | 24-hour soak | NOT RUN FOR BRIDGE | uninterrupted actual device/receiver evidence |
| MBR-022 | 72-hour soak | NOT RUN FOR BRIDGE | release-level long-run evidence |

Status vocabulary:

- `NOT IMPLEMENTED`
- `PLANNED`
- `IN PROGRESS`
- `IMPLEMENTED_NOT_TESTED`
- `TESTED_HOST`
- `TESTED_QEMU`
- `TESTED_HARDWARE`
- `MEASURED`
- `VERIFIED`
- `BLOCKED`
- `NOT AVAILABLE`

A feature may have several independent labels: implementation status, test status, hardware status, measurement status and security status. One does not imply the others.

---

# PART XVIII — NON-NEGOTIABLE CLAIMS AND STOP CONDITIONS

# 18. Do not cross these lines

1. Do not build a second Linux OS or standalone miner GUI. Integrate directly into HSCL1.
2. Do not create a second solver or second MCP server. Connect to existing HSCL1/CQ-HECS interfaces.
3. Do not scan the whole network. Only probe `.61` and `.66` unless explicitly authorized later.
4. Do not rely on IP address alone for physical device identity.
5. Do not flash before a verified private backup and restore plan.
6. Do not clear NVS, change pool/wallet/Wi-Fi or alter thermal/power settings during the telemetry milestone.
7. Do not use the app-partition WLAN backup as a full-chip backup.
8. Do not store high-frequency telemetry in NVS.
9. Do not invent a data partition or write to unused flash addresses.
10. Do not run TLS, compression, database writes, or ML inference in mining hot paths.
11. Do not pause mining for normal telemetry or receiver heartbeats.
12. Do not resume mining automatically from a research SHA session.
13. Do not claim ASIC internal SHA round traces. The existing oracle is software C on the ESP32-S3.
14. Do not claim all ASIC attempts/nonces are logged; the hardware reports candidates/counters, not every hash attempt.
15. Do not send secrets or raw unredacted logs into training datasets, GitHub, CI or public reports.
16. Do not let the neural model choose SAT/UNSAT truth or mark its own output verified.
17. Do not claim full-round SHA-256, SHA-256d, Bitcoin or P=NP is broken or solved from reduced-round research.
18. Do not tune voltage/frequency/power/thermal limits without explicit human-approved experiment and existing firmware safety checks.
19. Do not run an unbounded cron/build/training loop. Use bounded ticks, locks, budgets and stop conditions.
20. Do not claim a PR was merged, a firmware was flashed, a service installed or a device validated unless the action actually happened and the evidence exists.

Stop and mark `BLOCKED` on:

- ambiguous device identity;
- missing/unverified backup;
- unexpected firmware/partition mismatch;
- secret leak;
- untrusted receiver certificate/key;
- repeated authentication failures;
- unexpected NVS or partition modification;
- queue corruption or unexplained event loss;
- thermal/fan/power safety warning;
- mining performance regression beyond the declared threshold;
- solver proof/model check failure;
- dataset privacy/leakage failure;
- resource budget breach;
- unsupported hardware/firmware combination.

---

# APPENDIX A — FORMULAS, METRICS AND RECOMMENDED ANALYSIS

## A.1 Energy efficiency

\[
\eta = \frac{P}{H_{\mathrm{TH/s}}} \quad \mathrm{J/TH}
\]

If hash rate is reported in GH/s:

\[
\eta = \frac{1000 P_{\mathrm{W}}}{H_{\mathrm{GH/s}}}
\]

Only calculate when `P` and `H` are valid and aligned to the same sampling interval. Do not divide the current instantaneous power by a stale 1-hour hashrate without flagging the mismatch.

## A.2 Accepted/rejected share rate

For an interval \([t_0,t_1]\):

\[
\lambda_{\mathrm{accept}} = \frac{A(t_1)-A(t_0)}{t_1-t_0}
\]

\[
\lambda_{\mathrm{reject}} = \frac{R(t_1)-R(t_0)}{t_1-t_0}
\]

\[
\rho_{\mathrm{reject}} = \frac{\Delta R}{\Delta A+\Delta R}
\]

If the counter decreases, the device rebooted, or its counter semantics changed, start a new counter epoch. Never silently wrap a negative delta into a huge positive rate.

## A.3 Hashrate coefficient of variation

For a window of valid hashrate samples \(H_i\):

\[
CV_H = \frac{\sigma(H)}{\mu(H)}
\]

Report sample count, sample interval, mean, standard deviation, median, p5/p95 and missing-sample ratio. Do not smooth away drops that may represent real outages.

## A.4 Share latency

Maintain histograms rather than only means:

- p50, p90, p95, p99;
- minimum/maximum;
- count and timeout count;
- protocol, pool class and difficulty bucket;
- connection/session generation.

## A.5 Receiver backlog

For unacknowledged records:

\[
B(t) = N_{\mathrm{produced}}(t) - N_{\mathrm{durably\ acked}}(t)
\]

Report oldest-event age and estimated drain time, not only queue count.

## A.6 Model reward and cost

A training objective for solver guidance may be:

\[
R = -\log(1 + T) - \alpha\,\log(1+M) - \beta\,I_{\mathrm{timeout}}
\]

where \(T\) is solve time, \(M\) is peak memory and timeout penalty is explicit. Tune only on the training/validation split. Also report PAR-2 and solved count separately; a single reward can hide regressions.

For operational mining prediction, use a multi-objective score rather than hashrate alone, for example:

\[
J = w_1\,\mathrm{normalized}(\mathrm{J/TH})
  + w_2\,\mathrm{normalized}(\mathrm{reject\ rate})
  + w_3\,\mathrm{normalized}(\mathrm{thermal\ margin}^{-1})
  + w_4\,\mathrm{normalized}(\mathrm{downtime})
\]

The weight choice is an operator/product policy, not a mathematical truth. Report the component metrics beside any composite.

---

# APPENDIX B — REQUIRED ARTIFACTS PER EXPERIMENT

Every experiment must produce a directory or equivalent artifact bundle containing:

1. `experiment.json` — hypothesis, input dataset IDs, parameters, seeds, budget and owner;
2. `source_manifest.json` — HSCL1, ESP-Miner and CQ-HECS SHAs plus dependency versions;
3. `device_manifest.json` — anonymized device class, board/ASIC and firmware, not secrets;
4. `dataset_manifest.json` — raw source batch IDs, transformations, split hashes and exclusions;
5. `command_log.jsonl` — exact commands/arguments and exit statuses;
6. `resource_telemetry.json` — CPU/RAM/GPU/storage and wall time;
7. `raw_results.jsonl` — solver/benchmark outputs;
8. `verification.json` — independent witness/proof/trace checks;
9. `plots/` — only derived, reproducible visualizations;
10. `summary.md` — readable findings and limitations;
11. `model_card.md` — where a model is trained;
12. `sha256sums.txt` — digest list for the artifact files.

Use existing `hcs.run.v2` or the current shared run envelope where appropriate; do not fork a second evidence schema.

---

# APPENDIX C — RECOMMENDED FEATURE FLAGS

Suggested firmware flags (names illustrative; adapt to current Kconfig naming style):

- `CONFIG_HCS_MINER_BRIDGE` — compile bridge support;
- `CONFIG_HCS_MINER_TELEMETRY` — periodic low-rate metrics;
- `CONFIG_HCS_MINER_EVENT_CAPTURE` — event taps;
- `CONFIG_HCS_MINER_HEARTBEAT` — 30-second receiver heartbeat;
- `CONFIG_HCS_MINER_UPLOAD` — authenticated batch upload;
- `CONFIG_HCS_MINER_MDNS` — service discovery;
- `CONFIG_HCS_MINER_RESEARCH_SHA` — existing optional SHA software oracle;
- `CONFIG_HCS_MINER_PRIVATE_BACKUP_EXPORT` — separate gated secret export, disabled unless security requirements are met.

Defaults:

- all new transfer features disabled until host pairing is completed;
- telemetry may collect to RAM only after local opt-in/firmware setting;
- no secret backup export by default;
- no persistent flash spool in Phase 1;
- no firmware auto-update;
- no ML-based tuning;
- the existing mining and safety logic remains active.

---

# APPENDIX D — GLOSSARY

- **ASIC:** Application-Specific Integrated Circuit; here, the BM1366 hashing chip.
- **AxeOS:** The existing web UI and HTTP API served by ESP-Miner.
- **Batch ACK:** Host acknowledgement that a batch is validated and durably stored.
- **Boot ID:** Random identity for one device boot, used to disambiguate monotonic sequence/time.
- **Candidate nonce:** A nonce reported by ASIC/firmware for validation; not every nonce searched.
- **Dataset lineage:** Trace from every training/evaluation row to raw source event and transformation.
- **HCS Miner Bridge:** HSCL1's receiver/collector and the matching bounded ESP-Miner telemetry capability.
- **Heartbeat:** Device-initiated 30-second liveness/state exchange with HSCL1.
- **J/TH:** Joules per terahash; lower is more energy efficient at equal validity and uptime.
- **mDNS/DNS-SD:** Local service discovery on a LAN.
- **NVS:** ESP-IDF non-volatile settings storage, including sensitive configuration.
- **PSRAM:** External pseudo-static RAM available on supported ESP32-S3 boards.
- **SAT witness:** An assignment independently evaluated to satisfy a Boolean formula.
- **UNSAT proof:** A certificate independently checked by a trusted proof checker.
- **Software SHA trace:** SHA round state generated by ordinary software, not a view into ASIC registers.
- **Spool:** Bounded temporary storage of events not yet acknowledged by HSCL1.

---

# FINAL DIRECTIVE TO THE ENGINEERING AGENT

Do not build “another miner app”. Build the **HCS Miner Research Bridge inside HSCL1**.

First make the data safe, attributable, durable and useful. Then make it intelligent. Let the miner continue doing the one thing it is good at—hashing—while HSCL1 performs the heavy analysis, dataset preparation, solver experiments, model training and agentic research. Keep the physical firmware lean, predictable and safety-first. Make every dataset traceable to actual observations and every claimed improvement reproducible.

**The success criterion is not the number of logs or the number of neural networks. It is a growing, privacy-safe, independently verified body of real-world evidence that helps HSCL1 understand the miner, improve its own research workflows, and propose better solver heuristics without ever confusing a prediction with proof.**

Made with ❤️ by hcsmedia · timfromhcs
