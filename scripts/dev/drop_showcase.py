"""Drop a showcase image and its manifest entry (used when the capture does not show its caption)."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SHOWCASE = ROOT / "docs/img/showcase"


def main(names: list[str]) -> int:
    manifest = SHOWCASE / "manifest.json"
    entries = json.loads(manifest.read_text(encoding="utf-8"))
    keep = [e for e in entries if e.get("filename") not in set(names)]
    removed = len(entries) - len(keep)
    manifest.write_text(json.dumps(keep, indent=2) + "\n", encoding="utf-8")
    for name in names:
        f = SHOWCASE / name
        if f.exists():
            f.unlink()
    print(f"removed {removed} manifest entries and {len(names)} files")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
