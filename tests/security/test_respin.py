"""hscl-respin: refuses unsafe situations and captures only HSCL1-owned, secret-free files."""
import importlib.machinery
import importlib.util
import os
from pathlib import Path

import pytest

SRC = Path(__file__).resolve().parents[2] / "packages/debian/hscl-workshop/usr/lib/hscl/workshop/hscl-respin"
loader = importlib.machinery.SourceFileLoader("hscl_respin", str(SRC))
spec = importlib.util.spec_from_loader("hscl_respin", loader)
rs = importlib.util.module_from_spec(spec)
loader.exec_module(rs)

GB = 2**30


def test_only_live_sessions_are_accepted():
    rs.check_live("BOOT_IMAGE=/casper/vmlinuz quiet splash")            # grub boot image path
    rs.check_live("quiet splash", cdrom_has_squashfs=True)              # squashfs present under /cdrom
    for bad in ("root=/dev/vda2 ro quiet", "BOOT_IMAGE=/boot/vmlinuz-7.0.0 root=UUID=x", ""):
        with pytest.raises(rs.RespinError):
            rs.check_live(bad)


@pytest.mark.parametrize("fs", ["tmpfs", "ramfs", "overlay", "squashfs", "iso9660", "9p", "vfat", "ntfs", ""])
def test_unacceptable_output_filesystems_are_refused(fs):
    with pytest.raises(rs.RespinError, match="filesystem"):
        rs.check_target(fs, "/dev/vdb1", "/dev/sr0", 100 * GB, 10 * GB)


def test_output_on_boot_device_or_too_small_is_refused():
    with pytest.raises(rs.RespinError, match="boot device"):
        rs.check_target("ext4", "/dev/sr0", "/dev/sr0", 100 * GB, 10 * GB)
    with pytest.raises(rs.RespinError, match="free"):
        rs.check_target("ext4", "/dev/vdb1", "/dev/sr0", 5 * GB, 14 * GB)
    rs.check_target("ext4", "/dev/vdb1", "/dev/sr0", 50 * GB, 14 * GB)


def test_collect_takes_hscl_trees_and_skips_secrets_and_symlinks(tmp_path):
    def put(rel, data=b"x"):
        p = tmp_path / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(data)
    put("usr/share/hscl/brand/mark.svg")
    put("usr/share/hscl/workshop.token")
    put("usr/share/hscl/.bash_history")
    put("usr/share/plasma/wallpapers/org.hcs.hscl1.rain/contents/ui/main.qml")
    put("usr/share/wallpapers/HSCL1Midnight/metadata.json")
    put("usr/share/wallpapers/Kubuntu/metadata.json")
    put("usr/share/applications/hscl-handbook.desktop")
    put("usr/share/applications/firefox.desktop")
    put("etc/shadow")
    put("home/live/.ssh/id_ed25519")
    put("usr/lib/hscl/workshop/hooks/__pycache__/x.pyc")
    got = {p.as_posix() for p in rs.collect(tmp_path)}
    assert "usr/share/hscl/brand/mark.svg" in got
    assert "usr/share/plasma/wallpapers/org.hcs.hscl1.rain/contents/ui/main.qml" in got
    assert "usr/share/wallpapers/HSCL1Midnight/metadata.json" in got
    assert "usr/share/applications/hscl-handbook.desktop" in got
    for leaked in ("usr/share/hscl/workshop.token", "usr/share/hscl/.bash_history", "usr/share/wallpapers/Kubuntu/metadata.json",
                   "usr/share/applications/firefox.desktop", "etc/shadow", "home/live/.ssh/id_ed25519"):
        assert leaked not in got, leaked
    assert not any("__pycache__" in g or g.endswith(".pyc") for g in got)


@pytest.mark.skipif(os.name != "posix", reason="symlinks need POSIX")
def test_symlinks_are_not_followed(tmp_path):
    (tmp_path / "usr/share/hscl").mkdir(parents=True)
    (tmp_path / "secret.txt").write_text("s")
    (tmp_path / "usr/share/hscl/link").symlink_to(tmp_path / "secret.txt")
    (tmp_path / "usr/share/plasma").symlink_to(tmp_path)
    assert rs.collect(tmp_path) == []
