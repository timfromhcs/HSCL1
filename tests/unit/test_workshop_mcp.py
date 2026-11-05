"""Workshop MCP server: protocol conformance, schemas, argument validation, tool failures as results, memory guard."""
import base64
import io
import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts" / "workshop"))
import mcp_server as ms  # noqa: E402
import vm as vmmod  # noqa: E402


class FakeVm:
    running = True
    api_port = 1

    def __init__(self):
        self.sent = []

    def screenshot_png(self):
        return b"\x89PNG-fake"

    def keys(self, k):
        self.sent.append(("keys", k))

    def type(self, t):
        self.sent.append(("type", t))

    def click(self, x, y, double=False):
        self.sent.append(("click", x, y, double))

    def rpc(self, op, args=None, timeout=0):
        if op == "screenshot":
            return {"png_b64": base64.b64encode(b"\x89PNG-guest").decode()}
        if op == "put_file":
            return {"path": args["path"], "bytes": len(base64.b64decode(args["content_b64"]))}
        return {"op": op, "args": args}


class FakeManager:
    def __init__(self):
        self.vm = FakeVm()
        self.started = []

    def get(self, name):
        if name != "default":
            raise vmmod.VmError(f"no running VM named {name!r}")
        return self.vm

    def start(self, name, iso, disk, memory, firmware):
        self.started.append((name, iso, disk, memory, firmware))
        return self.vm

    def stop(self, name):
        return None

    def list(self):
        return [{"name": "default", "running": True}]

    def stop_all(self):
        pass


@pytest.fixture()
def srv():
    return ms.Server(FakeManager())


def call(srv, name, args=None, mid=1):
    return srv.handle({"jsonrpc": "2.0", "id": mid, "method": "tools/call", "params": {"name": name, "arguments": args or {}}})


def test_initialize_and_notification(srv):
    r = srv.handle({"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}})
    assert r["result"]["protocolVersion"] == ms.PROTOCOL and "tools" in r["result"]["capabilities"]
    assert srv.handle({"jsonrpc": "2.0", "method": "notifications/initialized"}) is None
    assert srv.handle({"jsonrpc": "2.0", "id": 2, "method": "ping"})["result"] == {}


def test_every_tool_has_description_and_closed_schema(srv):
    tools = srv.handle({"jsonrpc": "2.0", "id": 1, "method": "tools/list"})["result"]["tools"]
    names = {t["name"] for t in tools}
    assert {"vm_start", "vm_stop", "vm_screenshot", "vm_keys", "vm_type", "vm_click", "guest_status", "guest_doctor",
            "guest_screenshot", "guest_put_file", "guest_hook", "guest_restart_shell", "guest_respin"} <= names
    for t in tools:
        assert t["description"] and t["inputSchema"]["type"] == "object" and t["inputSchema"]["additionalProperties"] is False
    assert not names & {"exec", "shell", "run_command", "vm_exec"}, "no generic command tool"


def test_screenshot_returns_an_image_block(srv):
    r = call(srv, "vm_screenshot")["result"]
    assert r["isError"] is False and r["content"][0]["type"] == "image" and r["content"][0]["mimeType"] == "image/png"
    assert base64.b64decode(r["content"][0]["data"]).startswith(b"\x89PNG")
    g = call(srv, "guest_screenshot")["result"]
    assert base64.b64decode(g["content"][0]["data"]) == b"\x89PNG-guest"


def test_input_tools_reach_the_vm(srv):
    call(srv, "vm_keys", {"keys": ["alt", "f2"]})
    call(srv, "vm_type", {"text": "hello"})
    call(srv, "vm_click", {"x": 0.5, "y": 0.25, "double": True})
    assert srv.m.vm.sent == [("keys", ["alt", "f2"]), ("type", "hello"), ("click", 0.5, 0.25, True)]


def test_put_file_reads_the_local_file_and_forwards_base64(srv, tmp_path):
    f = tmp_path / "a.svg"
    f.write_bytes(b"<svg/>")
    r = call(srv, "guest_put_file", {"local_path": str(f), "guest_path": "/usr/share/hscl/a.svg"})["result"]
    assert json.loads(r["content"][0]["text"]) == {"path": "/usr/share/hscl/a.svg", "bytes": 6}


@pytest.mark.parametrize("name,args", [
    ("vm_keys", {}), ("vm_keys", {"keys": "alt"}), ("vm_click", {"x": "a", "y": 1}), ("vm_type", {"text": 5}),
    ("vm_start", {"firmware": "coreboot"}), ("vm_start", {"memory_mb": True}), ("vm_stop", {"evil": 1}),
    ("guest_put_file", {"local_path": "x"}), ("guest_put_file", {"local_path": "x", "guest_path": "/y", "mode": "4755"}),
])
def test_invalid_arguments_are_protocol_errors(srv, name, args):
    r = call(srv, name, args)
    assert r["error"]["code"] == -32602


def test_unknown_tool_and_method(srv):
    assert call(srv, "rm_rf")["error"]["code"] == -32602
    assert srv.handle({"jsonrpc": "2.0", "id": 9, "method": "resources/list"})["error"]["code"] == -32601


def test_tool_failures_are_results_with_iserror(srv):
    r = call(srv, "vm_screenshot", {"name": "other"})["result"]
    assert r["isError"] is True and "no running VM" in r["content"][0]["text"]


def test_memory_guard_blocks_vm_start(tmp_path, monkeypatch):
    monkeypatch.setattr(vmmod.q, "free_memory_mb", lambda: 1000)
    m = vmmod.VmManager(tmp_path)
    iso = tmp_path / "x.iso"
    iso.write_bytes(b"x")
    with pytest.raises(vmmod.VmError, match="refusing to start"):
        m.start("t", str(iso), None, 4096)


def test_vm_start_rejects_bad_input(tmp_path):
    m = vmmod.VmManager(tmp_path, mem_guard=False)
    with pytest.raises(vmmod.VmError):
        m.start("t", None, "disk.img", 4096)         # not qcow2
    with pytest.raises(vmmod.VmError):
        m.start("t", str(tmp_path / "missing.iso"), None, 4096)
    with pytest.raises(vmmod.VmError):
        m.start("t", None, None, 99999)


def test_stdio_roundtrip_in_a_real_subprocess():
    reqs = "\n".join(json.dumps(x) for x in (
        {"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}},
        {"jsonrpc": "2.0", "method": "notifications/initialized"},
        {"jsonrpc": "2.0", "id": 2, "method": "tools/list"},
    )) + "\nnot json\n"
    p = subprocess.run([sys.executable, str(ROOT / "scripts/workshop_mcp.py")], input=reqs, capture_output=True, text=True, timeout=30)
    lines = [json.loads(x) for x in p.stdout.splitlines()]
    assert lines[0]["id"] == 1 and lines[1]["id"] == 2 and len(lines[1]["result"]["tools"]) >= 13
    assert lines[2]["error"]["code"] == -32700


def test_project_mcp_config_points_at_the_entry_point():
    cfg = json.loads((ROOT / ".mcp.json").read_text())
    assert cfg["mcpServers"]["hscl-workshop"]["args"] == ["scripts/workshop_mcp.py"]
    assert (ROOT / "scripts/workshop_mcp.py").exists()
