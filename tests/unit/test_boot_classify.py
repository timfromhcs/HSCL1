"""Boot failure classifier: real cases from the rebuild rounds r1-r4 plus a clean log that must not match anything."""
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))

import boot_classify as bc  # noqa: E402

R2_SHELL = """[    3.2] Loading, please wait...
Gave up waiting for root file system device.  Common problems:
 - Boot args (cat /proc/cmdline)
ALERT!  /dev/disk/by-label/HSCL1 does not exist.  Dropping to a shell!


BusyBox v1.37.0 (Ubuntu 1:1.37.0-7ubuntu1) built-in shell (ash)
Enter 'help' for a list of built-in commands.

(initramfs)
"""

CLEAN = """[    0.000000] Linux version 7.0.0-30-generic
[    2.1] casper: mounting /cdrom/casper/filesystem.squashfs
[    6.0] systemd[1]: Reached target Graphical Interface.
[    7.0] sddm[812]: Starting...
[    7.5] sddm[812]: Display server started.
"""


def names(text):
    return {f["class"] for f in bc.classify(text)}


def test_r2_initramfs_shell_is_recognised():
    found = bc.classify(R2_SHELL)
    assert found and found[0]["class"] == "initramfs-shell"
    assert "BOOT=casper" in found[0]["hint"]


def test_clean_boot_log_matches_nothing():
    assert bc.classify(CLEAN) == []


def test_each_known_failure_class_is_detected():
    cases = {
        "casper-no-medium": "Unable to find a medium containing a live file system",
        "kernel-panic": "Kernel panic - not syncing: VFS: Unable to mount root fs on unknown-block(0,0)",
        "init-failed": "No working init found.  Try passing init= option to kernel.",
        "emergency-mode": "You are in emergency mode. After logging in, type journalctl -xb",
        "dependency-failed": "[DEPEND] Dependency failed for Local File Systems.",
        "sddm-failed": "systemd[1]: Failed to start Simple Desktop Display Manager.",
        "session-starter-failed": "bash: /usr/libexec/start-kubuntu-live-env: No such file or directory",
        "plymouth-failed": "plymouthd: Failed to load theme hscl1-logo",
        "squashfs-error": "SQUASHFS error: Unable to read data cache entry [1234]",
        "oom": "Out of memory: Killed process 1234 (plasmashell)",
    }
    for cls, line in cases.items():
        assert cls in names(line), cls


def test_only_the_first_matching_line_per_class_is_reported():
    text = "(initramfs)\nnoise\n(initramfs)\n"
    found = [f for f in bc.classify(text) if f["class"] == "initramfs-shell"]
    assert len(found) == 1 and found[0]["line"] == 1


def test_windows_line_endings_do_not_break_matching():
    assert "initramfs-shell" in names(R2_SHELL.replace("\n", "\r\n"))


def test_hang_needs_silence_and_an_unchanged_screen():
    assert bc.detect_hang(300, 300)["class"] == "hang"
    assert bc.detect_hang(300, 10) is None   # screen still changing: not a hang
    assert bc.detect_hang(10, 300) is None   # serial still talking: not a hang


def test_cli_exit_codes(tmp_path):
    bad, good = tmp_path / "bad.log", tmp_path / "good.log"
    bad.write_text(R2_SHELL, encoding="utf-8")
    good.write_text(CLEAN, encoding="utf-8")
    run = lambda p: subprocess.run([sys.executable, str(ROOT / "scripts/boot_classify.py"), str(p)], capture_output=True, text=True)  # noqa: E731
    assert run(bad).returncode == 1
    assert run(good).returncode == 0
    assert run(tmp_path / "missing.log").returncode == 2
