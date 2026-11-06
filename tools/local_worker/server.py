#!/usr/bin/env python3
"""MCP server `localdelegate` (plan L, task L5): one tool, `local_code`, over stdio (newline-delimited JSON-RPC).

The tool asks a LOCAL model (through the loopback gateway) to edit named files so that a caller-chosen test command passes. The work
happens in a throwaway copy; the answer is a verdict plus a unified diff that is only a PROPOSAL (`applied` is always false): the
caller reviews and applies it. Surface kept deliberately small: no directory argument (the root comes from HSCL_WORKER_ROOT), a
short allow-list of test executables, bounded sizes, a free-RAM gate before every run. Secrets never enter prompts or results.
"""
from __future__ import annotations

import json
import os
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Mapping, TextIO

import gateway
import loop
import memgate

NAME = "localdelegate"
VERSION = "0.1.0"
DEFAULT_PROTOCOL = "2025-06-18"
ALLOWED_EXE = {"python", "python3", "py", "pytest", "cargo", "node", "npm"}
MODEL_RE = r"^[A-Za-z0-9][A-Za-z0-9._-]{0,63}$"
MAX_TASK = 8000
MAX_FILES = 8
MAX_CMD = 16
MAX_DIFF = 20000
MAX_OUT = 2000
# Resident sizes (MiB) of the models registered in the gateway; unknown models use DEFAULT_MODEL_MB.
# MEASURED peak private memory of the server process on 2026-11-06 (K q8_0 / V q4_0, c 4096): bonsai-9b 4.5-4.9 GB, bonsai-4b 3.8 GB,
# qwen3-4b about 4.1 GB resident in the gateway. The file sizes (2.7 / 1.3 / 2.5 GB) are NOT the memory cost: runtime buffers live in
# shared system memory. bonsai-27b and qwen3.5-9b are estimates (not measured yet).
MODEL_MB = {"qwen3-4b": 4300, "jev-1.5b": 0, "bonsai-27b": 9000, "bonsai-9b": 4900, "bonsai-4b": 3900, "qwen3.5-9b": 6800}
DEFAULT_MODEL_MB = 6000
KV_MB = 600

TOOL = {
    "name": "local_code",
    "description": (
        "Delegate a small, well-specified coding task to a LOCAL model. It edits only the listed files in a throwaway copy and "
        "re-runs your test command for up to max_rounds rounds. Returns {ok, rounds, reason, diff, last_output, applied:false}. "
        "The diff is a proposal; review it and apply it yourself. Escalate to a stronger model when ok is false."
    ),
    "inputSchema": {
        "type": "object",
        "properties": {
            "task": {"type": "string", "description": "What to implement or fix (<= 8000 chars)."},
            "files": {"type": "array", "items": {"type": "string"}, "description": "Editable files, relative to the project root (1-8)."},
            "test_cmd": {"type": "array", "items": {"type": "string"}, "description": "Test command as argv, e.g. [\"python\", \"check.py\"]. Executable must be one of: " + ", ".join(sorted(ALLOWED_EXE)) + "."},
            "model": {"type": "string", "description": "Gateway model id (default qwen3-4b)."},
            "max_rounds": {"type": "integer", "minimum": 1, "maximum": 5},
            "protected": {"type": "array", "items": {"type": "string"}, "description": "Files that must not change (tests)."},
        },
        "required": ["task", "files", "test_cmd"],
        "additionalProperties": False,
    },
}


@dataclass
class Deps:
    root: Path
    run_task: Callable
    make_chat: Callable[[str], Callable[[list], str]]
    gate: Callable[[str], dict]


class InvalidParams(Exception):
    pass


def _rel_ok(p: object) -> bool:
    if not isinstance(p, str) or not p or len(p) > 200:
        return False
    s = p.replace("\\", "/")
    return not (s.startswith("/") or ":" in s or any(part in ("..", "") for part in s.split("/")))


def validate(args: object) -> dict:
    import re

    if not isinstance(args, dict):
        raise InvalidParams("arguments must be an object")
    allowed = set(TOOL["inputSchema"]["properties"])
    extra = set(args) - allowed
    if extra:
        raise InvalidParams(f"unknown arguments: {sorted(extra)}")
    task = args.get("task")
    if not isinstance(task, str) or not task.strip() or len(task) > MAX_TASK:
        raise InvalidParams("task must be a non-empty string of at most 8000 characters")
    for key in ("files", "protected"):
        v = args.get(key, [] if key == "protected" else None)
        if not isinstance(v, list) or (key == "files" and not 1 <= len(v) <= MAX_FILES) or len(v) > MAX_FILES:
            raise InvalidParams(f"{key} must be a list of at most {MAX_FILES} relative paths (files: at least 1)")
        if not all(_rel_ok(x) for x in v):
            raise InvalidParams(f"{key} contains a path outside the project root or an invalid path")
    cmd = args.get("test_cmd")
    if not isinstance(cmd, list) or not 1 <= len(cmd) <= MAX_CMD or not all(isinstance(c, str) and c and len(c) <= 300 for c in cmd):
        raise InvalidParams("test_cmd must be a non-empty argv list of at most 16 strings")
    exe = Path(cmd[0]).name.lower().removesuffix(".exe")
    if exe not in ALLOWED_EXE:
        raise InvalidParams(f"test_cmd[0] must be one of {sorted(ALLOWED_EXE)}")
    rounds = args.get("max_rounds", 3)
    if isinstance(rounds, bool) or not isinstance(rounds, int) or not 1 <= rounds <= 5:
        raise InvalidParams("max_rounds must be an integer from 1 to 5")
    model = args.get("model", "qwen3-4b")
    if not isinstance(model, str) or not re.fullmatch(MODEL_RE, model):
        raise InvalidParams("model must be a plain gateway model id")
    return {"task": task, "files": args["files"], "protected": args.get("protected", []), "test_cmd": cmd, "max_rounds": rounds, "model": model}


def _text(obj: object, is_error: bool) -> dict:
    return {"content": [{"type": "text", "text": obj if isinstance(obj, str) else json.dumps(obj, ensure_ascii=False)}], "isError": is_error}


def _call(args: dict, deps: Deps) -> dict:
    a = validate(args)
    g = deps.gate(a["model"])
    if not g["ok"]:
        return _text(f"memory_gate: {g['reason']}", True)
    try:
        res = deps.run_task(
            deps.make_chat(a["model"]), deps.root, a["files"], a["task"], a["test_cmd"],
            max_rounds=a["max_rounds"], protected=a["protected"],
        )
    except gateway.GatewayError as e:
        return _text(f"gateway_error: {e.code}", True)
    body = {
        "ok": res.ok, "rounds": res.rounds, "reason": res.reason,
        "diff": res.diff[:MAX_DIFF], "last_output": res.last_output[-MAX_OUT:],
        "applied": False, "note": "The diff is a proposal: review it, then apply it yourself.",
    }
    return _text(body, False)


def handle(msg: object, deps: Deps) -> dict | None:
    if not isinstance(msg, dict) or "method" not in msg:
        return {"jsonrpc": "2.0", "id": None, "error": {"code": -32600, "message": "invalid request"}}
    mid, method, params = msg.get("id"), msg["method"], msg.get("params") or {}
    if "id" not in msg:
        return None  # notification: never answered

    def ok(result: object) -> dict:
        return {"jsonrpc": "2.0", "id": mid, "result": result}

    def err(code: int, message: str) -> dict:
        return {"jsonrpc": "2.0", "id": mid, "error": {"code": code, "message": message}}

    if method == "initialize":
        proto = params.get("protocolVersion") if isinstance(params, dict) else None
        return ok({"protocolVersion": proto if isinstance(proto, str) else DEFAULT_PROTOCOL, "capabilities": {"tools": {}}, "serverInfo": {"name": NAME, "version": VERSION}})
    if method == "ping":
        return ok({})
    if method == "tools/list":
        return ok({"tools": [TOOL]})
    if method == "tools/call":
        if not isinstance(params, dict) or params.get("name") != "local_code":
            return err(-32602, "unknown tool")
        try:
            return ok(_call(params.get("arguments"), deps))
        except InvalidParams as e:
            return err(-32602, str(e))
    return err(-32601, f"method not found: {method}")


def serve(stdin: TextIO, stdout: TextIO, deps: Deps) -> None:
    for line in stdin:
        line = line.strip()
        if not line:
            continue
        try:
            msg = json.loads(line)
        except json.JSONDecodeError:
            reply: dict | None = {"jsonrpc": "2.0", "id": None, "error": {"code": -32700, "message": "parse error"}}
        else:
            reply = handle(msg, deps)
        if reply is not None:
            stdout.write(json.dumps(reply, ensure_ascii=False) + "\n")
            stdout.flush()


def make_deps(env: Mapping[str, str] | None = None) -> Deps:
    env = os.environ if env is None else env
    # HSCL_WORKER_ROOT wins; Claude Code sets CLAUDE_PROJECT_DIR in the environment of the servers it spawns; OpenCode starts the
    # server in the workspace, so "HSCL_WORKER_ROOT": "." works there.
    name = "HSCL_WORKER_ROOT" if env.get("HSCL_WORKER_ROOT") else "CLAUDE_PROJECT_DIR"
    raw = env.get(name, "")
    root = Path(raw).resolve() if raw else None
    if root is None or not root.is_dir():
        raise ValueError("HSCL_WORKER_ROOT (or CLAUDE_PROJECT_DIR) must point to an existing project directory")
    reserve = int(env.get("HSCL_WORKER_RESERVE_MB", memgate.DEFAULT_RESERVE_MB))
    base = env.get("HSCL_WORKER_GATEWAY", gateway.DEFAULT_URL)

    def gate(model: str) -> dict:
        return memgate.decide(MODEL_MB.get(model, DEFAULT_MODEL_MB), KV_MB, memgate.free_mb(), reserve)

    def make_chat(model: str) -> Callable[[list], str]:
        return lambda msgs: gateway.chat(msgs, model, max_tokens=1500, base_url=base)

    return Deps(root=root, run_task=loop.run_task, make_chat=make_chat, gate=gate)


def main() -> int:
    try:
        deps = make_deps()
    except ValueError as e:
        print(f"{NAME}: {e}", file=sys.stderr)
        return 2
    serve(sys.stdin, sys.stdout, deps)
    return 0


if __name__ == "__main__":
    sys.exit(main())
