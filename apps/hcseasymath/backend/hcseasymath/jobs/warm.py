"""Client for the zygote: same contract as ``run_isolated`` without the per-request imports."""

from __future__ import annotations

import json
import os
import signal
import socket
import subprocess
import sys
import tempfile
import threading
import time
from pathlib import Path
from typing import Any

from ..core.engine import failure_result
from .worker import DEFAULT_MEMORY_BYTES, MAX_OUTPUT_BYTES

_BACKEND_DIR = str(Path(__file__).resolve().parents[2])


class WarmWorker:
    def __init__(self, *, engine: str | None = None, extra_pythonpath: str | None = None) -> None:
        """``engine`` ("module:function") and ``extra_pythonpath`` exist for tests; the HTTP layer never passes them."""
        self._engine = engine
        self._extra_pythonpath = extra_pythonpath
        self._lock = threading.Lock()
        self._proc: subprocess.Popen[bytes] | None = None
        self._tmp: tempfile.TemporaryDirectory[str] | None = None
        self.last_child_pid: int = 0

    # -- lifecycle ---------------------------------------------------------------------------
    @property
    def zygote_pid(self) -> int:
        return self._proc.pid if self._proc else 0

    @property
    def socket_dir(self) -> str:
        return self._tmp.name if self._tmp else ""

    def start(self) -> None:
        with self._lock:
            self._start_locked()

    def _start_locked(self) -> None:
        self._stop_locked()
        self._tmp = tempfile.TemporaryDirectory(prefix="hcsem-zy-")  # mkdtemp is mode 0700
        env = {
            "PATH": "/usr/bin:/bin",
            "PYTHONPATH": os.pathsep.join(p for p in (_BACKEND_DIR, self._extra_pythonpath) if p),
            "LANG": "C.UTF-8",
            "LC_ALL": "C.UTF-8",
            "PYTHONHASHSEED": "0",
            "PYTHONDONTWRITEBYTECODE": "1",
        }
        self._proc = subprocess.Popen(
            [sys.executable, "-m", "hcseasymath.jobs.zygote", os.path.join(self._tmp.name, "z.sock"),
             *([self._engine] if self._engine else [])],
            stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, stdin=subprocess.DEVNULL,
            env=env, cwd=self._tmp.name, start_new_session=True, close_fds=True,
        )
        assert self._proc.stdout is not None
        if self._proc.stdout.readline().strip() != b"ready":
            self._stop_locked()
            raise RuntimeError("the zygote did not report ready")

    def stop(self) -> None:
        with self._lock:
            self._stop_locked()

    def _stop_locked(self) -> None:
        if self._proc is not None:
            try:
                os.killpg(self._proc.pid, signal.SIGKILL)
            except (ProcessLookupError, PermissionError):
                pass
            self._proc.wait()
            self._proc = None
        if self._tmp is not None:
            self._tmp.cleanup()
            self._tmp = None

    def _ensure(self) -> None:
        with self._lock:
            if self._proc is None or self._proc.poll() is not None:
                self._start_locked()

    # -- request -----------------------------------------------------------------------------
    def run(
        self, request: Any, *, timeout_s: float = 10.0,
        memory_bytes: int = DEFAULT_MEMORY_BYTES, cpu_seconds: int | None = None,
    ) -> dict[str, Any]:
        """Execute ``request`` in a forked child and return a result dict. Never raises."""
        operation = request.get("operation", "unknown") if isinstance(request, dict) else "unknown"
        if not isinstance(operation, str):
            operation = "unknown"
        cpu = cpu_seconds if cpu_seconds is not None else int(timeout_s) + 2
        deadline = time.monotonic() + timeout_s
        try:
            self._ensure()
            sock_path = os.path.join(self.socket_dir, "z.sock")
            conn = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        except (OSError, RuntimeError) as exc:
            return failure_result(request, operation, "engine_unavailable", f"cannot start worker: {exc.__class__.__name__}")
        pid = 0
        try:
            conn.settimeout(max(deadline - time.monotonic(), 0.001))
            conn.connect(sock_path)
            pid = int(self._read_line(conn))
            self.last_child_pid = pid
            envelope = {"limits": {"memory_bytes": memory_bytes, "cpu_seconds": cpu}, "request": request}
            conn.sendall(json.dumps(envelope, default=repr).encode("utf-8"))
            conn.shutdown(socket.SHUT_WR)
            buf = bytearray()
            while True:
                conn.settimeout(max(deadline - time.monotonic(), 0.001))
                chunk = conn.recv(65536)
                if not chunk:
                    break
                buf.extend(chunk)
                if len(buf) > MAX_OUTPUT_BYTES:
                    self._kill(pid)
                    return failure_result(request, operation, "resource_limit", "output exceeded the size limit")
        except socket.timeout:
            self._kill(pid)
            return failure_result(request, operation, "resource_limit", f"time limit of {timeout_s:g}s exceeded")
        except (OSError, ValueError):
            self._kill(pid)
            return failure_result(request, operation, "engine_unavailable", "worker connection failed")
        finally:
            conn.close()
        self._kill(pid)  # no stray grandchildren after a normal exit either
        if not buf:
            return failure_result(request, operation, "resource_limit", "worker stopped without a result")
        try:
            data = json.loads(bytes(buf))
        except (ValueError, UnicodeDecodeError):
            return failure_result(request, operation, "internal_error", "worker returned invalid output")
        if not isinstance(data, dict):
            return failure_result(request, operation, "internal_error", "worker returned a non-object")
        if data.get("_child_resource") == "memory":
            return failure_result(request, operation, "resource_limit", "memory limit exceeded")
        if "_child_error" in data:
            return failure_result(request, operation, "invalid_input", str(data["_child_error"]))
        return data

    @staticmethod
    def _read_line(conn: socket.socket) -> bytes:
        line = bytearray()
        while not line.endswith(b"\n"):
            ch = conn.recv(1)
            if not ch:
                raise OSError("zygote closed the connection")
            line.extend(ch)
            if len(line) > 32:
                raise ValueError("bad pid line")
        return bytes(line)

    @staticmethod
    def _kill(pid: int) -> None:
        if pid > 1:
            try:
                os.killpg(pid, signal.SIGKILL)
            except (ProcessLookupError, PermissionError):
                pass
