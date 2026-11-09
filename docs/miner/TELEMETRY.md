# Miner telemetry — measured on `timsminer` (2026-11-09)

Device: `192.168.178.61`, hostname `timsminer`, board **201**, ASIC **BM1366**,
firmware **v4.0.2-rc1-sha-research**, MAC `74:4D:BD:77:DD:3C`.
Read-only collection (`GET /api/system/info`); no settings were written and nothing was flashed.

## Snapshot

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
