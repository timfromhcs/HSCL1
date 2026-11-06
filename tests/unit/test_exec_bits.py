"""Every file that starts with a shebang is stored executable (100755) in git - tracked AND not yet tracked.

A Windows checkout reports no exec bits, so a clone on Linux (the builder copies the repo into WSL's ext4) lost them and
`scripts/remaster-iso.sh` failed with exit 126. Untracked files are included because the gate used to pass locally on a new
script and fail in CI after the commit (three times on 2026-11-06): an untracked shebang file has no mode yet, so it must be
added with `git add --chmod=+x PATH` (or `git update-index --chmod=+x PATH` after `git add`) before the gate can pass.
"""
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def _git(root: Path, *args: str) -> str:
    return subprocess.run(["git", *args], cwd=root, capture_output=True, check=True).stdout.decode("utf-8", "replace")


def shebang_violations(root: Path) -> list[str]:
    bad = []
    for entry in filter(None, _git(root, "ls-files", "-s", "-z").split("\0")):
        meta, path = entry.split("\t", 1)
        p = root / path
        if meta.split()[0] == "100644" and p.is_file() and p.read_bytes()[:2] == b"#!":
            bad.append(f"{path} (tracked as 100644)")
    for path in filter(None, _git(root, "ls-files", "--others", "--exclude-standard", "-z").split("\0")):
        p = root / path
        if p.is_file() and p.read_bytes()[:2] == b"#!":
            bad.append(f"{path} (untracked: add it with --chmod=+x)")
    return bad


def test_shebang_files_are_executable_in_the_index():
    bad = shebang_violations(ROOT)
    assert not bad, f"shebang files without the executable bit: {bad}"


def _repo(tmp_path: Path) -> Path:
    _git(tmp_path, "init", "-q")
    _git(tmp_path, "config", "user.email", "t@example.invalid")
    _git(tmp_path, "config", "user.name", "t")
    return tmp_path


def test_checker_flags_untracked_tracked_644_and_accepts_755(tmp_path):
    repo = _repo(tmp_path)
    (repo / "plain.py").write_text("x = 1\n", encoding="utf-8")
    (repo / "ok.py").write_text("#!/usr/bin/env python3\n", encoding="utf-8")
    (repo / "bad.py").write_text("#!/usr/bin/env python3\n", encoding="utf-8")
    (repo / "new.py").write_text("#!/usr/bin/env python3\n", encoding="utf-8")
    _git(repo, "add", "plain.py", "bad.py")
    _git(repo, "add", "--chmod=+x", "ok.py")
    bad = shebang_violations(repo)
    assert any(b.startswith("bad.py") and "100644" in b for b in bad)
    assert any(b.startswith("new.py") and "untracked" in b for b in bad)
    assert not any(b.startswith(("ok.py", "plain.py")) for b in bad)
