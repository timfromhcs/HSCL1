"""The installer wrapper: software rendering, no drkonqi, and a bounded restart on a signal death.

Measured 2026-11-11 on `HSCL1-rc4`, 10 starts in one boot, five with the current wrapper and five with
`QT_QPA_PLATFORM=xcb`: both series ended 4 up / 1 dead (`artifacts/boot-installer-probe/p3-summary.png`). The
platform plugin is therefore not the cause, and `QT_QUICK_BACKEND=software` alone does not remove the fault -
the installer dies in about one start in five while it builds its first page. The journal is always the same:
`KCrash: appFilePath points to nullptr`, `KCrash: Application 'unknown' crashing`, drkonqi fails
(`org.freedesktop.systemd1 exited with status 1`), then `Killed calamares -D8`.

The wrapper keeps the software-render settings, stops KCrash from spawning drkonqi, and restarts the installer
when it dies from a signal - a normal exit is passed through unchanged, and it gives up after three tries.
"""

from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
WRAPPER = ROOT / "packages/debian/hscl-branding/usr/bin/hscl-calamares"
HOOK = ROOT / "distro/live/hooks/010-hscl-defaults.sh"
GATE = ROOT / "distro/live/verify-image.sh"


def test_the_wrapper_forces_software_rendering_and_delegates():
    text = WRAPPER.read_text(encoding="utf-8")
    assert "export QT_QUICK_BACKEND=software" in text
    assert "export LIBGL_ALWAYS_SOFTWARE=1" in text
    assert "/usr/bin/calamares-launch-normal" in text, "it must delegate, not reimplement the launcher"
    assert "exec /usr/bin/calamares" not in text, "an exec would lose the exit code and the restart"


def test_the_wrapper_stops_drkonqi_from_covering_the_wizard():
    text = WRAPPER.read_text(encoding="utf-8")
    assert "export KCRASH_DUMP_ONLY=1" in text


@pytest.mark.parametrize("signal_rc", ["134", "137", "139"])
def test_signal_deaths_are_retried(signal_rc):
    text = WRAPPER.read_text(encoding="utf-8")
    assert signal_rc in text, f"exit {signal_rc} (signal death) must be retried"


def test_a_normal_exit_is_passed_through_and_the_retries_are_bounded():
    text = WRAPPER.read_text(encoding="utf-8")
    assert 'if [ "$rc" -eq 0 ]; then' in text
    assert 'exit "$rc"' in text
    assert "while [ \"$attempt\" -le 3 ]" in text, "the restart must be bounded"


def test_the_single_instance_lock_is_retried():
    """rc5's probe: a restart that arrived too early got exit 87 ('another instance running') and gave up."""
    text = WRAPPER.read_text(encoding="utf-8")
    assert "    87)" in text
    assert "single-instance lock" in text
    assert "sleep 5" in text


def test_only_an_early_crash_is_restarted():
    """A crash after the first minute may have written to the disk; restarting over that would be worse."""
    text = WRAPPER.read_text(encoding="utf-8")
    assert 'started=$(date +%s)' in text
    assert 'elapsed=$(( $(date +%s) - started ))' in text
    assert '[ "$elapsed" -le 60 ]' in text
    assert "not restarting an install in progress" in text


def test_the_desktop_entry_is_patched_to_the_wrapper():
    text = HOOK.read_text(encoding="utf-8")
    assert "s#^Exec=sudo /usr/bin/calamares-launch-normal$#Exec=sudo /usr/bin/hscl-calamares#" in text


def test_the_image_gate_checks_the_wrapper():
    text = GATE.read_text(encoding="utf-8")
    assert "installer runs the software-render wrapper" in text
    assert "installer wrapper exists" in text
    assert "KCRASH_DUMP_ONLY" in text, "the gate should prove the wrapper is the one with the restart logic"


def test_the_wrapper_is_executable_in_the_index():
    """The repo has a gate for shebang files; this keeps the new one from tripping it."""
    import subprocess

    out = subprocess.run(
        ["git", "ls-files", "-s", str(WRAPPER.relative_to(ROOT))],
        capture_output=True, text=True, encoding="utf-8", errors="replace", cwd=str(ROOT), check=False,
    )
    mode = out.stdout.split(" ", 1)[0] if out.stdout else ""
    assert mode in {"100755", ""}, f"tracked as {mode}; run git update-index --chmod=+x"
