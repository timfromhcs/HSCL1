"""Plan L, Task L6: one source (ai-shared/) generates the Claude Code and OpenCode files for the local worker."""
import json
import re
import shutil
import sys
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))
import round_log  # noqa: E402
import sync_ai_shared as sync  # noqa: E402


@pytest.fixture
def repo(tmp_path):
    shutil.copytree(ROOT / "ai-shared", tmp_path / "ai-shared")
    (tmp_path / ".mcp.json").write_text(json.dumps({"mcpServers": {"hscl-workshop": {"command": "python", "args": ["x.py"]}}}, indent=2), encoding="utf-8")
    return tmp_path


def front(text: str) -> tuple[dict, str]:
    assert text.startswith("---\n")
    head, body = text[4:].split("\n---\n", 1)
    return yaml.safe_load(head), body


def test_mcp_json_adds_only_our_server_and_keeps_the_others(repo):
    out = sync.render(repo)
    d = json.loads(out[".mcp.json"])
    assert set(d["mcpServers"]) == {"hscl-workshop", "localdelegate"}
    assert d["mcpServers"]["hscl-workshop"] == {"command": "python", "args": ["x.py"]}
    ld = d["mcpServers"]["localdelegate"]
    assert ld["command"] == "python" and ld["args"] == ["${CLAUDE_PROJECT_DIR:-.}/tools/local_worker/server.py"]
    assert "env" not in ld  # Claude Code provides CLAUDE_PROJECT_DIR to the spawned server itself


def test_claude_agent_can_only_use_the_one_delegate_tool(repo):
    meta, body = front(sync.render(repo)[".claude/agents/local-worker.md"])
    assert meta["name"] == "local-worker" and meta["description"]
    assert meta["tools"] == "mcp__localdelegate__local_code"
    assert {x.strip() for x in meta["disallowedTools"].split(",")} >= {"Write", "Edit", "Bash"}
    assert meta["model"] == "haiku" and meta["maxTurns"] == 3
    assert "local_code" in body and "ESCALATE" in body


def test_opencode_agent_denies_everything_then_allows_the_one_tool(repo):
    meta, body = front(sync.render(repo)[".opencode/agents/local-worker.md"])
    assert meta["mode"] == "subagent" and meta["steps"] == 4
    perms = meta["permissions"]
    assert perms[0] == {"action": "*", "resource": "*", "effect": "deny"}  # last match wins: broad deny first
    allowed = [p for p in perms if p["effect"] == "allow"]
    assert [p["action"] for p in allowed] == ["localdelegate_local_code*"]
    assert {"edit", "shell"} <= {p["action"] for p in perms if p["effect"] == "deny"}
    assert "local_code" in body


def test_opencode_json_registers_the_server_with_a_relative_root(repo):
    d = json.loads(sync.render(repo)["opencode.json"])
    s = d["mcp"]["servers"]["localdelegate"]
    assert s["type"] == "local" and s["command"] == ["python", "tools/local_worker/server.py"]
    assert s["environment"] == {"HSCL_WORKER_ROOT": "."} and s.get("disabled") is False


def test_existing_opencode_json_content_is_preserved(repo):
    (repo / "opencode.json").write_text(json.dumps({"instructions": ["AGENTS.md"], "mcp": {"servers": {"other": {"type": "local", "command": ["x"]}}}}), encoding="utf-8")
    d = json.loads(sync.render(repo)["opencode.json"])
    assert d["instructions"] == ["AGENTS.md"] and set(d["mcp"]["servers"]) == {"other", "localdelegate"}


def test_generated_text_has_no_secrets_and_no_unmeasured_claims(repo):
    forbidden = ["TurboQuant 3", "TQ3_0", "24 GB", "active on Vulkan", "ghp_", "password"]
    for path, text in sync.render(repo).items():
        for bad in forbidden:
            assert bad not in text, f"{path} contains {bad!r}"
        for pat in round_log.SECRET_PATTERNS:
            assert not pat.search(text), f"{path} matches a secret pattern"
    for p in (ROOT / "ai-shared").rglob("*"):
        if p.is_file():
            for bad in forbidden[:4]:
                assert bad not in p.read_text(encoding="utf-8"), f"{p} contains {bad!r}"


def test_render_is_deterministic(repo):
    assert sync.render(repo) == sync.render(repo)


def test_check_reports_drift_and_write_fixes_it(repo):
    assert sorted(sync.check(repo)) == sorted(sync.render(repo))  # nothing written yet: everything drifts
    sync.write(repo)
    assert sync.check(repo) == []
    (repo / ".claude/agents/local-worker.md").write_text("tampered\n", encoding="utf-8")
    assert sync.check(repo) == [".claude/agents/local-worker.md"]


def test_the_real_repository_is_in_sync():
    assert sync.check(ROOT) == [], "run: python scripts/sync_ai_shared.py --write"


def test_cli_exit_codes(repo, capsys):
    assert sync.main(["--root", str(repo), "--check"]) == 1
    assert sync.main(["--root", str(repo), "--write"]) == 0
    assert sync.main(["--root", str(repo), "--check"]) == 0
    assert re.search(r"in sync", capsys.readouterr().out)
