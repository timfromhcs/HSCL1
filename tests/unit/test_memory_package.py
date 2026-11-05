"""hscl-memory package files: bounded, conservative, and they never target the desktop shell."""
import re
from pathlib import Path

P = Path(__file__).resolve().parents[2] / "packages/debian/hscl-memory"


def text(rel):
    return (P / rel).read_text(encoding="utf-8")


def test_zram_is_half_of_ram_capped_and_zstd():
    z = text("etc/systemd/zram-generator.conf")
    assert "zram-size = min(ram / 2, 8192)" in z and "compression-algorithm = zstd" in z


def test_sysctl_values_are_the_two_documented_ones():
    keys = dict(l.split(" = ") for l in text("etc/sysctl.d/91-hscl-memory.conf").splitlines() if l and not l.startswith("#"))
    assert keys == {"vm.swappiness": "100", "vm.page-cluster": "0"}


def test_earlyoom_spares_the_desktop_and_prefers_ai_workloads():
    d = text("etc/systemd/system/earlyoom.service.d/90-hscl.conf")
    assert d.count("ExecStart=") == 2 and "ExecStart=\n" in d, "clears the packaged ExecStart first"
    avoid = re.search(r"--avoid '([^']+)'", d).group(1)
    prefer = re.search(r"--prefer '([^']+)'", d).group(1)
    for must_survive in ("plasmashell", "kwin_wayland", "sddm"):
        assert must_survive in avoid and must_survive not in prefer
    assert "llama-server" in prefer


def test_ai_slice_is_capped_below_100_percent():
    s = text("usr/lib/systemd/system/hscl-ai.slice")
    high = int(re.search(r"MemoryHigh=(\d+)%", s).group(1))
    mx = int(re.search(r"MemoryMax=(\d+)%", s).group(1))
    assert 0 < high < mx < 100


def test_control_file_depends_on_the_two_tools():
    c = text("DEBIAN/control")
    assert "earlyoom" in c and "systemd-zram-generator" in c and "not been benchmarked" in c
