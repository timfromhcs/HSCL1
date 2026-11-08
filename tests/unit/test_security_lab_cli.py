"""Tests for `hscl lab` CLI execution, attestation gating, and status reporting."""
from __future__ import annotations

import json
import os
import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]


def find_hscl_binary() -> Path | None:
    debug_bin = ROOT / "target" / "debug" / ("hscl.exe" if os.name == "nt" else "hscl")
    if debug_bin.is_file():
        return debug_bin
    which = shutil.which("hscl")
    if which:
        return Path(which)
    return None


@pytest.fixture
def hscl_bin() -> Path:
    b = find_hscl_binary()
    if b is None:
        pytest.skip("hscl binary not compiled in target/debug")
    return b


VALID_IMAGE = "docker.io/kalilinux/kali-rolling@sha256:" + "a" * 64
REQUIRED_ATTESTATION = "I am authorized to test this target"


def test_lab_status_text_and_json(hscl_bin: Path):
    res = subprocess.run([str(hscl_bin), "lab", "status"], capture_output=True, text=True, cwd=str(ROOT))
    assert res.returncode == 0
    assert "lab folder:" in res.stdout
    assert "toolsets:" in res.stdout

    res_json = subprocess.run([str(hscl_bin), "--json", "lab", "status"], capture_output=True, text=True, cwd=str(ROOT))
    assert res_json.returncode == 0
    data = json.loads(res_json.stdout)
    assert "podman_installed" in data
    assert "labs_root" in data
    assert "basic" in data.get("toolsets", [])
    assert data["defaults"]["network"] == "none"
    assert "cap-drop=ALL" in data["defaults"]["run_phase_capabilities"]


def test_lab_toolsets_text_and_json(hscl_bin: Path):
    res = subprocess.run([str(hscl_bin), "lab", "toolsets"], capture_output=True, text=True, cwd=str(ROOT))
    assert res.returncode == 0
    assert "basic: nmap tcpdump tshark whois bind9-dnsutils netcat-openbsd" in res.stdout

    res_json = subprocess.run([str(hscl_bin), "--json", "lab", "toolsets"], capture_output=True, text=True, cwd=str(ROOT))
    assert res_json.returncode == 0
    data = json.loads(res_json.stdout)
    assert isinstance(data, list)
    basic = next((item for item in data if item.get("name") == "basic"), None)
    assert basic is not None
    assert "nmap" in basic["packages"]
    assert "tcpdump" in basic["packages"]


def test_lab_spec_generates_command_without_attestation(hscl_bin: Path):
    res = subprocess.run(
        [str(hscl_bin), "lab", "spec", "--project", "testproj", "--image", VALID_IMAGE],
        capture_output=True,
        text=True,
        cwd=str(ROOT),
    )
    assert res.returncode == 0
    assert "podman run" in res.stdout
    assert "--name hscl-lab-testproj" in res.stdout
    assert "--cap-drop=ALL" in res.stdout
    assert "--security-opt=no-new-privileges" in res.stdout
    assert "--network=none" in res.stdout
    assert VALID_IMAGE in res.stdout


def test_lab_subcommands_fail_closed_without_attestation(hscl_bin: Path):
    have_podman = shutil.which("podman") is not None

    subcommands = [
        ["run", "--project", "testproj", "--image", VALID_IMAGE],
        ["install", "--project", "testproj", "--image", VALID_IMAGE, "--toolset", "basic"],
        ["commit", "--project", "testproj"],
        ["destroy", "--project", "testproj"],
    ]

    for sub in subcommands:
        res = subprocess.run([str(hscl_bin), "lab", *sub], capture_output=True, text=True, cwd=str(ROOT))
        assert res.returncode == 1
        output = res.stdout + res.stderr
        if have_podman:
            assert "refused: lab execution requires the attestation" in output
            assert REQUIRED_ATTESTATION in output
        else:
            assert "podman is not installed" in output

        # Test with wrong attestation
        res_wrong = subprocess.run(
            [str(hscl_bin), "lab", *sub, "--yes=yes"],
            capture_output=True,
            text=True,
            cwd=str(ROOT),
        )
        assert res_wrong.returncode == 1
        output_wrong = res_wrong.stdout + res_wrong.stderr
        if have_podman:
            assert "refused: lab execution requires the attestation" in output_wrong
        else:
            assert "podman is not installed" in output_wrong

        # Test with --json output
        res_json = subprocess.run(
            [str(hscl_bin), "--json", "lab", *sub],
            capture_output=True,
            text=True,
            cwd=str(ROOT),
        )
        assert res_json.returncode == 1
        if have_podman:
            data = json.loads(res_json.stdout)
            assert data["executed"] is False
            assert data["required_attestation"] == REQUIRED_ATTESTATION
            assert REQUIRED_ATTESTATION in data["hint"]
