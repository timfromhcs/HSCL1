# Plan: local sub-agents v2 (priority over the HSCL1 image work, set by the owner 2026-11-07)

Order the owner gave: (1) fix the local sub-agents here and in OpenCode, (2) add diffusion LLMs and vision towers as efficient extras, (3) update the plans, (4) build this first and well, (5) then use the new agents in the RSI loop so they learn better, cheaper and faster. The HSCL1 image work is paused (state at the end).

## Rules that came out of the last hours (all measured, not guessed)
- **One heavy thing at a time.** Never a QEMU VM and the local model together; at most one local task at once. With two `local_code` runs and a VM: CPU 100 %, 2.7 GB RAM free (qemu 4.1 GB, llama-server 3.5 GB, memory compression 1.2 GB); the guests froze and looked like product crashes.
- **The 8080 server is not "0 MB".** Resident 2.7-3.5 GB while working, about 1.3 GB asleep. The delegate's gate treated `jev-1.5b` as 0 MB, which hid this.
- **Cancelling a task does not cancel the generation.** After `TaskStop` the CPU stayed at 100 % until the server process was killed.
- **The default model is fine.** `jev-1.5b` (the Bonsai-9B MTP server) solved 10/10 worker tasks at 10.6 s/task; the problem was load, not model quality.

## Track 1: delegate fixes (here and OpenCode share `tools/local_worker/`)
Test first, pure functions with injected probes, stdlib only:
1. `hostgate`: refuse to start when a QEMU process runs, when CPU load over a short sample is above a threshold, or when available RAM is below need + reserve; reasons are explicit (`host_busy: ...`).
2. Single-flight lock (lock file with PID, stale-lock takeover): a second `local_code` while one runs returns `busy` at once.
3. Gate memory by **residency**: `jev-1.5b` counts 0 MB only if the llama-server process is already resident, otherwise its measured wake cost; model choice by free RAM (small and resident first).
4. Bounded requests: lower per-request timeout and token cap so a stuck generation ends by itself; the result says how the run ended.
5. Evidence: every run (ok or not) is logged for the RSI loop (see Track 4) with the real test output as the verification event.
6. Docs: `docs/LOCAL_WORKER.md`, `ai-shared/` spec re-synced (`scripts/sync_ai_shared.py --write`) so the OpenCode agent file matches.

## Track 2: diffusion LLMs as an optional extra backend (research first, nothing downloaded yet)
Facts checked 2026-11-07:
- The installed Prism Vulkan build (12128) ships `llama-diffusion-cli.exe`; upstream's `examples/diffusion` documents Dream, LLaDA and RND1; LLaDA 2.0 is an open upstream PR (#17454). **Vulkan support for diffusion is unconfirmed** (to measure with the shipped binary).
- Speed lever is the step count: one empirical study reports 512 -> 8 steps cuts FLOPs to 1.6 % and raises throughput 63x for DiffuCoder-7B, with an accuracy cost. Long generations reduce efficiency. Dream-Coder-7B (open weights) reports 21.4 % pass@1 on LiveCodeBench: modest. Open-dCoder 0.5B is open but trails the 7B models. Mercury is API-only (not usable locally).
- Not found: a 2026 open-weight diffusion coder with consumer-hardware tokens/s numbers; GGUF files from a trustworthy source with a licence we have read.
Plan: a **separate, opt-in** backend id (`diffusion-*`) behind the same `local_code` contract; admitted only after (a) licence read from the model card, (b) GGUF SHA-256 recorded, (c) the same 10-task benchmark (`tools/local_worker/bench.py`) beats or matches `jev-1.5b` on pass@1 and time/task or uses less memory, (d) the step count is part of the measurement. Until then it stays `EXPERIMENTAL`, not wired in.

## Track 3: vision towers (mmproj) in the plan
Already present: `Ternary-Bonsai-2-9B-mmproj-Q8_0.gguf` and `llama-mtmd-cli`/`llama-qwen2vl-cli`/`llama-minicpmv-cli` in the build. Plan: model registry entries carry the tower's memory cost separately (model + mmproj + image tokens in KV), the gate counts it, images only when the task needs them; measure RSS with and without mmproj on the real server before claiming any number.

## Other models ("LFM or so")
Checked: LFM2 licence is the "LFM Open License v1.0" (custom, terms not read by me), no code benchmark found; LFM3 appears only in one third-party post (not confirmed by Liquid); Qwen2.5-Coder-3B is under `qwen-research`, not a free licence. **Nothing is pulled** until a licence is read and the benchmark gate above says it helps. Pulling is allowed by the owner "if needed"; it is not needed yet.

## Track 4: RSI loop with the new agents
State: 27 verified pairs in `rsi-capture`; the auto-trainer daemon writes only a manifest (no weights); `docs/research/2026-11-07-auto-lora-merge-feasibility.md` says no auto-merge before several hundred diverse verified pairs, a held-out set, a training route that works on the model's format, and the 10-task benchmark as a promotion gate. What changes: the delegate becomes the **data source** (each test-verified `local_code` run is a verified pair; failures are kept as negatives), one task at a time, logged through `rsi_start`/`rsi_log`/`rsi_finalize`. `llama-finetune.exe` exists in the build but whether it can train a PQ2_0 ternary model is unverified (probably not; needs an fp16 parent).

## HSCL1 image work: paused, state
Committed and green: installer title version fix, not-encrypted-/boot setting (no visible effect in the erase+encrypt path), hscl-cqhecs in the image, in-guest checks, dev2 image (sha256 4d04e7ca...). In progress, uncommitted until this plan's Track 1 is done: the installer "Notes" page (qsTr + `.qm`, hook, gates; 7 tests green; live German test not finished: the page stayed English until I made it retranslate on show, not yet seen working). Red pending tests parked in `docs/superpowers/pending-tests/` (slideshow i18n, ts coverage).
