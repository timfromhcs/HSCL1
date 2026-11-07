# HSCL1 plan: an own compute backend for the iGPU (instead of a ZLUDA clone), RAM-as-GPU-memory, matrix-multiplication kernels, kernel autotuning as a safe RSI use case

Owner request 2026-11-06: research how to update/build faster, "RAM/VRAM emulation", "something like ZLUDA but our own and better", a RAM-to-GPU converter with the best matrix-multiplication algorithm and an extra own backend so local AI runs better, then AI/RSI, benchmark, finished release, fastest build/test/verify/screenshot/README/release path.
This file is the detail plan for master-plan phase P25; sibling of `2026-11-06-freeze-devmode-memory-tiering.md` (P16 memory advisor) and `2026-11-06-local-agent-harness.md` (P24). The master plan wins on conflicts.
Source grades: **SECONDARY** = blogs/news/papers seen as search snippets; **UNVERIFIED** = not checked against a primary source or a measurement on our machine; **OWN** = our reasoning.

---

## 1. Research digest (what was found, and what was not)

| # | Finding | Source | Grade |
|---|---|---|---|
| B1 | **ZLUDA** is a translation layer that intercepts CUDA API calls and reroutes them to AMD's ROCm/HIP stack; users still need ROCm components. Version 6 appeared 2026-06-29; the maintainer says the project has no commercial funding and is back to weekend-project status; it is not a complete CUDA reimplementation (NCCL, TensorRT, custom CUDA extensions likely do not run); one source claims running CUDA binaries through it on AMD may violate Nvidia's terms for commercial use (**UNVERIFIED**, check the licence text). PTX-to-LLVM internals and **SCALE** (Spectral Compute) were **not** covered by the search | https://www.tomshardware.com/pc-components/gpu-drivers/cuda-emulator-for-amd-gpus-zluda-loses-funding-with-v6-release-embattled-project-goes-back-to-hobby-status-but-now-includes-32-bit-physx-support , https://www.phoronix.com/news/ZLUDA-ROCm-7 | SECONDARY |
| B2 | For llama.cpp on AMD GPUs the Vulkan backend (RADV) often **leads on text generation** and ROCm more often on prompt processing (RDNA4 discrete); on Strix Halo (RDNA3.5 iGPU) plain RADV Vulkan gave the best results in Phoronix's ROCm 7.0 testing. **No Radeon 680M number and no Vulkan-vs-CPU figure for it was found** | https://www.phoronix.com/review/rocm-71-llama-cpp-vulkan , https://www.phoronix.com/review/amd-rocm-7-strix-halo/4 , https://github.com/ggml-org/llama.cpp/discussions/10879 | SECONDARY |
| B3 | On shared-memory APUs there is no fast dedicated pool: the mapped system memory acts as VRAM; default GTT limit about 50 % of RAM, raised through TTM limits (see P16). One forum user says GTT needs address translation and may disturb the TLB when the CPU uses it concurrently; a 5-10 % bandwidth gain from disabling the IOMMU is an anecdote | https://rocm.docs.amd.com/en/latest/how-to/system-optimization/rdna3-5.html , https://community.frame.work/t/igpu-vram-how-much-can-be-assigned/73081 | SECONDARY (docs) / anecdote (forum) |
| B4 | Decode is **memory-bandwidth bound**: rule of thumb tokens/s about bandwidth / model size; one write-up gives 89.6 GB/s for dual-channel DDR5-5600, about 13 tokens/s for an 8B model, 75 % utilisation; the CPU gets about half of the bandwidth the GPU can use on these chips and both share the same bus | https://dev.to/josh_green_dev/why-ddr5-bandwidth-kills-dual-llm-inference-on-apus-benchmarks-inside-42p1 , https://news.lavx.hu/article/memory-bandwidth-the-unseen-barrier-to-local-llm-performance-on-amd-hardware | SECONDARY |
| B5 | Quantised GEMV: weights in 4-bit cut bandwidth, but on-the-fly dequantisation adds compute and can push GEMV from memory-bound toward compute-bound; decode is dominated by matrix-vector, prefill by matrix-matrix; a fused dequantise-multiply kernel is the standard shape; a Q4_K kernel example uses one warp per output element with a shuffle reduction and no shared memory; a fused dequant-GEMM CPU rebuild reported 10-30 % more throughput, most in decode. Marlin and llama.cpp's own `mmvq` wave/subgroup choices were **not** covered | https://arxiv.org/pdf/2606.11357 , https://arxiv.org/pdf/2508.08531 , https://www.turintech.ai/blog/improving-vllm-cpu-inference-rebuilding-a-dequantisation-gemm-kernel | SECONDARY |
| B6 | Skinny GEMM (batch 1-16) is memory-bound; **split-K / Stream-K** partitions K to occupy the GPU and avoid wave quantisation (final wave leaves compute units idle), at the price of a reduction step (atomic or second kernel); sliced-K splits K across warps for small M,N and large K; Stream-K is described as reducing the number of tile sizes to profile | https://docs.nvidia.com/cutlass/latest/media/docs/cpp/efficient_gemm.html , https://arxiv.org/pdf/2402.00025v2 | SECONDARY (NVIDIA-side concepts; transfer to RDNA2 is **UNVERIFIED**) |
| B7 | **KernelBench** (ICML 2025, 250 PyTorch workloads, metric fast_p = fraction both correct and faster than a baseline by factor p): frontier reasoning models matched the baseline in under 20 % of cases; execution and profiler feedback in an iterative loop helped; difficulty grows with p. **KernelFoundry** (2026, evolutionary, SYCL/CUDA) proposes templated kernels so the model tunes tile/block sizes and notes shortcomings of KernelBench that need careful reading of reported speedups | https://arxiv.org/pdf/2502.10517 , https://arxiv.org/html/2603.12440v1 | SECONDARY |
| B8 | Not found: Vulkan `VK_EXT_external_memory_host` behaviour/throughput on RDNA APUs; whether the 680M exposes `VK_KHR_cooperative_matrix` (OWN: RDNA2 has no matrix units, so a matrix-core path is unlikely there); AlphaEvolve and Kernel Tuner results; llama.cpp `test-backend-ops` availability in our pinned build | search gaps | UNVERIFIED |

## 2. What "RAM as GPU memory" and "a better ZLUDA" can honestly mean here

1. **On an iGPU the RAM already is the GPU memory.** The 680M uses the same DRAM as the CPU. "Emulating VRAM from RAM" is raising the GTT/TTM limit (P16), not emulation, and it cannot exceed DRAM bandwidth. Consequence (**OWN**, to be measured): for **decode**, an iGPU path is bounded by the same bytes-per-second as the CPU path, so a GPU backend will not make token generation dramatically faster than a well-tuned CPU path on this machine; the GPU can help **prefill** (compute-bound), free CPU cores, and possibly lower power. Anyone promising otherwise has not measured.
2. **"SSD as memory"** is streaming through the page cache (P16 M5): bounded by sequential read bandwidth; no kernel can change that.
3. **A ZLUDA-style CUDA translation layer is the wrong target for HSCL1:** huge surface (driver API, PTX, libraries), maintained by a project that just went back to hobby status, depends on ROCm (which does not officially list our iGPU; HSA override tricks are **UNVERIFIED** here), and carries a possible licence question (B1). Our workload does not need CUDA: Vulkan compute already runs llama.cpp on this class of hardware without ROCm.
4. **The right "own backend" is small and measured:** a Vulkan compute micro-library of the few kernels that matter for inference (bandwidth/triad test, quantised GEMV, tiled GEMM, later attention), with a correctness reference and a benchmark harness, used (a) to learn where the 680M really stands, (b) to feed the memory advisor (P16) with real bandwidths, and (c) only if it beats the existing ggml-vulkan kernels on specific shapes, to propose them upstream or load them as a plugin.
5. **Not planned:** CUDA binary translation, PTX handling, anything that runs Nvidia binaries on AMD. If the owner wants that, it needs a separate legal review first (stop-and-ask).

## 3. Phases (each ends with numbers, not claims)

- **B0 Baseline on the real machine (host side, no new code).** On the owner's Windows host with the real Radeon 680M: `vulkaninfo` (device, heaps, subgroup size, cooperative-matrix extension present or not), the pinned llama.cpp `llama-bench` CPU-only vs Vulkan (`-ngl 99`) with one 2B and one 7B-class GGUF: prompt-processing and token-generation tokens/s, 3 runs, median and spread. Also the DRAM bandwidth from a bounded memcpy/triad test and the DDR5 speed from firmware/SMBIOS. Output: one table; it decides whether a GPU backend is worth any effort.
- **B1 Micro-benchmarks (Rust, own code).** A small crate with `wgpu` or `ash` (decision after a spike: portability vs control of subgroup operations): (a) stream triad on a host-visible and a device-local buffer: achieved GB/s vs the DRAM ceiling; (b) GEMV f16 and fused-dequant Q8_0/Q4_K with variants: naive, vec4 loads, subgroup-reduction, different workgroup sizes, wave32 vs wave64 if exposed; (c) tiled GEMM f16 with shared memory, split-K variant for skinny shapes. Every kernel has a CPU reference and a tolerance; a kernel that is wrong never reaches the benchmark table.
- **B2 Apples-to-apples against ggml-vulkan.** Compare per-op, same shapes as the real models (e.g. 4096x4096 Q4_K GEMV, 4096x11008 prefill GEMM with N = 512), using the pinned llama.cpp's op-level performance test if its build has it (**UNVERIFIED**; otherwise time ggml ops through a small harness). Report achieved GB/s and GFLOPS next to the ceilings.
- **B3 Decision gate.** If our kernel beats ggml-vulkan by a margin that survives 3 runs on at least two shapes: write it up and prepare an upstream proposal or a backend plugin. If not: publish the negative result honestly; the benchmark crate stays as a diagnostic tool (it still feeds P16).
- **B4 Autotuning loop = the safe RSI use case.** Objective is **verifiable**: correct against the reference and faster, measured by the harness. Search space = templated parameters (tile sizes, vector width, workgroup size, unroll, split-K factor, subgroup size) explored by grid/random/evolutionary search first (no model needed); optional LLM-proposed kernel *variants* second, because KernelBench shows free-form generation is weak (B7) while templated parameter tuning is the part reported to work (KernelFoundry). Guards from P17: the evaluator, reference kernels and tolerances are **protected paths** the search cannot edit; candidates run in a disposable VM or container without secrets; held-out shapes the search never saw; an archive of variants with results; human approval to merge a winner.
- **B5 Integration with the advisor (P16).** Measured bandwidths and the best kernels' parameters become inputs of `hscl ai tier`/`hscl ai fit`: predicted ceilings use **measured** DRAM and GTT bandwidth, not datasheet numbers.

## 4. Guesses (hypotheses, each mapped to a measurement)
| # | Guess | Why | Measured by |
|---|---|---|---|
| GB1 | Token generation on the 680M iGPU is not much faster than on the 8 CPU cores, because both are limited by the same DRAM bandwidth (B4) | shared bus | B0 table |
| GB2 | **[WEAKENED by 11.2 and 12.1]** Prompt processing gains most from the GPU; the earlier reasoning "no matrix units, so the gain is modest" was wrong about the extension: `VK_KHR_cooperative_matrix` is exposed on this device (speed unknown) | OWN reasoning corrected by the inventory | B0 with cooperative matrix on/off, B1 probe |
| GB3 | Fused dequant GEMV on a 12-CU iGPU becomes compute-bound for Q4_K unless loads are vectorised and the reduction is done with subgroup operations (B5) | dequant cost | B1(b) |
| GB4 | The practical wins are parameter tuning (workgroup size, vector width, subgroup use, split-K), not new algorithms | KernelFoundry-style templated tuning, split-K for skinny shapes (B6, B7) | B4 |
| GB5 | Placement in GTT vs device-local heap makes little difference on this APU, but TLB effects under concurrent CPU use may show up | B3 | B1(a) with and without CPU load |
| GB6 | A better ZLUDA is not needed to run local AI on this machine; Vulkan is enough | B2 | B0 |

## 5. Open questions
| # | Question | Answer by |
|---|---|---|
| O1 | Does the 680M expose cooperative-matrix or only plain compute? Subgroup size(s)? | B0 `vulkaninfo` |
| O2 | What are the real DRAM speed and the achievable copy bandwidth of the owner's machine? | B0/B1(a) |
| O3 | How much faster is Vulkan than CPU for prefill and for decode on this machine? | B0 |
| O4 | Does `VK_EXT_external_memory_host` (import host memory without a copy) exist and help on RDNA2 APUs? | spike in B1 |
| O5 | `wgpu` or `ash` for the micro-library? | spike |
| O6 | Does the pinned llama.cpp ship an op-level performance test? | `--help`/build tree of the pinned build |
| O7 | Is a plugin interface for external ggml backends practical, or is upstreaming the only route? | read ggml's backend registry docs |
| O8 | Licence position of any CUDA-compatibility work (only if the owner asks) | owner + legal |
| O9 | Does Linux-on-metal (owner boots the image) change the numbers vs the Windows host driver? | owner |

## 6. Risks and honesty
- The most likely honest outcome is "the existing Vulkan backend is already near the bandwidth ceiling for decode on this machine"; the plan values that answer as much as a faster kernel.
- No benchmark number enters README or release notes without hardware, driver, build, model and three-run spread next to it.
- Anything about training or model-weight self-modification stays out of scope.

---

## 7. Uncomfortable findings and ways around them (second research round; SOTA pointers)

The inconvenient results of section 1 are: decode on an iGPU shares the CPU's DRAM bandwidth (B4); ZLUDA is a hobby project (B1); free-form LLM kernel generation is weak (B7); no 680M numbers exist (B2). The search for ways around the bandwidth wall points to levers that act on **bytes read per generated token**, not on kernel speed. They come **before** any own kernel.

| # | Lever | What the sources say | Grade | Fits our setup because |
|---|---|---|---|---|
| W1 | **Choose models by active parameters (MoE).** Bytes per token follow the active experts, not the total size | Qwen3-30B-A3B (about 3B active) reported at 12-15 tok/s on a Ryzen 9 7950X3D with Q6_K, 15-20 tok/s expected on dual-channel DDR5 laptops, about 18-20 on a Snapdragon X Elite with about 135 GB/s, over 100 tok/s on a Strix Halo APU in an aggregator summary (original data not verified) | SECONDARY (community, uncontrolled) | `hscl ai fit` must report **bytes read per token** (active weights + KV), not only file size; try one MoE next to one dense model on our machine |
| W2 | **Speculative decoding.** Verifying K drafted tokens reads the weights once, which matters exactly when decode is bandwidth-bound | EAGLE-3 reported 2-2.5x in other frameworks (llama.cpp PR #18039, rebased, MTP-compatible, wired into the simple speculative example first, a June 2026 load-assertion bug report exists); the 2-3x claim for the llama.cpp integration is a social-media post | SECONDARY, rough edges | Test cheap forms first (prompt-lookup/n-gram, a small same-family draft model); the draft model must fit the cache/RAM budget; measure acceptance rate on **our** coding tasks, not on benchmarks |
| W3 | **Batch K sequences.** Weights are loaded once for all K; attention/KV reads are **not** amortised; small batches (4-16) stay memory-bound; the gain saturates | General roofline analyses and a small llama.cpp Apple-GPU study (batch up to 4, saturating) | SECONDARY | This is the cost model for A10 (K rollouts + verifier): aggregate tokens/s should rise with K at small K, then flatten as KV reads dominate; sweep `-np` and plot aggregate vs per-slot tokens/s, long contexts hurt first |
| W4 | **Reuse the KV prefix in agent loops.** Keep system prompt and tool schemas byte-identical, pin the agent to one slot, save/restore slot state | llama-server slot save/restore works (restore of a small slot in under a millisecond in one tutorial); a proxy reports skipping about 96 % of prompt processing after restoring a snapshot; snapshots are large (about 0.2 GB at 3.7k tokens, 0.8 GB at 15k); slot choice takes the first sufficient prefix match; sliding-window models (Gemma-4-E2B example) lose most of the gain; sharing one prefix across sessions is only a feature proposal | SECONDARY (community) | Prefill is the compute-bound phase where a 12-CU iGPU is weakest, and an agent resends the same long prefix every step: this is probably the biggest practical win for the local agent (P24) |
| W5 | **[SUPERSEDED by 12.1: this machine has four equal 6 GB LPDDR5 channels, no mixed-DIMM case; only the speed/bus-width measurement remains]** **Verify the memory configuration first.** A mixed-capacity laptop (for example 8+16 GB) may run part of its RAM single-channel | Intel's flex-mode documentation: the matched portion runs dual-channel, the remainder single-channel at half bandwidth; **AMD platforms were not covered**; Task Manager does not show channel mode | SECONDARY (Intel docs, retail forums) | Our machine reports 24 GB DDR5 (CLAUDE.md); whether it is 2x12, 8+16 or soldered+SODIMM is unknown here. Read the DIMM layout and speed (WMI `Win32_PhysicalMemory`, a CPU-Z memory tab) and run a STREAM-style test; if the bandwidth is half of the rated value, that is the largest free speed-up in this whole plan |
| W6 | **Fewer bytes per weight and per KV entry.** Lower quantisation, q8_0 KV (P16), shorter contexts | P16 M7 | SECONDARY | Already in P16; the advisor ranks options by bytes per token |
| W7 | **Lossless weight compression (DFloat11).** Huffman coding of the BF16 exponent gives about 70 % size, bit-identical output, an on-the-fly GPU decode kernel; reported 2.3-46.2x faster than CPU-offloading an uncompressed model (not versus uncompressed on-GPU) | https://arxiv.org/pdf/2504.11651 , https://neurips.cc/virtual/2025/poster/115225 | SECONDARY | Our weights are already integer-quantised GGUF, so the exponent trick does not apply directly; entropy coding of quantised blocks is a **research idea** (small expected gain, kernel cost on a small iGPU); parked, not planned |
| W8 | **Sustained, not burst, performance.** Laptop power limits and temperature | OWN reasoning, no source | UNVERIFIED | Every benchmark gets a 10-minute run; report the first and the last minute |
| W9 | **Chunked prefill** (piggybacking decodes with chunked prefills) | SARATHI https://arxiv.org/pdf/2308.16369 | SECONDARY | Relevant only when serving several agents at once; later |

Reading list (titles as found; none read in full yet): EAGLE-3 arXiv 2503.01840, multi-token prediction arXiv 2404.19737 (both named in the llama.cpp discussion), DFloat11 arXiv 2504.11651, SARATHI arXiv 2308.16369, KernelBench arXiv 2502.10517, KernelFoundry arXiv 2603.12440, "The Correctness Illusion in LLM-Generated GPU Kernels" arXiv 2606.20128, "Operator-Aware Mixed-Precision Tolerance Calibration for Tensor Kernels" arXiv 2607.16228, TileFuse arXiv 2606.11357.

## 8. Creative tests (how to find the truth cheaply and catch wrong kernels)

| # | Test | What it catches | Grade of the idea |
|---|---|---|---|
| T1 | **Roofline canary:** sweep threads 1..16 in `llama-bench`; the knee where tokens/s stops rising shows bandwidth saturation; report tokens/s as a percentage of a STREAM-style measured bandwidth ("bandwidth efficiency") | decides if any kernel work can still help (efficiency near 75 % means no) | OWN; one report quotes 75 % utilisation in performance mode |
| T2 | **Memory-config probe:** DIMM layout and speed (WMI/CPU-Z) + STREAM at several buffer sizes (the single-channel region of a flex layout would show a bimodal result) | single-channel or JEDEC-speed surprises | OWN; flex mode facts are Intel's |
| T3 | **Metamorphic tests for GEMM/GEMV:** linearity A(B+C)=AB+AC, scaling A(sB)=s(AB), (AB)^T = B^T A^T, identity and zero matrices, row/column permutation invariance, block decomposition; compare to an f64 CPU reference with a **tolerance that grows with K** (accumulation error), not one fixed `allclose` | wrong index math, tile edge bugs, quant-block bugs that a single-shape check misses (a 2026 preprint says KernelBench's oracle is `allclose` on the reference shape and misses input-dependent bugs) | SECONDARY (preprint) + OWN |
| T4 | **Shape fuzzing:** random M,N,K including 1, odd sizes, K not a multiple of the quant block (32/256), very large K, non-aligned buffers; denormals, infinities, NaN propagation | out-of-range reads/writes, tail handling | OWN |
| T5 | **Mutation testing of our own kernels:** inject an off-by-one in the tile loop, a dropped last element, a wrong sign; the harness must go red (same rule as our gates) | a harness that cannot fail | OWN (project rule) |
| T6 | **Three-way differential:** own kernel vs ggml-vulkan vs CPU on identical inputs | which one is wrong when they disagree | OWN |
| T7 | **End-to-end equivalence:** logits/KL divergence between CPU and Vulkan on a fixed prompt set within a stated tolerance | numerics drift that op-level tests miss | OWN |
| T8 | **Debug run with Vulkan validation layers** (and robust buffer access) | API misuse, out-of-bounds in shaders | UNVERIFIED (search covered neither GPU-assisted validation nor shader bounds fuzzing; read the Khronos validation-layer docs first) |
| T9 | **Determinism check:** same input twice gives bitwise-equal output; split-K with atomics will not: document which kernels are deterministic | flaky benchmarks, unreproducible bug reports | OWN |
| T10 | **Sustained run:** 10 minutes of decode, tokens/s and temperature per minute | thermal throttling hidden by short runs | OWN |

## 9. Revised phase order (replaces the order in section 3; levers before kernels)
1. **B0 baseline + memory probe (T1, T2):** `vulkaninfo`, DIMM layout/speed, STREAM-style bandwidth, `llama-bench` CPU vs Vulkan 1..16 threads (3 runs, spread). Cheapest and most informative; it can end the whole kernel question.
2. **L1 MoE vs dense (W1):** one MoE and one dense model of similar quality on our machine; add *bytes per token* to the `hscl ai fit` output.
3. **L2 batching sweep (W3):** `-np` 1,2,4,8 with the agent task prompts; feeds A10.
4. **L3 prefix reuse (W4):** measure prompt-processing time per agent step with and without slot reuse on the A1 task set.
5. **L4 speculative decoding (W2):** prompt-lookup/n-gram and a small draft model first; EAGLE-3 only if the pinned build ships it and its load bug is fixed.
6. **B1-B3 own kernels** only if B0 shows bandwidth efficiency clearly below the ceiling or L1-L4 leave a compute-bound phase worth attacking (prefill GEMM). Tests T3-T9 are part of B1, not an afterthought.
7. **B4 autotuning (the safe RSI use case)** with the protected evaluator (P17); candidates by parameter search first, LLM variants second.
8. **B5 integration with the advisor (P16)** using the measured numbers.

## 10. Updated risks
- The most valuable outcome may be a **table that says where the time goes** and which cheap levers work; this is a legitimate result and goes into the README only with hardware, driver, build, model and spread.
- If the memory probe shows single-channel operation, the fix is hardware (matching DIMMs), not software: say so plainly.
- Every claim of a speed-up needs the T3-T7 correctness evidence next to it.

---

## 11. Round 3: gaps filled, assumptions corrected (sources are search snippets unless stated; flags must be re-checked against the pinned llama.cpp build with `--help`)

### 11.1 Tools and flags found
| Topic | Finding | Source | Consequence |
|---|---|---|---|
| KL divergence for quantisation quality | `llama-perplexity` works in two steps: run the **f16** model with `--kl-divergence-base FILE` (saves its logits; the file is huge: 11 GiB for LLaMA 2 and 37 GiB for LLaMA 3 on the wikitext-2 test set), then run the candidate with the same base file plus `--kl-divergence`. Output: KLD, perplexity and log perplexity ratio, how often the top token changes, percentiles of the change in the probability of the correct token. Scale seen in one table: q6_K KLD about 0.0055, f16 baseline about 0.00055. Wikitext-2 is the contributor convention. Mirrors of different llama.cpp versions: flag names may have moved | https://sources.debian.org/src/llama.cpp/7965%2Bdfsg-1/tools/perplexity/README.md , https://github.com/ggerganov/llama.cpp/pull/5076 | The KV-type quality gate (P16 T-kv) is feasible with stock tools. Budget disk for the logits file (use a short text slice or few chunks for our 2B model) and calibrate the threshold by comparing q8_0 KV against f16 on our model (Q21) |
| Speculative decoding flags | Draft model: `-md/--model-draft` (same tokenizer as the main model), `--draft-max` (default 16 in the mirrored doc), `--draft-min`, `-ngld` for draft GPU layers. Draftless: `--spec-type ngram-simple|ngram-map-k4v|ngram-mod` with `--spec-ngram-size-n/m` and `--spec-ngram-min-hits`; a draftless type takes precedence if both are set. An open issue reports `llama-server` drafting fewer tokens and running 10-15 % slower than `llama-speculative-simple` with identical settings. A `--draft-p-min` flag appears only in a generated Q&A dataset: do not rely on it | https://github.com/ggerganov/llama.cpp/pull/10455 , https://github.com/ggml-org/llama.cpp/issues/12968 , https://unsloth.ai/docs/basics/inference-and-deployment/speculative-decoding | L4 order: draftless n-gram first (no extra model, no extra bandwidth for a draft), then a small same-family draft; benchmark **both** server and the simple example; verify every flag in the pinned `--help` |
| Vulkan validation | GPU-Assisted Validation instruments shaders at run time and reports errors; **off by default**; enabled via Vulkan Configurator, `vk_layer_settings.txt` or `VK_EXT_validation_features`; needs Vulkan 1.1+, extra device memory and descriptor slots; for `buffer_reference` it checks address/size ranges when `VK_EXT_buffer_device_address` is enabled; `khronos_validation.select_instrumented_shaders` limits instrumentation. The slides are 2019-2020 and mark buffer-address checks "in development"; `robustBufferAccess` is a separate device feature and was not covered | https://fuchsia.googlesource.com/third_party/Vulkan-ValidationLayers/+/HEAD/docs/gpu_validation.md | T8 is feasible as a debug-only run; read the current LunarG documentation for the exact setting names before scripting it; never ship with validation on |
| Offline compliance scan | `oscap-chroot CHROOT_PATH xccdf eval ...` performs an offline SCAP evaluation of a filesystem mounted at an arbitrary path (man pages from Red Hat, newest dated 2016; `--cpe` does not support external OVAL dependencies yet). Lynis `--rootdir` and kernel-hardening-checker usage were **not** found | https://man.archlinux.org/man/oscap-chroot.8.en | Q7 is mostly answered: try `oscap-chroot` on the unsquashed rootfs with the upstream Ubuntu datastream; availability in Ubuntu 26.04's `openscap-utils` is UNVERIFIED; Lynis and the kernel checker still run inside a booted VM |
| Plasma Welcome pages | Custom pages live in `/usr/share/plasma/plasma-welcome/extra-pages/`; a numeric prefix with a dash orders them; they appear **right before the "Get Involved" page**, so our `01-HSCL1.qml` is **not** the first page; the first page is the stock "Welcome ... running KDE Plasma" (what we saw); custom pages are QML-only (root inherits `Kirigami.Page`); a KDE feature request to remove or customise the default pages is still open | https://www.github.com/KDE/plasma-welcome , https://bugs.kde.org/show_bug.cgi?id=499555 | X2 answered: expected behaviour. We cannot remove the stock first page (it names HSCL1 through os-release; the KDE mascot is KDE's own). To make our page prominent we would need a different mechanism (our own welcome app, W23.1) |
| Release upgrades | `/etc/update-manager/release-upgrades`, `[DEFAULT] Prompt=never|normal|lts`: `never` disables the notification **and** manual `do-release-upgrade -d`; with `never` the tool says no new release was found, a known misleading message | https://bugs.launchpad.net/ubuntu/bionic/+source/update-manager/+bug/1795024 | U3 is an owner decision with three options: `never` (safe for identity, blocks users), `lts` (next LTS only, happens in 2028), `normal` (default: may offer an interim Ubuntu release that replaces our identity). Nothing found on how derivatives set `unattended-upgrades` origins |
| systemd on 26.04 | systemd 259 (package 259.5-0ubuntu3, 259.9 in proposed at the time of the listing), cgroup v1 removed; upstream NEWS lists `importctl` for sysext/confext/portable images; whether sysext is enabled by default on Kubuntu was **not** covered | https://www.ubuntuupdates.org/package/core/resolute/main/base/systemd , https://www.github.com/systemd/systemd/blob/main/NEWS | E1 (sysext experiment) is unchanged; it also tells us whether `importctl` exists on the image |

### 11.2 Assumptions corrected or weakened
- **"The 680M needs a matrix path":** no source shows cooperative-matrix support for RDNA2 iGPUs; llama.cpp logs for a sibling RDNA2 card (RX 6700 XT) show RADV reporting `warp size: 64` and `fp16: 1`. Inference, not a fact for the 680M: it probably behaves like that card. Check with `llama-server --list-devices` or `vulkaninfo` (O1).
- **Driver version is a benchmark variable:** a Mesa update changed RADV prompt processing by about 13 % on Strix Halo (521 to 624 tok/s on one model) while token generation stayed about 49 tok/s (https://www.hardware-corner.net/llama-cpp-amd-radv-vulkan-driver-update/). **Every benchmark record must carry the Mesa/driver version.** Our image ships Mesa 26.0.8 (seen in the squashfs path list); the Windows host driver differs, so Windows and image numbers are different experiments.
- **Prompt processing on iGPUs can be fast with Vulkan** (Strix Halo numbers above), so "the GPU only helps a little in prefill" (GB2) is **weaker** than I wrote; keep it a hypothesis until B0 measures the 680M.
- **Flex-mode memory facts are Intel's;** AMD Ryzen 7000-series laptop behaviour with mixed DIMMs was not found. The memory probe (T2) measures instead of assuming.

### 11.3 New open questions
| # | Question | Answer by |
|---|---|---|
| O10 | What does `--list-devices`/`vulkaninfo` say for the 680M: warp size, fp16, int dot, cooperative matrix? | B0 |
| O11 | Does the pinned llama.cpp offer `--spec-type` and the n-gram flags, and does server vs simple example differ on our machine? | pinned `--help` + L4 |
| O12 | Size of the logits file for a 2B model on a 2-4 chunk slice, and the KLD of q8_0 KV vs f16 on our model | T-kv experiment |
| O13 | Is `oscap-chroot` present in Ubuntu 26.04 and does it run with the upstream Ubuntu datastream? | try in WSL |
| O14 | Which `release-upgrades` setting does the owner want (U3)? | owner |
| O15 | Do Windows-host and image (Mesa 26.0.8) numbers agree within noise for the same model? | B0 on both |


---

## 12. This machine, measured on 2026-11-06 (inventory before any benchmark)

### 12.1 Facts (PRIMARY: read from this PC with WMI and `vulkaninfo`; the raw dump is `artifacts/vulkaninfo-host.txt`)
| Item | Value | Consequence |
|---|---|---|
| CPU | AMD Ryzen 7 7735HS, 8 cores / 16 threads, L3 16 MiB | the whole decode working set is far larger than the cache; a draft model of a few hundred MB does not fit L3 either |
| RAM | **four 6 GB modules** on channels A-D (SMBIOS memory type 35 = LPDDR5), rated 6400 MT/s, **configured 5500 MT/s**; Windows sees 19.8 GB of 24 GB | **The mixed-DIMM / flex-mode worry (W5) does not apply**: all channels are equal. Bus width is not reported: 128-bit x 5500 MT/s would be 88 GB/s, 128-bit x 6400 would be 102.4 GB/s, a 64-bit bus half of that. Spec sites disagree (102.4 vs 51.2 GB/s): **measure** |
| Missing 4.2 GB | about 4 GB (`AdapterRAM` 4 GB) is carved out for the GPU in firmware | OS and apps live in 19.8 GB; at measurement time only 6.4 GB were free, so a model plus KV cache above about 6 GB competes with the desktop. Benchmarks need a quiet machine |
| GPU | AMD Radeon Graphics (device id 0x1681 = the Radeon 680M family), Windows driver 32.0.21043.12001, Vulkan reports the **AMD proprietary driver 26.6.1**, API 1.4.315 (not RADV: the HSCL1 image uses Mesa RADV, a different driver) | Windows-host numbers and image numbers are **different experiments** |
| Vulkan heaps | device-local heap **9.10 GiB** (budget 8.64 GiB), a **4.55 GiB** host-visible heap, a 256 MiB device-local heap | the hard GPU budget on the Windows host is about 8.6 GiB for weights + KV + compute buffers |
| Subgroups | subgroup size 64, min 32 / max 64, `subgroupSizeControl = true` | kernels can request wave32 or wave64 and the choice is a tuning parameter (B1) |
| Compute limits | shared memory 32 KiB, 1024 invocations per workgroup, timestamps supported, **`timestampPeriod` = 10 ns** per tick | kernel timings need loops long enough (hundreds of microseconds at least) to be meaningful |
| **Extensions present** | **`VK_KHR_cooperative_matrix` (feature true, compute stage)**, `VK_EXT_external_memory_host`, `VK_KHR_shader_integer_dot_product`, `VK_KHR_shader_float16_int8`, `VK_KHR_16bit_storage`, `VK_KHR_8bit_storage`, `VK_KHR_buffer_device_address`, `VK_KHR_shader_subgroup_extended_types`, `VK_EXT_memory_budget`, `VK_AMD_shader_core_properties(2)` | **Corrects an earlier assumption** (11.2 / GB2): the driver exposes cooperative matrix on this iGPU. Exposed does not mean fast (it may be lowered to ordinary wave arithmetic): the supported component types and the real speed-up are measured (B0 with the cooperative-matrix path on and off in llama.cpp, and a probe of `vkGetPhysicalDeviceCooperativeMatrixPropertiesKHR` in B1). `VK_EXT_external_memory_host` exists: host-pointer import (zero copy) is possible in principle; its speed is unknown (O4) |
| Validation | `VK_LAYER_KHRONOS_validation` 1.4.357 and `glslc`, `glslangValidator`, `slangc`, `spirv-opt`, `spirv-val` from the Vulkan SDK 1.4.357 are installed | T8 (validation-layer debug run) is possible now; shader compilation needs nothing new |
| Toolchain | Rust 1.96, cargo, cmake, ninja, Python; ROCm/HIP SDK 7.1 present (`hipconfig`, clang); no gcc/cl | micro-benchmarks in Rust (`ash` + shaders compiled by `glslc`); a C STREAM test is not needed because the Rust triad does the same job |
| Power plan | **Balanced** | benchmarks must record it; run with High performance and restore afterwards (reversible host setting, tell the owner) |
| AI binaries | **no `llama-bench`, `llama-server`, `llama-perplexity` or `test-backend-ops` on this PC**, no `.gguf` files in the usual places; Ollama holds one 14 GB blob | see 12.2 |

### 12.2 What is still needed (and how it is obtained safely)
1. **llama.cpp, pinned build b12130** (the build already used for the 2B probe): `llama-b12130-bin-win-vulkan-x64.zip` (37 681 384 bytes) and `llama-b12130-bin-win-cpu-x64.zip` (24 730 443 bytes), downloaded from the official release and **checked against the GitHub-reported sha256** (`200fee57...5e9d` for the Vulkan zip, `6a6e4de5...78a7` for the CPU zip) before anything is unpacked, into a disposable folder under `artifacts/`.
2. **Small GGUF models** with their upstream sha256 checked: one dense coder model of about 3B (Q4_K_M), a 0.5B model of the **same family** as draft for speculative decoding (same tokenizer), one small MoE (about 7B total / 1B active) for L1, and, for the KL gate, the f16 version of the 2B probe model. The 14 GB Ollama blob is too large for the 8.6 GiB device-local budget and for 19.8 GB of RAM with the desktop running; it stays unused.
3. **A quiet machine:** close browsers and heavy apps (6.4 GB free right now), no VM and no build during measurements, High performance plan, AC power; the release run must be finished first.
4. **Sensors without extra tools:** Windows performance counters through `Get-Counter`/`typeperf` (CPU `% Processor Performance`, GPU engine utilisation, committed memory) sampled each second give clock behaviour and detect throttling indirectly; temperatures would need a vendor tool and are **not** available now: say so in every report.
5. **Code to write:** the Rust micro-benchmark crate (STREAM-style triad on CPU threads, then Vulkan triad/GEMV/GEMM through `ash`), the harness that runs `llama-bench` with fixed arguments and stores JSON, and the report generator. Nothing else is missing.
6. **Decision made from the inventory:** use `ash` + GLSL compiled by `glslc` (present): the device exposes subgroup size control and cooperative matrix, and the search found no evidence that `wgpu` exposes subgroup-size control on Vulkan (its WebGPU-side subgroup features are still new and platform-limited). `slangc` is installed as a later alternative.

## 13. How to benchmark and test (method; sources are snippets of tool docs and posts, verify against the pinned build)

**llama.cpp level**
- `llama-bench` defaults to 5 repetitions per test and reports mean +/- spread; it excludes tokenisation and sampling; it has a warm-up control and priority options; it can measure at a given context depth. We use `-r 5` or more, **report the spread, never only a mean**, and keep prompt processing (`-p`, compute-bound) separate from token generation (`-n`, bandwidth-bound).
- Warm-up is separate from timed runs; the first call pays for loading, page cache misses and shader compilation. Discard at least two warm-up runs per configuration and say which mode was used.
- Steady state: let the machine run about 5 minutes under load before the timed runs and also run the 10-minute sustained test (T10); report the first and the last minute. A laptop under a 35-45 W limit will not hold burst clocks (sourced only as general advice; our own counters decide).
- Test at **several context depths** (for example 0, 2k, 8k tokens): short prompts flatter the result and the KV read cost only shows at depth.
- Record with every row: CPU, RAM layout and configured speed, GPU, **driver name and version**, llama.cpp build number, model file name and sha256, quantisation, KV types, flags, threads, power plan, free memory, date. A number without these does not go into the README.
- Compare **cooperative matrix on and off** if the pinned build offers a switch (its name must be taken from the build's own documentation, not from memory) and Vulkan vs CPU-only builds on the same model.
- Time-to-first-token and generation throughput are different metrics; the agent harness (P24) cares about both because its prefix is resent every step.

**Own kernels (Vulkan)**
- Timing with timestamp queries: only if `timestampPeriod` is non-zero and the queue reports valid bits; ticks times the period give nanoseconds; read 64-bit results; write the first timestamp at the top of the pipeline; **never call `vkDeviceWaitIdle` inside the timed loop**. Here the period is 10 ns, so each measurement covers many dispatches (at least 100 microseconds per sample, preferably milliseconds) and the median of many samples is reported.
- Bandwidth = (bytes read + bytes written) / time, counted from the kernel's own access pattern (GEMV: weight bytes + vector bytes; GEMM: A + B + C); compare to the **measured** STREAM-style triad, not the datasheet. GFLOPS = 2*M*N*K / time.
- Cold vs warm: run each shape with a buffer set larger than any cache for the bandwidth tests; separate "first dispatch" (pipeline creation, shader compile) from steady dispatches.
- Correctness before speed (T3-T9); every benchmark row links to the correctness run of the same kernel version.
- Debug-only run with `VK_LAYER_KHRONOS_validation` (GPU-assisted validation is off by default and needs enabling through the layer settings; read the current LunarG settings reference before scripting it); never time with validation on.

**Statistics**
- At least 5 repetitions (30 for micro-kernels); report median, minimum, maximum and the interquartile range; flag a row whose spread exceeds 10 percent of the median as unstable and rerun on a quieter machine; never compare numbers from different drivers or power plans.

## 14. Rebuild path ("umbauen"): from measurements to a backend that llama.cpp can load
1. **Stage 0 (no backend):** results only, as tables in BUILD_LOG and a short report; the micro-library stays a diagnostic tool (B1-B3).
2. **Stage 1 (kernel upstream or fork):** if a kernel wins on two real shapes over 3 runs, prepare it as a change to the existing Vulkan backend of ggml (same shader layout, same tests of `test-backend-ops` if the pinned build has it) and offer it upstream; keep our harness as the evidence.
3. **Stage 2 (out-of-tree backend, only if Stage 1 is impossible):** ggml supports dynamically loaded backends: a backend built as a shared library (`GGML_BACKEND_DL`, which needs shared libraries) must export `ggml_backend_init` and may export `ggml_backend_score` so the loader can skip it on unsupported systems; applications load it through `ggml_backend_load` / `ggml_backend_load_all`; a library built this way must register its own backends or linking applications find no devices (sources: llama.cpp PR #10469 and `ggml-backend-reg.cpp` excerpts; **there is no step-by-step guide**, read the headers of the pinned build first, O7). This is a real maintenance burden (the backend interface changes with ggml) and is only justified by a measured gain.
4. **Gate for each stage:** the end-to-end equivalence test (T7, KL against the CPU result), the three-way differential (T6) and the sustained run (T10) on the exact pinned build.
5. **What is deliberately not built:** a CUDA translation layer (section 2), anything that would need ROCm for the 680M, and any change that cannot be reverted by deleting one plugin file.

## 15. Updated open questions (inventory answered some)
| # | Question | Status |
|---|---|---|
| O1 | Warp size, fp16, cooperative matrix on the 680M | **answered in part:** subgroup 64 (32-64 controllable), fp16 and int8/16-bit storage present, cooperative-matrix feature exposed; component types and actual speed-up still open (B1 probe, B0 on/off) |
| O2 | RAM speed and bandwidth | **answered in part:** four equal 6 GB LPDDR5 channels, 6400 rated, 5500 configured; achieved bandwidth still to measure (STREAM-style triad) |
| O4 | Does `VK_EXT_external_memory_host` exist | **yes (extension present)**; whether importing a host pointer is fast is open |
| O16 | Is the 5500 MT/s configured speed a firmware limit or a power state? Can it be raised? | owner/BIOS; not touched by us |
| O17 | Does the Windows driver's cooperative-matrix path beat the plain path for prompt processing? | B0 on/off |
| O18 | How much GPU memory does the Windows host really allow for a model (9.1 GiB heap, 8.6 GiB budget) with a browser open? | measure with `VK_EXT_memory_budget` during a load test |


## Verified 2026-11-07: what the owner asked for, and what is actually possible
Owner request: better offload, more RAM as VRAM, CPU alongside GPU, SSD as "VRAM backup", a second fast model as
offload. Full evidence in `docs/research/2026-11-07-apu-offload-vram-spill.md`; the short version:

| Request | Reality | Task |
|---|---|---|
| more RAM for the GPU | `ttm.pages_limit` (default half of RAM), **not** `amdgpu.gttsize` (deprecated); cmdline/modprobe + reboot; >= 4 GB desktop headroom | W2.5 |
| CPU as GPU alongside | already how partial offload works (`-ngl`, `-ot`, `-ncmoe`); the APU shares one memory bus, so this buys capacity, not speed | W2.10 |
| SSD as VRAM backup | **not possible** in llama.cpp: no VRAM/KV spill to disk, Vulkan has no unified-memory oversubscription (CUDA does) | W2.11 + KNOWN_LIMITATIONS |
| second fast model as offload | that is **speculative decoding** (`-md/--spec-draft-model`, `--spec-draft-n-max`); costs its own weights+KV, gain unmeasured on this iGPU | W2.10, measure with `llama-bench` |
| our current flags | `--mmap/--no-mmap/--mlock` **were removed upstream**; `--load-mode auto` disables mmap on Vulkan iGPUs (PR #26081); `-nkvo` is the KV-in-RAM switch | W2.10 (probe the pinned build first) |

Two iGPU defects reported by users on the same 680M class: all-NaN logits fixed by
`GGML_VK_DISABLE_INTEGER_DOT_PRODUCT=1` (#31509) and a device-lost under `--load-mode auto` fixed by `mmap` (#27360).
Both are recorded as **opt-in workarounds**, never defaults, until measured here.
