import json
import subprocess
import sys
from pathlib import Path

BACKEND = str(Path(__file__).resolve().parents[2] / "backend")


def run(*args):
    return subprocess.run(
        [sys.executable, "-m", "hcseasymath", *args],
        capture_output=True, text=True, env={"PYTHONPATH": BACKEND, "PATH": "/usr/bin:/bin"},
    )


def test_doctor_json_reports_real_versions_and_honest_flags():
    out = run("doctor", "--json")
    assert out.returncode == 0
    d = json.loads(out.stdout)
    assert d["app"] == "hcseasymath"
    assert d["python"].startswith("3.")
    for pkg in ("sympy", "numpy", "scipy", "fastapi", "pydantic"):
        assert d["packages"][pkg]
    assert d["accelerators"] == {"hcsuda": "not_used"}
    assert d["listens"] is False
    assert d["isolated_worker"] in {"supported", "unsupported_platform"}


def test_doctor_does_not_open_a_listener_or_the_network():
    out = run("doctor")
    assert out.returncode == 0 and "hcseasymath" in out.stdout


def test_unknown_commands_fail_with_a_usage_error():
    out = run("rm", "-rf")
    assert out.returncode == 2
