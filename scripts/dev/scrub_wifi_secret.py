"""Remove the Wi-Fi password from captured artifacts (the Kconfig warning printed it once).

Reads the password from the fork's sdkconfig and rewrites matches in artifacts/ text files.
Prints only counts, never the secret.
"""

from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SDKCONFIG = ROOT / "artifacts/cross-repos/ESP-Miner/sdkconfig"
ARTIFACTS = ROOT / "artifacts"
# The harness stores captured command output outside the repository.
SHELL_LOGS = Path.home() / ".local/share/opencode/shell"


def main() -> int:
    text = SDKCONFIG.read_text(encoding="utf-8", errors="replace")
    m = re.search(r'^CONFIG_ESP_WIFI_PASSWORD="(.*)"$', text, re.MULTILINE)
    if not m:
        print("no password in sdkconfig; nothing to scrub")
        return 0
    secret = m.group(1).encode()
    if len(secret) < 8:
        print("password too short to scrub safely; refusing")
        return 2

    hits = 0
    roots = [ARTIFACTS] + ([SHELL_LOGS] if SHELL_LOGS.is_dir() else [])
    for base in roots:
        for path in base.rglob("*"):
            if not path.is_file() or path.stat().st_size > 20_000_000:
                continue
            if path.suffix.lower() not in {".out", ".log", ".txt", ".json", ".md"}:
                continue
            try:
                data = path.read_bytes()
            except OSError:
                continue
            if secret not in data:
                continue
            count = data.count(secret)
            path.write_bytes(data.replace(secret, b"<redacted>"))
            hits += count
            print(f"scrubbed {count} occurrence(s) in {path}")
    print(f"total occurrences scrubbed: {hits}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
