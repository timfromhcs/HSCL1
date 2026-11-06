#!/usr/bin/env python3
"""Generate the Claude Code and OpenCode files for the local worker from ONE source (`ai-shared/`), plan L task L6.

Owned (rewritten completely): `.claude/agents/local-worker.md`, `.opencode/agents/local-worker.md`.
Merged (only our entry is added or replaced, everything else is kept): `.mcp.json` (`mcpServers.localdelegate`) and
`opencode.json` (`mcp.servers.localdelegate`). Nothing here contains a secret or a claim that is not backed by a measurement.

Usage: python scripts/sync_ai_shared.py [--root DIR] (--check | --write)
Exit codes: 0 = in sync / written, 1 = drift found (with --check).
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


def _load_spec(root: Path) -> tuple[dict, str]:
    spec = json.loads((root / "ai-shared" / "spec.json").read_text(encoding="utf-8"))
    body = (root / "ai-shared" / "local-worker.prompt.md").read_text(encoding="utf-8").strip() + "\n"
    return spec, body


def _json(obj: object) -> str:
    return json.dumps(obj, indent=2, ensure_ascii=False) + "\n"


def _existing(root: Path, name: str) -> dict:
    p = root / name
    return json.loads(p.read_text(encoding="utf-8")) if p.is_file() else {}


def render(root: Path) -> dict[str, str]:
    root = Path(root)
    spec, body = _load_spec(root)
    srv, agent = spec["server"], spec["agent"]
    tool = f"mcp__{srv['name']}__{srv['tool']}"
    desc = json.dumps(agent["description"], ensure_ascii=False)

    mcp = _existing(root, ".mcp.json")
    mcp.setdefault("mcpServers", {})[srv["name"]] = {
        "command": "python",
        "args": ["${CLAUDE_PROJECT_DIR:-.}/" + srv["script"]],
    }

    oc = _existing(root, "opencode.json")
    oc.setdefault("$schema", "https://opencode.ai/config.json")
    oc.setdefault("mcp", {}).setdefault("servers", {})[srv["name"]] = {
        "type": "local",
        "command": ["python", srv["script"]],
        "environment": {"HSCL_WORKER_ROOT": "."},
        "disabled": False,
    }

    claude = (
        "---\n"
        f"name: {agent['name']}\n"
        f"description: {desc}\n"
        f"tools: {tool}\n"
        "disallowedTools: Write, Edit, Bash\n"
        f"model: {agent['claude']['model']}\n"
        f"maxTurns: {agent['claude']['maxTurns']}\n"
        "---\n" + body
    )
    opencode = (
        "---\n"
        f"description: {desc}\n"
        "mode: subagent\n"
        f"steps: {agent['opencode']['steps']}\n"
        "permissions:\n"
        '  - {action: "*", resource: "*", effect: deny}\n'
        '  - {action: edit, resource: "*", effect: deny}\n'
        '  - {action: shell, resource: "*", effect: deny}\n'
        f'  - {{action: "{srv["name"]}_{srv["tool"]}*", resource: "*", effect: allow}}\n'
        "---\n" + body
    )
    return {
        ".mcp.json": _json(mcp),
        "opencode.json": _json(oc),
        f".claude/agents/{agent['name']}.md": claude,
        f".opencode/agents/{agent['name']}.md": opencode,
    }


def _read(path: Path) -> str | None:
    return path.read_text(encoding="utf-8") if path.is_file() else None


def check(root: Path) -> list[str]:
    root = Path(root)
    return [rel for rel, text in render(root).items() if _read(root / rel) != text]


def write(root: Path) -> list[str]:
    root = Path(root)
    changed = check(root)
    for rel, text in render(root).items():
        if rel in changed:
            p = root / rel
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(text, encoding="utf-8", newline="\n")
    return changed


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    mode = ap.add_mutually_exclusive_group(required=True)
    mode.add_argument("--check", action="store_true")
    mode.add_argument("--write", action="store_true")
    a = ap.parse_args(argv)
    if a.write:
        changed = write(a.root)
        print("written: " + (", ".join(changed) if changed else "nothing to change (in sync)"))
        return 0
    drift = check(a.root)
    if drift:
        print("drift: " + ", ".join(drift) + "  (run: python scripts/sync_ai_shared.py --write)")
        return 1
    print("ai-shared outputs are in sync")
    return 0


if __name__ == "__main__":
    sys.exit(main())
