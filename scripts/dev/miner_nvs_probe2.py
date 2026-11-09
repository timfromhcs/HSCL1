"""Inspect the full NVS partition and the WLAN profile fields (key masked)."""

from __future__ import annotations

import re
import subprocess

import serial  # noqa: F401  (ensures pyserial exists for the docs)
from pathlib import Path

DUMP = Path("artifacts/miner/nvs-full.bin")
SSID = "FRITZ!Box 7590 MP-2,4GhZ"

data = DUMP.read_bytes()
runs = [s.decode("ascii", "replace") for s in re.findall(rb"[ -~]{3,}", data)]
print("runs:", len(runs))
for needle in ("wifissid", "wifipass", "pool", "hostname", "prim_idx", "myssid", SSID):
    print(f"  {needle!r}: {needle in runs}")

out = subprocess.run(
    ["netsh", "wlan", "show", "profile", f"name={SSID}", "key=clear"],
    capture_output=True,
    text=True,
    encoding="cp850",
    errors="replace",
)
lines = out.stdout.splitlines()
for line in lines:
    if ":" in line:
        key, _, value = line.partition(":")
        low = key.strip().lower()
        if "schl" in low or "key" in low or "authent" in low or "verschl" in low:
            shown = "<masked>" if ("schl" in low or "key" in low) and value.strip() else value
            print(f"{key.strip()}: {shown}")
print("returncode:", out.returncode)
