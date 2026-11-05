"""HSCL1 Workshop MCP server (stdio, JSON-RPC 2.0, newline-delimited). Local only: no network listener.

Tools let an agent run a VM, take screenshots, send keys/text/clicks, and use the guest Workshop API
(status, doctor, screenshot, put_file, run_hook, restart_shell, respin). Every tool has a JSON schema; arguments are validated.
"""
from __future__ import annotations

import base64
import json
import sys
from pathlib import Path
from typing import Any, Callable

sys.path.insert(0, str(Path(__file__).resolve().parent))
import vm as vmmod  # noqa: E402

PROTOCOL = "2024-11-05"
Content = list[dict]


def text(s: str) -> Content:
    return [{"type": "text", "text": s}]


def png(b: bytes) -> Content:
    return [{"type": "image", "data": base64.b64encode(b).decode(), "mimeType": "image/png"}]


def schema(props: dict, required: list[str] | None = None) -> dict:
    return {"type": "object", "properties": props, "required": required or [], "additionalProperties": False}


S, N, I, B = {"type": "string"}, {"type": "number"}, {"type": "integer"}, {"type": "boolean"}
NAME = {"type": "string", "description": "VM name (default: default)", "default": "default"}


class Server:
    def __init__(self, manager: vmmod.VmManager | None = None):
        self.m = manager or vmmod.VmManager()
        self.tools: dict[str, tuple[str, dict, Callable[[dict], Content]]] = {}
        self._register()

    def tool(self, name: str, desc: str, sch: dict, fn: Callable[[dict], Content]) -> None:
        self.tools[name] = (desc, sch, fn)

    def vm(self, a: dict):
        return self.m.get(a.get("name", "default"))

    def _register(self) -> None:
        t = self.tool
        t("vm_start", "Start a QEMU VM from an ISO and/or a qcow2 disk (UEFI/BIOS). Refuses when memory is low.",
          schema({"name": NAME, "iso": S, "disk": S, "memory_mb": I, "firmware": {"type": "string", "enum": ["uefi", "bios"]}}),
          self._vm_start)
        t("vm_stop", "Stop a VM.", schema({"name": NAME}), lambda a: (self.m.stop(a.get("name", "default")), text("stopped"))[1])
        t("vm_list", "List VMs.", schema({}), lambda a: text(json.dumps(self.m.list())))
        t("vm_screenshot", "Screenshot of the VM display (PNG).", schema({"name": NAME}), lambda a: png(self.vm(a).screenshot_png()))
        t("vm_keys", "Press a key chord, e.g. [\"alt\",\"f2\"] (QEMU qcodes).",
          schema({"name": NAME, "keys": {"type": "array", "items": S, "minItems": 1}}, ["keys"]),
          lambda a: (self.vm(a).keys(a["keys"]), text("ok"))[1])
        t("vm_type", "Type text.", schema({"name": NAME, "text": S}, ["text"]), lambda a: (self.vm(a).type(a["text"]), text("ok"))[1])
        t("vm_click", "Click at fractional screen coordinates (0..1).",
          schema({"name": NAME, "x": N, "y": N, "double": B}, ["x", "y"]),
          lambda a: (self.vm(a).click(float(a["x"]), float(a["y"]), bool(a.get("double", False))), text("ok"))[1])
        t("guest_status", "Guest Workshop status (version, live, session user, operations).", schema({"name": NAME}),
          lambda a: text(json.dumps(self.vm(a).rpc("status"))))
        t("guest_doctor", "Run `hscl doctor --json` in the guest.", schema({"name": NAME}), lambda a: text(json.dumps(self.vm(a).rpc("doctor"))))
        t("guest_screenshot", "Screenshot from inside the guest session (spectacle).", schema({"name": NAME}),
          lambda a: png(base64.b64decode(self.vm(a).rpc("screenshot")["png_b64"])))
        t("guest_put_file", "Copy a local file into an allow-listed guest directory.",
          schema({"name": NAME, "local_path": S, "guest_path": S, "mode": {"type": "string", "enum": ["0644", "0755"]}}, ["local_path", "guest_path"]),
          lambda a: text(json.dumps(self.vm(a).rpc("put_file", {"path": a["guest_path"], "mode": a.get("mode", "0644"),
                                                              "content_b64": vmmod.b64_file(a["local_path"])}))))
        t("guest_hook", "Run a hook script from the guest hooks directory.", schema({"name": NAME, "hook": S}, ["hook"]),
          lambda a: text(json.dumps(self.vm(a).rpc("run_hook", {"name": a["hook"]}))))
        t("guest_restart_shell", "Restart the Plasma shell in the guest session.", schema({"name": NAME}),
          lambda a: text(json.dumps(self.vm(a).rpc("restart_shell"))))
        t("guest_respin", "Render the live state into a new installer ISO on a writable guest disk.",
          schema({"name": NAME, "out_dir": S}, ["out_dir"]),
          lambda a: text(json.dumps(self.vm(a).rpc("respin", {"out_dir": a["out_dir"]}, timeout=7200))))

    def _vm_start(self, a: dict) -> Content:
        name = a.get("name", "default")
        vm = self.m.start(name, a.get("iso"), a.get("disk"), a.get("memory_mb", 4096), a.get("firmware", "uefi"))
        return text(json.dumps({"started": name, "running": vm.running}))

    # ---- protocol
    def validate(self, sch: dict, args: Any) -> None:
        if not isinstance(args, dict):
            raise ValueError("arguments must be an object")
        for k in sch.get("required", []):
            if k not in args:
                raise ValueError(f"missing required argument: {k}")
        props = sch["properties"]
        for k, v in args.items():
            if k not in props:
                raise ValueError(f"unknown argument: {k}")
            want = props[k].get("type")
            ok = {"string": isinstance(v, str), "integer": isinstance(v, int) and not isinstance(v, bool),
                  "number": isinstance(v, (int, float)) and not isinstance(v, bool), "boolean": isinstance(v, bool),
                  "array": isinstance(v, list), None: True}[want]
            if not ok:
                raise ValueError(f"argument {k} must be {want}")
            if "enum" in props[k] and v not in props[k]["enum"]:
                raise ValueError(f"argument {k} must be one of {props[k]['enum']}")

    def handle(self, msg: dict) -> dict | None:
        mid, method = msg.get("id"), msg.get("method")
        is_note = "id" not in msg

        def ok(result):
            return None if is_note else {"jsonrpc": "2.0", "id": mid, "result": result}

        def err(code, message):
            return None if is_note else {"jsonrpc": "2.0", "id": mid, "error": {"code": code, "message": message}}

        if method == "initialize":
            return ok({"protocolVersion": PROTOCOL, "capabilities": {"tools": {}}, "serverInfo": {"name": "hscl-workshop", "version": "0.1.0"}})
        if method in ("notifications/initialized", "notifications/cancelled"):
            return None
        if method == "ping":
            return ok({})
        if method == "tools/list":
            return ok({"tools": [{"name": n, "description": d, "inputSchema": s} for n, (d, s, _f) in self.tools.items()]})
        if method == "tools/call":
            params = msg.get("params") or {}
            name = params.get("name")
            if name not in self.tools:
                return err(-32602, f"unknown tool: {name}")
            desc, sch, fn = self.tools[name]
            try:
                self.validate(sch, params.get("arguments", {}))
                return ok({"content": fn(params.get("arguments", {})), "isError": False})
            except ValueError as e:
                return err(-32602, str(e))
            except Exception as e:  # noqa: BLE001  tool failures are results, not protocol errors
                return ok({"content": text(f"{type(e).__name__}: {e}"), "isError": True})
        return err(-32601, f"method not found: {method}")

    def serve(self, rfile=None, wfile=None) -> None:
        rfile = rfile or sys.stdin
        wfile = wfile or sys.stdout
        for line in rfile:
            line = line.strip()
            if not line:
                continue
            try:
                msg = json.loads(line)
                resp = self.handle(msg) if isinstance(msg, dict) else {"jsonrpc": "2.0", "id": None, "error": {"code": -32600, "message": "invalid request"}}
            except json.JSONDecodeError:
                resp = {"jsonrpc": "2.0", "id": None, "error": {"code": -32700, "message": "parse error"}}
            if resp is not None:
                wfile.write(json.dumps(resp) + "\n")
                wfile.flush()
        self.m.stop_all()


def main() -> int:
    Server().serve()
    return 0


if __name__ == "__main__":
    sys.exit(main())
