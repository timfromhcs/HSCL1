#!/usr/bin/env python3
"""HSCL1 Workshop daemon: a finite JSON-RPC operation set for VM development (stdlib only).

Transport: line-delimited JSON on the virtio port /dev/virtio-ports/hscl.api (or any stream for tests).
Authority: whoever holds the hypervisor end of the port already controls the VM, so there is no extra secret on
that channel; nothing here listens on the network. Operations are a closed list; there is no generic "run command".
`put_file` writes only below allow-listed directories, `run_hook` runs only files from the hooks directory.

Request : {"id": 1, "op": "status", "args": {}}
Response: {"id": 1, "ok": true, "result": ...} | {"id": 1, "ok": false, "error": "..."}
"""
from __future__ import annotations

import base64
import json
import os
import re
import select
import subprocess
import sys
import time
from pathlib import Path

VERSION = 1
MAX_FILE_BYTES = 8 * 1024 * 1024
MAX_LINE_BYTES = 12 * 1024 * 1024
MAX_REPLY_BYTES = 4 * 1024 * 1024  # a reply the host cannot take in time wedges the port; refuse to build one this large
HOOKS_DIR = "/usr/lib/hscl/workshop/hooks"
ALLOWED_PREFIXES = (
    "/usr/share/hscl/",
    "/usr/share/plasma/",
    "/usr/share/wallpapers/HSCL1",
    "/usr/share/color-schemes/HCS",
    "/usr/share/sddm/themes/hscl1/",
    "/usr/share/icons/hicolor/",
    "/usr/share/applications/hscl-",
    "/etc/calamares/branding/hscl1/",
    "/etc/hscl/",
    "/usr/lib/hscl/",
    "/usr/share/doc/hscl-",
    "/var/lib/hscl/workshop/debs/",
    HOOKS_DIR + "/",
)
ALLOWED_EXACT = ("/usr/bin/hscl", "/usr/bin/hcscoder", "/usr/bin/hscl-control-center", "/usr/bin/hscl-handbook")
HOOK_NAME = re.compile(r"^[a-z0-9][a-z0-9._-]{0,40}$")
ALLOWED_MODES = {"0644": 0o644, "0755": 0o755}


class OpError(Exception):
    """A request-level error that is reported to the caller (never a crash)."""


def validate_put_path(path: str, root: str = "/") -> Path:
    """Return the real target below `root`, or raise OpError. Rejects traversal, relative paths, symlinks and
    anything outside ALLOWED_PREFIXES. `root` exists so tests can run against a temporary tree."""
    if not isinstance(path, str) or not path.startswith("/") or "\x00" in path:
        raise OpError("path must be absolute")
    if ".." in Path(path).parts or "//" in path:
        raise OpError("path must be normalised (no '..' or '//')")
    if not (path in ALLOWED_EXACT or any(path.startswith(p) for p in ALLOWED_PREFIXES)):
        raise OpError("path is outside the allow-listed directories")
    base = Path(root)
    target = base / path.lstrip("/")
    # no symlink anywhere between root and the target (existing components only)
    cur = base
    for part in Path(path.lstrip("/")).parts:
        cur = cur / part
        if cur.is_symlink():
            raise OpError("symlinks are not allowed in the path")
        if not cur.exists():
            break
    return target


def op_put_file(args: dict, root: str = "/") -> dict:
    target = validate_put_path(args.get("path"), root)
    mode = ALLOWED_MODES.get(str(args.get("mode", "0644")))
    if mode is None:
        raise OpError("mode must be 0644 or 0755")
    try:
        data = base64.b64decode(args.get("content_b64", ""), validate=True)
    except Exception as e:  # noqa: BLE001
        raise OpError(f"content_b64 is not valid base64: {e}") from None
    if len(data) > MAX_FILE_BYTES:
        raise OpError(f"file larger than {MAX_FILE_BYTES} bytes")
    target.parent.mkdir(parents=True, exist_ok=True)
    tmp = target.with_name(target.name + ".hscl-tmp")
    fd = os.open(tmp, os.O_WRONLY | os.O_CREAT | os.O_TRUNC | getattr(os, "O_NOFOLLOW", 0), mode)
    with os.fdopen(fd, "wb") as f:
        f.write(data)
    os.chmod(tmp, mode)
    os.replace(tmp, target)
    return {"path": args["path"], "bytes": len(data), "mode": oct(mode)}


def op_run_hook(args: dict, hooks_dir: str = HOOKS_DIR) -> dict:
    name = args.get("name")
    if not isinstance(name, str) or not HOOK_NAME.match(name):
        raise OpError("invalid hook name")
    p = Path(hooks_dir) / name
    if p.is_symlink() or not p.is_file():
        raise OpError("hook not found (must be a regular file in the hooks directory)")
    try:
        r = subprocess.run(["/bin/sh", str(p)], capture_output=True, timeout=int(args.get("timeout", 120)), cwd="/")
    except subprocess.TimeoutExpired:
        raise OpError("hook timed out") from None
    return {"exit": r.returncode, "stdout": r.stdout[-8192:].decode("utf-8", "replace"),
            "stderr": r.stderr[-8192:].decode("utf-8", "replace")}


def session_user() -> tuple[str, int] | None:
    """User and uid that own plasmashell (the desktop session), or None."""
    try:
        out = subprocess.run(["ps", "-o", "user=,uid=", "-C", "plasmashell"], capture_output=True, text=True, timeout=5).stdout
    except Exception:  # noqa: BLE001
        return None
    for line in out.splitlines():
        f = line.split()
        if len(f) == 2 and f[1].isdigit():
            return f[0], int(f[1])
    return None


def as_session_user(argv: list[str], timeout: int = 60) -> subprocess.CompletedProcess:
    su = session_user()
    if su is None:
        raise OpError("no desktop session is running")
    user, uid = su
    rt = f"/run/user/{uid}"
    wl = next((n for n in sorted(os.listdir(rt)) if n.startswith("wayland-") and not n.endswith(".lock")), "wayland-0") if os.path.isdir(rt) else "wayland-0"
    env = ["env", f"XDG_RUNTIME_DIR={rt}", f"WAYLAND_DISPLAY={wl}", f"DBUS_SESSION_BUS_ADDRESS=unix:path={rt}/bus"]
    return subprocess.run(["runuser", "-u", user, "--", *env, *argv], capture_output=True, timeout=timeout)


def op_screenshot(_args: dict) -> dict:
    out = f"/tmp/hscl-shot-{int(time.time() * 1000)}.png"
    r = as_session_user(["spectacle", "-b", "-n", "-f", "-o", out])
    p = Path(out)
    if not p.is_file() or p.stat().st_size == 0:
        raise OpError("screenshot failed: " + r.stderr.decode("utf-8", "replace")[-300:])
    data = p.read_bytes()
    p.unlink()
    if len(data) > MAX_FILE_BYTES:
        raise OpError("screenshot too large")
    return {"format": "png", "bytes": len(data), "png_b64": base64.b64encode(data).decode()}


def op_restart_shell(_args: dict) -> dict:
    r = as_session_user(["systemctl", "--user", "restart", "plasma-plasmashell.service"], timeout=60)
    return {"exit": r.returncode, "stderr": r.stderr.decode("utf-8", "replace")[-300:]}


def run_json(argv: list[str]) -> object:
    r = subprocess.run(argv, capture_output=True, text=True, timeout=120)
    try:
        return json.loads(r.stdout)
    except json.JSONDecodeError:
        raise OpError(f"{argv[0]} did not return JSON (exit {r.returncode})") from None


def op_status(_args: dict) -> dict:
    cmdline = Path("/proc/cmdline").read_text() if Path("/proc/cmdline").exists() else ""
    osr = {}
    if Path("/usr/lib/os-release").exists():
        for line in Path("/usr/lib/os-release").read_text().splitlines():
            if "=" in line:
                k, v = line.split("=", 1)
                osr[k] = v.strip('"')
    su = session_user()
    return {"workshop": VERSION, "hscl1_version": osr.get("HSCL1_VERSION"), "live": os.path.exists("/cdrom/casper/filesystem.squashfs") or "/casper/" in cmdline,
            "session_user": su[0] if su else None, "ops": sorted(OPS), "port": dict(PORT_STATS)}


def op_respin(args: dict) -> dict:
    out = args.get("out_dir")
    if not isinstance(out, str) or not out.startswith("/"):
        raise OpError("out_dir must be an absolute path")
    r = subprocess.run(["/usr/lib/hscl/workshop/hscl-respin", "--out-dir", out], capture_output=True, text=True, timeout=7200)
    return {"exit": r.returncode, "stdout": r.stdout[-4096:], "stderr": r.stderr[-4096:]}


OPS = {
    "status": op_status,
    "doctor": lambda a: run_json(["hscl", "doctor", "--json"]),
    "report": lambda a: run_json(["hscl", "report"]),
    "screenshot": op_screenshot,
    "put_file": op_put_file,
    "run_hook": op_run_hook,
    "restart_shell": op_restart_shell,
    "respin": op_respin,
}


def handle(line: str, ops: dict | None = None) -> dict:
    """Process one request line; never raises."""
    ops = OPS if ops is None else ops
    rid = None
    try:
        if len(line) > MAX_LINE_BYTES:
            raise OpError("request too large")
        req = json.loads(line)
        if not isinstance(req, dict):
            raise OpError("request must be an object")
        rid = req.get("id")
        op = req.get("op")
        if op not in ops:
            raise OpError(f"unknown operation: {op!r}")
        args = req.get("args", {})
        if not isinstance(args, dict):
            raise OpError("args must be an object")
        return {"id": rid, "ok": True, "result": ops[op](args)}
    except OpError as e:
        return {"id": rid, "ok": False, "error": str(e)}
    except json.JSONDecodeError:
        return {"id": rid, "ok": False, "error": "request is not valid JSON"}
    except Exception as e:  # noqa: BLE001  - a handler bug must not kill the daemon
        return {"id": rid, "ok": False, "error": f"internal error: {type(e).__name__}"}


WRITE_TIMEOUT_S = 20.0
PORT_STATS = {"restarts": 0, "write_timeouts": 0}


class WriteTimeout(OSError):
    """The host end of the port did not take our reply within WRITE_TIMEOUT_S."""


class FdReader:
    """Line reader on a (non-blocking) fd. readline() returns b'' on EOF, like a file object."""

    def __init__(self, fd: int):
        self.fd, self.buf = fd, bytearray()

    def readline(self) -> bytes:
        while True:
            i = self.buf.find(b"\n")
            if i >= 0:
                line = bytes(self.buf[: i + 1])
                del self.buf[: i + 1]
                return line
            select.select([self.fd], [], [])
            try:
                chunk = os.read(self.fd, 65536)
            except BlockingIOError:
                continue
            if not chunk:
                rest, self.buf = bytes(self.buf), bytearray()
                return rest
            self.buf.extend(chunk)


class TimedWriter:
    """Writes with a deadline. A virtio-serial write that the host cannot drain blocks the guest forever (QEMU issue 4672);
    with a deadline the daemon notices, reopens the port and carries on instead of going silent."""

    def __init__(self, fd: int, timeout: float = WRITE_TIMEOUT_S):
        self.fd, self.timeout = fd, timeout

    def write(self, data: bytes) -> int:
        view, end = memoryview(data), time.monotonic() + self.timeout
        while view:
            try:
                n = os.write(self.fd, view)
                view = view[n:]
            except BlockingIOError:
                left = end - time.monotonic()
                if left <= 0:
                    PORT_STATS["write_timeouts"] += 1
                    raise WriteTimeout("host end of the port is not draining") from None
                select.select([], [self.fd], [], min(left, 1.0))
        return len(data)

    def flush(self) -> None:
        pass


def serve(rfile, wfile, ops: dict | None = None) -> None:
    wfile.write((json.dumps({"hello": "hscl-workshopd", "version": VERSION}) + "\n").encode())
    wfile.flush()
    for raw in iter(rfile.readline, b""):
        line = raw.decode("utf-8", "replace").strip()
        if not line:
            continue
        resp = handle(line, ops)
        data = (json.dumps(resp) + "\n").encode()
        if len(data) > MAX_REPLY_BYTES:
            data = (json.dumps({"id": resp.get("id"), "ok": False, "error": f"reply too large ({len(data)} bytes, limit {MAX_REPLY_BYTES})"}) + "\n").encode()
        wfile.write(data)
        wfile.flush()


def serve_socket(path: str) -> int:
    """Local root-only unix socket (no network). One connection at a time; used by `hscl workshop` on a running system."""
    import socket
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    os.chmod(Path(path).parent, 0o700)
    if os.path.exists(path):
        os.unlink(path)
    srv = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    srv.bind(path)
    os.chmod(path, 0o600)
    srv.listen(1)
    while True:
        conn, _ = srv.accept()
        with conn, conn.makefile("rwb", buffering=0) as f:
            serve(f, f)


def main(argv: list[str]) -> int:
    if len(argv) > 2 and argv[1] == "--socket":
        return serve_socket(argv[2])
    port = argv[1] if len(argv) > 1 else "/dev/virtio-ports/hscl.api"
    if not os.path.exists(port):
        print(f"no such port: {port}", file=sys.stderr)
        return 1
    # The host may connect and disconnect many times; keep serving until the service is stopped. The port is opened once per
    # session non-blocking, reads and writes wait with select, and a write the host does not drain within WRITE_TIMEOUT_S
    # makes us close and reopen the port instead of hanging.
    while True:
        fd = -1
        try:
            fd = os.open(port, os.O_RDWR | os.O_NONBLOCK)
            select.select([], [fd], [])  # like the old blocking hello write: wait until a host is connected (no timeout here)
            serve(FdReader(fd), TimedWriter(fd))
        except WriteTimeout as e:
            print(f"hscl-workshopd: {e}; reopening the port", file=sys.stderr, flush=True)
        except OSError:
            pass
        finally:
            if fd >= 0:
                try:
                    os.close(fd)
                except OSError:
                    pass
        PORT_STATS["restarts"] += 1
        time.sleep(0.5)
