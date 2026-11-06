"""Host-side Workshop RPC: one persistent connection, every request sent exactly once, slow replies awaited, stale replies skipped.

Background (QEMU issue 4672): a guest write to a virtio-serial port can hang forever when the host side closes the connection while
the port is throttled. The old harness opened a connection per call and re-sent after timeouts; the guest daemon then 'stopped
answering' at a different check in every run. A fake guest on a TCP socket reproduces the connection pattern.
"""
import json
import socket
import sys
import threading
import time
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "scripts/workshop"))
import vm as vmmod  # noqa: E402


class FakeGuest:
    """Speaks the daemon protocol: hello, then one JSON reply per request line."""

    def __init__(self, delay=0.0, hello=True, stale_first=False, hello_delay=0.0):
        self.srv = socket.socket()
        self.srv.bind(("127.0.0.1", 0))
        self.srv.listen(5)
        self.port = self.srv.getsockname()[1]
        self.connections = 0
        self.requests = []
        self.delay, self.hello, self.stale_first, self.hello_delay = delay, hello, stale_first, hello_delay
        self.stop = False
        threading.Thread(target=self.run, daemon=True).start()

    def run(self):
        self.srv.settimeout(0.2)
        while not self.stop:
            try:
                conn, _ = self.srv.accept()
            except (socket.timeout, OSError):
                continue
            self.connections += 1
            threading.Thread(target=self.serve, args=(conn,), daemon=True).start()

    def serve(self, conn):
        f = conn.makefile("rwb", buffering=0)
        try:
            if self.hello:
                time.sleep(self.hello_delay)
                f.write(b'{"hello":"fake","version":1}\n')
            for raw in iter(f.readline, b""):
                req = json.loads(raw)
                self.requests.append(req)
                if self.stale_first and len(self.requests) == 1:
                    f.write(json.dumps({"id": 0, "ok": True, "result": {"stale": True}}).encode() + b"\n")
                time.sleep(self.delay)
                f.write(json.dumps({"id": req["id"], "ok": True, "result": {"echo": req["op"]}}).encode() + b"\n")
        except OSError:
            pass

    def close(self):
        self.stop = True
        self.srv.close()


def make_vm(port):
    v = object.__new__(vmmod.Vm)
    v.api_port, v._rpc, v._rid = port, None, 0
    return v


@pytest.fixture
def guest():
    gs = []

    def make(**kw):
        g = FakeGuest(**kw)
        gs.append(g)
        return g
    yield make
    for g in gs:
        g.close()


def test_many_calls_use_one_connection_and_each_request_is_sent_once(guest):
    g = guest()
    vm = make_vm(g.port)
    for i in range(25):
        assert vm.rpc(f"op{i}", timeout=20) == {"echo": f"op{i}"}
    vm._close_rpc()
    assert g.connections == 1
    assert [r["op"] for r in g.requests] == [f"op{i}" for i in range(25)]  # no duplicates, no re-sends


def test_a_slow_reply_is_awaited_without_reconnecting_or_resending(guest):
    g = guest(delay=1.5)
    vm = make_vm(g.port)
    assert vm.rpc("slow", timeout=30) == {"echo": "slow"}
    assert vm.rpc("slow2", timeout=30) == {"echo": "slow2"}
    vm._close_rpc()
    assert g.connections == 1 and len(g.requests) == 2


def test_stale_reply_from_an_older_request_is_skipped(guest):
    g = guest(stale_first=True)
    vm = make_vm(g.port)
    assert vm.rpc("a", timeout=20) == {"echo": "a"}
    vm._close_rpc()


def test_works_when_the_hello_line_was_lost(guest, monkeypatch):
    monkeypatch.setattr(vmmod, "HELLO_WAIT_S", 1.0)  # an older daemon that never says hello gets the request after this wait
    g = guest(hello=False)
    vm = make_vm(g.port)
    assert vm.rpc("a", timeout=40) == {"echo": "a"}
    vm._close_rpc()
    assert len(g.requests) >= 1


def test_guest_error_is_reported_not_retried(guest):
    g = guest()
    vm = make_vm(g.port)

    orig = g.serve

    def failing(conn):
        f = conn.makefile("rwb", buffering=0)
        f.write(b'{"hello":"fake"}\n')
        for raw in iter(f.readline, b""):
            req = json.loads(raw)
            g.requests.append(req)
            f.write(json.dumps({"id": req["id"], "ok": False, "error": "nope"}).encode() + b"\n")

    g.serve = failing
    with pytest.raises(vmmod.VmError, match="nope"):
        vm.rpc("x", timeout=20)
    vm._close_rpc()
    assert len(g.requests) == 1
    g.serve = orig


def test_late_hello_is_awaited_on_one_connection_never_dropped_for_silence(guest):
    """QEMU serves one client per socket chardev and only sees it leave while the guest port is open: dropping a quiet connection
    while the guest daemon is still starting stacks stale connections until the port refuses everything (VM finding 2026-11-06)."""
    g = guest(hello_delay=4.0)
    vm = make_vm(g.port)
    t0 = time.time()
    assert vm.rpc("status", timeout=30) == {"echo": "status"}
    assert time.time() - t0 >= 3.5
    vm._close_rpc()
    assert g.connections == 1 and [r["op"] for r in g.requests] == ["status"]
