# Research: using CPU and iGPU evenly for local inference, and measuring it (three web rounds, 2026-11-07)

Owner request (2026-11-07): benchmark everything, free RAM and load models as needed, load CPU and iGPU evenly. Method: three consecutive research rounds, each more detailed, then the plan is updated, then work resumes. Status words: ANSWERED, PARTIAL, UNVERIFIED (anecdote / vendor), MEASURE (only this machine can answer).

## Machine baseline (measured, this machine)
- CPU Ryzen 7 7735HS (8C/16T). RAM: four 6 GB modules, Channel A-D, rated 6400, configured **5500 MT/s**, 24 GB installed, **20.3 GB visible** to Windows; the driver reports **4095 MB adapter RAM** (UMA frame buffer reserved in the BIOS). Theoretical bandwidth about 88 GB/s (5500 MT/s x 16 B), shared by CPU and iGPU.
- GPU driver 32.0.21043.12001; power plan "Balanced". Vulkan: `Vulkan0: AMD Radeon Graphics (14226 MiB, 13515 MiB free)`, `uma: 1`, `int dot: 1`, `matrix cores: none`.
- Earlier measurement (llama-bench, Prism build b12128): Bonsai-2-4B PQ2_0 decode 14.1 t/s (CPU compute) vs 30.4 t/s (Vulkan); Bonsai-2-9B 8.9 vs 20.9 t/s; prefill 159/236 and 110/143 t/s. Server process memory: iGPU dedicated usage about 25 MB, shared 2.5-2.7 GB.
- `llama-bench` of this build has `-lm`, `-C/--cpu-mask`, `--cpu-strict`, `--poll`, `--prio`, `--delay`, `-dev`, `-ts`, `-sm`, `-ot`, `-nopo`, `-fa`, `-nkvo`, `-pg`, `-d`, `-o json|jsonl|csv|md|sql`, `-r` (default 5); it has **no `-tb`** (checked with `--help`).

## Round 1 - broad survey (two read-only agents)
| Question | Finding | Status |
|---|---|---|
| Does splitting work between CPU and iGPU help on UMA iGPUs? | **No direct published benchmark** of partial `-ngl`, two concurrent processes, or CPU+iGPU concurrency on a 680M/780M-class machine. Indirect: a 780M video benchmark shows prefill 176.8 vs 34.6 t/s on the iGPU but decode only 13.9 vs 10.1 t/s (bandwidth-bound; anecdote); AMD's 2024 blog says Intel Arc iGPU offload was slower than CPU-only for most models (vendor-slanted); forum comments say an iGPU on 2-channel memory is no faster than the CPU for decode (UNVERIFIED). A 50/50 split win on a discrete GPU came from VRAM overflow and does not transfer. | PARTIAL |
| Speculative decoding as the way to use idle CPU | Strix Halo data only: MTP about 3.1x (Qwen3.6-27B) because the heads reuse the same weight read; a draft model 2.0x; n-gram-mod 0 % (one author) but another reports n-gram as the zero-bandwidth winner on iGPUs; on a 3090 n-gram and classic draft were net zero. MTP/DFlash needed `--parallel 1` in that test. No 680M data. | PARTIAL |
| Parallel slots (`-np`) | Claimed to raise aggregate throughput only if `-b/-ub` allow it; slots split the context (32768 / 8 = 4096). Apple Silicon only. | PARTIAL |
| Windows counters | GPU Engine counters per PID/engine type and `GPU Process Memory` exist; which engtype Vulkan compute uses on this driver, and whether `Shared` or `Local Usage` is reported for UMA, is UNVERIFIED. Per-core `Processor Information` counters exist. DRAM bandwidth: AMD uProf is the only vendor user-space option on Windows; Rembrandt support unverified; fallback = model bytes x decode t/s. Hidden variable: APU power limits (STAPM/slow/fast); one Linux user got 17 GB/s until RyzenAdj reset the limits. | PARTIAL |
| Server/bench features | Every server response has `timings` (prefill vs decode per request); `--metrics`, `/slots`; `cache_prompt:false` avoids cache skew; server has `--cpu-mask-batch`, `--prio-batch`, `--poll-batch`. `GGML_VK_*` variables include `PERF_LOGGER`, `PREFER_HOST_MEMORY`, `DISABLE_ASYNC`, `DISABLE_MMVQ`, `MAX_NODES_PER_SUBMIT`. | ANSWERED (docs) |
| Statistics | llama-bench default 5 repetitions with mean +- stddev is the only authoritative anchor found; rigorous practice not yet sourced. | OPEN -> round 2 |

Sources: <https://www.amd.com/en/blogs/2024/accelerating-llama-cpp-performance-in-consumer-llm.html>, <https://sleepingrobots.com/dreams/beellama-dflash-strix-halo/>, <https://github.com/ggml-org/llama.cpp/discussions/27154>, <https://github.com/ggml-org/llama.cpp/discussions/24222>, <https://github.com/ggml-org/llama.cpp/blob/master/tools/llama-bench/README.md>, <https://github.com/ggml-org/llama.cpp/blob/master/tools/server/README.md>.

### Open questions carried into round 2
Source level (agent 1): does the ggml scheduler run CPU and Vulkan splits concurrently or in series; how is the PQ2_0 CPU path implemented (SIMD or generic); MTP in the fork (Vulkan, partial offload, acceptance); CPU draft model plus Vulkan target; Vulkan memory-heap choice on APUs.
Windows level (agent 2): engine type of Vulkan compute and Local/Shared Usage semantics; CPU throttling and power-limit readout (uProf, HWiNFO, RyzenAdj; kernel-driver implications); DRAM bandwidth measurement; power plan / HAGS / EcoQoS effects; rigorous benchmark statistics.
Measure here (no web answer possible): partial `-ngl`, two-lane aggregate throughput, bandwidth, `-np`, thread count, `--cpu-strict`, `--poll`.
