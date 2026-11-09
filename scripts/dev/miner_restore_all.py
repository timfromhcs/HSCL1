"""Restore the measured pre-flash settings on timsminer (LAN API, secrets masked).

Reads the snapshot taken before the factory flash and PATCHes /api/system with the pool, tuning and
display values. The wallet address and pool password are never printed.

Usage: miner_restore_all.py [HOST] [SNAPSHOT_DIR]
"""

from __future__ import annotations

import json
import sys
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
KEYS = (
    "stratumURL",
    "stratumPort",
    "stratumUser",
    "stratumSuggestedDifficulty",
    "stratumProtocol",
    "stratumTLS",
    "frequency",
    "coreVoltage",
    "overclockEnabled",
    "display",
    "rotation",
    "invertscreen",
    "hostname",
)


def mask(value: object) -> str:
    text = str(value)
    return f"{text[:4]}…{text[-4:]} ({len(text)} chars)" if len(text) > 8 else "*" * len(text)


def main(argv: list[str]) -> int:
    host = argv[1] if len(argv) > 1 else "192.168.178.61"
    snap = (
        Path(argv[2])
        if len(argv) > 2
        else sorted((ROOT / "artifacts/miner").glob("192.168.178.61-*"))[0]
    )
    snapshot = json.loads((snap / "api_system_info.json").read_text(encoding="utf-8"))
    body: dict[str, object] = {
        k: snapshot[k] for k in KEYS if k in snapshot
    }
    # v2.15+ takes the pool through the `pools` array; the flat stratumURL/User fields are ignored.
    body["pools"] = [
        {
            "id": 0,
            "stratumProtocol": snapshot.get("stratumProtocol", "SV1"),
            "stratumURL": snapshot["stratumURL"],
            "stratumPort": snapshot["stratumPort"],
            "stratumUser": snapshot["stratumUser"],
            "stratumPassword": "x",
            "stratumSuggestedDifficulty": snapshot.get("stratumSuggestedDifficulty", 1000),
            "stratumExtranonceSubscribe": bool(snapshot.get("stratumExtranonceSubscribe", False)),
            "stratumTLS": 0,
            "stratumDecodeCoinbase": bool(snapshot.get("stratumDecodeCoinbase", True)),
            "stratumV2ChannelType": snapshot.get("stratumV2ChannelType", "extended"),
        }
    ]
    body["primaryPoolIndex"] = 0
    req = urllib.request.Request(
        f"http://{host}/api/system",
        data=json.dumps(body).encode(),
        method="PATCH",
        headers={"Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(req, timeout=15) as r:
            status, response = r.status, r.read()[:200]
    except Exception as exc:  # noqa: BLE001
        print(f"PATCH failed: {exc}")
        return 1
    shown = {k: v for k, v in body.items() if k not in ("stratumPassword", "pools", "stratumUser")}
    pools = body.get("pools") or []
    shown["pools"] = [
        {**p, "stratumUser": mask(p.get("stratumUser", "")), "stratumPassword": "<set>"} for p in pools
    ]
    print(f"PATCH /api/system -> HTTP {status}")
    print("restored:", json.dumps(shown, ensure_ascii=False))
    if response:
        print("device said:", response.decode("utf-8", "replace")[:200])
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
