"""Live view of VM runs: enable rules, atomic frame writing, resilience (plan P7.x)."""
import os
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts" / "workshop"))
sys.path.insert(0, str(ROOT / "scripts"))

import watch  # noqa: E402


def test_enable_rules():
    assert watch.watch_enabled({}) is True
    assert watch.watch_enabled({"CI": "true"}) is False
    assert watch.watch_enabled({"CI": "true", "HSCL_WATCH": "1"}) is True
    assert watch.watch_enabled({"HSCL_WATCH": "0"}) is False
    assert watch.watch_enabled({"HSCL_WATCH": "off"}) is False


class FakeVm:
    running = True

    def __init__(self):
        self.n = 0

    def screenshot_png(self):
        self.n += 1
        return b"PNGDATA" + str(self.n).encode()


class BrokenVm:
    running = True

    def screenshot_png(self):
        raise RuntimeError("qmp gone")


def test_writer_updates_frame_and_status(tmp_path, monkeypatch):
    monkeypatch.setattr(watch, "INTERVAL_S", 0.05)
    w = watch.Watcher(FakeVm(), tmp_path, "t", spawn_viewer=False).start()
    w.set_status("step one")
    time.sleep(0.4)
    w.stop()
    assert (tmp_path / "live.png").read_bytes().startswith(b"PNGDATA")
    assert (tmp_path / "live.txt").read_text() == "step one\n"
    assert w.frames >= 2
    assert not list(tmp_path.glob("*.tmp"))


def test_failing_vm_never_raises(tmp_path, monkeypatch):
    monkeypatch.setattr(watch, "INTERVAL_S", 0.05)
    w = watch.Watcher(BrokenVm(), tmp_path, "t", spawn_viewer=False).start()
    time.sleep(0.2)
    w.stop()
    assert w.frames == 0


def test_no_watch_flag_is_consumed(monkeypatch):
    monkeypatch.setattr(sys, "argv", ["x", "a", "--no-watch", "b"])
    monkeypatch.delenv("HSCL_WATCH", raising=False)
    import importlib
    import vm as vmmod
    importlib.reload(vmmod)
    assert sys.argv == ["x", "a", "b"]
    assert os.environ["HSCL_WATCH"] == "0"
    monkeypatch.delenv("HSCL_WATCH", raising=False)
