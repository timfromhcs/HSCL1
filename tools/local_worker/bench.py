#!/usr/bin/env python3
"""Task benchmark for local models (plan L, task L7).

Runs the ten tasks of `bench_tasks.py` through the verify-patch loop (`loop.run_task`) with each model behind the gateway and reports:
solved (tests green within the round budget), pass@1 (green in round 1), mean seconds per task. A model whose RAM gate is closed is
SKIPPED (not counted as a failure); a gateway error is recorded as an error for that model. Results go to `bench-tasks-<time>.json`.

Usage: python bench.py --models qwen3-4b,bonsai-9b [--rounds 3] [--limit N] [--out DIR] [--gateway URL] [--no-gate]
"""
from __future__ import annotations

import argparse
import json
import sys
import tempfile
import time
from pathlib import Path
from typing import Callable

import bench_tasks
import gateway
import loop
import memgate
import server

DEFAULT_OUT = Path("artifacts/local")


def _materialize(task: dict, root: Path) -> Path:
    d = root / task["id"]
    d.mkdir(parents=True)
    (d / "impl.py").write_text(task["stub"], encoding="utf-8", newline="\n")
    (d / "check.py").write_text(task["check"], encoding="utf-8", newline="\n")
    return d


def run_benchmark(
    models: list[str],
    chat_factory: Callable[[str], Callable[[list], str]],
    tasks: list[dict] | None = None,
    gate: Callable[[str], dict] | None = None,
    max_rounds: int = 3,
    timeout_s: int = 60,
    clock: Callable[[], float] = time.monotonic,
    limit: int | None = None,
) -> dict:
    tasks = list(bench_tasks.TASKS if tasks is None else tasks)[: limit or None]
    out: dict = {"max_rounds": max_rounds, "tasks": [t["id"] for t in tasks], "models": {}}
    for model in models:
        g = gate(model) if gate else {"ok": True, "reason": ""}
        if not g["ok"]:
            out["models"][model] = {"skipped": f"memory_gate: {g['reason']}"}
            continue
        chat = chat_factory(model)
        rows = []
        error = None
        with tempfile.TemporaryDirectory(prefix="hscl-bench-") as td:
            for t in tasks:
                d = _materialize(t, Path(td))
                t0 = clock()
                try:
                    r = loop.run_task(chat, d, ["impl.py"], t["prompt"], [sys.executable, "check.py"], max_rounds=max_rounds, timeout_s=timeout_s, protected=["check.py"])
                except gateway.GatewayError as e:
                    error = f"gateway_error: {e.code}"
                    break
                rows.append({"id": t["id"], "ok": r.ok, "rounds": r.rounds, "seconds": round(clock() - t0, 2), "reason": r.reason})
        if error:
            out["models"][model] = {"error": error, "completed": len(rows)}
            continue
        out["models"][model] = {
            "tasks": rows,
            "total": len(rows),
            "solved": sum(1 for x in rows if x["ok"]),
            "pass_at_1": sum(1 for x in rows if x["ok"] and x["rounds"] == 1),
            "mean_seconds": round(sum(x["seconds"] for x in rows) / len(rows), 2) if rows else 0.0,
        }
    return out


def render_markdown(result: dict) -> str:
    lines = [
        f"Task benchmark ({len(result['tasks'])} tasks, up to {result['max_rounds']} rounds)",
        "",
        "| model | solved | pass@1 | mean s/task |",
        "|---|---|---|---|",
    ]
    for model, m in result["models"].items():
        if "skipped" in m:
            lines.append(f"| {model} | {m['skipped']} | | |")
        elif "error" in m:
            lines.append(f"| {model} | {m['error']} (after {m['completed']} tasks) | | |")
        else:
            lines.append(f"| {model} | {m['solved']}/{m['total']} | {m['pass_at_1']}/{m['total']} | {m['mean_seconds']} |")
    return "\n".join(lines) + "\n"


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--models", required=True, help="comma-separated gateway model ids")
    ap.add_argument("--rounds", type=int, default=3)
    ap.add_argument("--limit", type=int, default=None)
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--gateway", default=gateway.DEFAULT_URL)
    ap.add_argument("--no-gate", action="store_true", help="skip the free-RAM gate (for tests)")
    a = ap.parse_args(argv)
    models = [m for m in a.models.split(",") if m]

    def gate(model: str) -> dict:
        return memgate.decide(server.MODEL_MB.get(model, server.DEFAULT_MODEL_MB), server.KV_MB, memgate.free_mb())

    def factory(model: str) -> Callable[[list], str]:
        return lambda msgs: gateway.chat(msgs, model, max_tokens=1500, base_url=a.gateway, timeout=900)

    result = run_benchmark(models, factory, gate=None if a.no_gate else gate, max_rounds=a.rounds, limit=a.limit)
    a.out.mkdir(parents=True, exist_ok=True)
    stamp = time.strftime("%Y%m%d-%H%M%S")
    (a.out / f"bench-tasks-{stamp}.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(render_markdown(result))
    return 0


if __name__ == "__main__":
    sys.exit(main())
