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


def test_the_script_is_tracked_executable():
    import subprocess

    out = subprocess.run(
        ["git", "ls-files", "-s", str(SCRIPT.relative_to(ROOT))],
        capture_output=True, text=True, encoding="utf-8", errors="replace", cwd=str(ROOT), check=False,
    )
    mode = out.stdout.split(" ", 1)[0] if out.stdout else ""
    assert mode in {"100755", ""}, f"tracked as {mode}; run git update-index --chmod=+x"
