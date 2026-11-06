"""Every tracked file that starts with a shebang is stored executable (100755) in git.

A Windows checkout reports no exec bits, so a clone on Linux (the builder copies the repo into WSL's ext4) lost them and
`scripts/remaster-iso.sh` failed with exit 126.
"""
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def test_shebang_files_are_executable_in_the_index():
    out = subprocess.run(["git", "ls-files", "-s", "-z"], cwd=ROOT, capture_output=True, check=True).stdout.decode("utf-8", "replace")
    bad = []
    for entry in filter(None, out.split("\0")):
        meta, path = entry.split("\t", 1)
        mode = meta.split()[0]
        p = ROOT / path
        if mode == "100644" and p.is_file() and p.read_bytes()[:2] == b"#!":
            bad.append(path)
    assert not bad, f"shebang files stored as 100644: {bad}"
