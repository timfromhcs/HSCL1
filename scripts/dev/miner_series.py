"""Poll a Bitaxe/AxeOS miner read-only and summarise the series.

Read-only GETs only. Never sends settings, never restarts, never flashes.
A sample that times out is retried once and then recorded as a gap instead of aborting the series:
the AxeOS web server is single-threaded and occasionally misses a request.
Usage: miner_series.py HOST [SAMPLES] [INTERVAL_S]
"""

from __future__ import annotations

import json
import statistics
import sys
import time
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
FIELDS = [
    "hashRate",
    "hashRate_1m",
    "hashRate_10m",
    "hashRate_1h",
    "temp",
    "power",
    "coreVoltageActual",
    "actualFrequency",
    "fanspeed",
    "fanrpm",
    "sharesAccepted",
    "sharesRejected",
    "bestDiff",
    "wifiRSSI",
    "uptimeSeconds",
]


def fetch(host: str) -> dict:
    with urllib.request.urlopen(f"http://{host}/api/system/info", timeout=6) as r:
        return json.loads(r.read())


def main(argv: list[str]) -> int:
    host = argv[1] if len(argv) > 1 else "192.168.178.61"
    samples = int(argv[2]) if len(argv) > 2 else 10
    interval = float(argv[3]) if len(argv) > 3 else 10.0
    rows: list[dict] = []
    gaps = 0
    for i in range(samples):
        info = None
        for attempt in (1, 2):
            try:
                info = fetch(host)
                break
            except Exception as exc:  # noqa: BLE001 - report, never fabricate
                if attempt == 2:
                    print(f"sample {i + 1}: {exc}")
                    gaps += 1
                else:
                    time.sleep(0.5)
        if info is None:
            continue
        rows.append({k: info.get(k) for k in FIELDS})
        print(
            f"[{i + 1}/{samples}] {info.get('hashRate', 0):8.1f} GH/s  "
            f"{info.get('temp', 0):3} C  {info.get('power', 0):6.2f} W  "
            f"freq {info.get('actualFrequency', 0)} MHz  shares "
            f"{info.get('sharesAccepted', 0)}/{info.get('sharesRejected', 0)}"
        )
        if i + 1 < samples:
            time.sleep(interval)

    if not rows:
        print(f"no samples; {gaps} gap(s)")
        return 1

    def stats(key: str) -> dict:
        vals = [r[key] for r in rows if isinstance(r.get(key), (int, float))]
        if not vals:
            return {}
        return {
            "min": round(min(vals), 3),
            "max": round(max(vals), 3),
            "mean": round(statistics.fmean(vals), 3),
            "stdev": round(statistics.pstdev(vals), 3) if len(vals) > 1 else 0.0,
        }

    first, last = rows[0], rows[-1]
    accepted = (last.get("sharesAccepted") or 0) - (first.get("sharesAccepted") or 0)
    rejected = (last.get("sharesRejected") or 0) - (first.get("sharesRejected") or 0)
    elapsed = max(1.0, (last.get("uptimeSeconds") or 0) - (first.get("uptimeSeconds") or 0))
    hash_stats = stats("hashRate")
    power_stats = stats("power")
    mean_ghs = hash_stats.get("mean", 0) or 0
    mean_w = power_stats.get("mean", 0) or 0
    summary = {
        "host": host,
        "samples": len(rows),
        "gaps": gaps,
        "window_seconds": elapsed,
        "hashrate_ghs": hash_stats,
        "temp_c": stats("temp"),
        "power_w": power_stats,
        "fan_rpm": stats("fanrpm"),
        "wifi_rssi": stats("wifiRSSI"),
        "shares_delta": {"accepted": accepted, "rejected": rejected},
        "reject_rate_percent": round(100.0 * rejected / (accepted + rejected), 3)
        if (accepted + rejected)
        else 0.0,
        # J/TH: (W / (GH/s / 1000)) = W * 1000 / GH/s
        "efficiency_j_per_th": round(mean_w * 1000.0 / mean_ghs, 2) if mean_ghs else None,
    }
    stamp = time.strftime("%Y%m%d-%H%M%S")
    out = ROOT / "artifacts" / "miner" / f"series-{stamp}.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps({"summary": summary, "rows": rows}, indent=2), encoding="utf-8")
    print(json.dumps(summary, indent=2))
    print(f"written to {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
