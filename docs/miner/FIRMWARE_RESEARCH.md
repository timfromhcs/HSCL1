# Miner firmware research — 2026-11-09

Purpose: close the open questions in `ARCHITECTURE.md` that needed current upstream facts, before the
`hscl miner` slice was written. Every statement names its source and the date it was checked. Anything
not found here is still open and listed at the end.

## 1. Upstream firmware state

| Fact | Source (checked 2026-11-09) |
|---|---|
| `bitaxeorg/ESP-Miner` latest stable tag is **v2.15.4**; v2.15.0 (2026-08-21) embedded the AxeOS web UI into `esp-miner.bin` so no separate `www.bin` is needed | GitHub releases page for `bitaxeorg/ESP-Miner`; release notes v2.15.0 |
| `POST /api/system/OTAWWW` still exists but on v2.15.0+ only installs a **custom** UI and sets `useCustomWWW` | AxeOS API reference (d-central.tech, published 2026-08-14, re-verified for v2.15.0) and `main/http_server/openapi.yaml` |
| mDNS support was added in v2.15, so devices answer as `<hostname>.local` | release notes v2.15.0 |
| Factory/OTA images are per board variant (`esp-miner-factory-XXX-….bin`); flashing the wrong variant replaces the factory MAC with the eFuse MAC | upstream flashing docs; fork `docs/OTA_SAFETY.md` §3 |

## 2. This fork (`timfromhcs/ESP-Miner`)

Branch `codex/hscl1-research-bridge-contract`, HEAD `f024618`, changelog top entry **4.0.2-rc1**
(2026-10-29). It adds the research guard, SHA tracing and a read-only partition backup on top of the
upstream hardening work.

Decisive wording from its own `docs/OTA_SAFETY.md` (v4.0.2-rc1):

> "No authentication beyond the network-range check, no TLS. Never expose it to an untrusted network."
> "No signature verification." "No downgrade protection."

Consequences that shaped the HSCL1 CLI:

1. **No claim of a secure update channel.** `hscl miner plan` prints those three limitations as warnings
   on every plan, and the docs do not describe OTA as verified or signed.
2. **LAN only is enforced in code.** `miner::is_private_host()` accepts loopback, RFC1918, link-local,
   unique-local and `*.local`; `1.1.1.1`, `example.com` and `172.32.0.1` are refused before a socket is
   opened. This is also the MCP boundary (`hscl_miner_probe`).
3. **Rollback exists but is not automatic.** An OTA never overwrites the running slot, so the previous
   image is still bootable; recovery is `POST /api/system/boot` with the other partition or USB flashing.
   The plan prints that hint instead of implying an automatic rollback.
4. **Wrong-variant risk is an operator check, not a tool check.** The firmware cannot detect it, so the
   plan tells the operator to compare `boardVersion` and `ASICModel` first.
5. **USB recovery path stays documented.** Browser (esptool-js) or `esptool` at offset `0x0` with the
   factory image.

## 3. What was deliberately not built

- No automatic device discovery/broadcast scan: a sweep of the LAN is indistinguishable from scanning
  someone else's network and is outside the product's remit. `hscl miner probe <host>` takes an address.
- No credentials or pool configuration writes: those change mining behaviour on third-party hardware.
- No signature verification of firmware, because the firmware does not provide one. A local SHA-256 is
  recorded for reproducibility, which is integrity against transfer errors, **not** authenticity.
- No eFuse/Secure-Boot provisioning. That is a one-way hardware operation; it requires an owner decision,
  a recovery plan, and a physical device.

## 4. Open questions (still open after this round)

1. Which board(s) does the owner actually want to support first (401/601/Hex/GT)? The CLI is board-neutral
   and reads `boardVersion`/`ASICModel`, but a hardware BOM decision is not made here.
2. Secure Boot / flash encryption on a new board: enabling eFuse bits is irreversible and would have to be
   tested on sacrificial hardware first.
3. Pairing/authentication protocol for the receiver (see `ARCHITECTURE.md` §4): still a draft, and the
   firmware has no pairing implementation to test against.
4. Whether the receiver should auto-start at boot (system service) or stay on-demand.

## 5. Sources

- `bitaxeorg/ESP-Miner` releases and `main/http_server/openapi.yaml` (OTA/OTAWWW paths).
- `d-central.tech/axeos-api-reference` (2026-08-14, re-verified v2.15.0) — endpoint list and the LAN rule.
- `github.com/bitaxeorg/ESP-Miner` readme — bitaxetool, endpoint list, `www.bin` history.
- Fork `timfromhcs/ESP-Miner` at `f024618`: `docs/OTA_SAFETY.md`, `CHANGELOG.md`, `flashing.md`.
- Kratos supported-miner table (2026-11-09) — board families and API versions, used only to check that
  the endpoint assumption is not Bitaxe-only.
