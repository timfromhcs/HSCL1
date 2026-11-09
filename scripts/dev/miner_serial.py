"""Read the Bitaxe serial console for a bounded time (read-only).

Usage: miner_serial.py COM3 [seconds]
Prints the decoded log; never writes to the port.
"""

from __future__ import annotations

import sys
import time

import serial


def main(argv: list[str]) -> int:
    port = argv[1] if len(argv) > 1 else "COM3"
    seconds = float(argv[2]) if len(argv) > 2 else 15.0
    with serial.Serial(port, 115200, timeout=1) as ser:
        end = time.time() + seconds
        buf = bytearray()
        while time.time() < end:
            chunk = ser.read(4096)
            if chunk:
                buf.extend(chunk)
    text = buf.decode("utf-8", "replace")
    print(text[-8000:])
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
