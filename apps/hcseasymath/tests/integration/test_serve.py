"""End to end (gate E4): start the real server, use it, stop it, prove nothing listens."""

import json
import os
import signal
import socket
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

import pytest

pytestmark = pytest.mark.skipif(
    not sys.platform.startswith("linux"), reason="gate runs on Linux (WSL/CI)"
)

BACKEND = str(Path(__file__).resolve().parents[2] / "backend")


def start():
    env = {"PYTHONPATH": BACKEND, "PATH": "/usr/bin:/bin", "LANG": "C.UTF-8"}
    proc = subprocess.Popen(
        [sys.executable, "-m", "hcseasymath", "serve", "--port", "0"],
        stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=env, text=True,
    )
    line = proc.stdout.readline()
    info = json.loads(line)
    return proc, info


def call(info, path, body=None, token=True, headers=None):
    hdrs = dict(headers or {})
    if token:
        hdrs["Authorization"] = f"Bearer {info['token']}"
    data = None
    if body is not None:
        data = json.dumps(body).encode()
        hdrs["Content-Type"] = "application/json"
    req = urllib.request.Request(info["url"].rstrip("/") + path, data=data, headers=hdrs)
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            return r.status, r.read().decode(), {k.lower(): v for k, v in r.headers.items()}
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode(), {k.lower(): v for k, v in e.headers.items()}


def can_bind(port):
    """True when nothing in the kernel listens on 127.0.0.1:port.

    A bare connect() is not proof either way under WSL2: its network layer can accept a
    connection to a recently used loopback port and close it again, although the kernel
    has no listener (observed: peer port differs, state CLOSE-WAIT, empty `ss -ltn`).
    """
    with socket.socket() as s:
        # SO_REUSEADDR ignores leftover TIME_WAIT sockets but still refuses an active listener.
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            s.bind(("127.0.0.1", port))
            return True
        except OSError:
            return False


def kernel_listeners(port):
    out = subprocess.run(["ss", "-ltnH"], capture_output=True, text=True).stdout
    return [r for r in out.splitlines() if f":{port} " in r + " "]


def port_open(port):
    with socket.socket() as s:
        s.settimeout(0.5)
        return s.connect_ex(("127.0.0.1", port)) == 0


def test_serve_use_stop_and_leave_no_listener():
    proc, info = start()
    try:
        assert info["url"].startswith("http://127.0.0.1:")
        port = int(info["url"].rsplit(":", 1)[1].rstrip("/"))
        assert len(info["token"]) >= 32

        code, body, _ = call(info, "/api/v1/health", token=False)
        assert code == 200 and json.loads(body)["status"] == "ok"

        code, body, _ = call(info, "/api/v1/symbolic/differentiate",
                             {"expression": "x**3 - 3*x**2 + 2*x", "variable": "x"})
        res = json.loads(body)
        assert code == 200 and res["result_expression"] == "3*x**2 - 6*x + 2"
        assert res["exactness"] == "symbolic_exact"

        code, _, _ = call(info, "/api/v1/symbolic/differentiate",
                          {"expression": "x", "variable": "x"}, token=False)
        assert code == 401

        # The listener must be loopback only: it must not answer on a non-loopback address.
        assert port_open(port) and not can_bind(port) and kernel_listeners(port)
    finally:
        proc.send_signal(signal.SIGTERM)
        try:
            rc = proc.wait(timeout=15)
        except subprocess.TimeoutExpired:
            proc.kill()
            rc = None
    # uvicorn shuts down gracefully, then re-raises the captured signal, so a clean stop
    # on SIGTERM reports -SIGTERM (verified in uvicorn/server.py capture_signals).
    assert rc in (0, -signal.SIGTERM), f"unexpected exit status {rc}"
    stderr = proc.stderr.read()
    assert "Traceback" not in stderr, stderr
    time.sleep(0.2)
    assert kernel_listeners(port) == [], "no listener may remain after exit"
    assert can_bind(port), "the port must be free again after exit"


def test_the_served_page_is_same_origin_with_a_strict_csp_and_no_external_urls():
    proc, info = start()
    try:
        code, body, headers = call(info, "/", token=False)
        assert code == 200 and "text/html" in headers["content-type"]
        csp = headers["content-security-policy"]
        assert "default-src 'self'" in csp and "'unsafe-eval'" not in csp
        assert "http://" not in body.replace("http://127.0.0.1", "") and "https://" not in body
        assert "location.hash" in body, "the token must come from the URL fragment, never the query"
        assert info["token"] not in body
    finally:
        proc.send_signal(signal.SIGTERM)
        proc.wait(timeout=15)


def test_it_binds_loopback_only():
    proc, info = start()
    try:
        port = int(info["url"].rsplit(":", 1)[1].rstrip("/"))
        out = subprocess.run(["ss", "-ltnH"], capture_output=True, text=True).stdout
        rows = [r.split() for r in out.splitlines() if f":{port} " in r + " "]
        assert rows, "listener not found"
        assert all(r[3].startswith("127.0.0.1:") for r in rows), rows
    finally:
        proc.send_signal(signal.SIGTERM)
        proc.wait(timeout=15)
