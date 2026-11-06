# Local worker: routine coding on local models instead of cloud tokens

`localdelegate` is a small MCP server (`tools/local_worker/server.py`) with **one** tool, `local_code`. It asks a local model (through the LocalAI Gateway on `http://127.0.0.1:8090/v1`) to edit the files you name, in a throwaway copy of the project, until your test command passes or the round budget (default 3, max 5) is used up. It returns `{ok, rounds, reason, diff, last_output, applied:false}`. **The diff is a proposal**: review it and apply it yourself. If `ok` is false, escalate to a stronger model.

## What is guaranteed (tested)
- The local model can only write the files you list; test files you list as `protected` cannot change; paths outside the project, absolute paths and symlinks are refused.
- The test command runs without a shell; its executable must be one of `python`, `python3`, `py`, `pytest`, `cargo`, `node`, `npm`; time and output are capped.
- The gateway client talks to loopback only, switches thinking off, retries an empty answer once with a bigger budget.
- A free-RAM gate (model + KV estimate + 3000 MiB) runs before every call; if it is closed the tool reports `memory_gate` and does nothing.

## What is not guaranteed
- Quality. Local models make subtle mistakes (measured: a 4B model parsed integers as floats and its own tests did not notice). Write tests that check types and edge cases.
- Speed numbers are throughput on this machine (see `docs/research/2026-11-06-local-subagents-prism-bonsai-turboquant.md`), not task success rates; the task benchmark (plan L7) is still to be run.

## Setup
1. Start the gateway (it loads models lazily). Models live in `C:\LocalAIBACKEND`.
2. Claude Code: the project `.mcp.json` registers `localdelegate`; approve it when asked. The subagent `local-worker` (`.claude/agents/local-worker.md`) can use only this tool.
3. OpenCode: the project `opencode.json` registers the server (`HSCL_WORKER_ROOT` is `.`, the workspace); the agent `local-worker` (`.opencode/agents/local-worker.md`) denies everything except this tool.
4. Environment: `HSCL_WORKER_ROOT` (or `CLAUDE_PROJECT_DIR`, which Claude Code sets for the servers it starts), optional `HSCL_WORKER_RESERVE_MB`, `HSCL_WORKER_GATEWAY`, `LOCAL_AI_KEY`. Secrets belong in the environment, never in these files.

## One source of truth
Edit `ai-shared/spec.json` and `ai-shared/local-worker.prompt.md`, then run `python scripts/sync_ai_shared.py --write`. `--check` (and a unit test) fails when the generated files drift. `.mcp.json` and `opencode.json` are merged: only the `localdelegate` entry is managed.
