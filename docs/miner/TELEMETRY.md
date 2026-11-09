# Miner telemetry — measured on `timsminer` (2026-11-09)

Device: `192.168.178.61`, hostname `timsminer`, board **201**, ASIC **BM1366**,
firmware **v4.0.2-rc1-sha-research**, MAC `74:4D:BD:77:DD:3C`.
Read-only collection (`GET /api/system/info`); no settings were written and nothing was flashed.

## Pre-flash snapshot

| Field | Value |
|---|---|
| Hashrate (instant / 1 m / 10 m / 1 h) | 467.8 / 431.9 / 435.5 / 434.6 GH/s |
| ASIC temperature | 66 °C |
| Input power | 11.41 W (5.06 V, 2.26 A) |
| Core voltage / frequency | 1089 mV / 485 MHz (actual 485) |
| Fan | 28 % / 2779 rpm |
| Shares (accepted / rejected) | 30 093 / 145 (0.48 % reject) |
| Best diff (all time / session) | 399 832 532 / 69 461 248 |
| Wi-Fi RSSI | −67 dBm |
| Uptime | 631 084 s ≈ 7.3 days |

## OTA flash (2026-11-09, 18:36 UTC)

Built from the fork's branch head (`codex/hscl1-research-bridge-contract`, `f024618`) with ESP-IDF
v6.0.2 on Windows:

| Field | Value |
|---|---|
| Image | `build/esp-miner.bin`, 2 758 656 bytes |
| SHA-256 | `ecb7463009e87608f32b1d9b7af34595dd6da1d7c7aa726c8f9eca32c2c09408` |
| Command | `hscl miner ota 192.168.178.61 --firmware … --yes="I am authorized to flash this device"` |
| Result | HTTP 2xx, `OTA accepted`, 263 s wall clock (upload + flash write over Wi-Fi) |
| Version before → after | `v4.0.2-rc1-sha-research` → `v4.0.2-rc1` |
| Board / ASIC after | `201` / `BM1366` (unchanged) |
| MAC after | `74:4D:BD:77:DD:3C` (unchanged — correct variant, no eFuse-MAC replacement) |
| Hostname after | `timsminer` (unchanged) |

## Post-flash series (8 s interval, 6 valid samples)

| Metric | mean | note |
|---|---|---|
| Hashrate | ~452 GH/s (instant samples 409–487) | in line with pre-flash 430–470 |
| Power | 11.30 W | unchanged |
| Fan | 2439 rpm | lower than pre-flash 2698 (cooler/less load at the time) |
| Efficiency | **24.97 J/TH** | vs 27.5 J/TH pre-flash, same power class |
| Shares delta | 9 accepted / 1 rejected | 10 % over 10 shares — **not** a meaningful reject rate |

The reject percentage in a ten-share window is noise; only the long-run counter (145/30 238 ≈ 0.48 %)
is a usable figure.

## Observation: the HTTP server stops answering under load

## Series (10 s interval, 8 valid samples)

| Metric | min | max | mean | stdev |
|---|---|---|---|---|
| Hashrate (GH/s) | 360.7 | 485.3 | 430.0 | 41.4 |
| Temperature (°C) | 66 | 66 | 66.0 | 0.0 |
| Power (W) | 11.28 | 11.34 | 11.31 | 0.02 |
| Fan (rpm) | 2592 | 2867 | 2698 | 86 |
| RSSI (dBm) | −65 | −64 | −64.3 | 0.4 |

Derived: **27.5 J/TH** (`W × 1000 / (GH/s)`) at 11.31 W and 411 GH/s; share delta over the window was
16 accepted / 1 rejected.

## Observation: the HTTP server stops answering under load

Sample 9 of the first run and later runs hit a **6 s timeout** while the device kept hashing (share
counters advanced across the gap). No reboot, no version change. Two short series captured only 2 of 6
samples each. The firmware's web server is single-threaded and serves the dashboard/WebSocket from the
same task; a burst of polling while another client is connected is a plausible cause. It is **not**
diagnosed here — it is recorded so it is not mistaken for a dead device.

Implication for tooling: `hscl miner probe` has a 6 s timeout and a 256 KiB cap; a timeout is reported
as an error, never as "device unknown/healthy". Retry once, then stop.

## Data files

Raw JSON lives under `artifacts/miner/` (gitignored):
`192.168.178.61-<stamp>/api_system_info.json` and `series-<stamp>.json`.
The pool user string is deliberately **not** copied into this document.

## Reproduce

```console
$ python scripts/dev/miner_collect.py 192.168.178.61     # one snapshot + key fields
$ python scripts/dev/miner_series.py  192.168.178.61 10 5 # series + summary JSON
```
