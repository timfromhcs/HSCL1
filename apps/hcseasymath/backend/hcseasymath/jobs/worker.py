"""Run one operation in a killable child process (decision D5).

The API process never evaluates a request itself: it starts a child with a wall-clock
timeout, a memory cap and a minimal environment, reads at most ``MAX_OUTPUT_BYTES`` of
its output and turns every failure into a typed result.
"""

from __future__ import annotations

import json
import os
import signal
import subprocess
import sys
import tempfile
import threading
from pathlib import Path
from typing import Any

from ..core.engine import failure_result
from . import child as _child

MAX_OUTPUT_BYTES = 1024 * 1024
DEFAULT_MEMORY_BYTES = 2 * 1024 * 1024 * 1024
_BACKEND_DIR = str(Path(__file__).resolve().parents[2])


def _kill_group(proc: subprocess.Popen[bytes]) -> None:
    try:
        os.killpg(proc.pid, signal.SIGKILL)
    except (ProcessLookupError, PermissionError):
        pass


def run_isolated(
    request: Any,
    *,
    timeout_s: float = 10.0,
    memory_bytes: int = DEFAULT_MEMORY_BYTES,
    cpu_seconds: int | None = None,
    entry: str = "hcseasymath.jobs.child",
    extra_pythonpath: str | None = None,
) -> dict[str, Any]:
    """Execute ``request`` in a child process and return a result dict. Never raises.

    ``entry`` and ``extra_pythonpath`` exist for tests; the HTTP layer never passes them.
    """
    cpu = cpu_seconds if cpu_seconds is not None else int(timeout_s) + 2
    pythonpath = os.pathsep.join(p for p in (_BACKEND_DIR, extra_pythonpath) if p)
    env = {
        "PATH": "/usr/bin:/bin",
        "PYTHONPATH": pythonpath,
        "LANG": "C.UTF-8",
        "LC_ALL": "C.UTF-8",
        "PYTHONHASHSEED": "0",
        "PYTHONDONTWRITEBYTECODE": "1",
    }
    operation = request.get("operation", "unknown") if isinstance(request, dict) else "unknown"
    if not isinstance(operation, str):
        operation = "unknown"

    with tempfile.TemporaryDirectory(prefix="hcsem-") as workdir:
        try:
            proc = subprocess.Popen(
                [sys.executable, "-m", entry, str(memory_bytes), str(cpu)],
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.DEVNULL,
                env=env,
                cwd=workdir,
                start_new_session=True,
                close_fds=True,
            )
        except OSError as exc:
            return failure_result(request, operation, "engine_unavailable", f"cannot start worker: {exc.__class__.__name__}")

        buf = bytearray()
        over = threading.Event()

        def reader() -> None:
            assert proc.stdout is not None
            while True:
                chunk = proc.stdout.read1(65536)
                if not chunk:
                    return
                if len(buf) + len(chunk) > MAX_OUTPUT_BYTES:
                    over.set()
                    _kill_group(proc)
                    return
                buf.extend(chunk)

        thread = threading.Thread(target=reader, daemon=True)
        thread.start()
        try:
            assert proc.stdin is not None
            proc.stdin.write(json.dumps(request, default=repr).encode("utf-8"))
            proc.stdin.close()
        except (BrokenPipeError, OSError):
            pass

        timed_out = False
        try:
            proc.wait(timeout=timeout_s)
        except subprocess.TimeoutExpired:
            timed_out = True
            _kill_group(proc)
            proc.wait()
        _kill_group(proc)  # no stray grandchildren after a normal exit either
        thread.join(timeout=2.0)

    if timed_out:
        return failure_result(request, operation, "resource_limit", f"time limit of {timeout_s:g}s exceeded")
    if over.is_set():
        return failure_result(request, operation, "resource_limit", "output exceeded the size limit")
    rc = proc.returncode
    if rc == _child.EXIT_RESOURCE:
        return failure_result(request, operation, "resource_limit", "memory limit exceeded")
    if rc is not None and rc < 0:
        return failure_result(request, operation, "resource_limit", f"worker stopped by signal {-rc}")
    if rc != 0:
        return failure_result(request, operation, "internal_error", f"worker exited with code {rc}")
    try:
        data = json.loads(bytes(buf))
    except (ValueError, UnicodeDecodeError):
        return failure_result(request, operation, "internal_error", "worker returned invalid output")
    if not isinstance(data, dict):
        return failure_result(request, operation, "internal_error", "worker returned a non-object")
    if "_child_error" in data:
        return failure_result(request, operation, "invalid_input", str(data["_child_error"]))
    return data
