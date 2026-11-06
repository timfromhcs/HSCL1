# Plan L: local subagents (Bonsai / Qwen on the PrismML Vulkan build) instead of cloud tokens

> **For agentic workers:** REQUIRED SUB-SKILL: superpowers:executing-plans. Parent: `2026-11-06-masterplan-resume-s1.md`. Research (4 rounds): `docs/research/2026-11-06-local-subagents-prism-bonsai-turboquant.md`.

**Goal:** a verify-patch worker that runs on local models through the existing LocalAI Gateway (`http://127.0.0.1:8090/v1`), callable from Claude Code and OpenCode as one MCP tool, so routine coding work stops burning cloud tokens, with measured quality and a strict memory discipline.

**Architecture:** `local_worker` (stdlib-only Python, MCP stdio) = bounded loop: ask the local model for a whole-file edit -> apply to a throwaway copy -> run the caller's test command -> feed failures back -> stop on green or after N rounds -> return diff + verdict. Escalation to the cloud model is the caller's decision on red. The gateway stays the governor (RAM budget, LRU, `duo`); a free-RAM gate runs before every call.

**Tech Stack:** Python 3.13 (stdlib), pytest, PowerShell, llama.cpp PrismML build `prism-b12128-d7b2896` (Vulkan), OpenCode v2.2.5, Claude Code.

## Global Constraints
- Install only on `C:` under `C:\LocalAIBACKEND` (models) and this repository (code); every downloaded file is checked against the SHA-256 published by the host (Hugging Face LFS oid or GitHub digest) before use.
- No TurboQuant fork binaries. KV cache `q8_0` (rotation is on by default in mainline).
- Local server bound to `127.0.0.1`; secrets only through environment variables; the plain-text GitHub token and OpenCode password in `~/.config/opencode` are owner items to rotate (never copied into this repo or logs).
- Thinking off for executors; tool calls validated by our parser (`cli/hscl/src/toolcall.rs` protocol); at most 8 tools per agent.
- A local model's output is never trusted: tests decide. Nothing is claimed faster/cheaper without a measurement in `artifacts/local/`.
- Memory: refuse to start a model if free RAM < model + KV + 3 GB; one big model at a time.

## Review Focus
- The model writes outside the worktree (`..`, absolute paths, symlinks) -> refused.
- The test command hangs or prints megabytes -> timeout and output cap.
- The model returns empty content (thinking ate the budget) -> counted as a failed round, retried once with thinking off, never as success.
- The model "fixes" by editing the tests -> test files are read-only inputs, diff touching them = red.
- Gateway down or RAM gate closed -> clear error code, caller escalates, no partial writes.

## Tasks

### Task L1: model fetcher with hash verification
**Files:** Create `tools/local_worker/fetch_model.py`, `tests/unit/test_fetch_model.py`.
**Interfaces:** `expected_sha256(repo: str, filename: str, api_get=...) -> str` (reads the LFS oid from the Hugging Face tree API), `fetch(repo, filename, dest_dir, opener=...) -> Path` (resumable, verifies, deletes on mismatch).
- [x] Tests with a fake opener (18, red first): matching hash keeps the file; mismatch deletes it and raises; verified file not re-downloaded; resume from `.part`; destination outside the allowed root, bad file names and repo ids refused
- [x] Implemented `tools/local_worker/fetch_model.py` (default root is `C:\LocalAIBACKEND`, where the gateway resolves models). Downloads started in the background (log `artifacts/local/fetch.log`): then fetch (owner approved install on C:): `prism-ml/Ternary-Bonsai-2-9B-gguf` PQ2_0-MTP-Q8_0, `prism-ml/Ternary-Bonsai-2-4B-gguf` PQ2_0, Qwen3.5-9B Q4 (repo id from the model card, hash from the API)
- [ ] Register the models in `C:\LocalAIBACKEND\models.yaml` (backup first; est_mem_mb from `hscl ai fit`)

### Task L2: memory gate
**Files:** Create `tools/local_worker/memgate.py`, tests.
**Interfaces:** `can_start(model_mb: int, kv_mb: int, free_mb: int, reserve_mb: int = 3000) -> bool`; `free_mb() -> int` (Windows `GlobalMemoryStatusEx` via ctypes, fallback `/proc/meminfo`).
- [x] Tests (11, red first): boundary values, configurable reserve, negative inputs, meminfo parsing, plausible live value
- [x] Implemented `tools/local_worker/memgate.py` (ctypes `GlobalMemoryStatusEx`, `/proc/meminfo` fallback, CLI exit 0/1). Live smoke: 5237 MiB available refused a 3600+600 MiB start (need 7200)

### Task L3: verify-patch loop (core)
**Files:** Create `tools/local_worker/loop.py`, `tests/unit/test_local_loop.py`.
**Interfaces:** `run_task(chat: Callable[[list[dict]], str], workdir: Path, files: list[str], task: str, test_cmd: list[str], max_rounds: int = 3, timeout_s: int = 120, protected: list[str] = ()) -> Result`; `Result{ok: bool, rounds: int, diff: str, last_output: str, reason: str}`.
- [x] 14 tests (red first, fake `chat`, includes the real int/float bug the 4B model made): green round 1 with untouched real tree; feedback reaches round 2; round budget; empty answer / no FILE block = failed round; 4 path-escape forms refused; non-editable and protected files refused; hanging test killed; output capped; symlink target not followed (skips on Windows without symlink rights, runs under WSL/Linux CI)
- [x] Implemented `tools/local_worker/loop.py`: whole-file `FILE:` blocks applied to a temp copy, `subprocess.run(shell=False)`, diff returned for review; the client receives a copy of the history (found by a failing test)

### Task L4: gateway client
**Files:** `tools/local_worker/gateway.py`.
**Interfaces:** `chat(messages, model, max_tokens, base_url="http://127.0.0.1:8090/v1") -> str` with `/no_think`, one retry with thinking off when content is empty, `<tool_call>`-in-reasoning fallback hook (kept off by default); loopback-only URL check.
- [x] 16 tests (red first), incl. a real loopback stub server: 6 non-loopback/odd URLs refused, 3 loopback forms accepted, thinking off two ways without touching the caller's list, key only from env, empty answer retried once with a doubled budget, `<think>` stripped, unclosed think = empty, stable codes (`unavailable`, `http_500`, `empty`, `bad_response`), no proxy for loopback
- [x] Implemented `tools/local_worker/gateway.py`; forge check green (pytest, bash -n, ShellCheck, secret scan)

### Task L5: MCP server `localdelegate`
**Files:** `tools/local_worker/server.py` (stdlib JSON-RPC over stdio), tests.
**Interfaces:** one tool `local_code(task: str, files: list[str], test_cmd: list[str], model: str = "qwen3-4b", max_rounds: int = 3)` returning verdict + diff stat + unified diff (capped); read-only/`dry` flag; `workdir` fixed to the repository root passed in the environment.
- [x] 26 tests (red first): `initialize`, notifications unanswered, exactly 1 tool with a closed schema, happy path (diff is a proposal, `applied` false), red verdict is a normal result, 15 invalid-argument cases (-32602: bad paths, disallowed executable, too many files, unknown fields, ...), unknown tool/method, closed RAM gate and gateway failure = tool error with code, garbage input survives, `make_deps` needs `HSCL_WORKER_ROOT`, and a process-level test over real stdio
- [x] Implemented `tools/local_worker/server.py` (stdlib only). Executable allow-list for `test_cmd`: python, python3, py, pytest, cargo, node, npm
- [x] Registered through L6 (verified in the official docs by a research subagent: Claude Code sets `CLAUDE_PROJECT_DIR` for spawned servers, OpenCode starts in the workspace); `make_deps` accepts `HSCL_WORKER_ROOT` or `CLAUDE_PROJECT_DIR`

### Task L6: shared agent/prompt source and generator
**Files:** `ai-shared/AGENTS.md` (measured facts only), `ai-shared/agents/local-worker.md`, `ai-shared/mcp.json`, `scripts/sync_ai_shared.py` generating `.claude/agents/local-worker.md`, `.mcp.json`, `.opencode/agents/local-worker.md`.
- [x] 10 tests (red first, YAML front matter parsed with PyYAML): `.mcp.json` keeps `hscl-workshop` and adds only `localdelegate` (6-line diff); Claude agent `tools: mcp__localdelegate__local_code`, `disallowedTools: Write, Edit, Bash`, `model: haiku`, `maxTurns: 3`; OpenCode agent denies everything first, then allows only `localdelegate_local_code*`; no secrets, no unmeasured claim strings; deterministic; `--check`/`--write` exit codes; the real repository is verified in sync by a test
- [x] Implemented `scripts/sync_ai_shared.py`, `ai-shared/spec.json`, `ai-shared/local-worker.prompt.md`, generated `.mcp.json`, `opencode.json`, `.claude/agents/local-worker.md`, `.opencode/agents/local-worker.md`, docs `docs/LOCAL_WORKER.md`

### Task L7: benchmark harness (evidence)
**Files:** `tools/local_worker/bench.py`, `tools/local_worker/tasks/*.json` (10 tiny tasks with hidden tests incl. the int/float parser trap), `artifacts/local/*.json`.
- [x] `tools/local_worker/bench.py` + `bench_tasks.py` (19 tests, tasks self-validated): solved, pass@1, mean seconds per task, RAM gate or error recorded per model; `llama-bench -ngl 0` vs `99` done for Bonsai 4B/9B (decode 14.1 -> 30.4 and 8.9 -> 20.9 t/s, no CPU fallback). Peak RSS and Qwen3.5-9B still open
- [x] Results table in `docs/research/2026-11-06-local-subagents-prism-bonsai-turboquant.md`: Bonsai-9B 10/10 (9 in round 1), Bonsai-4B 9/10, Qwen3-4B 7/10. Default executor candidate: **bonsai-9b**; fast helper: **bonsai-4b**. Open: Qwen3.5-9B head-to-head (needs ~9.4 GB available), repeat runs for variance

### Task L8: always-on queue ("never idle")
- [x] `scripts/local_queue.py` (13 tests, red first): reads unchecked `- [ ] [local] {json spec} :: task` steps, validates them with the MCP server's validator, runs them through the verify-patch loop behind the gateway, records each run with `round_log.py` (new `next_round`), stops on a closed RAM gate, gateway error, wall-clock or item limit; remembers finished items; **results are diff files in `artifacts/local/proposals/` with a `git apply --check` verdict, never applied, committed or pushed, and plan boxes are never ticked by it** (deviation from the original idea of a worktree branch: diff files are simpler and cannot touch history). Dry run on the real plans: 0 items (no step is tagged yet)

## Order
L1 (fetch, in background) -> L2 -> L3 -> L4 -> L5 -> L6 -> L7 -> L8. Owner items: rotate the two plaintext secrets; confirm DE/EN prompt wording; decide whether OpenCode runs as autostart service with a password from the environment.
