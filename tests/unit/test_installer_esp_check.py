"""The installer must refuse to report success when the EFI partition is empty.

Measured 2026-11-11 on an rc10 install: Calamares said "All done", the target had the kernel and `/boot/grub`, but
the ESP (`vda1`, FAT32) and `/boot/efi` inside the new root were **empty** - the firmware fell back to its UEFI
shell and the system never booted. The check runs as a shellprocess right after the `bootloader` module, inside the
target chroot, and fails the install instead of hiding the problem.
"""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "packages/debian/hscl-branding/usr/bin/hscl-verify-esp"
CONF = ROOT / "packages/debian/hscl-branding/etc/calamares/modules/hscl_verify_esp.conf"
HOOK = ROOT / "distro/live/hooks/010-hscl-defaults.sh"
GATE = ROOT / "distro/live/verify-image.sh"


def test_the_script_fails_without_an_efi_loader():
    text = SCRIPT.read_text(encoding="utf-8")
    assert "EFI/BOOT/BOOTX64.EFI" in text
    assert "grubx64.efi" in text
    assert "exit 1" in text
    assert "would not boot" in text


def test_the_module_runs_in_the_target_after_the_bootloader():
    conf = CONF.read_text(encoding="utf-8")
    assert "dontChroot: false" in conf, "the check must inspect the target, not the live system"
    assert '"/usr/bin/hscl-verify-esp"' in conf
    hook = HOOK.read_text(encoding="utf-8")
    assert "s|^  - bootloader$|  - bootloader\\n  - shellprocess@hscl_verify_esp|" in hook
    assert "hscl_verify_esp.conf" in hook


def test_the_image_gate_checks_the_wiring():
    text = GATE.read_text(encoding="utf-8")
    assert "installer verifies the ESP after the bootloader" in text
    assert "ESP check follows the bootloader module" in text


def test_the_failure_path_reports_what_discriminates_the_cause():
    """The cause is unknown (Q-66), so the failure must name the state, not only the symptom.

    "no loader" alone cannot distinguish "the ESP was never mounted at /boot/efi" from "the bootloader module
    reported success and wrote nothing". The guard prints both, so the next recurrence is diagnosable without
    another multi-boot probe.
    """
    text = SCRIPT.read_text(encoding="utf-8")
    assert "diagnose()" in text
    # called from both failure exits, not only from the last one
    calls = [line for line in text.splitlines() if line.strip() == "diagnose"]
    assert len(calls) == 2, "both failure paths must call diagnose"
    for probe in ("findmnt", "/proc/mounts", "ls -la \"$efi\"", "/boot/grub"):
        assert probe in text, f"the diagnostics must include {probe}"
    assert "Q-66" in text, "name the open queue row so the log is traceable"


def test_the_script_stays_posix_sh():
    """It runs in the target chroot under Calamares; bash may not be the interpreter there."""
    text = SCRIPT.read_text(encoding="utf-8")
    assert text.splitlines()[0] == "#!/bin/sh"
    for bashism in ("[[", "function ", "local ", "declare "):
        assert bashism not in text, f"bashism {bashism!r} in a /bin/sh script"


def test_the_script_is_tracked_executable():
    import subprocess

    out = subprocess.run(
        ["git", "ls-files", "-s", str(SCRIPT.relative_to(ROOT))],
        capture_output=True, text=True, encoding="utf-8", errors="replace", cwd=str(ROOT), check=False,
    )
    mode = out.stdout.split(" ", 1)[0] if out.stdout else ""
    assert mode in {"100755", ""}, f"tracked as {mode}; run git update-index --chmod=+x"
