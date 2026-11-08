# HCS Miner Research Bridge — Architecture Decision Record

**Document ID:** ADR-2026-11-08-MINER-001  
**Date:** 2026-11-08  
**Status:** Draft (awaiting owner review)  
**Author:** HSCL1 Autonomous Engineering Agent  
**References:** `AGENTS_HSCL1_BITAXE_MINER_RESEARCH_BRIDGE_MASTER_2026-11-08.md`, `MINER_BRIDGE_RESEARCH_LEDGER.md`

---

## 1. Context and Problem Statement

HSCL1 needs a reliable, safe, local-first data bridge from physical Bitaxe mining hardware (two known candidate devices at `192.168.178.61` and `192.168.178.66`) into HSCL1's research, evidence, ML, and SAT workflows.

The firmware source is the user's fork `timfromhcs/ESP-Miner` (branch `feat/timsminer-sha-research-mode`, 8 commits ahead of master), which already implements:
- Portable C SHA-256/SHA-256d with incremental hashing and round tracing
- Research guard with state machine, pairing token, identity, thermal, power, job, and time-budget checks
- Bounded HTTP API routes for research state, capabilities, challenge/arm/pause/resume/cancel/disarm, SHA trace/digest
- Read-only backup of the running application partition with streamed SHA-256 digest
- USB research console with strict parser

**What is NOT yet implemented** (per contract Part I, section 1.1.2):
- HSCL1 receiver service
- mDNS/DNS-SD service discovery
- Periodic 30-second receiver heartbeat
- Device-to-host batch upload or acknowledgment protocol
- Reliable offline upload queue
- Device registry or pairing lifecycle managed by HSCL1
- Persistent miner event spool with reviewed partition layout
- Structured event dataset exporter
- Model training pipeline or ML registry
- HSCL1 Miner Lab UI or CLI subcommands
- CQ-HECS dataset ingestion connector
- Secure export of NVS configuration secrets
- Full-chip or NVS backup through WLAN

---

## 2. Decision: Receiver Location and Runtime

### 2.1 Chosen Location

**The HCS Miner Receiver shall be implemented as a headless service in the existing HSCL1 Rust workspace**, exposed through the existing `hscl` CLI as `hscl miner ...` subcommands.

**Rationale:**
- Root `AGENTS.md` section 3.3 specifies the HSCL1 codebase already has a Rust workspace and `hscl` CLI
- The receiver must be testable without the GUI; the existing Qt Control Center does not yet expose a Miner receiver
- Rust provides memory safety for a long-running network service handling untrusted input
- Single binary deployment aligns with HSCL1's packaging model
- No new runtime stack introduced (decision M3 in research ledger)

### 2.2 Service Characteristics

| Property | Value |
|----------|-------|
| **Process model** | Long-running daemon, started on demand via `hscl miner receiver start` |
| **Default state** | **Off by default** — explicit opt-in required (root `AGENTS.md` rule 9: no silent telemetry) |
| **Binding** | Single private LAN interface (configurable), not `0.0.0.0` |
| **Port** | Configurable; `8765` is an unapproved proposal with known existing users (Section 3) |
| **Protocol** | HTTPS with pinned host certificate (see Section 4) |
| **Authentication** | Per-device HMAC-SHA-256 over canonical request (method, path, timestamp, sequence, body hash) |
| **Pairing** | One-time challenge/response ceremony with physical presence proof |
| **Firewall** | Private-network restriction via HSCL1 nftables profile |

### 2.3 Integration Points

```
┌─────────────────────────────────────────────────────────────────┐
│ HSCL1 Rust Workspace                                            │
│                                                                 │
│  cli/hscl/                    services/hcs-miner-ingest/       │
│  ├── miner.rs  ◄─────────────►  ├── receiver.rs                │
│  ├── status.rs                ├── pairing.rs                   │
│  ├── receiver.rs              ├── ingest.rs                    │
│  └── ...                      ├── storage.rs                   │
│                                 └── schemas.rs                 │
│                                                                 │
│  Shared: ai-shared/ (if typed contracts exist)                 │
└─────────────────────────────────────────────────────────────────┘
```

The `hscl` CLI is the **only** user-facing entry point. The receiver daemon has no independent CLI.

---

## 3. Port Choice and Conflict Check

### 3.1 Port Proposal: 8765 Is Not Approved Yet

The target-host bind and conflict check remains required. CQ-HECS Studio already defaults to 8765 (`cqhecs/studio/app.py` at integration 5ed3d2e); whether sockets conflict depends on their actual bound addresses. Inspect the effective bind configuration, not only whether a process happens to be running.

The previous claim that 8765 has no IANA assignment was incorrect: [IANA registers ultraseek-http for TCP/UDP 8765](https://www.iana.org/assignments/service-names-port-numbers?search=8765). A registration neither proves local occupancy nor makes this a collision-free HCS default. Prior comparisons of serial baud rates with network ports are withdrawn.

Diagnostic examples (tool errors are failures, never proof that a port is free):

```bash
ss -ltn 'sport = :8765'
getent services 8765
nft list ruleset
```

A future receiver must report bind failures clearly and never terminate another service or silently choose an exposed interface. Finalize an explicit configured port only after the target-host service/firewall check and integration tests.

### 3.2 Configuration

The port **must be configurable** via:
1. `hscl miner receiver start --port <N>`
2. Config file at `$XDG_CONFIG_HOME/hscl/miner.toml` (or `/etc/hscl/miner.toml` for system-wide)
3. Environment variable `HSCL_MINER_RECEIVER_PORT`

No final default is approved by this draft. If 8765 remains a candidate, require explicit configuration plus the target-host conflict/bind test; do not infer availability from a failed diagnostic command.

---

## 4. Pairing Protocol

### 4.1 Threat Model

**Security correction (2026-11-08): the previous public-identifier HKDF sketch is withdrawn.** This remains a draft; no receiver or firmware pairing implementation is attested by this document.

| Threat | Required control / limit |
|--------|--------------------------|
| LAN adversary spoofs miner | Independent high-entropy per-pair secret, provisioned over an authenticated physical channel; MAC/hostname/build hash are metadata only |
| Replay | Fresh single-use challenge and monotonic request sequence, bound to the reviewed transcript and identities |
| Compromised miner firmware | Outside pairing's protection: malicious firmware can steal/use its keys. A button press does not repair compromised firmware |
| Spoofed receiver / first-use MITM | Authenticate receiver fingerprint through the trusted physical provisioning channel; a fingerprint returned over the same unauthenticated LAN connection proves nothing |
| Secrets in logs/crash dumps | Never log keys; restrict/disable core dumps and minimize secret copies/lifetimes. Process memory can contain plaintext keys; compromise/dump exposure cannot be ruled out |

### 4.2 Pairing Ceremony (Candidate, Not Implemented)

1. Operator explicitly enables pairing on the chosen physical device over a trusted USB console. A BOOT press may demonstrate presence, but alone does not authenticate a peer or establish a shared secret.
2. The host obtains a new 32-byte secret from its OS cryptographic RNG for this pairing. Provision it, the receiver certificate fingerprint and identity bindings through the authenticated physical channel. Never put it in a URL, shell argument, log, Git or ordinary unauthenticated HTTP response.
3. Both peers prove possession using a reviewed authenticated pairing protocol bound to fresh challenges, both identities and the receiver fingerprint. A six-digit display code is only a user confirmation aid; it is not keying material. Exact transcript encoding, canonicalization and failure handling need security review before code.
4. Persist only after both peers confirm the same pairing. Abort/delete pending material on timeout, mismatch or failed authentication. Store secrets with restricted access on each endpoint; no blanket encrypted-at-rest claim is made for ESP NVS.
5. Test simulated peers, attacker-chosen public identifiers, wrong peer/certificate, replay, timeout, repeated attempts, revocation and restart before any real-device rollout.

### 4.3 Secret Material and Derivation Requirements

Device MAC, hostname, firmware build hash and boot identifier are not authentication secrets. HKDF cannot create secret entropy from values known to an attacker; see [RFC 5869 section 3](https://www.rfc-editor.org/rfc/rfc5869.html#section-3). The former `IKM = firmware_unique_id || boot_id` construction must not be implemented.

Use independently generated 256-bit secret material and a reviewed key schedule with explicit domain separation and unambiguous identity/transcript binding. This ADR deliberately does not prescribe an unreviewed wire protocol or a homemade password exchange. If device-side random generation is selected later, check the pinned ESP-IDF version's entropy prerequisites before generating keys; [Espressif RNG guidance](https://docs.espressif.com/projects/esp-idf/en/stable/esp32s3/api-reference/system/random.html) distinguishes active hardware-entropy conditions from pseudo-random-only operation. Current stable documentation is not proof of the firmware's exact pinned API behavior.

### 4.4 Pairing Expiry and Rotation

- An active pairing challenge expires after **60 seconds**, is single-use and has bounded attempts; no 24-hour bearer credential is accepted. A longer operator registration workflow must not preserve an active authentication challenge.
- Completed pairing: HMAC key valid until explicit revocation
- Re-pairing requires explicit owner action (`hscl miner pair --revoke <device_id>` then new pairing)
- Key rotation: not in v1; future work with forward secrecy

---

## 5. Receiver Health and Status Endpoint

### 5.1 Local-Only Health Endpoint

```
GET http://127.0.0.1:<port>/v1/health
```

**Response:**
```json
{
  "status": "healthy",
  "receiver_id": "uuid-v4",
  "version": "hcs-miner-ingest-0.1.0",
  "uptime_seconds": 3600,
  "bound_interface": "192.168.178.100",
  "bound_port": 8765,
  "tls": { "enabled": true, "cert_sha256": "..." },
  "paired_devices": 2,
  "active_uploads": 0,
  "storage": { "used_bytes": 104857600, "quota_bytes": 10737418240 }
}
```

**Access control:** Bind to `127.0.0.1` only. Not exposed on LAN interface.

---

## 6. Data Flow Summary

```
Miner (ESP-Miner firmware)
    │
    ├── 30s heartbeat ──► POST /v1/devices/{id}/heartbeat
    │                      { device_id, boot_id, seq_ack, queue_depth, ... }
    │
    ├── Event batches ──► POST /v1/devices/{id}/events
    │                      [ { schema, device_id, boot_id, sequence, ... }, ... ]
    │
    ◄── ACK ───────────── 200 OK { ack_sequence, ack_hashes[] }
    │
    ◄── Advisory ──────── GET /v1/devices/{id}/commands (optional, signed)
```

All miner-initiated. No miner-to-miner or miner-to-internet connections introduced.

---

## 7. Security Decisions

| Decision | Status | Notes |
|----------|--------|-------|
| TLS with pinned cert | **Required** | Self-signed cert generated at first receiver start; fingerprint shown during pairing |
| HMAC-SHA-256 auth | **Required** | Per-device key from pairing ceremony |
| Request freshness window | **Required** | ±30s clock skew tolerance; monotonic sequence prevents replay |
| Rate limiting | **Required** | Per-device: 10 req/s burst, 1 req/s sustained for heartbeat; 1 MB/s for events |
| Payload size limits | **Required** | Heartbeat: 4 KB; Events batch: 256 KB (configurable) |
| No internet exposure | **Required** | Firewall rule: LAN interface only; reject non-RFC1918 source |
| Secret redaction | **Required** | Before any logging; keys, tokens, passwords never in logs |
| mDNS advertisement | **Optional (v2)** | Only after firmware advertises `_hcs-miner._tcp.local.` |

---

## 8. Open Questions (Require Owner Decision)

1. **Certificate management**: Should the receiver generate a self-signed cert on first start, or use a pre-provisioned cert from HSCL1's PKI? (Current ADR assumes self-signed with TOFU during pairing)

2. **Physical presence proof**: Which method does the hardware support? USB console `pair <code>` command, or BOOT button (upstream PR #2055)? The firmware branch documents USB console; BOOT button is upstream.

3. **Receiver auto-start**: Should the receiver start at boot (systemd service) or only on-demand via `hscl miner receiver start`? (Current ADR: on-demand only for v1)

4. **Port 8765 confirmation**: Run the conflict check procedure on the target hardware and confirm.

---

## 9. Acceptance Criteria for This ADR

- [ ] Port 8765 conflict check passes on target HSCL1 build host
- [ ] Owner confirms pairing physical presence method (USB console vs BOOT button)
- [ ] Owner confirms certificate management approach
- [ ] Owner confirms receiver auto-start preference
- [ ] Schema drafts (next section) validate against this ADR's data shapes
- [ ] No conflicts with root `AGENTS.md` rules 7, 9, 13

---

## 10. Revision History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 0.1 | 2026-11-08 | HSCL1 Autonomous Agent | Initial draft |
| 0.2 | 2026-11-08 | HSCL1 takeover audit | Withdraw public-ID-derived secret; require cryptographic randomness and authenticated physical provisioning; correct compromise/dump/first-use boundaries and challenge expiry; still draft, no implementation |