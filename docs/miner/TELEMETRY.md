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

## Native series after the recovery (`hscl miner series`, 3 × 3 s)

| Field | Value |
|---|---|
| Hashrate (instant / 1 m) | 335 / 326 GH/s |
| Temperature | 59–60 °C |
| Power | 11.0 W |
| Shares | 173 accepted / 2 rejected (session) |
| Pool | `sha256.eu.mine.zpool.ca:3333` |
| RSSI | −50 dBm |

The unit sits ~100 GH/s below the pre-flash 466 GH/s sample. Not diagnosed: pool difficulty ramp,
thermal settling and the fresh build all differ. It is recorded rather than explained.

## Recovery build (2026-11-09, 19:35 UTC) — display and network restored
The factory flash had erased NVS, so the app fell back to board `000` and the serial log showed
`E system: Display init failed` / `esp_lcd_new_panel_io_i2c: i2c add device fail` — the black screen.

Per-unit build (source `f024618`, same ESP-IDF 6.0.2) with:

| Setting | Value | Effect |
|---|---|---|
| `ESP_MINER_BOARD_VERSION` | `201` | display and ASIC init work again without NVS |
| `ESP_MINER_CONFIG_AP_STUCK` | `1` | open config AP `Bitaxe_DD3C` stays up as a hardcoded fallback |
| `CONFIG_ESP_WIFI_SSID` / `PASSWORD` | home SSID / stored secret | device rejoins the WLAN after a reset |
| `CONFIG_LWIP_LOCAL_HOSTNAME` | `timsminer` | keeps the DHCP name |

Flashed as an app image at `0x10000` (SHA-256 `8f7321a1…`). Serial boot after the flash:
`Display init success!`, `LVGL: Starting LVGL task`, `ASIC Ready!`, `IP_ACQUIRED ip=192.168.178.61`,
`Connected to SSID: FRITZ!Box 7590 MP-2,4GhZ`.

Pool and tuning were restored through the v2.15 `pools` array (flat `stratumURL` is ignored):

```json
{"pools":[{"id":0,"stratumURL":"sha256.eu.mine.zpool.ca","stratumPort":3333,
           "stratumUser":"<wallet>","stratumPassword":"x","stratumProtocol":"SV1",
           "stratumDifficulty":1000}],"primaryPoolIndex":0,
 "frequency":485,"coreVoltage":1100,"display":"SSD1306 (128x32)"}
```

After a restart: **466 GH/s, pool difficulty 1000, 4 shares accepted in 42 s, 485 MHz**.

## LAN inventory (2026-11-09, `hscl miner discover`)

| Host | Name | MAC | Board | ASIC | Firmware |
|---|---|---|---|---|---|
| 192.168.178.61 | timsminer | 74:4D:BD:77:DD:3C | 201 | BM1366 | v4.0.2-rc1 |
| 192.168.178.66 | blackharkminer | 74:4D:BD:77:99:80 | 201 | BM1366 | v4.0.2-rc1-blackharkminer |
| 192.168.178.80 | bitaxe-tim2 | 28:84:85:A6:1B:E0 | 601 | BM1370 | v4.0.2-rc1-tim2 |

Devices are identified by MAC, not by address: the router re-assigned addresses during the day, and
`.61` was briefly answered by another miner. `hscl miner discover` and `hscl miner serve` therefore
report the MAC with every reading.

## Recovery images (2026-11-09)

Built for the two board families on this LAN, to be flashed **only** if a unit loses its NVS again.
Nothing was flashed onto the healthy units `.66` and `.80`.

| Board | File | Bytes | SHA-256 |
|---|---|---|---|
| 201 (BM1366) | `artifacts/miner/recovery/esp-miner-recovery-201.bin` | 2 758 656 | `8f7321a1761413d0f00a6780c6c427cf6fbf277e49fe1e81ff41e7aa0959556d` |
| 601 (BM1370) | `artifacts/miner/recovery/esp-miner-recovery-601.bin` | 2 758 656 | `25b2193f0b45cc9f6bf351d8c1ab17f6fb37906ca512fa75bd60ab3d607e2b49` |

Both bake `ESP_MINER_BOARD_VERSION=<board>`, `ESP_MINER_CONFIG_AP_STUCK=1`, the home SSID/password and the
hostname from `sdkconfig`. Build script: `scripts/dev/build_miner_recovery.ps1 -Board 201|601`.
Checksums are appended to `artifacts/miner/recovery/SHA256SUMS.txt`.

**Why not flash them:** `.66` (blackharkminer) and `.80` (bitaxe-tim2) are healthy and mining with their
own NVS. A factory flash erases that configuration — the exact mistake that cost timsminer its settings.
The images are recovery material, not updates; an update would be the app image at `0x10000`.

## USB factory flash (2026-11-09, ~18:58 UTC) — and its cost
Done after the OTA, with the same build, to exercise the USB path:

| Field | Value |
|---|---|
| Port | `COM3` (Espressif VID 303A, USB-Serial/JTAG), ESP32-S3 rev v0.2, 16 MB flash |
| Image | merged factory image `esp-miner-factory-201-v4.0.2-rc1.bin`, 15 802 368 B |
| SHA-256 | `fadf559c9d9be86cdea500de55e48cea314e1bc395b9716476fb2b62301a2616` |
| Command | `hscl miner flash --port COM3 --offset 0x0 --firmware … --yes="…"` |
| Result | 15 802 368 B written at 0x0 in 49.7 s, **hash verified**, hard reset |

**What went wrong (and is now documented and guarded):** a merged factory image covers the whole range
from `0x0`, so the NVS partition at `0x9000` is overwritten with `0xFF`. The device came back with
default settings: the serial log repeats `Wi-Fi status: No access point found (Error 201)` for SSID
`myssid`, and a read of `0x9000` shows the placeholder pool (`public-pool.io`, `replace-this-with-your-btc-address.bitaxe`)
and `sta.ssid = "myssid"`. **The previous Wi-Fi credentials and pool configuration were erased.**

Consequences applied to the tooling and docs:

- `hscl miner flash` now defaults to `--offset 0x10000` (app image, keeps NVS); `0x0` must be explicit.
- A file smaller than 1 MiB at `0x0` is refused (it is an app image, not a factory image).
- The plan prints "a factory image at 0x0 also erases NVS" as a warning.
- `docs/FLASHING.md` in the fork states that a factory flash is a factory reset.

The device is reachable on **USB** and in its bootloader/app, but not on the LAN until Wi-Fi is
configured again (AxeOS AP or the USB console). That reconfiguration needs the network credentials and is
therefore an owner step.

## Post-OTA series (8 s interval, 6 valid samples)
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
