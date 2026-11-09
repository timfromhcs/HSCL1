"""`hscl mcp` stdio JSON-RPC 2.0 protocol conformance and tool validation."""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]


def find_hscl_binary() -> Path | None:
    debug_bin = ROOT / "target" / "debug" / ("hscl.exe" if os.name == "nt" else "hscl")
    if debug_bin.is_file():
        return debug_bin
    which = shutil.which("hscl")
    if which:
        return Path(which)
    return None


@pytest.fixture
def hscl_bin() -> Path:
    b = find_hscl_binary()
    if b is None:
        pytest.skip("hscl binary not compiled in target/debug")
    return b


class McpSession:
    def __init__(self, binary: Path, allow_write: bool = False):
        args = [str(binary), "mcp"]
        if allow_write:
            args.append("--allow-write")
        self.proc = subprocess.Popen(
            args,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True, encoding="utf-8", errors="replace",
            cwd=str(ROOT),
        )

    def req(self, id_: int, method: str, params: dict | None = None) -> dict:
        msg = {"jsonrpc": "2.0", "id": id_, "method": method}
        if params is not None:
            msg["params"] = params
        self.proc.stdin.write(json.dumps(msg) + "\n")
        self.proc.stdin.flush()
        line = self.proc.stdout.readline()
        assert line, "server exited unexpectedly"
        return json.loads(line)

    def close(self):
        try:
            self.proc.stdin.close()
            self.proc.terminate()
            self.proc.wait(timeout=2)
        except Exception:
            self.proc.kill()


def test_hscl_mcp_handshake_and_read_only_tools(hscl_bin: Path):
    s = McpSession(hscl_bin, allow_write=False)
    try:
        init = s.req(1, "initialize", {
            "protocolVersion": "2024-11-05",
            "capabilities": {},
            "clientInfo": {"name": "pytest-client", "version": "1.0"},
        })
        assert init.get("result", {}).get("protocolVersion") == "2024-11-05"
        assert "Read-only" in init["result"]["instructions"]

        tools = s.req(2, "tools/list", {})
        names = [t["name"] for t in tools["result"]["tools"]]
        assert len(names) == 18
        assert "hscl_version" in names
        assert "hscl_cqhecs_status" in names
        assert "hscl_memory_status" in names
        assert "hscl_lab_status" in names
        assert "hscl_wallpaper_list" in names
        assert "hscl_language_status" in names
        assert "hscl_language_list" in names
        assert "hscl_privacy_status" in names
        assert "hscl_wallpaper_apply" not in names  # write tool hidden in read-only mode
        assert "hscl_language_set" not in names  # write tool hidden in read-only mode

        # Tool calls return structured text content and no protocol error
        ver = s.req(3, "tools/call", {"name": "hscl_version", "arguments": {}})
        assert ver.get("result", {}).get("isError") is False
        assert "HSCL1" in ver["result"]["content"][0]["text"]

        cq = s.req(4, "tools/call", {"name": "hscl_cqhecs_status", "arguments": {}})
        assert cq.get("result", {}).get("isError") is False
        assert "runtime" in cq["result"]["content"][0]["text"]

        mem = s.req(5, "tools/call", {"name": "hscl_memory_status", "arguments": {}})
        assert mem.get("result", {}).get("isError") is False
        assert "ai_budget_percent" in mem["result"]["content"][0]["text"]

        lab = s.req(6, "tools/call", {"name": "hscl_lab_status", "arguments": {}})
        assert lab.get("result", {}).get("isError") is False
        assert "labs_root" in lab["result"]["content"][0]["text"]
    finally:
        s.close()


def test_hscl_mcp_allow_write_tools(hscl_bin: Path):
    s = McpSession(hscl_bin, allow_write=True)
    try:
        s.req(1, "initialize", {"protocolVersion": "2024-11-05", "capabilities": {}, "clientInfo": {"name": "test"}})
        tools = s.req(2, "tools/list", {})
        names = [t["name"] for t in tools["result"]["tools"]]
        assert len(names) == 22
        assert "hscl_wallpaper_apply" in names
        assert "hscl_theme_set" in names
        assert "hscl_graphics_apply" in names
        assert "hscl_language_set" in names

        # Invalid preset argument is rejected with JSON-RPC error
        bad = s.req(3, "tools/call", {"name": "hscl_wallpaper_apply", "arguments": {"name": "../traversal"}})
        assert bad.get("error", {}).get("code") == -32602
    finally:
        s.close()
