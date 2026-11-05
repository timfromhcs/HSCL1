# Local AI + coding tools + MCP + Wallpaper Studio (research-backed plan)

> Executed autonomously after this plan. Evidence in `docs/BUILD_LOG.md`. AGENTS.md wins on conflict (§9 local AI, §19 branding/licences).
> Owner requests of 2026-11-05: wallpaper animation creator; low-VRAM mode; more agentic coding tools and backends adapted to the hardware
> automatically; small open LLMs selectable for download with **abliterated variants proposed**; coding tools built into the OS with HCS
> branding; more MCP servers and functions.

## 1. Research findings (2026-11-05; sources: Hugging Face API, npm/PyPI metadata, web roundups)

**Models - verified against the live Hugging Face file tree (names, sizes, LFS sha256 are fetched by a script, not typed):**

| Tier (RAM guide) | Repo | Quant | Size | Licence on card |
|---|---|---|---|---|
| tiny (>= 4 GB) | `mradermacher/Huihui-Qwen3.5-2B-abliterated-GGUF` | Q4_K_M | 1.27 GB | apache-2.0 |
| tiny (>= 6 GB) | `mradermacher/Huihui-gemma-4-E2B-it-abliterated-GGUF` | Q4_K_M | 3.43 GB | apache-2.0 |
| small (>= 8 GB) | `mradermacher/Huihui-Qwen3.5-4B-abliterated-GGUF` | Q4_K_M | 2.71 GB | apache-2.0 |
| medium (>= 12 GB) | `mradermacher/Huihui-Qwen3.5-9B-abliterated-GGUF` | Q4_K_M | 5.63 GB | apache-2.0 |
| medium (>= 16 GB) | `culturerevolt/gemma-4-12b-heretic-abliterated-GGUF` | Q4_K_M | 7.38 GB | apache-2.0 |
| coder, large (>= 24 GB, MoE 3B active) | `mradermacher/Huihui-Qwen3-Coder-30B-A3B-Instruct-abliterated-i1-GGUF` | i1-Q4_K_M | 18.56 GB | apache-2.0 |

All are GGUF (no pickle). They are community "abliterated/heretic" derivatives of Qwen/Gemma bases: **refusal behaviour was removed by
the community, not by the base publisher**; quality and safety are not guaranteed. Catalog entries carry `base_model`, `variant: abliterated`,
the source repo and a warning text. Other ranked candidates found but not catalogued yet (size/maturity): Qwen3.8 27B/Flash-Next
abliterated, DeepSeek V4 Flash abliterated (too large for the target hardware).

**Backends:** llama.cpp is the portable choice (CMake `GGML_VULKAN` for AMD/Intel iGPU via Mesa RADV, `GGML_HIP` for ROCm, CPU fallback).
ROCm is not assumed for integrated GPUs such as the Radeon 680M; Vulkan is the default there. Generic flags to use and **measure per machine
with `llama-bench` (nothing is claimed as a speed)**: `-ngl` (layer offload), `-c` (context), `-ctk/-ctv q8_0|q4_0` (KV-cache quantisation),
`-fa` (flash attention), `--mlock/--no-mmap`. Ollama stays an optional alternative, not a dependency.

**Agentic coding tools (open source, OpenAI-compatible local endpoint):**

| Tool | Licence (source) | Install path verified now | Decision |
|---|---|---|---|
| OpenCode | MIT (npm `opencode-ai` 1.19.5) | npm | catalog + HCS Code default |
| Codex CLI | Apache-2.0 (npm `@openai/codex` 0.166.0) | npm | catalog |
| Qwen Code | Apache-2.0 per roundup; npm licence field empty | npm `@qwen-code/qwen-code` 0.26.8 | catalog, **licence must be confirmed from the upstream repo before it ships** |
| Aider | Apache-2.0 per roundup; PyPI licence field empty | PyPI `aider-chat` 0.86.2 | catalog, same condition |
| OpenHands | MIT (PyPI `openhands-ai` 1.11.0) | PyPI | catalog (heavy, container based; opt-in) |
| Goose | Apache-2.0 per roundup (Linux Foundation) | no verified package -> manual link | listed, no installer |
| Crush | FSL-1.1-MIT (source-available, not OSI) | - | listed with a licence warning, opt-in |
| Roo Code (archived), Gemini CLI (retired), Continue (acquired) | - | - | excluded |

## 2. Decisions

| # | Decision |
|---|---|
| D1 | **Suggestions, not downloads.** `hscl ai model recommend` ranks catalog entries that fit the detected hardware (abliterated variants first, as requested, each with the community-derivative warning). Nothing is downloaded without an explicit `model download ID`; the expected sha256 comes from the Hugging Face file API and is verified after the download; GGUF only; free-space check; storage path chosen by the user. |
| D2 | **Hardware profile engine** (pure, tested): input = RAM, free RAM, CPU threads/AVX2, GPU vendor, dedicated vs shared VRAM, Vulkan presence; output = tier, backend (vulkan / cpu / rocm only when detected), llama.cpp parameters (`-ngl`, `-c`, KV quant, `-fa`, threads, batch), and the fitting model list. Unknown values stay unknown, never guessed. |
| D3 | **Low-VRAM mode** (user toggle + automatic when dedicated VRAM < model size): partial layer offload, KV cache `q8_0` (or `q4_0` when still tight), context capped by a memory estimate, mmap on, no `--mlock`. The same switch lowers the desktop load: rain density 1 and mark animation off. |
| D4 | **llama.cpp is built from a pinned source revision** (Vulkan + CPU) by `packages/debian/hscl-llama/build.sh` on the builder and shipped as `hscl-llama`; no `curl | sh`, no unpinned download. If the pinned revision cannot be resolved the task is BLOCKED with evidence. |
| D5 | **Coding tools are installed on demand** into the user's home (npm prefix / pipx), never preinstalled system-wide (size, licence review, update cadence). The OS ships the **HCS Code** front-end: launcher entry, HCS terminal theme/colour config and a pre-pointed local provider. **Upstream names, licences and copyright notices stay visible** ("HCS Code, powered by OpenCode"); HCS does not claim authorship and copies no upstream logos (AGENTS.md §19). |
| D6 | **MCP in the OS:** `hscl mcp` = stdio MCP server inside the OS. Read-only by default (status, doctor, security status, ai detect/recommend, theme list, tools list, handbook search); write tools exist only behind `--allow-write` and call the same allow-listed CLI operations. A catalog lists optional third-party MCP servers (filesystem, git, fetch, memory, playwright) with install commands and a config writer for the supported coding tools; none runs by default. |
| D7 | **Wallpaper Studio:** an effects library (rain, starfield, aurora, grid pulse, particles) as QML components, JSON presets with bounded numeric parameters, a creator page in the Control Center with live preview, `hscl wallpaper list/show/create/apply/export`, and the wallpaper plugin reading a preset. Reduced motion and low-VRAM mode always win over the preset. |

## 3. Slices (each: tests first, then code, then evidence)

- [ ] **A. Hardware profile + catalog.** `cli/hscl/src/ai/{profile,catalog}.rs`; `ai/catalog/models.json` generated by `scripts/build_model_catalog.py` from the HF API (exact filename, size, sha256); tests: tier boundaries, unknown GPU memory stays unknown, low-VRAM trigger, catalog schema (licence, base_model, warning, sha256 length 64), recommend never returns an entry larger than free RAM.
- [ ] **B. `hscl ai` commands.** `model list|recommend|download|verify|remove`, `profile`, `server start|stop|status` (llama-server bound to 127.0.0.1), `--low-vram`; tests with a local fake HTTP file server (hash mismatch, partial file resume, disk-full refusal, path escape rejected).
- [ ] **C. `hscl-llama` package** (pinned llama.cpp, Vulkan + CPU) and a smoke test in a VM: server starts, `/v1/models` answers on 127.0.0.1, CPU path works with the 2B model; Vulkan reported only after a real inference run.
- [ ] **D. Coding tools + HCS Code.** `tools/catalog/coding.toml`; `hscl code list|install|setup|launch|doctor`; config writers (OpenCode provider JSON, aider env, Codex/Qwen Code env) tested on temp homes; launcher `.desktop` ("HCS Code"), terminal colour profile from tokens; attribution file; licence gate: entries with unconfirmed licence cannot be installed by default.
- [ ] **E. `hscl mcp`.** stdio JSON-RPC server (initialize, tools/list, tools/call), read-only default, `--allow-write`; schema/validation tests like the Workshop MCP; MCP catalog + config writer.
- [ ] **F. Wallpaper Studio.** effect components + `Studio` page + presets (JSON schema, bounds), CLI, plugin preset support, QML tests (each effect runs/stops, preset bounds clamp), Control Center page tests with mock backend, de/fr strings.
- [ ] **G. Low-VRAM switch** end to end: `hscl power`/config flag read by the wallpaper plugin and the AI profile; Control Center toggle; tests.
- [ ] **H. Image integration + verification:** packages in the main ISO, verifier checks, handbook chapters (EN/DE/FR: Local AI, Coding tools, MCP, Wallpaper Studio), BUILD_LOG; VM check of the respun/new ISO.

## 4. Review focus

- A recommendation that cannot run on the machine (OOM, disk full) -> recommend only what fits free RAM + free disk; tests at tier edges.
- A tampered or truncated download passes -> sha256 from the API verified, size checked, partial files never promoted.
- Third-party tool shipped with an unconfirmed licence -> licence gate; "powered by" attribution tests.
- "Rebrand" read as hiding upstream -> attribution file and visible text are asserted by tests.
- An MCP write tool becomes a root path -> write tools off by default, only allow-listed CLI operations, no shell argument.
- Wallpaper presets overload weak GPUs -> numeric bounds, low-VRAM caps, reduced-motion override.
- Abliterated models presented as safe or official -> mandatory warning on every listing and first use; no auto-selection by agents.
