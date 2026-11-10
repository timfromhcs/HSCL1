"""A half-started WSL must skip the test, not fail it - and a real script failure must still fail."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tests"))

import shellutil  # noqa: E402


def _done(rc: int, out: str = "", err: str = "") -> subprocess.CompletedProcess:
    return subprocess.CompletedProcess(args=["bash"], returncode=rc, stdout=out, stderr=err)


def test_a_launcher_failure_becomes_a_skip():
    with pytest.raises(pytest.skip.Exception):
        shellutil.skip_if_shell_broken(_done(1, err="WslRegisterDistribution failed with error: 0x8007019e"))


def test_a_utf16_launcher_message_becomes_a_skip():
    """WSL writes its own errors as UTF-16 into the pipe; measured 2026-11-10 in a gate run."""
    german = "Ein Verbindungsversuch ist fehlgeschlagen. Siehe https://github.com/microsoft/WSL/issues"
    utf16 = german.encode("utf-16-le").decode("latin-1")
    with pytest.raises(pytest.skip.Exception):
        shellutil.skip_if_shell_broken(_done(0, out=utf16))


@pytest.mark.parametrize("marker", ["Catastrophic failure", "UtilBindVsock", "getaddrinfo", "wsl: "])
def test_the_known_launcher_markers_all_skip(marker):
    with pytest.raises(pytest.skip.Exception):
        shellutil.skip_if_shell_broken(_done(1, err=f"{marker} something"))


def test_a_real_script_failure_still_fails():
    result = shellutil.skip_if_shell_broken(_done(2, err="assertion: wrong language picked"))
    assert result.returncode == 2


def test_success_is_untouched():
    result = shellutil.skip_if_shell_broken(_done(0, out="de"))
    assert result.returncode == 0 and result.stdout == "de"
