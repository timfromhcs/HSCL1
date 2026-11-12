"""Run the ESP guard for real: an empty ESP must fail, a loader must pass.

The image gate only proves the script and its wiring exist. These tests execute it under `sh` with `HSCL_ESP`
pointed at throw-away directories, so the negative path (the one that protects users) is actually exercised and
not just asserted in prose.
"""

from pathlib import Path

import pytest

import shellutil

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "packages/debian/hscl-branding/usr/bin/hscl-verify-esp"

pytestmark = pytest.mark.skipif(not shellutil.usable(), reason="needs a POSIX shell (native bash or WSL)")


def run(esp: Path, grub: Path | None = None, boot: Path | None = None):
    """Run the guard with *every* absolute path it reads redirected.

    In production the script runs inside the target chroot, so `/boot/efi`, `/boot/grub` and `/boot` are the
    target's own. A test on a normal host must redirect all three: the CI runner has its own
    `/boot/grub/i386-pc`, so leaving `HSCL_GRUB` unset made the legacy branch fire and the empty-ESP test pass
    for the wrong reason. CI on PR #62 caught exactly that.
    """
    esp = Path(esp)
    neutral = esp.parent / (esp.name + "-nogrub")
    neutral.mkdir(parents=True, exist_ok=True)
    return shellutil.run_script(
        SCRIPT,
        env_overrides={
            "HSCL_ESP": esp,
            "HSCL_GRUB": grub if grub is not None else neutral,
            "HSCL_BOOT": boot if boot is not None else neutral,
        },
    )


def test_an_empty_esp_fails(tmp_path):
    result = shellutil.skip_if_shell_broken(run(tmp_path))
    assert result.returncode == 1, (result.stdout, result.stderr)
    assert "did not populate the EFI system partition" in result.stderr


def test_a_missing_efi_directory_fails(tmp_path):
    (tmp_path / "boot").mkdir()
    result = shellutil.skip_if_shell_broken(run(tmp_path))
    assert result.returncode == 1
    assert "missing" in result.stderr


def test_the_removable_loader_passes(tmp_path):
    (tmp_path / "EFI" / "BOOT").mkdir(parents=True)
    (tmp_path / "EFI" / "BOOT" / "BOOTX64.EFI").write_bytes(b"x")
    result = shellutil.skip_if_shell_broken(run(tmp_path))
    assert result.returncode == 0, result.stderr
    assert "BOOTX64.EFI" in result.stdout


def test_a_vendor_loader_passes(tmp_path):
    (tmp_path / "EFI" / "ubuntu").mkdir(parents=True)
    (tmp_path / "EFI" / "ubuntu" / "grubx64.efi").write_bytes(b"x")
    result = shellutil.skip_if_shell_broken(run(tmp_path))
    assert result.returncode == 0, result.stderr
    assert "grubx64.efi" in result.stdout


def test_an_efi_directory_without_a_loader_fails(tmp_path):
    (tmp_path / "EFI" / "ubuntu").mkdir(parents=True)
    (tmp_path / "EFI" / "ubuntu" / "grub.cfg").write_text("x")
    result = shellutil.skip_if_shell_broken(run(tmp_path))
    assert result.returncode == 1
    assert "would not boot" in result.stderr


def test_a_legacy_install_is_not_failed_for_having_no_esp(tmp_path):
    """`grub-install --target=i386-pc` writes /boot/grub/i386-pc and no ESP, by design.

    The ISO also boots in BIOS mode, so failing such an install would turn "you booted the ISO in BIOS mode"
    into "the installation is broken" - a false alarm that also hides the real UEFI case.
    """
    grub = tmp_path / "grub"
    (grub / "i386-pc").mkdir(parents=True)
    result = shellutil.skip_if_shell_broken(run(tmp_path / "esp", grub=grub))
    assert result.returncode == 0, result.stderr
    assert "legacy (BIOS) install" in result.stdout


def test_the_legacy_branch_needs_the_i386_pc_directory(tmp_path):
    """A grub directory without i386-pc is a UEFI install with a missing loader, not a legacy one."""
    grub = tmp_path / "grub"
    (grub / "x86_64-efi").mkdir(parents=True)
    result = shellutil.skip_if_shell_broken(run(tmp_path / "esp", grub=grub))
    assert result.returncode == 1
    assert "did not populate the EFI system partition" in result.stderr
