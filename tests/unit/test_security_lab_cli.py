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
    res = subprocess.run([str(hscl_bin), "lab", "status"], capture_output=True, text=True, encoding="utf-8", errors="replace", cwd=str(ROOT))
    assert res.returncode == 0
    assert "lab folder:" in res.stdout
    assert "toolsets:" in res.stdout

    res_json = subprocess.run([str(hscl_bin), "--json", "lab", "status"], capture_output=True, text=True, encoding="utf-8", errors="replace", cwd=str(ROOT))
    assert res_json.returncode == 0
    data = json.loads(res_json.stdout)
    assert "podman_installed" in data
    assert "labs_root" in data
    assert "basic" in data.get("toolsets", [])
    assert data["defaults"]["network"] == "none"
    assert "cap-drop=ALL" in data["defaults"]["run_phase_capabilities"]


def test_lab_toolsets_text_and_json(hscl_bin: Path):
    res = subprocess.run([str(hscl_bin), "lab", "toolsets"], capture_output=True, text=True, encoding="utf-8", errors="replace", cwd=str(ROOT))
    assert res.returncode == 0
    assert "basic: nmap tcpdump tshark whois bind9-dnsutils netcat-openbsd" in res.stdout

    res_json = subprocess.run([str(hscl_bin), "--json", "lab", "toolsets"], capture_output=True, text=True, encoding="utf-8", errors="replace", cwd=str(ROOT))
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
        text=True, encoding="utf-8", errors="replace",
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
        res = subprocess.run([str(hscl_bin), "lab", *sub], capture_output=True, text=True, encoding="utf-8", errors="replace", cwd=str(ROOT))
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
            text=True, encoding="utf-8", errors="replace",
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
            text=True, encoding="utf-8", errors="replace",
            cwd=str(ROOT),
        )
        assert res_json.returncode == 1
        if have_podman:
            data = json.loads(res_json.stdout)
            assert data["executed"] is False
            assert data["required_attestation"] == REQUIRED_ATTESTATION
            assert REQUIRED_ATTESTATION in data["hint"]


def test_lab_toolset_subcommands_dry_run_and_attestation(hscl_bin: Path):
    res_list = subprocess.run([str(hscl_bin), "lab", "toolset", "list"], capture_output=True, text=True, encoding="utf-8", errors="replace", cwd=str(ROOT))
    assert res_list.returncode == 0
    assert "web:" in res_list.stdout
    assert "forensics:" in res_list.stdout

    # Install dry-run
    res_inst = subprocess.run(
        [str(hscl_bin), "--json", "lab", "toolset", "install", "web", "--dry-run"],
        capture_output=True,
        text=True, encoding="utf-8", errors="replace",
        cwd=str(ROOT),
    )
    assert res_inst.returncode == 0
    data = json.loads(res_inst.stdout)
    assert data["action"] == "install_toolset"
    assert data["toolset"] == "web"
    assert data["dry_run"] is True

    # Install without attestation and without dry-run must fail
    res_fail = subprocess.run(
        [str(hscl_bin), "lab", "toolset", "install", "web"],
        capture_output=True,
        text=True, encoding="utf-8", errors="replace",
        cwd=str(ROOT),
    )
    assert res_fail.returncode == 1
    assert "refused" in res_fail.stdout.lower()


def test_lab_container_subcommands_dry_run_and_attestation(hscl_bin: Path):
    res_list = subprocess.run([str(hscl_bin), "--json", "lab", "container", "list"], capture_output=True, text=True, encoding="utf-8", errors="replace", cwd=str(ROOT))
    assert res_list.returncode == 0
    data = json.loads(res_list.stdout)
    assert isinstance(data, list)

    # Shell dry-run
    res_shell = subprocess.run(
        [str(hscl_bin), "--json", "lab", "container", "shell", "testproj", "--dry-run"],
        capture_output=True,
        text=True, encoding="utf-8", errors="replace",
        cwd=str(ROOT),
    )
    assert res_shell.returncode == 0
    shell_data = json.loads(res_shell.stdout)
    assert shell_data["action"] == "container_shell"
    assert shell_data["dry_run"] is True

    # Stop dry-run
    res_stop = subprocess.run(
        [str(hscl_bin), "--json", "lab", "container", "stop", "testproj", "--dry-run"],
        capture_output=True,
        text=True, encoding="utf-8", errors="replace",
        cwd=str(ROOT),
    )
    assert res_stop.returncode == 0
    stop_data = json.loads(res_stop.stdout)
    assert stop_data["action"] == "container_stop"
    assert stop_data["dry_run"] is True


def test_lab_vm_subcommands_dry_run_and_attestation(hscl_bin: Path):
    res_list = subprocess.run([str(hscl_bin), "--json", "lab", "vm", "list"], capture_output=True, text=True, encoding="utf-8", errors="replace", cwd=str(ROOT))
    assert res_list.returncode == 0
    profiles = json.loads(res_list.stdout)
    assert isinstance(profiles, list)
    names = [p["name"] for p in profiles]
    assert "isolated" in names
    assert "bridged" in names
    assert "usb-passthrough" in names

    # Create dry-run
    res_create = subprocess.run(
        [str(hscl_bin), "--json", "lab", "vm", "create", "isolated", "--name", "sec-test", "--dry-run"],
        capture_output=True,
        text=True, encoding="utf-8", errors="replace",
        cwd=str(ROOT),
    )
    assert res_create.returncode == 0
    create_data = json.loads(res_create.stdout)
    assert create_data["action"] == "create_vm"
    assert create_data["name"] == "sec-test"
    assert create_data["dry_run"] is True

    # Launch dry-run
    res_launch = subprocess.run(
        [str(hscl_bin), "--json", "lab", "vm", "launch", "sec-test", "--dry-run"],
        capture_output=True,
        text=True, encoding="utf-8", errors="replace",
        cwd=str(ROOT),
    )
    assert res_launch.returncode == 0
    launch_data = json.loads(res_launch.stdout)
    assert launch_data["action"] == "launch_vm"
    assert launch_data["dry_run"] is True

