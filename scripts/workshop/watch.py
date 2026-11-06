"""Live view of a VM screen during visual QA runs (owner request, plan P7.x).

Design: a background thread asks the VM for a screenshot about once per second and writes it atomically to WORKDIR/live.png
(plus live.txt with a status line). A small Tk window (`viewer.py`, separate process) shows that file. The viewer is optional
and never part of the test result: if it cannot start (no display, no Tk) or crashes, the run continues unchanged.

Enable/disable: environment HSCL_WATCH=1|0 (default: on when not running under CI), harness flag --no-watch sets it to 0.
"""
from __future__ import annotations

import os
import subprocess
import sys
import threading
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
INTERVAL_S = 1.0


def watch_enabled(env: dict | None = None) -> bool:
    env = os.environ if env is None else env
    v = env.get("HSCL_WATCH")
    if v is not None:
        return v.strip().lower() in ("1", "true", "yes", "on")
    return not env.get("CI")


def write_atomic(path: Path, data: bytes) -> None:
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_bytes(data)
    os.replace(tmp, path)


class Watcher:
    """Frame writer + viewer process for one VM. `vm` needs `screenshot_png()` and `running`."""

    def __init__(self, vm, workdir: Path, title: str, spawn_viewer: bool = True):
        self.vm, self.dir, self.title = vm, Path(workdir), title
        self.frame = self.dir / "live.png"
        self.status = self.dir / "live.txt"
        self._stop = threading.Event()
        self._thread = threading.Thread(target=self._loop, name=f"watch-{title}", daemon=True)
        self._viewer: subprocess.Popen | None = None
        self._spawn = spawn_viewer
        self._t0 = time.time()
        self.frames = 0

    def start(self) -> "Watcher":
        self._thread.start()
        if self._spawn:
            try:
                self._viewer = subprocess.Popen(
                    [sys.executable, str(HERE / "viewer.py"), str(self.frame), str(self.status), self.title],
                    stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            except Exception:  # noqa: BLE001  the viewer is a convenience, never a failure
                self._viewer = None
        return self

    def set_status(self, text: str) -> None:
        try:
            write_atomic(self.status, f"{text}\n".encode("utf-8"))
        except OSError:
            pass

    def _loop(self) -> None:
        while not self._stop.is_set():
            try:
                if getattr(self.vm, "running", True):
                    write_atomic(self.frame, self.vm.screenshot_png())
                    self.frames += 1
            except Exception:  # noqa: BLE001  a missed frame is fine
                pass
            self._stop.wait(INTERVAL_S)

    def stop(self) -> None:
        self._stop.set()
        if self._thread.is_alive():
            self._thread.join(timeout=5)
        if self._viewer and self._viewer.poll() is None:
            self._viewer.terminate()
