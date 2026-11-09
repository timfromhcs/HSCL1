"""Refresh the showcase images that this candidate actually captured, with its source_iso recorded."""

from __future__ import annotations

import json
import os
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "artifacts" / "boot-miner-qa-2026-11-09"
DST = ROOT / "docs" / "img" / "showcase"
MANIFEST = DST / "manifest.json"
ISO = "HSCL1-miner-qa-2026-11-09-amd64.iso sha256 e342b3ae"

MAPPING = {
    "desktop-final.png": ("01_desktop_clean.png", "Clean HSCL1 live desktop after the Welcome Center (candidate 2026-11-09)"),
    "t0-launcher-default.png": ("03_app_launcher_kickoff.png", "Kickoff launcher with the merged HSCL1 sections (candidate 2026-11-09)"),
    "t1-dolphin.png": ("10_app_dolphin.png", "Dolphin in the HCS dark palette (candidate 2026-11-09)"),
    "t2-konsole-doctor.png": (
        "08_terminal_hscl_status_doctor.png",
        "hscl doctor in the guest: PASS theme HCSMidnight (from /etc/skel), Secure Boot honestly skipped (candidate 2026-11-09)",
    ),
    "t5-desktop-icons.png": ("15_desktop_icons.png", "Desktop icon labels legible on the dark wallpaper (candidate 2026-11-09)"),
}


def main() -> int:
    entries = json.loads(MANIFEST.read_text(encoding="utf-8"))
    by_name = {e["filename"]: e for e in entries}
    changed = 0
    for source, (target, description) in MAPPING.items():
        src = SRC / source
        if not src.is_file():
            print(f"skip {source}: not captured")
            continue
        dest = DST / target
        shutil.copy2(src, dest)
        entry = by_name.get(target)
        if entry is None:
            entry = {"filename": target, "size": [1280, 800]}
            entries.append(entry)
            by_name[target] = entry
        entry["description"] = description
        entry["bytes"] = dest.stat().st_size
        entry["timestamp"] = os.path.getmtime(dest)
        entry["source_iso"] = ISO
        changed += 1
        print(f"updated {target}")

    # Drop entries that no longer exist on disk.
    entries = [e for e in entries if (DST / e["filename"]).is_file()]
    MANIFEST.write_text(json.dumps(entries, indent=2) + "\n", encoding="utf-8")
    print(f"refreshed {changed} image(s), manifest entries {len(entries)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
