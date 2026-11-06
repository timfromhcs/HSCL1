"""Plan L, Task L5: stdio MCP server `localdelegate` exposing exactly one tool, local_code."""
import io
import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "tools" / "local_worker"))
import gateway  # noqa: E402
import loop  # noqa: E402
import server  # noqa: E402


class Deps(server.Deps):
    pass


def make(tmp_path, run_task=None, gate=None, chat=None):
    calls = []

    def fake_run(chat_fn, workdir, files, task, test_cmd, **kw):
        calls.append({"workdir": workdir, "files": list(files), "task": task, "test_cmd": list(test_cmd), **kw})
        return loop.Result(True, 1, "--- a/x.py\n+++ b/x.py\n+print(1)\n", "ok", "green")

    d = server.Deps(
        root=tmp_path,
        run_task=run_task or fake_run,
        make_chat=lambda model: (chat or (lambda msgs: "unused")),
        gate=gate or (lambda model: {"ok": True, "reason": "enough available RAM"}),
    )
    return d, calls


def call(d, method, params=None, id_=1):
    msg = {"jsonrpc": "2.0", "method": method}
    if id_ is not None:
        msg["id"] = id_
    if params is not None:
        msg["params"] = params
    return server.handle(msg, d)


ARGS = {"task": "make x print 1", "files": ["x.py"], "test_cmd": ["python", "check.py"]}


def test_initialize_announces_tools_only(tmp_path):
    d, _ = make(tmp_path)
    r = call(d, "initialize", {"protocolVersion": "2025-06-18", "capabilities": {}, "clientInfo": {"name": "t", "version": "1"}})
    assert r["result"]["serverInfo"]["name"] == "localdelegate"
    assert r["result"]["capabilities"] == {"tools": {}}
    assert r["result"]["protocolVersion"] == "2025-06-18"


def test_notifications_get_no_answer(tmp_path):
    d, _ = make(tmp_path)
    assert call(d, "notifications/initialized", id_=None) is None


def test_exactly_one_tool_with_a_strict_schema(tmp_path):
    d, _ = make(tmp_path)
    tools = call(d, "tools/list")["result"]["tools"]
    assert [t["name"] for t in tools] == ["local_code"]
    schema = tools[0]["inputSchema"]
    assert set(schema["required"]) == {"task", "files", "test_cmd"} and schema["additionalProperties"] is False


def test_happy_path_returns_a_verdict_and_never_applies_the_diff(tmp_path):
    d, calls = make(tmp_path)
    r = call(d, "tools/call", {"name": "local_code", "arguments": {**ARGS, "max_rounds": 2}})["result"]
    body = json.loads(r["content"][0]["text"])
    assert r["isError"] is False and body["ok"] is True and body["reason"] == "green" and "+print(1)" in body["diff"]
    assert body["applied"] is False
    assert calls[0]["workdir"] == tmp_path and calls[0]["files"] == ["x.py"] and calls[0]["max_rounds"] == 2


def test_a_red_verdict_is_a_normal_result_not_a_tool_error(tmp_path):
    d, _ = make(tmp_path, run_task=lambda *a, **k: loop.Result(False, 3, "", "AssertionError", "max_rounds"))
    r = call(d, "tools/call", {"name": "local_code", "arguments": ARGS})["result"]
    assert r["isError"] is False and json.loads(r["content"][0]["text"])["ok"] is False


@pytest.mark.parametrize(
    "bad",
    [
        {"files": ["x.py"], "test_cmd": ["python", "c.py"]},  # no task
        {**ARGS, "task": ""},
        {**ARGS, "files": "x.py"},
        {**ARGS, "files": []},
        {**ARGS, "files": ["a.py"] * 9},
        {**ARGS, "files": ["../x.py"]},
        {**ARGS, "files": ["/etc/passwd"]},
        {**ARGS, "test_cmd": ["rm", "-rf", "/"]},
        {**ARGS, "test_cmd": []},
        {**ARGS, "test_cmd": ["python"] + ["a"] * 20},
        {**ARGS, "max_rounds": 99},
        {**ARGS, "max_rounds": "3"},
        {**ARGS, "model": "../../etc"},
        {**ARGS, "extra": 1},
        {**ARGS, "task": "x" * 9000},
    ],
)
def test_invalid_arguments_are_rejected_with_32602(tmp_path, bad):
    d, calls = make(tmp_path)
    r = call(d, "tools/call", {"name": "local_code", "arguments": bad})
    assert r["error"]["code"] == -32602 and not calls


def test_unknown_tool_and_method(tmp_path):
    d, _ = make(tmp_path)
    assert call(d, "tools/call", {"name": "bash", "arguments": {}})["error"]["code"] == -32602
    assert call(d, "resources/list")["error"]["code"] == -32601


def test_closed_memory_gate_is_a_tool_error_and_runs_nothing(tmp_path):
    d, calls = make(tmp_path, gate=lambda model: {"ok": False, "reason": "short by 1963 MiB"})
    r = call(d, "tools/call", {"name": "local_code", "arguments": ARGS})["result"]
    assert r["isError"] is True and "memory_gate" in r["content"][0]["text"] and not calls


def test_gateway_failure_is_a_tool_error_with_its_code(tmp_path):
    def boom(*a, **k):
        raise gateway.GatewayError("unavailable", "connection refused")

    d, _ = make(tmp_path, run_task=boom)
    r = call(d, "tools/call", {"name": "local_code", "arguments": ARGS})["result"]
    assert r["isError"] is True and "unavailable" in r["content"][0]["text"]


def test_serve_handles_a_session_and_survives_garbage(tmp_path):
    d, _ = make(tmp_path)
    lines = [
        json.dumps({"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {"protocolVersion": "2025-06-18"}}),
        "this is not json",
        json.dumps({"jsonrpc": "2.0", "method": "notifications/initialized"}),
        json.dumps({"jsonrpc": "2.0", "id": 2, "method": "tools/list"}),
        json.dumps({"jsonrpc": "2.0", "id": 3, "method": "ping"}),
    ]
    out = io.StringIO()
    server.serve(io.StringIO("\n".join(lines) + "\n"), out, d)
    replies = [json.loads(x) for x in out.getvalue().splitlines()]
    assert [r.get("id") for r in replies] == [1, None, 2, 3]
    assert replies[1]["error"]["code"] == -32700
    assert replies[3]["result"] == {}


def test_make_deps_requires_a_real_root_directory(tmp_path):
    with pytest.raises(ValueError, match="HSCL_WORKER_ROOT"):
        server.make_deps({})
    with pytest.raises(ValueError, match="HSCL_WORKER_ROOT"):
        server.make_deps({"HSCL_WORKER_ROOT": str(tmp_path / "missing")})
    assert server.make_deps({"HSCL_WORKER_ROOT": str(tmp_path)}).root == tmp_path.resolve()


def test_script_entry_point_speaks_mcp_over_real_stdio(tmp_path):
    """Process-level test (lesson of 2026-11-06): the file must serve when run as a program, not only as imported functions."""
    import os
    import subprocess

    script = Path(__file__).resolve().parents[2] / "tools" / "local_worker" / "server.py"
    req = "\n".join(
        [
            json.dumps({"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {"protocolVersion": "2025-06-18"}}),
            json.dumps({"jsonrpc": "2.0", "id": 2, "method": "tools/list"}),
        ]
    ) + "\n"
    env = {**os.environ, "HSCL_WORKER_ROOT": str(tmp_path)}
    r = subprocess.run([sys.executable, str(script)], input=req, capture_output=True, text=True, env=env, timeout=30)
    replies = [json.loads(x) for x in r.stdout.splitlines()]
    assert r.returncode == 0 and [x["id"] for x in replies] == [1, 2]
    assert replies[1]["result"]["tools"][0]["name"] == "local_code"
    env.pop("HSCL_WORKER_ROOT")
    bad = subprocess.run([sys.executable, str(script)], input="", capture_output=True, text=True, env=env, timeout=30)
    assert bad.returncode == 2 and "HSCL_WORKER_ROOT" in bad.stderr
