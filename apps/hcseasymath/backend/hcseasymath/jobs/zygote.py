"""Pre-imported zygote: imports the engine once, then forks one child per request.

Single-threaded on purpose (forking a threaded process is unsafe). Each connection on the
unix socket is one request: the zygote forks, tells the parent the child's pid, and closes its
own copy. The child starts a new session (so the parent can kill the whole group), applies its
resource limits, runs the operation and writes one JSON object. Nothing is shared between
requests except the read-only imported modules.
"""

from __future__ import annotations

import json
import os
import signal
import socket
import sys

MAX_ENVELOPE_BYTES = 64 * 1024 + 4096


def _read_envelope(conn: socket.socket) -> bytes:
    data = bytearray()
    while len(data) <= MAX_ENVELOPE_BYTES:
        chunk = conn.recv(65536)
        if not chunk:
            break
        data.extend(chunk)
    return bytes(data)


def _child(conn: socket.socket, execute) -> None:  # noqa: ANN001
    from .sandbox import apply_limits

    os.setsid()
    try:
        raw = _read_envelope(conn)
        if len(raw) > MAX_ENVELOPE_BYTES:
            conn.sendall(json.dumps({"_child_error": "request too large"}).encode())
            return
        envelope = json.loads(raw)
        limits = envelope["limits"]
        apply_limits(memory_bytes=int(limits["memory_bytes"]), cpu_seconds=int(limits["cpu_seconds"]))
        conn.sendall(json.dumps(execute(envelope["request"])).encode())
    except MemoryError:
        conn.sendall(json.dumps({"_child_resource": "memory"}).encode())
    except (ValueError, KeyError, TypeError, UnicodeDecodeError):
        conn.sendall(json.dumps({"_child_error": "request is not valid"}).encode())


def serve(path: str, engine: str = "hcseasymath.core.engine:execute") -> None:
    import importlib

    module_name, _, func_name = engine.partition(":")
    execute = getattr(importlib.import_module(module_name), func_name)  # the expensive import, done once

    signal.signal(signal.SIGCHLD, signal.SIG_IGN)  # children are reaped by the kernel
    srv = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    srv.bind(path)
    os.chmod(path, 0o600)
    srv.listen(32)
    sys.stdout.write("ready\n")
    sys.stdout.flush()
    while True:
        try:
            conn, _ = srv.accept()
        except InterruptedError:
            continue
        pid = os.fork()
        if pid == 0:
            srv.close()
            code = 0
            try:
                _child(conn, execute)
            except BaseException:  # noqa: BLE001 - a child must never fall back into the accept loop
                code = 1
            finally:
                os._exit(code)
        try:
            conn.sendall(f"{pid}\n".encode())
        except OSError:
            pass
        conn.close()


if __name__ == "__main__":
    serve(*sys.argv[1:3])
