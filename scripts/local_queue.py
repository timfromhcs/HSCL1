#!/usr/bin/env python3
"""Queue for the local worker (plan L, task L8): hands tagged plan steps to a local model and keeps the results as PROPOSALS.

A queue step is an unchecked plan line of this form (one JSON object, then `::`, then the task text):

    - [ ] [local] {"files": ["impl.py"], "test_cmd": ["python", "check.py"], "protected": ["check.py"]} :: implement foo

Each step runs through the verify-patch loop (`tools/local_worker/loop.py`) behind the loopback gateway. A green result is written as a
unified diff to `artifacts/local/proposals/<id>.diff` together with a `git apply --check` verdict; nothing is applied, committed or
pushed, and plan checkboxes are never ticked here. Steps that finished are remembered in a state file and not run twice. The queue
stops when the free-RAM gate closes, the gateway fails, the wall-clock limit or the item limit is reached. Every run is recorded
with `round_log.py`.

Usage: python scripts/local_queue.py [--model bonsai-9b] [--max-items 5] [--wall-seconds 900] [--dry-run]
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent / "tools" / "local_worker"))

import gateway  # noqa: E402
import loop  # noqa: E402
import memgate  # noqa: E402
import round_log  # noqa: E402
import server  # noqa: E402

LINE_RE = re.compile(r"^\s*-\s*\[ \]\s*\[local\]\s*(.*)$")


@dataclass
class Item:
    id: str
    plan: str
    task: str
    spec: dict | None
    error: str | None


def parse_plans_text(plan: str, text: str) -> list[Item]:
    items = []
    for line in text.splitlines():
        m = LINE_RE.match(line)
        if not m:
            continue
        rest = m.group(1)
        spec_text, sep, task = rest.partition("::")
        task = task.strip() if sep else rest.strip()
        spec, error = None, None
        if not sep:
            error = "missing '::' between the JSON spec and the task text"
        else:
            try:
                spec = json.loads(spec_text)
                if not isinstance(spec, dict):
                    error, spec = "spec must be a JSON object", None
            except json.JSONDecodeError as e:
                error = f"spec is not valid JSON: {e.msg}"
        digest = hashlib.sha256(f"{plan}\n{task}\n{json.dumps(spec, sort_keys=True)}".encode("utf-8")).hexdigest()[:12]
        items.append(Item(digest, plan, task, spec, error))
    return items


def parse_plans(plans_dir: Path) -> list[Item]:
    items: list[Item] = []
    for p in sorted(Path(plans_dir).glob("*.md")):
        items.extend(parse_plans_text(p.name, p.read_text(encoding="utf-8")))
    return items


def git_applies(diff: str, root: Path) -> bool:
    if not diff.strip():
        return False
    cp = subprocess.run(["git", "apply", "--check", "-"], input=diff.encode("utf-8"), cwd=root, capture_output=True)
    return cp.returncode == 0


def _load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8")) if path.is_file() else {"done": {}}


def run_queue(
    items: list[Item],
    root: Path,
    make_chat: Callable[[str], Callable[[list], str]],
    run_task: Callable,
    gate: Callable[[str], dict],
    model: str,
    state_path: Path,
    proposals_dir: Path,
    rounds_path: Path,
    max_items: int = 5,
    wall_seconds: float = 900,
    clock: Callable[[], float] = time.monotonic,
    applies: Callable[[str, Path], bool] = git_applies,
    dry_run: bool = False,
) -> dict:
    root = Path(root)
    state = _load(Path(state_path))
    out: dict = {"model": model, "items": [], "stopped": None}
    t0 = clock()
    ran = 0
    for it in items:
        if clock() - t0 >= wall_seconds:
            out["stopped"] = "wall_clock"
            break
        row = {"id": it.id, "plan": it.plan, "task": it.task, "status": "", "proposal": None}
        out["items"].append(row)
        if it.error:
            row.update(status="invalid", reason=it.error)
            continue
        try:
            v = server.validate({"task": it.task, **(it.spec or {})})
        except server.InvalidParams as e:
            row.update(status="invalid", reason=str(e))
            continue
        if it.id in state["done"]:
            row.update(status="already_done", reason=state["done"][it.id]["reason"])
            continue
        if ran >= max_items:
            row["status"] = "deferred"
            out["stopped"] = "max_items"
            break
        if dry_run:
            row["status"] = "would_run"
            continue
        g = gate(model)
        if not g["ok"]:
            out["items"].pop()
            out["stopped"] = f"memory_gate: {g['reason']}"
            break
        try:
            res = run_task(make_chat(model), root, v["files"], v["task"], v["test_cmd"], max_rounds=v["max_rounds"], protected=v["protected"])
        except gateway.GatewayError as e:
            out["items"].pop()
            out["stopped"] = f"gateway_error: {e.code}"
            break
        ran += 1
        if res.ok:
            Path(proposals_dir).mkdir(parents=True, exist_ok=True)
            pf = Path(proposals_dir) / f"{it.id}.diff"
            pf.write_text(res.diff, encoding="utf-8", newline="\n")
            row.update(status="proposed", proposal=str(pf), applies_cleanly=applies(res.diff, root))
        else:
            row["status"] = "escalate"
        row.update(rounds=res.rounds, reason=res.reason)
        state["done"][it.id] = {"ok": res.ok, "rounds": res.rounds, "reason": res.reason, "ts": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}
        Path(state_path).parent.mkdir(parents=True, exist_ok=True)
        Path(state_path).write_text(json.dumps(state, indent=2), encoding="utf-8")
        task_key = f"queue:{it.id}"
        round_log.record_round(task_key, round_log.next_round(rounds_path, task_key), {"solved": int(res.ok), "rounds": res.rounds}, f"local_code via {model}", res.reason, rounds_path)
    return out


def main(argv: list[str] | None = None) -> int:
    repo = HERE.parent
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--plans", type=Path, default=repo / "docs" / "superpowers" / "plans")
    ap.add_argument("--root", type=Path, default=repo)
    ap.add_argument("--model", default="bonsai-9b")
    ap.add_argument("--max-items", type=int, default=5)
    ap.add_argument("--wall-seconds", type=float, default=900)
    ap.add_argument("--gateway", default=gateway.DEFAULT_URL)
    ap.add_argument("--state", type=Path, default=repo / "artifacts" / "local" / "queue-state.json")
    ap.add_argument("--proposals", type=Path, default=repo / "artifacts" / "local" / "proposals")
    ap.add_argument("--rounds", type=Path, default=repo / "artifacts" / "auto-loop" / "rounds.jsonl")
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args(argv)

    def gate(model: str) -> dict:
        return memgate.decide(server.MODEL_MB.get(model, server.DEFAULT_MODEL_MB), server.KV_MB, memgate.free_mb())

    def make_chat(model: str) -> Callable[[list], str]:
        return lambda msgs: gateway.chat(msgs, model, max_tokens=1500, base_url=a.gateway, timeout=900)

    result = run_queue(
        parse_plans(a.plans), a.root, make_chat, loop.run_task, gate, a.model, a.state, a.proposals, a.rounds,
        max_items=a.max_items, wall_seconds=a.wall_seconds, dry_run=a.dry_run,
    )
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
