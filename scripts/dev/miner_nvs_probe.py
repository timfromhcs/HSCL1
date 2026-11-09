"""Report which NVS keys exist and whether a Wi-Fi password is stored in the Windows profile.

Prints key names only. The password is reported as `present: true/false`, never printed.
"""

from __future__ import annotations

import json
import re
import subprocess
from pathlib import Path

DUMP = Path("artifacts/miner/nvs-probe.bin")
SSID = "FRITZ!Box 7590 MP-2,4GhZ"


def main() -> int:
    data = DUMP.read_bytes() if DUMP.is_file() else b""
    runs = [s.decode("ascii", "replace") for s in re.findall(rb"[ -~]{4,}", data)]
    print("nvs has wifissid:", any(r == "wifissid" for r in runs))
    print("nvs has wifipass:", any(r == "wifipass" for r in runs))
    print("nvs has pool:", any(r == "pool" for r in runs))
    print("nvs ssid values:", [r for r in runs if r in ("myssid", SSID)])

    out = subprocess.run(
        ["netsh", "wlan", "show", "profile", f"name={SSID}", "key=clear"],
        capture_output=True,
        text=True,
        encoding="cp850",
        errors="replace",
    )
    text = out.stdout
    match = re.search(r"Schl\u00fcsselinhalt\s*:\s*(.+)", text) or re.search(r"Key Content\s*:\s*(.+)", text)
    present = bool(match and match.group(1).strip())
    print(json.dumps({"profile_found": out.returncode == 0, "password_present": present}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
