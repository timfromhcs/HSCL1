"""tests/shellutil.py: one way to run POSIX scripts on Linux, Git Bash and WSL (no silent skips)."""
import os
from pathlib import Path

import pytest

import shellutil


def test_bash_kind_is_known():
    assert shellutil.bash_kind() in ("native", "wsl", "none")


def test_to_bash_path_matches_the_detected_bash(tmp_path):
    p = tmp_path / "x.sh"
    p.write_text("#!/bin/sh\ntrue\n")
    got = shellutil.to_bash_path(p)
    if shellutil.bash_kind() == "wsl":
        assert got.startswith("/mnt/") and "\\" not in got
        assert got.lower().startswith("/mnt/" + str(tmp_path).split(":")[0].lower()[0] + "/")
    elif os.name == "nt":
        assert "\\" not in got and got[1:3] == ":/"
    else:
        assert got == str(p.resolve())


@pytest.mark.skipif(not shellutil.usable(), reason="needs a POSIX shell (native bash or WSL)")
def test_run_script_passes_overrides_and_arguments(tmp_path):
    s = tmp_path / "probe.sh"
    s.write_bytes(b'#!/bin/sh\nprintf "%s|%s" "$FOO" "$1"\n')
    r = shellutil.run_script(s, "baz", env_overrides={"FOO": "bar"})
    assert r.returncode == 0, r.stderr
    assert r.stdout == "bar|baz"


@pytest.mark.skipif(not shellutil.usable(), reason="needs a POSIX shell (native bash or WSL)")
def test_none_removes_a_variable(tmp_path):
    s = tmp_path / "probe.sh"
    s.write_bytes(b'#!/bin/sh\nprintf "%s" "${FOO-unset}"\n')
    r = shellutil.run_script(s, env_overrides={"FOO": None})
    assert r.stdout == "unset"


@pytest.mark.skipif(not shellutil.usable(), reason="needs a POSIX shell (native bash or WSL)")
def test_script_can_read_a_path_override(tmp_path):
    target = tmp_path / "data.txt"
    target.write_text("hello")
    s = tmp_path / "probe.sh"
    s.write_bytes(b'#!/bin/sh\ncat "$TARGET"\n')
    r = shellutil.run_script(s, env_overrides={"TARGET": target})
    assert r.stdout == "hello"


@pytest.mark.skipif(not shellutil.usable(), reason="needs a POSIX shell (native bash or WSL)")
def test_run_command_passes_overrides_to_a_plain_command():
    r = shellutil.run_command(["sh", "-c", 'printf "%s" "${FOO-unset}"'], env_overrides={"FOO": "bar"})
    assert r.returncode == 0, r.stderr
    assert r.stdout == "bar"


@pytest.mark.skipif(not shellutil.usable(), reason="needs a POSIX shell (native bash or WSL)")
def test_run_command_reports_a_missing_executable():
    with pytest.raises(FileNotFoundError):
        shellutil.run_command(["definitely-not-a-command-hscl1"])
