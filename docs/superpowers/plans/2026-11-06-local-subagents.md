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
- [ ] Failing tests (fake `chat`): green on round 1; green on round 2 after a failing first answer; stops at `max_rounds`; empty answer counts as a failed round; path escape refused; edit of a protected test file = red; hanging test killed by timeout; output capped
- [ ] Implement with whole-file replacement blocks (```path ... ```), copy of the tree in a temp dir, `subprocess.run` with `shell=False`

### Task L4: gateway client
**Files:** `tools/local_worker/gateway.py`.
**Interfaces:** `chat(messages, model, max_tokens, base_url="http://127.0.0.1:8090/v1") -> str` with `/no_think`, one retry with thinking off when content is empty, `<tool_call>`-in-reasoning fallback hook (kept off by default); loopback-only URL check.
- [ ] Tests with a stub HTTP server on 127.0.0.1: empty content then retry; non-loopback URL refused; HTTP 5xx maps to an error code

### Task L5: MCP server `localdelegate`
**Files:** `tools/local_worker/server.py` (stdlib JSON-RPC over stdio), tests.
**Interfaces:** one tool `local_code(task: str, files: list[str], test_cmd: list[str], model: str = "qwen3-4b", max_rounds: int = 3)` returning verdict + diff stat + unified diff (capped); read-only/`dry` flag; `workdir` fixed to the repository root passed in the environment.
- [ ] Tests: `initialize`, `tools/list` (exactly 1 tool), `tools/call` happy path with injected fake loop, invalid arguments rejected
- [ ] Register in `E:\hcslinux222\.mcp.json` (Claude Code, project scope) and in OpenCode config via `{env:...}`-only values

### Task L6: shared agent/prompt source and generator
**Files:** `ai-shared/AGENTS.md` (measured facts only), `ai-shared/agents/local-worker.md`, `ai-shared/mcp.json`, `scripts/sync_ai_shared.py` generating `.claude/agents/local-worker.md`, `.mcp.json`, `.opencode/agents/local-worker.md`.
- [ ] Tests: generated files contain no secret patterns (reuse `round_log` secret regexes), no claim strings ("TurboQuant 3", "24 GB", "active on Vulkan") unless backed by `artifacts/local/` evidence file

### Task L7: benchmark harness (evidence)
**Files:** `tools/local_worker/bench.py`, `tools/local_worker/tasks/*.json` (10 tiny tasks with hidden tests incl. the int/float parser trap), `artifacts/local/*.json`.
- [ ] Measures per model: pass@1, pass within 3 rounds, tokens/s, wall time, peak RSS; `llama-bench` `-ngl 0` vs `-ngl 99` for the Prism build (checks issue #329 symptom: PTQ1_0 vs PQ2_0 rate)
- [ ] Decision table written to `docs/research/` with numbers; the default executor is chosen from it

### Task L8: always-on queue ("never idle")
- [ ] `scripts/local_queue.py`: reads `docs/superpowers/plans/*.md` unchecked steps tagged `[local]`, dispatches to `local_code`, records each round with `round_log.py`, stops when the RAM gate closes or after a wall-clock cap; results are proposals in a worktree branch, never pushed automatically

## Order
L1 (fetch, in background) -> L2 -> L3 -> L4 -> L5 -> L6 -> L7 -> L8. Owner items: rotate the two plaintext secrets; confirm DE/EN prompt wording; decide whether OpenCode runs as autostart service with a password from the environment.
