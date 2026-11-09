"""Pull the three miners through the local hscl API and print a compact table."""

from __future__ import annotations

import json
import urllib.request

data = json.load(urllib.request.urlopen("http://127.0.0.1:8787/v1/miners", timeout=20))
rows = []
for entry in data.get("miners", []):
    info = entry.get("info") or {}
    pools = info.get("pools") or [{}]
    pool = pools[0]
    rows.append(
        {
            "host": entry.get("host"),
            "name": info.get("hostname"),
            "asic": info.get("asic"),
            "board": info.get("board_version"),
            "ghs": round(info.get("hashRate_1m") or info.get("hashRate") or 0, 1),
            "temp": info.get("temp_c"),
            "w": round(info.get("power") or 0, 2),
            "shares": f"{info.get('sharesAccepted')}/{info.get('sharesRejected')}",
            "pool": f"{pool.get('stratumURL')}:{pool.get('stratumPort')}",
            "freq": info.get("frequency"),
            "age_s": entry.get("age_seconds"),
        }
    )

widths = {"host": 15, "name": 16, "asic": 7, "board": 5, "ghs": 8, "temp": 5, "w": 6, "shares": 12, "pool": 34, "freq": 5, "age_s": 5}
hdr = " ".join(k.ljust(widths[k]) for k in widths)
print(hdr)
for r in rows:
    print(" ".join(str(r[k] if r[k] is not None else "-").ljust(widths[k]) for k in widths))
