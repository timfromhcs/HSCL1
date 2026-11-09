"""Bake the home Wi-Fi credentials into the firmware's Kconfig defaults (per-unit build).

The device's NVS was erased by the factory flash, so the app falls back to `CONFIG_ESP_WIFI_SSID`
(ESP-IDF's example value "myssid"). This script reads the password from the Windows WLAN profile for
the SSID the miner used before and patches the fork's `sdkconfig`. Neither the SSID key nor the
password is printed; only status flags are.

Usage: miner_bake_wifi.py [SSID]
"""

from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SDKCONFIG = ROOT / "artifacts/cross-repos/ESP-Miner/sdkconfig"
DEFAULT_SSID = "FRITZ!Box 7590 MP-2,4GhZ"


def profile_password(ssid: str) -> str | None:
    out = subprocess.run(
        ["netsh", "wlan", "show", "profile", f"name={ssid}", "key=clear"],
        capture_output=True,
    )
    text = out.stdout.decode("cp850", "replace")
    for pattern in (r"Schl\u00fcsselinhalt\s*:\s*(.+)", r"Key Content\s*:\s*(.+)"):
        m = re.search(pattern, text)
        if m:
            return m.group(1).strip()
    return None


def set_key(lines: list[str], key: str, value: str) -> list[str]:
    entry = f'{key}="{value}"'
    for i, line in enumerate(lines):
        if line.startswith(key + "="):
            lines[i] = entry
            return lines
    lines.append(entry)
    return lines


def main(argv: list[str]) -> int:
    ssid = argv[1] if len(argv) > 1 else DEFAULT_SSID
    pwd = profile_password(ssid)
    if not pwd:
        print("ERROR: no stored password for the profile; nothing changed")
        return 2
    if not SDKCONFIG.is_file():
        print(f"ERROR: {SDKCONFIG} not found")
        return 2
    lines = SDKCONFIG.read_text(encoding="utf-8").splitlines()
    lines = set_key(lines, "CONFIG_ESP_WIFI_SSID", ssid)
    lines = set_key(lines, "CONFIG_ESP_WIFI_PASSWORD", pwd)
    lines = set_key(lines, "CONFIG_LWIP_LOCAL_HOSTNAME", "timsminer")
    SDKCONFIG.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"patched {SDKCONFIG.name}: ssid set, password set ({len(pwd)} chars), hostname timsminer")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
