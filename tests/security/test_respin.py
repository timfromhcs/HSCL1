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
    put("usr/lib/hscl/workshop/hscl-respin")
    put("usr/bin/hscl")
    put("usr/bin/bash")
    put("home/live/.ssh/id_ed25519")
    put("usr/lib/hscl/workshop/hooks/__pycache__/x.pyc")
    got = {p.as_posix() for p in rs.collect(tmp_path)}
    assert "usr/share/hscl/brand/mark.svg" in got
    assert "usr/share/plasma/wallpapers/org.hcs.hscl1.rain/contents/ui/main.qml" in got
    assert "usr/share/wallpapers/HSCL1Midnight/metadata.json" in got
    assert "usr/share/applications/hscl-handbook.desktop" in got
    assert "usr/lib/hscl/workshop/hscl-respin" in got and "usr/bin/hscl" in got and "usr/bin/bash" not in got
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


def test_remaster_makes_the_squashfs_root_directory_root_owned():
    """VM finding 2026-11-06: `/` of installed systems was owned by uid 1000 because the overlay dirs were created as the build user.
    The script must create them as root, verify the rootfs root, and check the squashfs root owner after squashing."""
    from pathlib import Path
    root = Path(__file__).resolve().parents[2]
    sh = (root / "scripts/remaster-iso.sh").read_text(encoding="utf-8")
    assert 'sudo install -d -o root -g root -m 0755 "$ovl" "$ovl/up" "$ovl/wk" "$merged"' in sh
    assert "mkdir -p \"$ovl/up\"" not in sh
    assert 'unsquashfs -n -lls "$new_sq"' in sh and 'root/root' in sh
    vi = (root / "distro/live/verify-image.sh").read_text(encoding="utf-8")
    assert 'stat -c %u:%g:%a "$root"' in vi and '0:0:755' in vi


def test_the_squashfs_root_owner_check_does_not_close_the_pipe_early():
    """Seen 2026-11-06: `awk ... exit` made unsquashfs die with SIGPIPE (exit 141) and `set -o pipefail` aborted a finished build."""
    from pathlib import Path
    sh = (Path(__file__).resolve().parents[2] / "scripts/remaster-iso.sh").read_text(encoding="utf-8")
    line = next(l for l in sh.splitlines() if l.startswith("root_owner="))
    assert "exit" not in line and "head" not in line and "!done" in line


def test_rebuilt_initrd_is_mapped_and_proven_in_the_iso():
    """A missing -map once shipped the upstream boot splash with all gates green: the script must map the rebuilt initrd AND compare
    what the finished ISO contains."""
    from pathlib import Path
    s = (Path(__file__).resolve().parents[2] / "scripts" / "remaster-iso.sh").read_text(encoding="utf-8")
    assert '-map "$new_initrd" /casper/initrd' in s
    assert 'cmp -s "$work/iso-files/initrd.check" "$new_initrd"' in s
    assert s.index('-map "$new_initrd" /casper/initrd') < s.index('initrd.check')


def test_initrd_gets_boot_casper_default_only_while_building():
    """r2 dropped to the initramfs shell because the rebuilt initrd lacked default-boot-to-casper.conf. The snippet must be created before
    update-initramfs, removed right after (installed systems must not boot from casper) and required in the finished initrd."""
    from pathlib import Path
    s = (Path(__file__).resolve().parents[2] / "scripts" / "remaster-iso.sh").read_text(encoding="utf-8")
    make = s.index("default-boot-to-casper.conf\"")
    build = s.index("update-initramfs -c")
    drop = s.index('sudo rm -f "$conf_snip"')
    assert make < build < drop
    assert "conf/conf.d/default-boot-to-casper.conf; do" in s
    assert "export BOOT=casper" in s
