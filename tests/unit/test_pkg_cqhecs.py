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
    assert "python3 (>= 3.11)" in deps  # both repos need >= 3.11; the venv is built on demand
    # python3-venv is NOT installed in the base live image (checked 2026-11-07: no ensurepip), so a hard dependency would make
    # `dpkg -i` fail during the image build; it is recommended, and install-runtime reports it when missing
    assert "python3-venv" not in deps
    assert "python3-venv" in c.get("Recommends", "")
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
    assert '"$data_dir/venv"' in text  # user-level venv (no root helper needed), never the system python


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
def test_unknown_subcommand_is_a_usage_error():
    r = run("rm", "-rf", "/")
    assert r.returncode == 2


SHARE = PKG / "usr/share/hscl/cqhecs"


def test_requirements_are_fully_hash_pinned_and_use_no_other_index_or_editable_installs():
    lines = [l for l in (SHARE / "requirements-cp314.txt").read_text(encoding="utf-8").splitlines() if l.strip() and not l.startswith("#")]
    assert len(lines) >= 5
    for l in lines:
        assert re.search(r"--hash=sha256:[0-9a-f]{64}$", l), l
        assert re.match(r"^[A-Za-z0-9_.-]+(==\S+| @ https://github\.com/timfromhcs/CQ-HECS/releases/download/v5\.0\.0/\S+\.whl)", l), l
    text = " ".join(lines)
    assert "-e " not in text and "--index-url" not in text and "--extra-index-url" not in text and "git+" not in text
    assert any(l.startswith("cqhecs @ ") for l in lines)
    conf = dict(l.split("=", 1) for l in (SHARE / "runtime.conf").read_text(encoding="utf-8").split() if "=" in l)
    assert conf["python"] == "3.14" and conf["requirements"] == "requirements-cp314.txt"
    assert 1 < int(conf["download_bytes"]) < 200 * 1024 * 1024


def stub_python(tmp_path, version="3.14.3"):
    """A stand-in interpreter: logs every call, `-m venv DIR` fabricates DIR/bin/{python,cq-hecs}; no network, nothing real is installed."""
    log = tmp_path / "calls.log"
    stub = tmp_path / "python3"
    stub.write_text(f"""#!/usr/bin/env bash
echo "$0 $*" >> "{log.as_posix()}"
case "$1" in
  --version) echo "Python {version}" ;;
  -c)
    case "$2" in
      *ensurepip*) [ -n "${{STUB_NO_ENSUREPIP:-}}" ] && {{ echo "ModuleNotFoundError: No module named 'ensurepip'" >&2; exit 1; }} ;;
      *) echo "{'.'.join(version.split('.')[:2])}" ;;
    esac ;;
  -m)
    if [ "$2" = venv ]; then
      mkdir -p "$3/bin"
      cp "$0" "$3/bin/python"
      {{ echo '#!/usr/bin/env bash'; echo 'test "$1" = version || exit 2   # the real CLI has a version subcommand, not --version'; echo 'echo "cq-hecs 5.0.0"'; }} > "$3/bin/cq-hecs"
      chmod +x "$3/bin/cq-hecs"
    fi ;;
esac
exit 0
""", encoding="utf-8")
    return stub, log


def env_for(tmp_path, stub):
    return {
        "HSCL_CQHECS_VENV": (tmp_path / "venv").as_posix(),
        "HSCL_CQHECS_PYTHON": stub.as_posix(),
        "HSCL_CQHECS_SHARE": SHARE.as_posix(),
        "XDG_DATA_HOME": (tmp_path / "data").as_posix(),
    }


@needs_bash
def test_install_runtime_needs_an_explicit_yes_and_touches_nothing_without_it(tmp_path):
    stub, log = stub_python(tmp_path)
    r = run("install-runtime", env=env_for(tmp_path, stub))
    assert r.returncode == 6, r.stderr
    assert "61.5 MiB" in r.stdout  # the size is shown before anything happens
    assert not (tmp_path / "venv").exists()
    pip_or_venv = [l for l in (log.read_text() if log.exists() else "").splitlines() if " -m " in l]
    assert not pip_or_venv


@needs_bash
def test_install_runtime_with_yes_builds_a_venv_and_installs_only_from_the_hashed_file(tmp_path):
    stub, log = stub_python(tmp_path)
    r = run("install-runtime", "--yes", env=env_for(tmp_path, stub))
    assert r.returncode == 0, r.stdout + r.stderr
    calls = log.read_text().splitlines()
    venv = (tmp_path / "venv").as_posix()
    assert any(f"-m venv {venv}" in c for c in calls), calls
    pip = [c for c in calls if "-m pip install" in c]
    assert len(pip) == 1, calls
    for flag in ("--require-hashes", "--only-binary=:all:", "--no-input", "--disable-pip-version-check"):
        assert flag in pip[0], pip[0]
    assert f"-r {SHARE.as_posix()}/requirements-cp314.txt" in pip[0]
    assert "--index-url" not in pip[0] and "sudo" not in pip[0]
    d = run("doctor", "--json", env=env_for(tmp_path, stub))
    assert d.returncode == 0 and json.loads(d.stdout)["runtime"] == "ok"


@needs_bash
def test_install_runtime_refuses_a_python_the_pins_do_not_fit(tmp_path):
    stub, log = stub_python(tmp_path, version="3.12.3")
    r = run("install-runtime", "--yes", env=env_for(tmp_path, stub))
    assert r.returncode == 5
    assert "3.14" in r.stderr
    assert not (tmp_path / "venv").exists()


@needs_bash
def test_uninstall_runtime_removes_only_the_venv_and_needs_yes(tmp_path):
    stub, _ = stub_python(tmp_path)
    run("install-runtime", "--yes", env=env_for(tmp_path, stub))
    data = tmp_path / "data" / "hscl" / "cqhecs"
    data.mkdir(parents=True, exist_ok=True)
    (data / "my-research.json").write_text("{}", encoding="utf-8")
    assert run("uninstall-runtime", env=env_for(tmp_path, stub)).returncode == 6
    assert (tmp_path / "venv").exists()
    r = run("uninstall-runtime", "--yes", env=env_for(tmp_path, stub))
    assert r.returncode == 0, r.stderr
    assert not (tmp_path / "venv").exists()
    assert (data / "my-research.json").exists()  # user data is never removed


@needs_bash
def test_install_runtime_refuses_when_there_is_not_enough_free_disk_before_asking_or_downloading(tmp_path):
    share = tmp_path / "share"
    share.mkdir()
    for f in SHARE.iterdir():
        (share / f.name).write_text(f.read_text(encoding="utf-8"), encoding="utf-8")
    conf = (share / "runtime.conf").read_text(encoding="utf-8").splitlines()
    conf = [l for l in conf if not l.startswith("min_free_bytes=")] + ["min_free_bytes=900000000000000"]  # more than any disk
    (share / "runtime.conf").write_text("\n".join(conf) + "\n", encoding="utf-8")
    stub, log = stub_python(tmp_path)
    env = env_for(tmp_path, stub)
    env["HSCL_CQHECS_SHARE"] = share.as_posix()
    r = run("install-runtime", "--yes", env=env)
    assert r.returncode == 7, r.stdout + r.stderr
    assert "free" in r.stderr.lower() and "disk" in r.stderr.lower()
    assert not (tmp_path / "venv").exists()
    assert not [l for l in (log.read_text() if log.exists() else "").splitlines() if " -m " in l]


def test_runtime_conf_declares_a_realistic_minimum_free_space():
    conf = dict(l.split("=", 1) for l in (SHARE / "runtime.conf").read_text(encoding="utf-8").split() if "=" in l)
    # measured 2026-11-07: 61.5 MiB download, 269 MiB unpacked venv; require clearly more than both together
    assert 400 * 1024 * 1024 <= int(conf["min_free_bytes"]) <= 4 * 1024 * 1024 * 1024


@needs_bash
def test_install_runtime_explains_a_missing_python3_venv_and_changes_nothing(tmp_path):
    stub, log = stub_python(tmp_path)
    env = env_for(tmp_path, stub)
    env["STUB_NO_ENSUREPIP"] = "1"
    r = run("install-runtime", "--yes", env=env)
    assert r.returncode == 8, r.stdout + r.stderr
    assert "python3-venv" in r.stderr and "apt" in r.stderr
    assert not (tmp_path / "venv").exists()
    assert not [l for l in (log.read_text() if log.exists() else "").splitlines() if " -m venv" in l]
