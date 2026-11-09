"""Capture the Bitaxe serial log from boot, optionally resetting the board first (read-only).

Why: the previous capture opened the port after the boot had already happened, so a panic in the
first two seconds was invisible. This script toggles RTS to reset the ESP32-S3 and records from t=0.

Usage: miner_serial_capture.py [PORT] [SECONDS] [--reset]
"""

from __future__ import annotations

import re
import sys
import time
from pathlib import Path

import serial

PORT = "COM3"
SECONDS = 12.0
RESET = False
for arg in sys.argv[1:]:
    if arg == "--reset":
        RESET = True
    elif re.fullmatch(r"\d+(\.\d+)?", arg):
        SECONDS = float(arg)
    else:
        PORT = arg

OUT = Path("artifacts/miner/serial-capture.log")
ANSI = re.compile(r"\x1b\[[0-9;]*m")


def main() -> int:
    with serial.Serial(PORT, 115200, timeout=0.5) as ser:
        if RESET:
            ser.dtr = False
            ser.rts = True
            time.sleep(0.15)
            ser.rts = False
            time.sleep(0.05)
        end = time.time() + SECONDS
        buf = bytearray()
        while time.time() < end:
            chunk = ser.read(4096)
            if chunk:
                buf.extend(chunk)

    text = buf.decode("utf-8", "replace")
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(text, encoding="utf-8")
    clean = ANSI.sub("", text)
    lines = [line.strip() for line in clean.splitlines() if line.strip()]
    print(f"captured {len(text)} bytes -> {OUT} ({len(lines)} lines)")

    problems = [l for l in lines if any(k in l.lower() for k in ("panic", "abort", "guru", "assert", "stack", "backtrace", "reboot"))]
    if problems:
        print("PROBLEM LINES:")
        for line in problems[:15]:
            print("  ", line[:140])

    for key in ("ESP-Miner", "display", "lvgl", "lcd", "self_test", "self-test", "asic", "ip=", "Connected to SSID"):
        hits = [l for l in lines if key.lower() in l.lower()]
        if hits:
            print(f"[{key}] {len(hits)} line(s), last: {hits[-1][:120]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
