# Miner hardware: what can be built, and what cannot

This note exists because "build new miner hardware" is a physical task. Software can specify, verify and
flash; it cannot solder, and it cannot certify a board. The split below is deliberate.

## Already proven on real hardware (2026-11-09)

| Item | Evidence |
|---|---|
| Bitaxe board **201**, BM1366, `timsminer` | live `GET /api/system/info`; [TELEMETRY](TELEMETRY.md) |
| Firmware built from source (ESP-IDF 6.0.2, xtensa-esp-elf 15.2.0) | 2 758 656 B image, 34 % partition free |
| OTA flash through `hscl miner ota` | 263 s, HTTP 2xx, version changed, MAC and board unchanged |
| Read-only telemetry pipeline | `scripts/dev/miner_collect.py`, `miner_series.py` |

## What a "new" miner would need (not built)

| Decide | Why it matters | Status |
|---|---|---|
| Board family (Ultra/201 is the tested one; Supra BM1370 is the next tier) | ASIC, voltage regulator, fan controller and pin map all change per family | open |
| Power target | BM1366 boards run ~12 W class; BM1370 class is ~20–40 W and needs a different supply and cooling | open |
| Thermal design | the tested unit sits at 66 °C ASIC with 28 % fan; a denser board needs a real heatsink/fan curve | open |
| Enclosure and DC input | not a software question | open |
| Secure Boot / flash encryption (eFuse) | irreversible; needs sacrificial boards and a recovery plan | **not to be done on the working unit** |
| Certification / EMC | not performed and not claimed | open |

## Flashing and control paths (implemented)

```console
# USB (recovery / first flash)
hscl miner flash --port COM5 --firmware esp-miner-factory-201-<ver>.bin --yes="I am authorized to flash this device"

# OTA over the LAN
hscl miner plan 192.168.178.61 --firmware esp-miner.bin
hscl miner ota  192.168.178.61 --firmware esp-miner.bin --yes="I am authorized to flash this device"
```

Rules that the tooling enforces and that a new board does not change:

- only private/loopback/`*.local` hosts;
- the exact authorization phrase;
- SHA-256 recorded before sending, re-checked at send time;
- the three firmware limits (no TLS, no signature check, no downgrade protection) printed every time;
- a dry run that writes no state.

## MCP surface

Read-only tools: `hscl_miner_status`, `hscl_miner_probe`. Flashing is intentionally **not** an MCP tool:
an agent should not be able to write flash without a human-typed phrase in a shell.

## Honest boundary

Nothing here claims that a home-built board is safe, certified or profitable. Mining returns depend on
pool, difficulty and electricity price, which this project does not model. The only hardware claim is the
measured one in [TELEMETRY](TELEMETRY.md).
