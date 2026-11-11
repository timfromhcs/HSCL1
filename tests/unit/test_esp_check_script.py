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


def run(esp: Path):
    return shellutil.run_script(SCRIPT, env_overrides={"HSCL_ESP": esp})


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
