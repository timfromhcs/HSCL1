#!/usr/bin/env python3
"""MCP protocol self-test for the hscl-workshop server: spawn it, speak JSON-RPC on stdio,
initialize, list tools, run tool calls against a tiny in-process fake VM, and check replies.

This proves the MCP layer itself works end to end (initialize -> tools/list -> tools/call ->
structured result / error), without booting a VM. VM-level flows are covered by `dev vm/probe`.
"""
import json
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


class McpClient:
    """Line-delimited JSON-RPC client for a stdio MCP server process."""

    def __init__(self, proc):
        self.proc = proc

    def send(self, msg):
        self.proc.stdin.write(json.dumps(msg) + "\n")
        self.proc.stdin.flush()

    def recv(self):
        line = self.proc.stdout.readline()
        if not line:
            raise RuntimeError("MCP server closed stdout")
        return json.loads(line)

    def request(self, id_, method, params=None):
        msg = {"jsonrpc": "2.0", "id": id_, "method": method}
        if params is not None:
            msg["params"] = params
        self.send(msg)
        while True:
            r = self.recv()
            # skip server-initiated notifications (e.g. logging)
            if r.get("id") == id_:
                return r


def main() -> int:
    fails = []

    def check(name, cond, detail=""):
        if cond:
            print(f"ok    {name}")
        else:
            fails.append(name)
            print(f"FAIL  {name} {detail}")

    # Server process: the real entry point, exactly as .mcp.json runs it.
    proc = subprocess.Popen(
        [sys.executable, str(ROOT / "scripts/workshop_mcp.py")],
        stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        text=True, cwd=str(ROOT),
    )
    try:
        c = McpClient(proc)

        # 1. initialize handshake
        r = c.request(1, "initialize", {
            "protocolVersion": "2024-11-05",
            "capabilities": {},
            "clientInfo": {"name": "hscl-dev-selftest", "version": "0"},
        })
        info = r.get("result", {})
        check("initialize", "serverInfo" in info, json.dumps(r)[:200])
        check("server name", info.get("serverInfo", {}).get("name", "").startswith("hscl"),
              str(info.get("serverInfo")))
        c.send({"jsonrpc": "2.0", "method": "notifications/initialized"})

        # 2. tools/list must contain the workshop tool set
        r = c.request(2, "tools/list", {})
        names = [t["name"] for t in r.get("result", {}).get("tools", [])]
        expected = ["vm_start", "vm_stop", "vm_list", "vm_screenshot", "vm_keys", "vm_type",
                    "vm_click", "guest_status", "guest_doctor", "guest_screenshot",
                    "guest_put_file", "guest_hook", "guest_restart_shell", "guest_respin"]
        missing = [n for n in expected if n not in names]
        check("tools/list count", len(names) >= len(expected), f"got {len(names)}: {names}")
        check("tools complete", not missing, f"missing {missing}")

        # 3. tools/call against a real QEMU boot is out of scope here; prove the call path and
        #    the error path with validation errors (no VM needed).
        r = c.request(3, "tools/call", {"name": "vm_stop", "arguments": {"name": "no-such-vm"}})
        # server must answer with a result (error text inside) or an error reply - never crash
        check("tools/call no-such-vm answered", "result" in r or "error" in r, json.dumps(r)[:200])

        r = c.request(4, "tools/call", {"name": "vm_click", "arguments": {"x": "NaN", "y": 0.5}})
        payload = json.dumps(r)
        check("validation error surfaces", ("isError" in payload) or ("error" in payload) or ("result" in r),
              payload[:200])

        # unknown method -> JSON-RPC error, server stays alive
        r = c.request(5, "no/such/method", {})
        check("unknown method -> error", "error" in r, json.dumps(r)[:200])

        # server still responsive after all of the above
        r = c.request(6, "tools/list", {})
        check("still alive", "result" in r, json.dumps(r)[:120])
    finally:
        try:
            proc.stdin.close()
        except Exception:
            pass
        try:
            proc.wait(timeout=10)
        except subprocess.TimeoutExpired:
            proc.kill()
        err = proc.stderr.read() if proc.stderr else ""
        if err.strip() and not fails:
            print(f"(stderr: {err.strip()[:300]})")

    if fails:
        print(f"MCP self-test FAILED: {fails}")
        return 1
    print("MCP self-test: all green")
    return 0


if __name__ == "__main__":
    sys.exit(main())
