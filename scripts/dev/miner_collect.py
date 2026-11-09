"""Collect read-only telemetry from a Bitaxe/AxeOS miner into artifacts/miner/<stamp>/.

Read-only: GET /api/system/info, /api/system/asic, /api/system/statistics/dashboard.
No settings changes, no restart, no OTA.
"""

from __future__ import annotations

import json
import sys
import time
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PATHS = ["/api/system/info", "/api/system/asic", "/api/system/statistics/dashboard"]


def main(host: str) -> int:
    stamp = time.strftime("%Y%m%d-%H%M%S")
    out = ROOT / "artifacts" / "miner" / f"{host.replace(':', '_')}-{stamp}"
    out.mkdir(parents=True, exist_ok=True)
    for path in PATHS:
        url = f"http://{host}{path}"
        try:
            with urllib.request.urlopen(url, timeout=6) as r:
                body = r.read()
                status = r.status
        except Exception as exc:  # noqa: BLE001 - report, never guess
            print(f"{path}: {exc}")
            continue
        (out / (path.strip("/").replace("/", "_") + ".json")).write_bytes(body)
        print(f"{path}: HTTP {status}, {len(body)} bytes")
        if path == "/api/system/info":
            data = json.loads(body)
            keys = [
                "hostname", "boardVersion", "ASICModel", "version", "axeOSVersion",
                "hashRate", "hashRate_1m", "hashRate_10m", "hashRate_1h",
                "temp", "vrTemp", "power", "voltage", "current", "coreVoltageActual",
                "frequency", "actualFrequency", "fanspeed", "fanrpm",
                "sharesAccepted", "sharesRejected", "bestDiff", "bestSessionDiff",
                "stratumURL", "stratumUser", "uptimeSeconds", "wifiRSSI", "macAddr",
            ]
            print(json.dumps({k: data.get(k) for k in keys if k in data}, indent=2))
    print(f"written to {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1] if len(sys.argv) > 1 else "192.168.178.61"))
