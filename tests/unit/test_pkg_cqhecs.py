"""hscl-cqhecs (Genesis plan B1): a small app shell, no runtime, no network, no service. Rules from AGENTS_HCS_GENESIS.md 2.1-2.5."""
import json
import os
import re
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
PKG = ROOT / "packages/debian/hscl-cqhecs"
LAUNCHER = PKG / "usr/bin/hscl-cqhecs"


def control():
    out = {}
    for line in (PKG / "DEBIAN/control").read_text(encoding="utf-8").splitlines():
        if line and not line.startswith(" ") and ":" in line:
            k, v = line.split(":", 1)
            out[k.strip()] = v.strip()
    return out


def _bash():
    """On Windows `bash` is usually the WSL launcher, which does not understand E:/ paths; Git-Bash does."""
    if not sys.platform.startswith("win"):
        return "bash"
    p = Path(os.environ.get("ProgramFiles", "C:/Program Files")) / "Git/bin/bash.exe"
    return str(p) if p.exists() else None


BASH = _bash()
needs_bash = pytest.mark.skipif(BASH is None, reason="no Git-Bash on this Windows host (Linux CI always runs these)")


def run(*args, env=None):
    e = {**os.environ, **(env or {})}
    return subprocess.run([BASH, LAUNCHER.as_posix(), *args], capture_output=True, text=True, env=e, timeout=30)


def test_control_names_the_package_and_needs_a_modern_python_but_no_compiler():
    c = control()
    assert c["Package"] == "hscl-cqhecs"
    assert c["Architecture"] == "all"
    deps = c.get("Depends", "")
    assert "python3 (>= 3.11)" in deps and "python3-venv" in deps  # both repos need >= 3.11; the venv is built on demand
    assert "build-essential" not in deps and "gcc" not in deps  # wheels exist for cp314, no compiler needed


def test_no_maintainer_script_touches_the_network_or_starts_anything():
    for name in ("preinst", "postinst", "prerm", "postrm"):
        f = PKG / "DEBIAN" / name
        if not f.exists():
            continue
        text = f.read_text(encoding="utf-8")
        for bad in ("curl", "wget", "pip ", "pip3", "apt-get", "apt install", "git clone", "systemctl enable", "systemctl start", "nc "):
            assert bad not in text, f"{name} contains {bad!r}"


def test_payload_has_no_weights_wheels_or_large_files_and_no_autostart_or_service():
    for p in PKG.rglob("*"):
        if not p.is_file():
            continue
        rel = p.relative_to(PKG).as_posix()
        assert p.suffix not in {".whl", ".gguf", ".safetensors", ".bin", ".so"}, rel
        assert p.stat().st_size < 256 * 1024, rel
        assert "etc/xdg/autostart" not in rel and "/systemd/" not in rel, rel


def test_desktop_entry_launches_the_launcher_and_is_not_hidden():
    d = PKG / "usr/share/applications/hscl-cqhecs.desktop"
    e = dict(line.split("=", 1) for line in d.read_text(encoding="utf-8").splitlines() if "=" in line and not line.startswith("#"))
    assert e["Type"] == "Application"
    assert e["Name"] == "CQ-HECS Studio"
    assert e["Exec"].startswith("hscl-cqhecs ")
    assert "Science" in e["Categories"]
    assert e.get("Hidden", "false") != "true" and e.get("NoDisplay", "false") != "true"


def test_launcher_is_strict_and_has_no_eval_or_arbitrary_exec():
    text = LAUNCHER.read_text(encoding="utf-8")
    assert re.search(r"^set -[a-zA-Z]*e[a-zA-Z]*u|^set -Eeuo pipefail", text, re.M)
    assert not re.search(r"\beval\b", text)
    assert "sudo" not in text
    assert "/opt/hscl/venvs/cqhecs" in text  # fixed default location, never the system python


@needs_bash
def test_doctor_reports_a_missing_runtime_honestly(tmp_path):
    nope, data = (tmp_path / "nope").as_posix(), (tmp_path / "data").as_posix()  # POSIX spelling: Git-Bash on Windows eats backslashes
    r = run("doctor", "--json", env={"HSCL_CQHECS_VENV": nope, "XDG_DATA_HOME": data})
    assert r.returncode == 3, r.stderr
    j = json.loads(r.stdout)
    assert j["runtime"] == "missing"
    assert j["venv"] == nope
    assert j["data_dir"] == f"{data}/hscl/cqhecs"
    assert j["network"] == "not used"


@needs_bash
def test_run_without_runtime_refuses_and_does_not_fall_back_to_system_python(tmp_path):
    r = run("run", "--", "--version", env={"HSCL_CQHECS_VENV": (tmp_path / "nope").as_posix()})
    assert r.returncode == 3
    assert "runtime" in r.stderr.lower() and "not installed" in r.stderr.lower()


@needs_bash
def test_install_runtime_is_not_pretended():
    r = run("install-runtime")
    assert r.returncode == 2
    assert "not implemented" in r.stderr.lower()


@needs_bash
def test_unknown_subcommand_is_a_usage_error():
    r = run("rm", "-rf", "/")
    assert r.returncode == 2
