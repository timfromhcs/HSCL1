"""Every `hscl` invocation in the 12-track guest script must still exist in the CLI.

The tracks are the deep verification of a candidate, so a renamed subcommand there produces a false
failure at the end of a 20-minute VM run. This parses the script and asks the same binary the docs gate
uses whether each command resolves.
"""

from __future__ import annotations

import re
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts/dev/verify_in_guest_tracks.py"
BIN = ROOT / "target" / "debug" / ("hscl.exe" if (ROOT / "target/debug/hscl.exe").exists() else "hscl")

INVOCATION = re.compile(r"/usr/bin/hscl((?:\s+(?:--json|[a-z][a-z0-9-]*)){1,4})")


def commands() -> list[list[str]]:
    """Unique command paths as written in the script (longest four words, literals included)."""
    found: list[tuple[str, ...]] = []
    for match in INVOCATION.finditer(SCRIPT.read_text(encoding="utf-8")):
        words = tuple(w for w in match.group(1).split() if w != "--json")
        if words:
            found.append(words)
    return [list(c) for c in dict.fromkeys(found)]


@pytest.mark.skipif(not BIN.exists(), reason="build the CLI first (cargo build)")
def test_every_track_command_resolves():
    assert BIN.exists(), BIN
    bad = []
    for cmd in commands():
        for cut in range(len(cmd), 0, -1):
            candidate = cmd[:cut]
            res = subprocess.run([str(BIN), *candidate, "--help"], capture_output=True, text=True, timeout=30)
            if res.returncode == 0:
                break
        else:
            bad.append("hscl " + " ".join(cmd))
    assert not bad, "commands in the track script that no longer exist: " + ", ".join(bad)


def test_the_script_mentions_all_twelve_tracks():
    text = SCRIPT.read_text(encoding="utf-8")
    for track in ["Track L", "Track K", "Track C", "Track B", "Track S", "Track D",
                  "Track R", "Track DEV", "Track SYS", "Track APP", "Track AI", "Track LAB"]:
        assert track in text, f"missing {track}"
