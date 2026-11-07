"""scripts/stress_vm.sh: the stress/fault tool must refuse anywhere but a disposable VM.

Plan G1 (docs/superpowers/plans/2026-11-06-ai-api-updates-stress.md): stress-ng, fio and memtester
run only inside a guest started for that purpose, the evidence lands as JSON under artifacts/stress/,
a failing tool makes the script exit non-zero, and a missing tool is recorded instead of hidden.

The tools are faked on PATH: the real binaries are not installed on this dev host, and a real run
belongs in the disposable VM (docs/TESTING.md), never here.
"""

from __future__ import annotations

import json
import os
import stat
from pathlib import Path

import pytest

import shellutil

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts" / "stress_vm.sh"


def _fake_tool(directory: Path, name: str, exit_code: int = 0) -> Path:
    """A stand-in binary that records its argv and reports a chosen exit code."""
    directory.mkdir(parents=True, exist_ok=True)
    log = directory / f"{name}.argv"
    body = (
        "#!/bin/sh\n"
        f'printf "%s\\n" "$@" > "{log.as_posix()}"\n'
        f'printf "fake {name} output\\n"\n'
        f"exit {exit_code}\n"
    )
    path = directory / name
    path.write_bytes(body.encode())
    path.chmod(path.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
    return path


def _marker(tmp_path: Path) -> Path:
    marker = tmp_path / "etc" / "hscl-vm-marker"
    marker.parent.mkdir(parents=True, exist_ok=True)
    marker.write_text("HSCL1 disposable test VM\n")
    return marker


def _path_with(bindir: Path) -> str:
    """Fake tools first, then the real POSIX tools, then whatever the host has.

    `/usr/bin:/bin` must come before the inherited PATH: WSL appends the Windows PATH by default,
    where `python3` resolves to the Microsoft Store alias (it exits 49 with "Python was not found").
    """
    first = shellutil.to_bash_path(bindir)
    if shellutil.bash_kind() == "wsl":
        return f"{first}:/usr/bin:/bin"
    return f"{first}:/usr/bin:/bin{os.pathsep}{os.environ.get('PATH', '')}"


def _fake_df(directory: Path, free_kb: int) -> Path:
    """Deterministic free space: the real host disk made these tests flaky (WSL root had 2.9 GiB)."""
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / "df"
    lines = [
        "#!/bin/sh",
        "printf 'Filesystem 1024-blocks Used Available Capacity Mounted on\\n'",
        f"printf 'fake 999999999 1 {free_kb} 1%% /tmp\\n'",
    ]
    path.write_bytes(("\n".join(lines) + "\n").encode())
    path.chmod(path.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
    return path


def _run(tmp_path: Path, *, tools: tuple[str, ...] = ("stress-ng", "fio", "memtester"),
         env: dict | None = None, args: tuple = (),
         free_kb: int = 99_000_000) -> "tuple[int, str, Path]":
    bindir = tmp_path / "bin"
    for name in tools:
        _fake_tool(bindir, name)
    _fake_df(bindir, free_kb)
    out = tmp_path / "out"
    overrides = {
        "PATH": _path_with(bindir),
        "HSCL_IN_DISPOSABLE_VM": None,
        "HSCL_VM_MARKER": None,
    }
    overrides.update(env or {})
    r = shellutil.run_script(SCRIPT, "--out", out, *args, env_overrides=overrides)
    return r.returncode, (r.stdout + r.stderr), out


needs_shell = pytest.mark.skipif(not shellutil.usable(), reason="needs a POSIX shell (native bash or WSL)")


@needs_shell
def test_refuses_without_the_disposable_vm_flag(tmp_path):
    marker = _marker(tmp_path)
    code, text, out = _run(tmp_path, env={"HSCL_VM_MARKER": marker})
    assert code == 2, text
    assert "HSCL_IN_DISPOSABLE_VM" in text
    assert not (out / "summary.json").exists()


@needs_shell
def test_refuses_with_the_flag_but_no_marker_file(tmp_path):
    code, text, out = _run(tmp_path, env={"HSCL_IN_DISPOSABLE_VM": "1",
                                          "HSCL_VM_MARKER": tmp_path / "absent-marker"})
    assert code == 2, text
    assert "marker" in text.lower()
    assert not (out / "summary.json").exists()


@needs_shell
def test_refuses_a_different_flag_value(tmp_path):
    marker = _marker(tmp_path)
    code, text, _ = _run(tmp_path, env={"HSCL_IN_DISPOSABLE_VM": "yes", "HSCL_VM_MARKER": marker})
    assert code == 2, text


@needs_shell
def test_runs_all_three_tools_and_writes_evidence(tmp_path):
    marker = _marker(tmp_path)
    code, text, out = _run(tmp_path, env={"HSCL_IN_DISPOSABLE_VM": "1", "HSCL_VM_MARKER": marker})
    assert code == 0, text
    summary = json.loads((out / "summary.json").read_text())
    assert summary["disposable_vm"] is True
    assert summary["marker"] in (shellutil.to_bash_path(marker), str(marker))
    names = [t["name"] for t in summary["tests"]]
    assert names == ["stress-ng", "fio", "memtester"]
    assert all(t["status"] == "ok" and t["exit"] == 0 for t in summary["tests"]), summary["tests"]
    for t in summary["tests"]:
        assert Path(t["log"]).exists() or (ROOT / t["log"]).exists()
    assert summary["overall"] == "ok"


@needs_shell
def test_the_documented_arguments_reach_each_tool(tmp_path):
    marker = _marker(tmp_path)
    _run(tmp_path, env={"HSCL_IN_DISPOSABLE_VM": "1", "HSCL_VM_MARKER": marker})
    argv = {name: (tmp_path / "bin" / f"{name}.argv").read_text().split()
            for name in ("stress-ng", "fio", "memtester")}
    assert "--klog-check" in argv["stress-ng"] and "--metrics-brief" in argv["stress-ng"]
    assert "randrw" in argv["fio"] or any("randrw" in a for a in argv["fio"])
    assert "1G" in " ".join(argv["fio"]) or "1GiB" in " ".join(argv["fio"])
    assert argv["memtester"] == ["256M", "1"]


@needs_shell
def test_a_failing_tool_still_writes_the_summary_and_exits_nonzero(tmp_path):
    marker = _marker(tmp_path)
    bindir = tmp_path / "bin"
    for name in ("stress-ng", "memtester"):
        _fake_tool(bindir, name)
    _fake_tool(bindir, "fio", exit_code=1)
    _fake_df(bindir, 99_000_000)
    out = tmp_path / "out"
    r = shellutil.run_script(SCRIPT, "--out", out, env_overrides={
        "PATH": _path_with(bindir),
        "HSCL_IN_DISPOSABLE_VM": "1", "HSCL_VM_MARKER": marker,
    })
    assert r.returncode != 0
    summary = json.loads((out / "summary.json").read_text())
    status = {t["name"]: t["status"] for t in summary["tests"]}
    assert status["fio"] == "failed" and status["stress-ng"] == "ok"
    assert summary["overall"] == "failed"


@needs_shell
def test_a_missing_tool_is_recorded_and_fails(tmp_path):
    marker = _marker(tmp_path)
    code, text, out = _run(tmp_path, tools=("stress-ng", "fio"),
                           env={"HSCL_IN_DISPOSABLE_VM": "1", "HSCL_VM_MARKER": marker})
    assert code != 0, text
    summary = json.loads((out / "summary.json").read_text())
    status = {t["name"]: t["status"] for t in summary["tests"]}
    assert status["memtester"] == "missing", summary["tests"]


@needs_shell
def test_shellcheck_is_clean_on_the_script():
    if not shellutil.usable():
        pytest.skip("needs a POSIX shell")
    try:
        r = shellutil.run_command(["shellcheck", "-S", "warning", shellutil.to_bash_path(SCRIPT)])
    except FileNotFoundError:
        pytest.skip("shellcheck is not on PATH on this host (CI and `forge check` run it)")
    assert r.returncode == 0, r.stdout + r.stderr


@needs_shell
def test_refuses_when_the_target_filesystem_is_almost_full(tmp_path):
    """fio writes a 1 GiB file; below a 2 GiB floor the script refuses and writes no evidence."""
    marker = _marker(tmp_path)
    code, text, out = _run(tmp_path, free_kb=500_000,
                           env={"HSCL_IN_DISPOSABLE_VM": "1", "HSCL_VM_MARKER": marker})
    assert code == 2, text
    assert "2 GiB" in text
    assert not (out / "summary.json").exists()
