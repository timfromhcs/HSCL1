# AGENTS.md — HCS Unified Compute, Hybrid SAT & Research Workstation

> **Product family:** HCSUDA + hcswaver + HSCL1 integration  
> **Publisher / credit:** HCSMEDIA — Made with love by hcsmedia  
> **Primary owner:** `timfromhcs`  
> **Research date:** 2026-11-07  
> **Execution mode:** inspect-first, evidence-first, local-first, CPU-baseline-first, feature-branch-first  
> **Standalone engine repository:** `https://github.com/timfromhcs/hcsuda` (create only after confirming it does not already exist)  
> **Research Studio repository:** `https://github.com/timfromhcs/hcswaver` (create or initialize only after inspecting current account/repository state)  
> **OS integration repository:** `https://github.com/timfromhcs/HSCL1`  
> **Existing scientific application:** `https://github.com/timfromhcs/CQ-HECS`  
> **Existing local model platform:** `https://github.com/timfromhcs/hcs-foundry`

This document is both a product specification and an autonomous execution contract. It tells the agent how to extend its existing master plan, create and build the standalone HCSUDA engine, create or extend the hcswaver Studio, and integrate both into HSCL1 while preserving the existing CQ-HECS and HCS Foundry responsibilities.

It is not permission to pretend that ambitious targets already work. Implement, benchmark, verify, document, and then promote capabilities. A proposal, paper, shader that compiles, device extension name, or green UI indicator is not proof of end-to-end functionality.

---

# 0. READ THIS FIRST — THE PRODUCT IN ONE PAGE

## 0.1 What we are building

Build a **unified scientific-computing and research environment** with three cooperating layers:

1. **HCSUDA (HCS Unified Device & Solver Architecture):** a reusable, standalone compute/runtime library. It manages CPU and optional Vulkan GPU compute, capability detection, bounded asynchronous data movement, quantized tensor blocks, tiered storage, selected GPU-friendly SAT preprocessing/inprocessing, benchmarks, and typed APIs.
2. **hcswaver Studio:** a user-facing research workstation. It combines reduction design, SAT/solver experiments, GPU/CPU telemetry, reproducible benchmarks, adversarial counterexample search, and Lean 4 proof workflows. It calls HCSUDA and adapters to existing projects rather than reimplementing their capabilities.
3. **HSCL1 integration:** installable Debian packages, launchers, `hscl` CLI integration, Control Center cards, hardware/capability detection, local documentation, and optional ISO inclusion. HSCL1 must remain usable even when no Vulkan GPU is available.

The larger HCS ecosystem supplies model and scientific tools:

- **HCS Foundry** is the existing local-model catalogue/runtime/training/MCP platform. Reuse its local inference service and typed MCP contract. Do not create a second model manager inside HCSUDA or hcswaver.
- **CQ-HECS** is the existing quantum-circuit/simulation and SAT research codebase with provenance contracts, multiple solver paths, a local Studio/API and existing tests. Reuse it through a stable adapter. Do not fork its SAT implementation into a second source of truth.
- **HCSUDA** adds the research track for heterogeneous compute and GPU-assisted SAT transformations/hints. It must not silently replace CQ-HECS, CaDiCaL or Kissat.

## 0.2 The relationship between projects

```text
                         HUMAN RESEARCHER
                                |
                         hcswaver Studio
          ------------------------------------------------
          Reduction Canvas | Solver Lab | Proof Desk | Bench
          3D Evidence View | Adversarial Arena | Job Console
          ------------------------------------------------
                |               |                |
          HCSUDA API       CQ-HECS adapter   HCS Foundry API/MCP
                |               |                |
     -------------------   -------------    --------------------
     CPU compute          circuit/sat       local models/agents
     Vulkan compute       simulation        model catalogue
     tiered block store   provenance        local inference
     QSTP codecs          existing solvers   typed agent tools
     GPU SAT transforms   test corpus        safe code proposals
     -------------------   -------------    --------------------
                                |
                          HSCL1 integration
            Debian packages | hscl CLI | Control Center
                 launcher | services | ISO manifest
```

**The dependency direction is deliberate:** hcswaver can use HCSUDA and existing adapters, but HCSUDA must not depend on hcswaver, HSCL1, or HCS Foundry UI code. HSCL1 packages the components; it does not own their compute algorithms.

## 0.3 What it is not

Do not claim that the first release:

- merges CPU and GPU into one physical processor;
- turns an HDD into actual VRAM or guarantees that a 70B/405B model runs well on 4 GB RAM/VRAM;
- provides a literally contiguous 2 TB GPU virtual address space;
- guarantees zero-copy, zero-transfer, zero-bottleneck, or a fixed sub-microsecond CPU-to-GPU task launch;
- accelerates every SAT instance with a GPU;
- proves `P = NP` or `P != NP`;
- makes continuous SAT relaxation a complete exact SAT solver;
- makes an experimental GPU transformation trusted without a checkable certificate;
- makes a Vulkan 1.4 device support every optional Vulkan extension or hardware matrix instruction;
- makes a browser WebGPU path equivalent to a native Vulkan path;
- simulates a full physical system merely because it visualizes solver telemetry.

The correct product claim is: **a capability-aware heterogeneous computing platform that measures where CPU, GPU, local storage, compression and specialized algorithms help, and returns verifiable results with explicit fallbacks and limitations.**

---

# 1. REQUIRED FIRST ACTION — REPOSITORY, MACHINE AND PLAN AUDIT

Do not code before this audit. Repository names above are targets, not proof that repositories exist or that the current agent has write access.

## 1.1 Inspect every repository

For each reachable repository, record:

```bash
git status --short --branch
git remote -v
git log -10 --oneline --decorate
git branch -a
git tag --list --sort=-version:refname | head -30
git ls-remote --heads origin
git ls-remote --tags origin
```

Repositories to inspect:

- `timfromhcs/HSCL1`
- `timfromhcs/CQ-HECS`
- `timfromhcs/hcs-foundry`
- `timfromhcs/hcswaver` if it exists
- `timfromhcs/hcsuda` if it exists

Read the current root `AGENTS.md`, all referenced plans, README, architecture, package manifests, API/MCP docs, tests, CI workflows, licensing and known-limitations docs. Prefer the latest remote default branch, but preserve any local uncommitted work. Do not assume a previous agent's audit is still current.

## 1.2 Permission and ownership check

- Determine whether the authenticated GitHub identity can read, create, push, open PRs, update repository settings and publish releases.
- Never report a push, PR, merge, release or repository creation as successful unless the API/CLI confirms it.
- If a target repository is missing and repository creation is permitted, create it with the correct public visibility, chosen license, description, default branch and security settings. If creation is not permitted, build locally and report the exact blocker and one command for the owner to run.
- Never use force-push, rewrite published history, delete unreviewed branches or push directly to `main`.
- Do not overwrite a root AGENTS file without reading it and preserving its existing requirements.

## 1.3 Extend the master plans before implementation

The agent must update the current plans, not merely add a new isolated file:

**HSCL1**
- Extend root `AGENTS.md` with an HCS Compute & Research Workstation integration section.
- Extend the current long-horizon plan under `docs/superpowers/plans/` with milestones for HCSUDA packages, hcswaver app integration, CPU fallback, Vulkan capability tests, ISO size budget and VM verification.
- Add ADRs under the repository's established ADR/decision directory.
- Update `docs/ARCHITECTURE.md`, `docs/CLI.md`, `docs/BUILDING.md`, `docs/CLAIMS.md`, package manifests and `docs/KNOWN_LIMITATIONS.md` only when backed by implementation/evidence.

**HCS Foundry**
- Extend its existing AGENTS/architecture plan with a HCSUDA compute-adapter and hcswaver orchestration contract.
- Keep model downloads, model metadata, local inference, agent models and existing model training in Foundry.
- Do not copy Foundry's model catalogue, resource governor, model downloader or MCP server into HCSUDA.

**CQ-HECS**
- Extend its research/agent plan with an optional HCSUDA hybrid-compute adapter.
- Keep CQ-HECS provenance/result contracts authoritative for CQ-HECS runs.
- Preserve its exact/approximate distinctions, its existing solver paths and independent verification.

**hcswaver**
- Establish its own product roadmap and API compatibility policy.
- Keep the UI, orchestration, workspace/project storage, user workflows and visual explanations here.

**HCSUDA**
- Establish the compute library roadmap, C++ ABI/API policy, file formats, benchmark corpus policy, driver capability contracts and release matrix.

Update plans through reviewable changes; do not make the four repositories one tangled monorepo as a shortcut.

---

# 2. RESEARCH FINDINGS AND WHAT THEY MEAN FOR THIS BUILD

The sources below were checked on 2026-11-07. They are starting references, not immutable facts. Re-check versions, papers, APIs, licenses, and benchmark availability before a release.

## 2.1 GPU-accelerated SAT inprocessing — strongest directly relevant precedent

**ParaFROST** is the closest mature precedent for the hybrid SAT idea. The peer-reviewed paper *Certified SAT solving with GPU accelerated inprocessing* (Osama, Wijs, Biere; published 2023, issue 2024) describes GPU-parallel simplification/inprocessing, compact clause structures, data-parallel garbage collection, bounded variable elimination, functional dependency extraction, and parallel generation of clausal proofs. The paper reports significant gains on selected benchmark instances and successfully checked generated proofs. The public project states that its GPU implementation requires CUDA and its GPU pool backend; its CPU solver can be built separately.

Implications:

- The idea “CPU CDCL + GPU performs bulk-parallel simplification” is research-backed.
- It is **not** evidence that a CUDA implementation can be dropped into a Vulkan project without porting.
- Reproduce a small transformation and its proof path before writing a large custom inprocessing engine.
- HCSUDA should first build a clean CPU baseline and a GPU transformation backend; the exact CDCL search remains CPU-owned initially.
- A GPU BVE implementation must preserve equisatisfiability and provide a proof/certificate or be checked by a trusted proof checker before its result is accepted.

References:
- Paper: https://link.springer.com/article/10.1007/s10703-023-00432-z
- Source: https://github.com/muhos/ParaFROST

## 2.2 GPU continuous local search — useful as a hint engine, not a proof engine

**FastFourierSAT** (Cen, Zhang, Fong; AAAI 2025) develops a massively parallel GPU method for gradient-driven continuous local search. The paper uses FFT-inspired computation of elementary symmetric polynomials and reports a large gradient speedup against previous CPU prototypes. This makes a GPU numerical relaxation / phase-search subsystem a valid research track.

Implications:

- Reproduce the paper's actual mathematical objective and algorithm; do not replace it with an arbitrary gradient of a convenient clause product and call it FastFourierSAT.
- The GPU may produce candidate assignments, variable phase suggestions or restart hints.
- A candidate assignment must always be evaluated against the original discrete CNF.
- A candidate that fails verification is a failed heuristic attempt, not a solver result.
- Continuous loss equal to zero for relaxed variables in `[-1,1]` is not by itself an integer SAT witness unless the resulting Boolean assignment is constructed and verified.
- A heuristic never proves UNSAT. UNSAT requires an independently checked certificate or a complete exact solver result with a trusted proof artifact.

Reference:
- AAAI paper: https://ojs.aaai.org/index.php/AAAI/article/view/33211
- arXiv: https://arxiv.org/abs/2308.15020

## 2.3 LLM-guided solver evolution — use the experiment discipline

**SATLUTION: Autonomous Code Evolution Meets NP-Completeness** (2025 preprint) describes a full-repository agentic workflow for SAT solver evolution. It separates planning and coding, uses benchmark feedback, and places correctness checks around candidate solver variants. The paper reports results exceeding selected SAT Competition winners on specified historical benchmark sets. Treat those results as a paper claim to reproduce independently, not a guaranteed property of HCSUDA or a claim that an arbitrary agent can outperform SOTA.

Implications:

- Agent-generated code is a candidate patch, not a trusted patch.
- Every candidate must compile in isolation, pass correctness and certificate tests, then run against a held-out benchmark suite.
- Do not use the same benchmark instances for repeated optimization and for final generalization claims.
- Store candidate source hashes, model/version, prompt/context metadata where permitted, tool calls, test outputs, benchmark versions and random seeds.
- Promote only candidates that improve a predeclared metric without correctness, memory, security or robustness regressions.

Reference:
- https://arxiv.org/abs/2509.07367

## 2.4 SAT competitions and realistic benchmarking

The SAT Competition is the community's central public evaluation framework. The 2025 Main Track reports solved-instance counts and PAR-2-derived scoring; the 2026 site publishes benchmark and results material and documents benchmark provenance and sanitization. Its benchmark format includes DIMACS CNF. This project must follow the published benchmark rules and must handle unsanitized inputs too, including duplicate literals and tautological clauses.

Implications:

- Use SAT Competition 2025 and 2026 material when legally downloadable and license-compatible.
- Record the exact instance set, solver binary hash, host, resource limits, timeout, memory limit, thread count and command line.
- Report PAR-2 and solved counts; do not cherry-pick a few easy instances.
- Split benchmark families into development/tuning and held-out evaluation, not random copies of closely related instances.
- Include industrial, crafted, random, graph, parity/XOR, pigeonhole and Tseitin families; label them by source/family.
- Compare with CaDiCaL and Kissat where their current official builds and licenses permit.

References:
- SAT Competition 2026: https://satcompetition.github.io/2026/
- 2026 benchmarks: https://satcompetition.github.io/2026/benchmarks.html
- 2025 results: https://satcompetition.github.io/2025/results.html
- Kissat overview / project sources: https://fmv.jku.at/kissat/ and https://github.com/arminbiere/kissat

## 2.5 Vulkan, SPIR-V and the real meaning of “unified memory”

Vulkan does not promise that a device exposes a single memory pool or that host-visible memory is as fast as device-local memory. The driver exposes memory heaps and types, with flags such as `DEVICE_LOCAL`, `HOST_VISIBLE`, `HOST_COHERENT` and `HOST_CACHED`. The Vulkan memory specification explicitly notes that on discrete GPUs, host-visible + device-local BAR memory is generally intended for small uploads and may have lower peak write performance than system memory. Buffer Device Address is a supported Vulkan feature, but it does not turn unrelated host pointers, disk offsets or arbitrary virtual addresses into safe GPU pointers.

Implications:

- Query every physical device's memory heaps, memory types, queue families, API version and optional features at runtime.
- Do not infer memory topology from GPU vendor/model strings alone.
- `HOST_VISIBLE` is not synonymous with zero-copy, coherent, high bandwidth, or available in unlimited size.
- On an APU, CPU and GPU share physical system RAM, but they still have separate execution engines, cache domains, synchronization costs, bandwidth contention and driver memory budgets.
- Treat “shared physical RAM” and “no explicit PCIe copy” as different from “no data movement cost”.
- Use buffer-device-address only when all required Vulkan feature bits, buffer usage flags, allocation rules, alignment requirements and synchronization are satisfied.
- Use a tested allocator such as Vulkan Memory Allocator (VMA), with explicit allocation classes and budget reporting; do not invent an allocator before a measured need.

References:
- Vulkan memory model and heap/type descriptions: https://docs.vulkan.org/spec/latest/chapters/memory.html
- Buffer Device Address guide: https://docs.vulkan.org/guide/latest/buffer_device_address.html
- BDA alignment: https://docs.vulkan.org/guide/latest/buffer_device_address_alignment.html
- Vulkan Memory Allocator: https://github.com/GPUOpen-LibrariesAndSDKs/VulkanMemoryAllocator

## 2.6 Vulkan queues and synchronization

A device may expose one universal queue, several queues, or separate compute/transfer-capable queue families. A dedicated transfer queue is not guaranteed. Queue ownership transfers and memory barriers are correctness requirements, not tuning decorations. Timeline semaphores are useful for tracking asynchronous work, but do not magically remove synchronization or host/device coherence obligations.

Implications:

- Query queue family capabilities; build a one-queue safe path first.
- Use `vkQueueSubmit2` / Synchronization2 and timeline semaphores only when enabled and supported.
- Explicitly handle queue-family ownership transitions for exclusive resources.
- Benchmark whether multiple queues overlap on the actual device. Multiple queues can serialize under the driver or contend for the same compute/memory resources.
- Never spin-wait in a permanent GPU kernel as the default work dispatcher.

References:
- Queues guide: https://docs.vulkan.org/guide/latest/queues.html
- Concurrent execution and synchronization: https://docs.vulkan.org/tutorial/latest/Advanced_Vulkan_Compute/08_Asynchronous_Compute/02_concurrent_execution.html
- Timeline semaphores: https://docs.vulkan.org/tutorial/latest/Advanced_Vulkan_Compute/08_Asynchronous_Compute/03_timeline_semaphores.html

## 2.7 Cooperative matrix/vector extensions are capability-gated

`VK_KHR_cooperative_matrix` is a ratified device extension. Its availability and supported component types, dimensions and scopes are still implementation-specific and must be queried. `VK_NV_cooperative_vector` is an NVIDIA-specific extension and is listed as **not ratified** in the Vulkan reference. Do not design a cross-vendor baseline around it.

Implications:

- Baseline GEMM must work with ordinary Vulkan compute shaders and/or CPU fallback.
- Cooperative matrix becomes an optional acceleration path after querying the relevant extension, features and supported properties.
- NVIDIA cooperative vector stays a separate optional adapter; never assume AMD support.
- Compile shader variants for declared capabilities and select them only after a runtime probe.

References:
- `VK_KHR_cooperative_matrix`: https://docs.vulkan.org/refpages/latest/refpages/source/VK_KHR_cooperative_matrix.html
- `VK_NV_cooperative_vector`: https://docs.vulkan.org/refpages/latest/refpages/source/VK_NV_cooperative_vector.html

## 2.8 Windows GPU watchdog / TDR

Windows WDDM uses Timeout Detection and Recovery. Microsoft's driver documentation describes a default timeout period of two seconds for a task that the GPU cannot complete or preempt. A permanent persistent-kernel spin loop can make the desktop unstable or trigger recovery; it is not a safe default for a workstation OS.

Implications:

- Use bounded dispatches and chunk long computations.
- Add cancellation, progress checkpoints and watchdog timeouts.
- Never suggest changing global TDR registry settings as a performance requirement.
- Any experiment with long-running kernels must be opt-in, isolated, and tested separately from the desktop UI path.

Reference:
- Microsoft WDDM TDR: https://learn.microsoft.com/en-us/windows-hardware/drivers/display/timeout-detection-and-recovery

## 2.9 AMD Radeon 680M / RDNA2 target

The user's known development target is a Ryzen 7 7735HS mini PC with Radeon 680M (RDNA2), Windows 11, Vulkan and CPU fallback; there is no CUDA. Linux Mesa RADV documents Vulkan 1.4 support for RDNA-class devices, but this does not imply that every extension, cooperative matrix mode or performance path exists on the specific driver/device. The exact device report is the authority.

Required policy:

- Tier 0 CPU: mandatory and testable without a GPU.
- Tier 1 Vulkan ordinary compute: target on Radeon 680M, after local feature/driver report.
- Tier 2 cooperative matrix, subgroup arithmetic or advanced memory: optional per-feature capability probe.
- No CUDA requirement anywhere in the baseline.
- Keep Windows and Linux capability records separate; do not assume a driver capability on one OS applies to the other.

References:
- Mesa RADV supported hardware/API versions: https://docs.mesa3d.org/drivers/radv.html
- AMD Radeon Vulkan driver support notes: https://www.amd.com/en/resources/support-articles/release-notes/RN-RAD-WIN-VULKAN.html

## 2.10 Storage, HDD streaming and compression

Lossless compression can improve stored-byte throughput when the compression ratio and decompression speed beat the storage bottleneck. LZ4 is deliberately fast, but compression ratio is data-dependent and can be close to 1.0 for already-quantized or high-entropy data. Quantization is lossy and adds a separate error budget. The Linux `posix_fadvise` interface offers access-pattern hints such as sequential and random, but those are hints and not binding scheduling commands.

Implications:

- Measure disk read, decompression, quantization, host-to-device copy and kernel time separately.
- Do not multiply physical drive bandwidth by a claimed compression ratio and present it as measured disk throughput.
- Test sequential and random access; do not force 64 MB / 128 MB chunks before measuring.
- Test multiple block sizes, queue depths, compression codecs and prefetch distances.
- Use platform-specific file I/O: `io_uring`/async I/O where supported on Linux; overlapped I/O/IOCP on Windows. Retain a simple portable synchronous fallback.
- HDD sequential-read optimizations do not rescue random access. An SSD/NVMe and an HDD need different profiles.

References:
- `posix_fadvise`: https://www.man7.org/linux/man-pages/man2/posix_fadvise.2.html
- LZ4 source and benchmark notes: https://github.com/lz4/lz4

## 2.11 Quantization and KV-cache research — do not misapply papers

The PDF mentions SKVQ and AQPIM beside each other. They are not the same research contribution:

- SKVQ is a 2024 KV-cache quantization line of work; it should be evaluated as a KV-cache method, not assumed to be a general CPU↔GPU transfer protocol.
- arXiv `2604.08426` is *KV Cache Offloading for Context-Intensive Tasks* (2026), not the original SKVQ paper. Its reported results show important accuracy degradation for some context-intensive tasks under modern KV offloading methods. This is a reason to include retrieval-heavy evaluation, not to promise a universal speedup.
- AQPIM (`2604.18137`) is *In-Memory Activation Quantization* for Processing-in-Memory architectures. Its gains depend on a PIM hardware/software co-design. It is not a ready-made algorithm for a consumer Radeon iGPU or a normal PCIe GPU.
- AWQ is a known low-bit weight-only quantization approach for LLM inference, but it is not the same thing as a universal cache or transfer protocol.

Implications:

- Keep model weight quantization, activation quantization, KV-cache quantization and storage/transfer compression as separate interfaces and separate quality reports.
- Integrate GGUF/llama.cpp through HCS Foundry; do not reinterpret or rewrite GGUF as QSTP without a tested and reversible converter.
- Evaluate long-context retrieval, not just perplexity or short chat prompts.
- QSTP is an HCS research proposal, not an existing published standard or known SOTA protocol. Its novelty and value must be demonstrated against established formats and baselines.

Related-work map:

| Work | Main target | What HCS can learn | Important limit for this project |
|---|---|---|---|
| SKVQ (COLM 2024) | Sliding-window KV-cache quantization, channel rearrangement, clipped dynamic quantization | Keep a high-precision recent window; study channel/group organisation and outliers | Model/runtime-specific KV cache algorithm, not generic HDD-to-GPU data transfer |
| KIVI (ICML 2024) | Asymmetric 2-bit KV cache; keys per-channel, values per-token | Quantization axes matter; one quantization layout is not optimal for every tensor role | Inference KV-cache method, not a universal tensor file format |
| KVQuant (NeurIPS 2024) | Non-uniform KV quantization, pre-RoPE keys, outlier handling | Sensitivity-aware group/axis design and outlier handling | Reported CUDA/A100 results do not establish Vulkan/Radeon support |
| QServe (MLSys 2025) | W4A8KV4 with hardware/system co-design | Dequantization overhead can erase storage/transfer savings; measure the entire path | Its throughput results are tied to supported accelerator kernels/runtime; do not assume same on iGPU |
| FServe (EMNLP Findings 2026) | FP8-native W4A8KV4 and attention-kernel co-design | Weight/KV formats and attention scheduler must be co-designed | Published accelerator-specific optimizations are not a ready-made generic Vulkan codec |
| TurboQuant / QJL / PolarQuant (Google Research, Mar 2026) | Vector/KV-cache and vector-search compression | Consider rotation, quantization, reconstruction error and vector retrieval evaluation | Integration and quality must be tested in the exact runtime; do not call it enabled just because a paper exists |
| FlexGen (ICML 2023) | Throughput-oriented LLM inference with GPU/CPU/disk offloading | Memory-tier scheduling can trade latency for capacity/throughput; use an optimization model | Its target includes batching/latency-insensitive work; disk offload can be very slow for interactive single-token decode |
| AQPIM (2026) | Product-quantized activations on Processing-in-Memory hardware | Memory-side compute and local data access are interesting co-design concepts | PIM-specific hardware results do not map directly to a consumer Radeon GPU or normal PCIe copy path |
| Context-intensive KV offloading (2026) | Accuracy on retrieval-heavy, context-intensive tasks | Include information-retrieval-heavy evals; compression/offload can lose salient details | A method that passes perplexity/needle tests may still fail structured extraction and long-context coverage |

A practical HCS evaluation matrix must keep four separate axes:

1. **Storage:** bytes on disk, compression codec, sequential/random access, checksums.
2. **Transfer:** bytes across host/device domains, queue wait, upload latency, overlap.
3. **Numeric quality:** quantization/reconstruction error and downstream model or matrix metrics.
4. **Task quality:** answer retrieval, code execution, tool-call correctness, SAT correctness or solver benchmark result.

A method is not a win merely because its file is smaller. It must improve the declared use case without unacceptable task-quality loss.

References:
- SKVQ (COLM 2024): https://openreview.net/forum?id=nI6JyFSnyV
- SKVQ arXiv: https://arxiv.org/abs/2405.06219
- KIVI (ICML 2024): https://proceedings.mlr.press/v235/liu24bz.html
- KVQuant: https://arxiv.org/abs/2401.18079
- QServe (MLSys 2025): https://proceedings.mlsys.org/paper_files/paper/2025/hash/fbe2b2f74a2ece8070d8fb073717bda6-Abstract-Conference.html
- FServe (EMNLP Findings 2026): https://aclanthology.org/2026.findings-emnlp.1556/
- TurboQuant (Google Research, 2026): https://research.google/blog/turboquant-redefining-ai-efficiency-with-extreme-compression/
- FlexGen (ICML 2023): https://proceedings.mlr.press/v202/sheng23a.html
- AQPIM: https://arxiv.org/abs/2604.18137
- Context-intensive KV offloading: https://arxiv.org/abs/2604.08426
- AWQ: https://proceedings.mlsys.org/paper_files/paper/2024/hash/42a452cbafa9dd64e9ba4aa95cc1ef21-Abstract-Conference.html

## 2.12 Lean 4 as a proof checker boundary

Lean 4 is an interactive theorem prover whose small kernel checks proof terms; tactics and automation are not trusted merely because they generated a proof. The hcswaver Proof Desk should therefore submit completed terms to the Lean kernel and display the compiler/kernel outcome. Lean formalization proves only the formal statement under the imported axioms and definitions; it does not automatically prove that the chosen statement matches the real-world algorithm or implementation.

Reference:
- Lean reference: https://lean-lang.org/doc/reference/latest/
- Learn Lean: https://lean-lang.org/learn/

## 2.13 Update 2026-11-07 (HSCL1 agent): open questions checked, and what was measured on the development machine

Status words: `CHECKED` = read in a source on this date; `MEASURED` = produced by a command on the development machine (Ryzen 7 7735HS, Radeon 680M, Windows 11) with the evidence named; `OPEN` = not resolved.

**Licences and code availability (changes to section 11 and Phase 5)**
- `CHECKED` ParaFROST is listed as **GPL-3.0**, implemented in **CUDA C++** (CUDA toolkit and an NVIDIA driver are required for the GPU solver); no Vulkan or non-CUDA port was found. Consequence: it may be read and used as an algorithmic reference, but copying code into HCSUDA ties HCSUDA to GPL-3.0 (compatible with HSCL1's GPL-3.0-or-later, **not** with Apache-2.0 CQ-HECS or MIT Foundry code paths). The rule stays: no ParaFROST source copied before the owner decides the HCSUDA licence (the licence of `hcsuda` is itself `OPEN`).
- `CHECKED` FastFourierSAT (AAAI 2025): the paper is public; **no code repository or licence was found** (the code-availability field on aggregator sites is empty). Consequence: HCSUDA must reimplement from the paper (as section 2.2 already requires) and can not rely on a reference implementation for differential tests; the reproduction needs its own small test corpus and a CPU reference of the same objective.
- `CHECKED` A 2025 preprint, *TurboSAT: Gradient-Guided Boolean Satisfiability Accelerated on GPU-CPU Hybrid System* (arXiv 2511.07737), is a second GPU gradient-guided SAT line. Read on 2026-11-07 (see the papers list below): SAT only, no code linked; it is now source 46.

**Certificates (changes to Phase 5 step 4)**
- `CHECKED` SAT Competition 2026, Main track: certificates are required for **both SAT and UNSAT** results; the organisers offer a choice of proof checkers: **DPR** (`dpr-trim`), **GRAT** (`gratgen`) and **VeriPB**; the verified `cake_lpr` pipeline for LRAT/LPR is documented. `drat-trim` is not in the 2026 list. The CaDiCaL 3.0 paper states that DRUP/DRAT was the standard until 2023 and that CaDiCaL supports LRAT (cheaper to check). The Experimental track accepts techniques without certificate support but a prize requires beating a top-3 Main-track solver; in 2025 an instance counted as unsolved when the checker timed out.
- `CHECKED` (page text downloaded and read in full, 2026-11-07): the 2026 output rules say the **proof format is DRAT** (text or binary DRAT, written to `proof.out`; backward compatible with RUP/DRUP), and that `proof.out` is then fed to `dpr-trim`, `gratgen` or `veripb` depending on the checker the participant selects; the verified `cake_lpr` pipeline (LRAT/LPR), GRAT and VeriPB documents are linked. SAT answers: `s SATISFIABLE` plus `v` lines of at most 4096 characters, the last terminated by `0`; **partial satisfying assignments are allowed** as long as at least one literal of every clause appears. So HCSUDA's own witness checker must accept partial models and check every clause against the original CNF.
- Decision proposed for the HCSUDA ADR (not decided by the owner): the solver-facing format is **DRAT** (what the competition checkers consume), checked by a separate, maintained checker (`dpr-trim` first because it is the closest to the competition pipeline; `cake_lpr` for a verified LRAT path where the solver can emit LRAT, e.g. CaDiCaL). A GPU transformation that cannot emit a DRAT-checkable step stays `EXPERIMENTAL` (the competition's own Experimental-track rule). `OPEN`: DPR/GRAT/VeriPB internals and exact command lines are in the linked documents and were not read.

**Papers read in full text on 2026-11-07 (PDF text extracted, searched for the facts below; not every section studied)**
- *TurboSAT* (arXiv 2511.07737, 7 pages, CC BY 4.0): SAT as a binarized matrix-multiplication layer with a differentiable objective on the GPU, promising partial assignments finished by CDCL on many CPU threads. Prototype on an NVIDIA DGX GB200 node (limited to 2 of 4 B200 GPUs and 141 ARM threads), PySAT + PyTorch 2.2 + CaDiCaL 1.9.5; one thread runs plain CaDiCaL from scratch, so it is never worse than the baseline by construction. Reported: 5.03x to 258.08x total speedup on *selected* satisfiable SAT-Competition-2024 instances (CDCL part alone 5.94x to 1367.73x, instances up to 74 776 variables / 393 322 clauses). **Limits stated: only satisfiable instances; "we can declare UNSAT only if all possible assignments have been exhausted ... leave UNSAT problems to future work".** No code or repository is linked. Consequence: this is a hint-engine result on datacenter hardware, not evidence for a 680M iGPU, and it gives no UNSAT path.
- *FastFourierSAT* (arXiv 2308.15020, AAAI 2025): gradient of one k-literal constraint in O(k^2) (FourierSAT: O(k^3)), mapped to GPU thread/data parallelism. No repository or licence is mentioned in the paper text.
- *SATLUTION* (arXiv 2509.07367): agents built on the Cursor environment with **two Claude models** (one planning, one coding), 70 evolution iterations on the SAT Competition 2024 benchmark, distributed CPU-cluster runtime feedback, a static rulebase that keeps soundness checks and **mandatory DRAT proof generation**; variants that failed functional or proof validation were discarded (4 in one reported subset). Results reported with a 5000 s timeout and PAR-2. Consequence for HCSUDA section 9: this recipe needs strong hosted models and a CPU cluster; it is not reproducible with the local 4B worker.
- *QLoRA* (arXiv 2305.14314, 26 pages): NF4 data type, double quantization (0.37 bits per parameter saved; with block size 64 the quantization constants cost 0.5 bits per parameter on average), paged optimizers; the frozen 4-bit weights are **dequantized to BFloat16 on every use and multiplied in 16 bit**; LoRA on **all** transformer linear layers is needed to match 16-bit finetuning; with a LoRA budget of 0.2 % of the weights the *activation/input gradients* (567 MB in their 7B example) dwarf the adapter parameters (26 MB), so gradient checkpointing is the key memory lever. Consequences for the QSTP codec (section 3.1): per-block metadata is a real cost: **FP32 scale + FP32 offset per 64 weights is 1.0 extra bit per weight (5 bits total); per 128 weights 0.5 bit; FP16 metadata halves that** - the Q4 reference codec must report effective bits per weight, not "4".

**Vulkan on the development machine (`MEASURED`, `vulkaninfo`, 2026-11-07)**
- Instance 1.4.357 (SDK `C:\VulkanSDK\1.4.357.0`), device "AMD Radeon(TM) Graphics" (the 680M), API **1.4.315**, driver **AMD proprietary 26.6.1**; subgroup size 64 (min 32, max 64, subgroup size control true).
- Features present: `synchronization2`, `timeline_semaphore`, `buffer_device_address`, `maintenance5`, `memory_budget`, `shaderFloat16`, 16-bit storage access. `VK_KHR_cooperative_matrix` is **listed with `cooperativeMatrix = true`**. `OPEN`: which component types, sizes and scopes the driver reports (query `vkGetPhysicalDeviceCooperativeMatrixPropertiesKHR`); the extension name alone proves nothing (section 2.7). Public llama.cpp history shows its cooperative-matrix path was disabled on the AMD proprietary Windows driver in late 2024 (PR 10597); whether that still holds is `OPEN`, so the Tier-2 path stays a separately probed and benchmarked option.
- Memory heaps on a 24 GB system: heap 0 **9.10 GiB** device-local, heap 1 **4.55 GiB** host-only, heap 2 **256 MiB** device-local and host-visible. This confirms section 3.4: the 9.1 GiB device-local figure is a driver budget over shared system RAM, not extra memory, and must not be added to RAM.

**Quantized KV cache costs prefill on this GPU (`MEASURED`, `llama-bench`, Vulkan, flash attention on, Qwen3-4B Q4_K_M, build 12128)**
| KV type K/V | prefill pp512 (t/s) | generation tg64 (t/s) |
|---|---|---|
| f16 / f16 | 280 | 26.8 |
| q8_0 / q8_0 | 252 | 25.6 |
| q4_0 / q4_0 | 180 | 24.1 |
This is a local instance of the point made in section 2.11 (QServe row): **dequantization overhead can erase the saving** — halving or quartering KV bytes did not speed up generation at all here and cost 10 % (q8_0) to 36 % (q4_0) of prefill speed; the saving is memory, not time. Raw tables: `docs/superpowers/plans/2026-11-07-local-agents-v2.md` of HSCL1. One model, one GPU, one short context: a data point, not a general law.

**Local model baseline for the agent roles (`MEASURED`)**
- The HSCL1 local worker (`tools/local_worker`) now serves **Qwen3-4B-Instruct-2507 Q4_K_M** on :8080 (replaced Bonsai-9B on the owner's instruction; Apache-2.0 per the Hub tag, SHA-256 recorded in the HSCL1 plan). On HSCL1's 10-task benchmark it solves 9/10 at about 9 s per task (Bonsai-9B: 10/10 at 10.6 s). Failure modes seen: coupled behaviours (argument list handling) and string normalisation. Consequence for section 9: a small local model is suitable for **bounded, test-verified single-file edits only**; SAT-solver evolution (SATLUTION-style) needs a much stronger model or stays a human-in-the-loop task. Do not plan HCSUDA agent loops that depend on a 4B model solving multi-behaviour tasks.
- The Python 3.14 install on the machine has CPU-only PyTorch 2.12.1 + PEFT 0.19.1 + Transformers 5.12.1 (no CUDA, no ROCm on Windows). LoRA training on the fp16 Qwen3-4B parent is therefore a CPU job (feasibility and gates: HSCL1 plan); nothing here should assume GPU training.

**Training backend, GPU idle, and host-device traffic (`CHECKED` / `MEASURED` 2026-11-07, HSCL1 agent)**
- `MEASURED`: CPU-only LoRA training of Qwen3-4B with a Q4 frozen base through the local HCSUDA slice (decode to fp32 at 3.8-4.2 G weights/s, then BLAS): 57.6 s per 512-token step, 6.1 GB RSS, effective about 140 GFLOP/s. A hand-written fused Q4 GEMM reached only 40-60 GFLOP/s against 260-360 for dense fp32 BLAS at batch 512, so the QLoRA-style "dequantize, then BLAS" path is the CPU baseline. The iGPU does about 2.2 TFLOP/s effective in `llama-bench` prefill of the same model, so the GPU is the main untapped resource.
- `CHECKED`: official ROCm PyTorch wheels for Windows do not list the Radeon 680M (RDNA2 iGPU); PyTorch has no Vulkan training backend. A Vulkan LoRA training stack **does exist**: `tetherto/qvac-fabric-llm.cpp` (llama.cpp fork, MIT, active; additions Apache 2.0 per the authors; Qwen3 dense verified, quantized `OUT_PROD`, cross-entropy backward, Q4/Q8/FP16/FP32 training, `llama-export-lora`). Decision for the HCSUDA roadmap: **do not rewrite a Vulkan training stack first; build, measure and gate the existing one, then reuse its ops** and put HCSUDA effort into the capability probe, the placement table, certificates and the data/benchmark gates. Building third-party code needs the owner's explicit approval (it was blocked once by the permission system).
- `CHECKED` (VMA documentation): on unified-memory devices a memory type that is both `HOST_VISIBLE` and `DEVICE_LOCAL` is the preferred choice and staging is only the fallback; on the 680M only the 256 MiB heap has both flags, the 9.1 GiB heap is device-local only. Consequence for sections 3.3/Phase 4: resident weights go to the large heap once; activation exchange uses a small host-visible device-local ring; the "back and forth" cost is measured per op, not assumed.
- `CHECKED`: lossless weight compression for GPU inference (DFloat11: Huffman-coded bf16 exponents, about 30 % smaller, bit-identical; ZipNN: storage/download; ZipServ: 3-bit exponents) targets bf16 weights that would otherwise cross PCIe. For Q4 weights on a UMA APU there is neither a PCIe hop nor much redundancy, so QSTP lossless codecs stay `DEFERRED` until the nibble-stream entropy of real checkpoints is measured and a decode kernel beats the memory-bandwidth saving.
- The "router" is the capability-aware placement table: per device and per op class (big matmul, decode, attention, small ops) which engine wins, from benchmarks stored with the machine report; no hard-coded vendor rules.

**GPU training measurement and research on co-execution, MTP, compression (HSCL1 agent, 2026-11-07, later)**
- `MEASURED`: the QVAC Fabric Vulkan LoRA trainer built from source on the Radeon 680M (`uma: 1`, no cooperative-matrix path) ran Qwen3-4B Q4_K_M at about 2 min per 512-token step with **no GPU engine above 1 % utilisation**, 10.4 GB working set, 9.3 GB shared / about 0 dedicated GPU memory and 1.8 GB free RAM, about 2x slower than the CPU+Q4 path (57.6 s). A backend existing and being verified for Qwen3 upstream is not evidence that it runs on a given iGPU. Consequence: HCSUDA's capability probe must record, per op class, **where the op actually ran** (engine counters, scheduler splits) and treat "GPU backend present" as `UNVERIFIED` until a repeat run shows GPU utilisation and a faster step.
- `CHECKED`: FusionML (arXiv 2607.22785, Apple Silicon): CPU+GPU row-split matmul 1.18x-1.38x for prefill, no gain for decode, 0.86x-0.97x for precision-matched training; the lazy-graph scheduler serialised CPU and GPU work unless an eager materialisation boundary was added. Treat intra-operator CPU+GPU splitting as a prefill/inference option with an expected ceiling of tens of percent, and as unproven for training.
- `CHECKED`: MTP (FastMTP 2509.18362, Tencent self-distillation 2603.23911, AdaMTP 2608.00434, Apple gated LoRA 2507.11851) speeds up **inference** and can be trained with LoRA on a frozen decoder; it is not a training-step accelerator. LoftQ (2402.05147), ApiQ and LowRA (2502.08141) improve the quality of 2-bit and sub-2-bit LoRA bases and cut weight memory; none reports a training-throughput gain on consumer hardware.
- `OPEN`: no documented Windows AMD driver switch for iGPU compute was found; ggml Vulkan environment variables and BIOS UMA frame-buffer size are the only levers identified, both unmeasured.

**Development machine, read from the hardware (HSCL1 agent, 2026-11-07; supersedes any vendor-sheet assumption above)**
- CPU Ryzen 7 7735HS (Zen 3+, 8C/16T, L2 4 MB, L3 16 MB, AVX2/FMA3, **no AVX-512/VNNI**, official 35-54 W). Memory **4 x 6 GB LPDDR5, configured 5500 MT/s** (rated 6400) on a 2-channel/128-bit controller: theoretical **88 GB/s shared by CPU and iGPU** (not measured yet); 19.8 of 24 GiB visible to Windows, the rest is the graphics carve-out. iGPU Radeon 680M, 12 CUs, 2200 MHz, wave32, int-dot yes, bf16 no, no cooperative-matrix path used; formula peak 3.38 TFLOP/s fp32. Generic OEM mini PC; BIOS string names a `28W` profile (unverified).
- Consequences for HCSUDA contracts: (1) capability and budget code must treat CPU and iGPU as **one memory and one power budget**; (2) the capability record must store *configured* memory speed, not the rated one, plus measured sustained bandwidth and sustained clocks under load; (3) for a 4B Q4 base the training step is compute-bound, so bandwidth tricks and lossless codecs do not help there; they matter for models that no longer fit RAM (tier planner); (4) the ISA tier table needs `avx2_fma` as the top x86 tier for this machine and must not assume VNNI/AVX-512; (5) any use of power-limit tools or BIOS changes is a user decision recorded in the run provenance, never automatic.
- `CHECKED` (source reading): the QVAC/ggml Vulkan backend runs the quantized output product (needed by the LoRA backward pass) only for F32, F16, Q4_0, Q8_0 and TQ2_0; a Q4_K model silently executes that op on the CPU. HCSUDA's placement table must therefore be keyed by **(op, weight format)**, not by op alone.

**Process rules learned (apply to every repository)**
- Never chain a commit after `test | tail`: the pipe hides the exit code. Redirect the output to a file and test `$?`.
- A test suite that grows slow gets a `slow` marker tier: the pre-push gate runs the fast tier plus changed tests, the full suite runs before merge and in CI (HSCL1: 595 s to 178 s).

---

# 3. MATHEMATICAL CONTRACTS — WHAT THE ENGINE MUST ACTUALLY COMPUTE

Every equation below must exist in code/tests and be documented with its domain, units, assumptions and numerical behaviour. Do not present a heuristic model as a theorem.

## 3.1 Blockwise offset quantization (QSTP Q4 baseline)

For a finite block `x[0..G-1]` and `k` bits, the first QSTP reference codec uses a stored block offset rather than forcing the represented range to include real zero:

```text
q_min = 0
q_max = 2^k - 1
offset = min(x)
scale = (max(x) - offset) / (q_max - q_min)
q_i = clamp(round((x_i - offset) / scale), q_min, q_max)
xhat_i = offset + scale * q_i
```

For a constant block, store `scale = 1`, `offset = constant`, and all quant symbols as zero. This avoids division by zero and reconstructs the constant. For the all-zero block the same rule gives offset 0. Store scale and offset (initially FP32 in the reference path; FP16 metadata is a separate measured optimization), bit width, layout, group size, codec version, original dtype, shape, block offsets, checksums and quantization method. Specify rounding ties and saturation explicitly. Use canonical endianness and stable serialization.

This is a block-offset affine representation. A separate zero-preserving affine codec may be implemented where the arithmetic kernel needs exact representation of real zero. In that codec, use `r_min = min(min(x), 0)`, `r_max = max(max(x), 0)`, `scale = (r_max-r_min)/(q_max-q_min)`, `zero = round(-r_min/scale)`, `q = round(x/scale)+zero`, `xhat=(q-zero)*scale`. Keep the zero point as a signed metadata value if the selected design allows it; do not silently clamp it to `[0,15]` while keeping an original range that does not include zero. The kernel and format must agree on the exact rule.

For ideal round-to-nearest offset quantization without clipping and ignoring floating-point metadata error, scalar quantization error is bounded by approximately `scale / 2`. Test actual floating-point results against the declared tolerance; do not claim exact reconstruction.

Example reference implementation in Python (for tests, not necessarily production):

```python
from __future__ import annotations
import numpy as np

def offset_q4_reference(x: np.ndarray) -> tuple[np.ndarray, float, float]:
    a = np.asarray(x, dtype=np.float32)
    if a.size == 0 or not np.isfinite(a).all():
        raise ValueError("expected a non-empty finite block")
    lo, hi = float(a.min()), float(a.max())
    if hi == lo:
        return np.zeros_like(a, dtype=np.uint8), 1.0, lo
    scale = (hi - lo) / 15.0
    q = np.clip(np.rint((a - lo) / scale), 0, 15).astype(np.uint8)
    return q, scale, lo

def offset_q4_decode(q: np.ndarray, scale: float, offset: float) -> np.ndarray:
    q = np.asarray(q, dtype=np.uint8)
    if not np.isfinite(scale) or scale <= 0 or not np.isfinite(offset):
        raise ValueError("invalid quantization metadata")
    return np.float32(offset) + q.astype(np.float32) * np.float32(scale)
```

Tests must compare the C++ encoder/decoder, Python reference and GPU decoder on the same fixed blocks and serialized byte stream, including large positive-offset and large negative-offset blocks.

## 3.2 Ternary packing — compact representation is not automatically good quantization

Ternary values have three symbols `{-1, 0, +1}`. Five ternary symbols can be encoded in one byte because `3^5 = 243 <= 256`. That is 8/5 = 1.6 stored bits per symbol for the packed symbols, before scales, zero points, block metadata, padding and checksums. `log2(3) ≈ 1.58496` is the information-theoretic lower bound, not the exact storage cost of a byte-packed group of five.

Use an explicit map such as `-1 -> 0`, `0 -> 1`, `+1 -> 2`, then encode five symbols as base-3 digits. Test all 243 possible packed values and reject byte values 243–255 as invalid/reserved. The PDF's proposed threshold `0.7 * mean(abs(block))` is an experiment parameter, not a mathematically guaranteed optimum. Evaluate alternative thresholds/scales on held-out activations/weights and publish error distributions.

Do not use a bit reinterpretation trick such as OR-ing a Q4 integer into a hard-coded FP16 bit pattern unless exhaustive bit-level tests prove every input and compiler path. The first correct implementation uses ordinary integer decode and floating-point conversion. Optimize only after profiling.

## 3.3 Out-of-core compute: correct pipeline model

For one chunk, measure:

- `t_disk`: read compressed bytes from disk;
- `t_decode`: decompress/dequantize on CPU or GPU;
- `t_upload`: stage/copy data to device-visible storage;
- `t_kernel`: execute the compute kernel;
- `t_sync`: synchronization and queue/driver overhead.

A serial execution time is approximately:

```text
T_serial = sum_i(t_disk_i + t_decode_i + t_upload_i + t_kernel_i + t_sync_i)
```

With a correctly overlapped multi-buffer pipeline and independent chunks, steady-state per-chunk time may approach:

```text
T_chunk_steady >= max(t_disk, t_decode, t_upload, t_kernel)
```

Total wall time still includes pipeline startup, pipeline drain, queue overhead, dependencies, cache misses and contention. This model is an explanatory lower bound, not a guarantee that all stages overlap.

Report:

```text
stored_bytes_per_second = bytes_read_from_disk / wall_time
logical_bytes_per_second = uncompressed_logical_bytes / wall_time
compute_throughput = completed_operations / wall_time
compression_ratio = uncompressed_bytes / stored_bytes
```

Never label `logical_bytes_per_second` as physical HDD bandwidth. If a 1.0 GB tensor is represented by 250 MB of compressed data, logical throughput can appear to be 4x stored throughput while the disk still reads only 250 MB.

A roofline estimate is:

```text
arithmetic_intensity = FLOPs / bytes_moved
attainable_FLOPs_per_second <= min(peak_compute_FLOPs_per_second,
                                    memory_bandwidth_bytes_per_second * arithmetic_intensity)
```

Use measured sustainable bandwidth and real data movement, not vendor peak values as expected results.

## 3.4 Memory budget contract

For a discrete GPU, keep separate budgets for system RAM, staging RAM, GPU-local memory and storage cache. For an APU, system RAM is shared physical capacity; do not add the GPU's reported shared-memory aperture to RAM as if it were a second pool.

```text
available_budget = measured_available_memory - safety_reserve
resident_set = OS_reserve + application_runtime + host_cache + device_resident
              + staging_buffers + model/runtime_overhead
require resident_set <= measured_safe_budget
```

The resource governor must re-measure under load. Never reserve all RAM/UMA for the solver. Keep the desktop and OS responsive.

## 3.5 Sparse SAT incidence representation

For a CNF with `C` clauses and `V` variables, an incidence representation may use a sparse matrix `S ∈ {-1,0,+1}^{C×V}` where the sign records the literal polarity. Do not assume a dense `C×V` matrix fits memory. Use CSR/CSC or a compact literal-indexed representation, and track each clause's actual length.

A relaxed clause-violation surrogate for a clause `c` with literals `l` can be written:

```text
p_false(l, u) = (1 - sign(l) * u[var(l)]) / 2
L_c(u) = product_{l in c} p_false(l, u)
L(u) = sum_c weight[c] * L_c(u)
```

For Boolean assignments `u_i ∈ {-1,+1}`, `L(u)=0` iff every non-empty clause is satisfied when all positive/negative signs are mapped consistently. For relaxed `u_i ∈ [-1,+1]`, a low loss is only a search signal. Discretize candidate assignments and verify the original CNF exactly.

The derivative involves clause products and accumulation to variables; it is not automatically one sparse GEMM. Profile an explicit gather-product/reduction or incidence-aware kernel and handle empty clauses, unit clauses, repeated literals, tautologies, zero denominators in stabilized logarithmic variants, and overflow/underflow.

## 3.6 Bounded Variable Elimination (BVE)

Let `C_x+` be clauses containing positive literal `x`, and `C_x-` clauses containing `¬x`. Candidate resolvents are:

```text
R_x = { (C \ {x}) ∪ (D \ {¬x}) : C ∈ C_x+, D ∈ C_x-,
        and the resulting clause is not tautological }
```

An elimination policy can bound the number or weighted literal cost of new resolvents relative to removed clauses. The exact policy must match a reference implementation and account for tautology removal, duplicate clauses, subsumption and memory budgets. Do not use an unqualified scalar formula as proof of correctness. Parallel elimination requires a proven independent set/conflict policy so two transformations do not race on the same clauses or variables.

Every inprocessing transformation must be covered by the chosen clausal proof format/checker or independently replayed by a trusted checker.

---

# 4. TARGET ARCHITECTURE AND REPOSITORY OWNERSHIP

## 4.1 HCSUDA standalone repository

Recommended layout (adapt after inspecting repository conventions; do not make empty folders just to match the diagram):

```text
hcsuda/
  AGENTS.md
  README.md
  LICENSE
  NOTICE
  CMakeLists.txt
  CMakePresets.json
  CMakeUserPresets.json.example
  rust-toolchain.toml                 # only if Rust components are selected
  pyproject.toml                      # optional Python bindings
  include/hcsuda/
    core.hpp
    result.hpp
    device.hpp
    capabilities.hpp
    memory_budget.hpp
    tensor.hpp
    qstp.hpp
    storage.hpp
    pipeline.hpp
    sat/solver_adapter.hpp
    sat/proof.hpp
    api.h
  src/
    core/
    cpu/
    vulkan/
    memory/
    qstp/
    sat/
    io/
  shaders/
    gemm_q4.comp
    sat_relax.comp
    sat_inprocess.comp
  python/                             # optional nanobind layer
  cli/
    hcsuda/
  schemas/
    hcsuda.result.v1.schema.json
    hcsuda.device.v1.schema.json
    hcsuda.run.v1.schema.json
  tests/
    unit/
    property/
    differential/
    vulkan/
    sat/
    storage/
    fault_injection/
  benchmarks/
    compute/
    qstp/
    storage/
    sat/
    manifests/
  research/
    literature/
    hypotheses/
    experiments/
    evidence/
    blockers/
  docs/
    ARCHITECTURE.md
    CAPABILITY_MATRIX.md
    API.md
    QSTP_FORMAT.md
    MEMORY_MODEL.md
    SAT_HYBRID.md
    BENCHMARKS.md
    LIMITATIONS.md
    SECURITY.md
    LICENSES.md
    ADR/
  .github/workflows/
```

Suggested implementation stack:

- C++20 core library with CMake + Ninja; keep C ABI stable at the external boundary.
- Vulkan backend optional at build-time and runtime; build CPU-only even without Vulkan SDK.
- Vulkan Memory Allocator (VMA) for allocation pools if compatible with the pinned Vulkan SDK.
- Volk or another maintained loader strategy only if current build conventions justify it.
- `glslangValidator` or a pinned shader compiler for GLSL->SPIR-V, plus `spirv-val` and `spirv-dis` for build verification.
- CTest + Catch2/GoogleTest (choose one based on actual repository dependencies); Python reference tests with pytest and NumPy only in optional dev/test environment.
- Nanobind/scikit-build-core Python binding is optional, not a prerequisite for the C++ library or HSCL1 packages.
- Compression adapters for LZ4 and Zstandard behind a stable codec interface; do not require both if the first benchmark proves only one is needed.

## 4.2 hcswaver Studio repository

hcswaver owns user experience and experiment orchestration, not low-level compute algorithms.

Suggested layout:

```text
hcswaver/
  AGENTS.md
  README.md
  LICENSE
  NOTICE
  package.json
  src-tauri/ or native-host/              # if Tauri is selected after audit
  web/ or studio-ui/
    src/
      app/
      workspaces/
      components/
      graph/
      telemetry/
      api/
      i18n/
      accessibility/
  contracts/
    hcswaver.run.v1.schema.json
    hcswaver.project.v1.schema.json
  adapters/
    hcsuda/
    cqhecs/
    foundry/
    lean/
  examples/
  fixtures/
  e2e/
  docs/
    UX_SPEC.md
    WORKFLOWS.md
    API_INTEGRATION.md
    PROVENANCE.md
    LIMITATIONS.md
    ADR/
```

The prior hcswaver concept defines five research rooms:

1. Reduction Canvas: verifier/Turing-machine abstraction, circuit/AIG/SAT reductions and gadget visualization.
2. Wavefront Observatory: actual solver events, graph summaries, branch/conflict/progression telemetry.
3. Solver Foundry: CPU and optional Vulkan solvers, solver selection, performance, proof status and experiment history.
4. Adversarial Arena: generate counterexamples against candidate heuristics/invariants with bounded search and recorded seeds.
5. Formal Proof Desk: Lean 4 editor/LSP, goals, build output, proof-tree navigation and exact kernel acceptance status.

Keep the five-room mental model, but label features by implementation status. For example, a visual projection of a graph is not the actual physical simulation of an algorithm. The 3D view must visualize real data/events or a clearly labelled derived layout.

## 4.3 Existing project adapters

**CQ-HECS adapter**
- Call the documented CLI/API/MCP contracts already present in CQ-HECS.
- Read and preserve `hcs.run.v2` provenance fields when importing CQ-HECS runs.
- Preserve engine selection, refusal reasons, proof status and exact-vs-approximate semantics.
- Do not rewrite its Python, C++, WASM or browser engines into HCSUDA unless a separately reviewed migration has tests and compatibility adapters.

**HCS Foundry adapter**
- Reuse its local model catalogue, runtime management, resource governor and OpenAI-compatible local inference endpoint when present.
- Reuse its typed MCP tools; do not create a generic shell/exec tool.
- Agent output may propose patches/heuristics/Lean proof candidates. Execution occurs in an isolated worktree/process with an allowlisted command registry and explicit user policy.
- No model weights in Git or in the base HSCL1 ISO. Provide optional downloads with model ID, revision, license, hash, size, and user consent.

**Lean adapter**
- Use a pinned Lean toolchain (`lean-toolchain`) and pinned Mathlib revision where used.
- Invoke the Lean compiler/build in a subprocess with timeout, memory budget and structured output.
- Only a successful kernel/build result marks a theorem proved.

---

# 5. HCSUDA IMPLEMENTATION PHASES — BUILD A PROVABLE VERTICAL SLICE FIRST

## Phase 0 — Baseline and architecture decisions

Deliver:
- Repository audit report for all five repositories.
- Hardware capability snapshot on Windows and (when available) Linux.
- ADRs: repo boundary, language/ABI, Vulkan optionality, file format, SAT integration, license strategy, packaging path.
- Master-plan changes in HSCL1, Foundry and CQ-HECS.
- A risk register and a feature/capability matrix.

Gate: no code until the integration plan clearly states what is reused, what is new, and how each interface is versioned.

## Phase 1 — CPU-only core, result contracts, CLI

Build the core without Vulkan first:

- Device capability report with a CPU-only device always present.
- Typed error/result model: `ok`, `unsupported`, `budget_exceeded`, `timeout`, `cancelled`, `invalid_input`, `device_lost`, `verification_failed`, `internal_error`.
- Deterministic run IDs and provenance record containing input SHA-256, code revision, binary/build flags, selected path, device/driver, precision, random seed, budget, timings, output digest and verification result.
- CLI: `hcsuda doctor`, `hcsuda device list`, `hcsuda budget`, `hcsuda qstp inspect`, `hcsuda bench smoke`, `hcsuda sat solve` (the last may initially delegate to a supported solver adapter).
- No fake features. Commands not implemented should be absent or explicitly return `unsupported`.

Gate: clean CPU build and all unit tests pass on Windows and Linux or CI hosts.

## Phase 2 — HCSUDA memory and QSTP container MVP

Implement a storage container before any GPU streaming:

- Versioned `.hcsblk`/`.hcsswap` file with fixed magic, format version, endianness, block table, codec IDs, quantization metadata, per-block stored length, decompressed length, checksum and offset bounds.
- Atomic create using a new file; never truncate an existing file without a safe explicit overwrite operation.
- Validate untrusted header values before allocation. Limit decompressed block size to configured budget. Reject integer overflow, overlapping ranges, unknown versions, bad hashes and truncated blocks.
- Provide raw FP32/FP16, Q8, Q4 affine codec. Add ternary only as experimental behind a feature flag after exhaustive tests.
- Add sequential and random read paths; expose cache hit/miss and prefetch telemetry.
- First disk backend can use portable buffered I/O; add Linux async I/O and Windows IOCP separately.

Gate: byte-level roundtrip, corruption tests, property-based random blocks, interrupted writes, crash recovery and bounded memory tests.

## Phase 3 — Vulkan capability probe and first compute primitive

- Build a Vulkan instance/device probe that enumerates physical devices, API version, driver, queue families, memory heaps/types, optional extensions and required feature structs.
- Emit JSON capability manifest; the frontend never guesses capabilities from a marketing name.
- Add a simple vector add and GEMM reference path using ordinary compute shaders; CPU path remains the oracle.
- Add a Q4 decoder and tiled matrix multiply only after basic buffers/barriers are correct.
- Use validation layers in development, `spirv-val` on every generated shader and a software Vulkan path (e.g. lavapipe) where it is useful for CI correctness—not for performance claims.
- Add device-loss recovery and CPU fallback.

Gate: same input results within declared tolerance on CPU and Vulkan, including edge dimensions, non-multiple tile dimensions, NaN/Inf policy, zero sizes and repeated allocation/destruction.

## Phase 4 — asynchronous pipeline and tiered memory

Build bounded stages:

```text
Storage reader -> host staging ring -> codec/decode -> Vulkan upload -> compute -> result/reuse
```

- Represent each block by a host-side stable ID and state; do not expose one imaginary GPU pointer for data that lives on disk.
- Track in-flight stage and ownership; use ring buffers with explicit state transitions.
- Add bounded queue depth, backpressure, cancellation and job priorities.
- Use timeline semaphores and separate transfer/compute queues only when capabilities are present and measured.
- For UMA, evaluate host-visible buffers against device-local allocations; do not assume one is faster.
- For discrete GPU, test staging + dedicated transfer queue if present; do not assume BAR memory is suited to large transfers.
- Test block size/prefetch distance sweep (e.g. 256 KiB, 1 MiB, 4 MiB, 16 MiB, 64 MiB, 128 MiB) instead of mandating one magic 64/128 MB chunk.

Gate: no data corruption under concurrent loads; pipeline stages measured independently; all queue dependencies verified with Vulkan validation.

## Phase 5 — hybrid SAT: exact CPU core + optional GPU helpers

Use this order:

1. Establish an adapter to a trusted CPU CDCL solver and to CQ-HECS existing SAT paths. Record version/license and SAT/UNSAT result contract.
2. Add independent CNF parsing/canonicalization with strict DIMACS behavior; preserve original input digest and normalized digest separately.
3. Add an independent SAT assignment checker against the *original* formula.
4. Add UNSAT proof verification via the chosen proof formats and maintained checkers. Decide DRAT/LRAT/FRAT based on actual upstream compatibility and tool availability (section 2.13: the 2026 competition offers DPR, GRAT and VeriPB checkers and documents the verified `cake_lpr` LRAT pipeline; proposed: DRAT proof checked by `dpr-trim`, and `cake_lpr` where the solver emits LRAT). Keep the checker separate from the solver process.
5. Implement GPU-friendly preprocessing/inprocessing one transformation at a time (start with a small, bounded BVE or functional-dependency extraction subset). Each transformation has a proof/replay path and exact budget.
6. Add a FastFourierSAT-style or equivalent GPU continuous-search hint adapter only after the algorithm is correctly reproduced from its source paper and its own test corpus exists.
7. Keep CDCL branching/search on CPU initially. GPU phase hints only influence a declared heuristic interface; they do not mutate solver state asynchronously.
8. Consider GPU clause database/learned clause assistance only after measurements show a benefit and correctness boundaries are explicit.

**Hard result contract:**
- SAT: assignment exists, is total or explicitly completed, and independently verifies against the original CNF.
- UNSAT: proof/certificate exists and an independent checker accepts it.
- UNKNOWN: timeout, unsupported path, resource exhaustion or no proof. Never convert UNKNOWN into UNSAT.
- ERROR: malformed input or internal failure. Do not return an answer.

Gate: small exhaustive differential tests against brute force; differential tests against CaDiCaL/Kissat/PySAT where available; proof checker accepts every UNSAT result; every SAT assignment is checked.

## Phase 6 — hcswaver research orchestration

Implement one complete user workflow before all rooms:

**Workflow: load CNF → inspect → plan → solve → verify → visualize → export**

1. User opens a DIMACS CNF or selects a generated benchmark family.
2. Studio calculates variables, clauses, literal count, clause width distribution, graph statistics, source digest and limits.
3. Planner shows which engine is capable, why it was selected and why alternatives were declined.
4. User chooses CPU-only, Vulkan-assisted or auto mode.
5. Job panel shows state, elapsed time, progress (only where actual progress exists), resource use and cancellation.
6. SAT witness / UNSAT proof is independently checked.
7. Timeline, clause graph and branch visualization use real solver telemetry; data is sampled/aggregated for large instances.
8. Export contains CNF digest, normalized digest, command, engine version, proof/witness, verification state, runtime, device report and environment.

Gate: Playwright/E2E test drives this workflow from a clean install with real small CNF instances, including SAT, UNSAT, malformed input, cancellation and unsupported GPU.

## Phase 7 — remaining hcswaver rooms

Implement incrementally:
- Reduction Canvas: small deterministic examples first; show each transformation and preserve a source-to-target mapping.
- Wavefront Observatory: variable/clause graph summaries, selected subgraphs, solver events and branch/conflict timeline. Never create one DOM node per literal for million-literal instances.
- Solver Foundry: list actual installed engines and tested capabilities; provide comparable benchmark runs.
- Adversarial Arena: generate small counterexamples against one declared hypothesis; shrink failing inputs; persist seed and minimization trace.
- Formal Proof Desk: Lean 4 editor/LSP, goals and compiler output. Distinguish “candidate lemma”, “build passed” and “kernel-checked theorem”.

Gate: every room has one end-to-end test and no dead controls or dummy progress states.

## Phase 8 — HSCL1 packaging and ISO

- Create `hcsuda-runtime` (shared library/runtime, optional Vulkan backend), `hcsuda-cli`, `hcswaver` and optional `hcswaver-examples` packages as justified by size/dependencies.
- Use Debian packaging conventions already present in HSCL1. Reuse its manifest/build/verification system.
- Add `hscl compute status`, `hscl compute devices`, `hscl compute doctor`, `hscl research launch` only after the CLI commands work and have JSON tests.
- Add a Control Center “Compute & Research” page reading actual machine JSON, not hard-coded telemetry.
- Make heavy Vulkan SDK/toolchains, Lean build caches, benchmarks, models and datasets opt-in developer bundles, not required base ISO payload.
- Launch hcswaver as an app; keep its compute service unprivileged.
- Run installer and first-boot tests in disposable VMs only.

Gate: clean ISO build, verify package dependency resolution, boot live ISO, install on disposable virtual disk, boot installed system, launch app, run CPU smoke, and verify that missing Vulkan is presented as a normal fallback state.

---

# 6. API, FILE FORMAT AND INTER-PROJECT CONTRACTS

## 6.1 HCSUDA API principles

Provide a stable, versioned C ABI for cross-language integration and a modern C++ wrapper for native callers. Keep the public API small.

Example conceptual interface:

```cpp
namespace hcsuda {
  struct DeviceReport;
  struct MemoryBudget;
  struct RunOptions;
  struct RunResult;

  Result<std::vector<DeviceReport>> enumerate_devices();
  Result<MemoryBudget> query_budget(const DeviceId& id);
  Result<RunResult> gemm(const TensorView& a,
                         const TensorView& b,
                         const RunOptions& options);
  Result<SatResult> solve_sat(const CnfView& cnf,
                              const SatOptions& options);
}
```

The API must:
- avoid throwing C++ exceptions across a C ABI;
- make ownership and lifetime explicit;
- accept cancellation tokens and time/memory budgets;
- report selected device and fallback reason;
- preserve input hashes and result provenance;
- version schemas and reject unknown major versions.

## 6.2 Model Context Protocol (MCP)

Prefer to expose the same HCSUDA operations through HCS Foundry's existing typed agent infrastructure or a small HCSUDA MCP adapter with **finite typed tools**. Do not add arbitrary `shell`, `exec`, unrestricted path, or arbitrary file-write tools.

Suggested read-only tools:
- `hcsuda.devices.list`
- `hcsuda.budget.inspect`
- `hcsuda.benchmark.plan`
- `hcsuda.sat.inspect`
- `hcsuda.run.status`
- `hcsuda.proof.verify`

Potential write tools with bounded schemas:
- `hcsuda.benchmark.run` (allowlisted benchmark IDs, strict duration/memory caps)
- `hcsuda.sat.solve` (input must come from an approved workspace root; explicit time/memory limits)
- `hcsuda.qstp.encode` (new output path under approved project storage; never overwrite)

Any write requires job IDs, progress/status reporting, cancellation and provenance. Default agent mode is read-only. User must explicitly enable write operations. The agent cannot install packages or change system-level GPU/driver settings through MCP.

## 6.3 QSTP / `.hcsswap` format rules

- Include magic, major/minor version, endianness, codec ID, quantizer ID, tensor/block dimensions, dtype, per-block scales/zero points, offsets, stored/uncompressed byte lengths, compression lengths and checksums.
- Use bounded integer types and check every offset + length for overflow and file boundary.
- Verify checksums before handing block bytes to a GPU shader.
- Store provenance for calibration data and quantizer parameters.
- Version every quantizer and decoder; never decode an unknown version with a “best guess”.
- Support raw lossless mode as a correctness reference.
- Add optional authenticated encryption only after a key-management design; never invent an encryption format.
- Never store model weights inside an SQLite blob. Metadata is in SQLite; heavy blocks are files/objects.

## 6.4 SQLite metadata schema (initial)

Use SQLite for small metadata and job state, not large tensor payloads.

Tables:
- `schema_migrations(version, applied_at, checksum)`
- `devices(device_id, vendor, name, api_version, driver, capability_json, first_seen_at, last_seen_at)`
- `memory_profiles(profile_id, device_id, host_total, host_available, device_heaps_json, safety_reserve, measured_at)`
- `artifacts(artifact_id, kind, path, sha256, size_bytes, format_version, license_id, created_at)`
- `runs(run_id, kind, input_sha256, engine, engine_version, device_id, seed, config_json, status, started_at, ended_at, result_sha256)`
- `run_events(event_id, run_id, sequence, event_type, payload_json, created_at)`
- `proofs(proof_id, run_id, format, path, sha256, checker, checker_version, verification_status, checked_at)`
- `benchmarks(benchmark_id, suite, family, source_url, license_id, split, sha256, metadata_json)`
- `measurements(measurement_id, run_id, metric, value, unit, sample_index, metadata_json)`
- `jobs(job_id, run_id, state, priority, cancel_requested, heartbeat_at, worker_id, failure_code)`

Use migrations, foreign keys, indexes, WAL where appropriate, transactional updates and crash-recovery tests. Do not persist secrets or raw sensitive prompts by default.

---

# 7. UX / UI IMPLEMENTATION CONTRACT

## 7.1 Design principles

The product should feel like a premium research workstation, not a neon dashboard that hides uncertainty.

- Dark-first HCS identity, optional light theme; readable contrast and restrained accents.
- Three-panel desktop layout: project/navigation, main work surface, inspector/context panel; collapsible panels and keyboard shortcuts.
- Global command palette (`Ctrl+K`), searchable commands, accessible focus management and Escape-to-close.
- Persistent bottom job/console area with logs, progress, resource budget, warnings and cancellation.
- Clear result badges: `SAT`, `UNSAT (proof checked)`, `UNKNOWN`, `FAILED`, `EXPERIMENTAL`, `NOT AVAILABLE`.
- Distinguish actual measured values, predictions, estimates, synthetic examples and demo data.
- No fake 3D activity. Animations reflect actual data flow or are clearly illustrative.
- No unbounded rendering: cluster/downsample huge graphs; expose the sampling strategy and original counts.
- Keyboard-first operation, screen-reader labels, focus indicators, high contrast, reduced motion and localization.
- Support EN/DE/FR with string catalogs; never hardcode UI language inside compute logs.

## 7.2 Core screens

**Workspace overview** — recent projects, engines present, active jobs, saved experiments, notices about unavailable capabilities.

**Reduction Canvas** — source language/verifier, circuit/AIG, CNF, variable/clause counts, transformation trace and export. Each transformation has a reversible or reproducible record.

**Wavefront Observatory** — actual branch events, conflict counts, propagation activity, selected graph neighborhoods, clause/variable heatmap and performance timeline. Do not call a graph animation “search-space simulation” unless it accurately encodes the solver's actual state.

**Solver Foundry** — choose engine, capability, CPU/GPU mode, budgets and verifier. Display why a mode is eligible or rejected.

**Adversarial Arena** — candidate heuristic/hypothesis, counterexample generator, minimization trace, reproducible seed, hold-out status.

**Formal Proof Desk** — Lean source, goals, diagnostics, build status, theorem name, imports/axioms and a direct path to the pinned source revision.

**Hardware & Memory** — physical memory topology as reported by driver/OS, not a fantasy 2 TB memory globe; host/GPU budget, memory type, transfer rates measured on the device, queue capabilities and backend status.

**Experiment report** — immutable provenance, input and output hashes, code revision, versions, settings, result, proof state, raw measurement links and limitations.

## 7.3 Accessibility and visual QA

Automate:
- axe or equivalent accessibility scan;
- keyboard-only traversal of each main workflow;
- reduced-motion mode;
- EN/DE/FR layout checks at 1366x768, 1920x1080 and 390px mobile width where relevant;
- long German/French string overflow;
- empty, loading, timeout, cancellation, crash and unavailable-engine states;
- contrast, focus, touch target sizes and semantic labels.

Screenshots must come from a running build and be stored as CI artifacts, not fabricated in documentation.

---

# 8. TESTING, VERIFICATION AND BENCHMARK PROTOCOL

## 8.1 Test pyramid

1. Unit tests: deterministic small functions and format parsing.
2. Property/fuzz tests: arbitrary input sizes, malformed CNF, corrupted files, quantizer metadata and memory offsets.
3. Differential tests: CPU reference vs GPU backend; independent SAT solver/checker; NumPy reference vs GEMM.
4. Integration tests: API, storage, worker lifecycle, model adapter, MCP transport and database migrations.
5. E2E tests: real user workflow in hcswaver.
6. VM tests: HSCL1 live boot, install, first boot, app launch, CPU fallback and package removal/upgrade.
7. Hardware tests: actual supported GPU hardware only; device and driver report attached.

## 8.2 Quantization correctness tests

Test:
- random normal, uniform, heavy-tailed and outlier-containing blocks;
- all-zero and constant blocks;
- min/max endpoints and values just either side of bin boundaries;
- group sizes 1, 2, 31, 32, 33, 127, 128, 129 and non-power-of-two lengths;
- all byte values for ternary pack/decode and reserved codes;
- CPU encode + CPU decode; CPU encode + GPU decode; GPU decode vs Python reference;
- serialization/deserialization and corrupted checksum;
- relative error, absolute max error, RMSE, cosine similarity and downstream metric degradation.

For affine Q4, compare observed error with the expected bound where its assumptions hold. For ternary, do not invent a universal bound; report empirical error distributions and downstream quality.

## 8.3 GEMM correctness tests

Reference: NumPy/BLAS FP64 or FP32 CPU computation, using deterministic input arrays and stated precision.

Cover:
- rectangular matrices;
- tile boundary dimensions (15, 16, 17, 31, 32, 33, 63, 64, 65);
- non-contiguous row strides if supported;
- zero and negative values;
- overflow-prone magnitudes;
- half precision and quantized input decode;
- misaligned/partial final blocks;
- repeated runs/device loss.

Report absolute error, relative error and maximum error with scale-aware denominator. A fixed tolerance such as Q4 `<1e-2` may be an initial target, but calibrate it on the actual operation and dataset. Never copy a tolerance from an unrelated kernel and declare it valid.

## 8.4 SAT correctness tests

Use a small brute-force oracle up to a configured variable limit. Create hand-checked formulas:

```dimacs
c SAT example: x1 and (not x1 or x2)
p cnf 2 2
1 0
-1 2 0
```

```dimacs
c UNSAT example: x1 and not x1
p cnf 1 2
1 0
-1 0
```

Test empty clauses, empty formula, unit clauses, tautological clauses, duplicate literals, repeated clauses, invalid literals, missing terminators and truncated files.

Requirements:
- Every SAT assignment is parsed and checked against the **original** CNF, not just the transformed formula.
- Every UNSAT result has an independently accepted proof certificate in certificate mode.
- Compare result status with brute force for small instances and with independent solver(s) for larger instances.
- Test transformations by checking proof/certificate validity and the equivalence/equisatisfiability contract.
- Randomly permute variables/clauses and test determinism where required.
- Timeout/resource limits return `UNKNOWN`, not `UNSAT`.

## 8.5 Vulkan and shader tests

- Compile every `.comp` shader in CI.
- Run `spirv-val` with the correct Vulkan target environment.
- Run Vulkan validation layers in debug integration tests.
- Add descriptor/range/alignment boundary tests; verify BDA feature flags and alignment.
- Test synchronization2 barriers, timeline values, queue family ownership and host flush/invalidate paths.
- Stress repeated allocate/submit/cancel/destroy and device-lost paths.
- Test shader bounds with sizes not divisible by workgroup dimensions.
- Run under software Vulkan for correctness when feasible, but use real hardware for performance evidence.
- Avoid kernels that spin forever. On Windows, test recovery behavior with bounded dispatches and do not alter system TDR registry settings.

## 8.6 Storage and memory fault-injection tests

Inject:
- short read/write;
- out-of-space;
- process crash during write;
- checksum mismatch;
- truncated header and block;
- integer-overflow offset;
- duplicate/overlapping blocks;
- decompression bomb / maximum output cap;
- cancellation during prefetch;
- disk disconnect where the OS reports it;
- two jobs competing for memory;
- low available RAM and failed GPU allocation.

The process must fail safely, preserve the source file, avoid writing outside the configured storage root and return a typed error.

## 8.7 Benchmark fairness and statistics

For every comparison:
- Same machine, driver, power profile, thermal state, input corpus, timeout, memory cap, thread count and warm/cold cache condition.
- Compare CPU baseline, Vulkan-only, hybrid CPU+GPU, raw/no-quantization and each quantization mode.
- Run multiple repetitions; report median, spread (IQR or confidence interval), sample count and outliers.
- Record wall time, CPU time, GPU utilization where observable, transfer bytes, disk bytes, throughput, memory peak, device stalls and correctness result.
- Store raw JSON/CSV plus machine report and command lines.
- Do not claim a global speedup from a small sample or one hand-picked instance.
- For SAT use PAR-2, solved count and per-family results; include hard timeouts.
- Keep a held-out suite untouched by automated tuning.

---

# 9. AGENTIC DEVELOPMENT AND SELF-HEALING LOOPS

## 9.1 Role split

When multi-agent execution is available, assign:

- **Lead integrator:** baseline, cross-repo contracts, merge order, plan updates, release truthfulness.
- **Compute architect:** memory, queues, device capability contracts and API.
- **Vulkan engineer:** shaders, synchronization, validation, device-specific profiling.
- **SAT researcher:** CDCL integration, BVE, FastFourierSAT reproduction, proof generation/checking.
- **Quantization/storage engineer:** QSTP, container format, codecs, I/O and corruption handling.
- **UI/UX engineer:** hcswaver screens, accessibility, localization, E2E.
- **Research auditor:** literature, mathematical assumptions, external baselines, licenses and claims.
- **OS/package engineer:** HSCL1 Debian packaging, CLI, Control Center, ISO/VM tests.

The lead owns interfaces and final merges. Subagents do not independently bump versions or edit cross-repo root plans without integration review.

## 9.2 Feature loop

For each feature:

1. State the user goal and the exact measurable acceptance criteria.
2. Research current primary sources and licenses.
3. Write/refresh an ADR and contract before code.
4. Create a minimal test that captures the invariant or expected behaviour.
5. Implement the smallest vertical slice.
6. Run formatter, linter, static analysis and focused test.
7. Run subsystem tests and independent/differential checks.
8. Run sanitizer/fuzzer/validation-layer tests relevant to the change.
9. Run benchmark only after correctness gates pass.
10. Inspect memory, security and diff; update docs and evidence ledger.
11. Commit one coherent checkpoint.
12. Push a feature branch after local gates pass; open/update a draft PR; wait for remote CI; repair failures in the same branch.

## 9.3 Self-healing repair loop

When something fails:

```text
FAILURE
  -> capture exact command, machine report, logs and minimal reproducer
  -> classify (source bug / test bug / environment / missing capability / flaky / upstream)
  -> add or confirm regression test
  -> identify violated invariant
  -> make one root-cause fix
  -> focused verification
  -> subsystem verification
  -> independent verification
  -> full gates at milestone boundary
  -> update evidence and checkpoint
```

- Up to three meaningful repair cycles for the same root cause.
- After three failed root-cause attempts, mark `BLOCKED`, preserve reproducer/logs and move to independent safe work.
- Do not indefinitely rerun, inflate timeouts, skip failing cases, reduce accuracy thresholds or disable validation to create a green status.
- A flaky test must be diagnosed; do not simply retry until it passes and call it fixed.
- A performance regression is not a self-healing opportunity to change the benchmark; establish why it changed first.

## 9.4 Research discovery loop

For each research hypothesis:

1. Write the hypothesis and falsification criterion.
2. Identify baseline algorithm/paper/commit and relevant limitations.
3. Implement a small reference/prototype with deterministic seeds.
4. Run the development benchmark corpus.
5. Minimize counterexamples and record failures.
6. Freeze the candidate and test on held-out data.
7. Check correctness certificates independently.
8. Compare runtime, memory, robustness and quality.
9. Record positive, neutral and negative results.
10. Promote only if acceptance criteria are met.

Agent-generated code must run in a disposable worktree/container/VM or restricted sandbox with no unapproved network or filesystem access. Do not let the model execute arbitrary shell commands on the host. Use command allowlists and finite typed tools.

---

# 10. BUILD, CI, PUSH, PR AND RELEASE POLICY

## 10.1 Local build gates

Before each push, run the applicable set:

```bash
# C++
cmake -S . -B build -G Ninja -DCMAKE_BUILD_TYPE=RelWithDebInfo
cmake --build build --parallel
ctest --test-dir build --output-on-failure

# Shaders (actual compiler paths/targets must be pinned)
glslangValidator -V --target-env vulkan1.2 shaders/gemm_q4.comp -o build/gemm_q4.spv
spirv-val --target-env vulkan1.2 build/gemm_q4.spv

# Python bindings / reference tests (only if included)
python -m pytest -q

# Studio (adapt to inspected package manager/lockfile)
npm ci
npm run lint
npm run typecheck
npm test -- --run
npm run build

# Rust host/CLI if used
cargo fmt --all -- --check
cargo clippy --workspace --all-targets -- -D warnings
cargo test --workspace
```

Do not paste commands that the project does not actually implement. The final README must contain the correct commands from the repository's lockfiles and scripts.

## 10.2 Push policy

Use independent feature branches per repository, for example:

- `codex/hcsuda-cpu-foundation`
- `codex/hcsuda-qstp-streaming`
- `codex/hcsuda-vulkan-compute`
- `codex/hcsuda-hybrid-sat`
- `codex/hcswaver-studio-mvp`
- `codex/hscl1-hcs-compute-integration`

Push only when:
- local tests for the changed component pass;
- no secret/model/dataset/large binary entered the diff;
- formatting, lockfiles and docs are updated;
- commit is a coherent checkpoint;
- exact changed files and commands are recorded.

Open a draft PR for cross-repo integration. Run remote CI and visual/VM jobs. Repair failures in the feature branch. Do not merge when required checks are red, skipped, unavailable or not actually run. Merge only under the repository's protection policy and the user's authorized scope; never bypass branch protections.

## 10.3 Cross-repository release order

1. Release HCSUDA API/ABI and schemas first.
2. Update hcswaver adapter to the pinned HCSUDA release/commit and run its integration tests.
3. Update CQ-HECS and Foundry adapters only through their own tested PRs.
4. Package the pinned HCSUDA/hcswaver versions in HSCL1 and run VM/ISO tests.
5. Publish the HCSUDA release with source, SBOM, checksums and limitations.
6. Publish hcswaver with compatible dependency metadata and UX evidence.
7. Publish HSCL1 image only after packaging/VM gates pass.

Never publish an ISO with moving Git branches as runtime dependencies. Pin release versions, source commit SHAs and package hashes.

## 10.4 Release acceptance

A release can call a feature `SUPPORTED` only if:
- code exists and is included in builds;
- API/CLI/UI actions work end to end;
- unit, integration and regression tests pass;
- correctness is independently verified where applicable;
- capability and limitations are documented;
- benchmark claims have raw results and a reproducible harness;
- security/license review is complete;
- package install/uninstall/upgrade paths are tested.

Use statuses:
`PLANNED`, `PROPOSED`, `IMPLEMENTED`, `UNIT-TESTED`, `INTEGRATION-TESTED`, `VM-VERIFIED`, `HARDWARE-VERIFIED`, `EXPERIMENTAL`, `BLOCKED`, `DEFERRED`, `REJECTED`.

---

# 11. LICENSE, SUPPLY CHAIN, SECURITY AND DATA RULES

- Inspect every dependency's license before integrating code or binary assets.
- Do not copy CUDA-specific ParaFROST source into HCSUDA until license compatibility and attribution are verified. Prefer a clean adapter or independently implemented algorithm based on the paper.
- Preserve each repository's current license. CQ-HECS is Apache-2.0, HCS Foundry is MIT, HSCL1 is GPL-3.0-or-later; do not copy code across those boundaries without a compatibility review and license notices.
- Pin submodules and third-party dependencies; record commit SHA, license and provenance.
- Generate SBOM (SPDX or CycloneDX) for engine, app, and OS packages.
- Do not bundle model weights, private data, datasets without redistribution rights, local logs or VM disk images in Git.
- Do not execute untrusted benchmark generators or generated agent patches on the host without sandboxing.
- Validate paths and archive extraction; prevent path traversal, decompression bombs and symlink escapes.
- Bind local service endpoints to loopback by default. Require explicit user action and authentication before network exposure.
- MCP defaults read-only; writes constrained to approved workspace roots and bounded job specifications.
- Keep secrets out of telemetry and provenance records. Redact personal paths/usernames where possible.
- No telemetry upload by default.

---

# 12. MASTER ROADMAP AND ACCEPTANCE MILESTONES

| Milestone | Deliverable | Acceptance gate |
|---|---|---|
| M0 | Audit + plan integration | Repository/machine maps, ADRs, master plans updated |
| M1 | HCSUDA CPU core | Clean CPU build, typed API/result, deterministic tests |
| M2 | QSTP/container and tiered file store | Corruption, roundtrip, crash, memory-bound tests |
| M3 | Vulkan probe and ordinary compute | CPU/Vulkan differential correctness; fallback works |
| M4 | Async streaming | Measured overlap, bounded queues, safe cancellation |
| M5 | Hybrid SAT adapter | SAT witness checks, UNSAT proof checker, differential tests |
| M6 | GPU SAT experiment | One proven transformation or hint path, isolated and measured |
| M7 | hcswaver MVP | Load→plan→solve→verify→visualize→export E2E |
| M8 | Remaining research rooms | Each room has a real workflow and E2E tests |
| M9 | HSCL1 packages | install/remove/upgrade, CLI and Control Center integration |
| M10 | HSCL1 VM/ISO integration | boot, install, CPU fallback, launch, regression gates |
| M11 | Release candidate | clean build, SBOM, signatures/checksums, docs, QA |

## Definition of done for the first public HCSUDA/hcswaver integrated beta

- [ ] HCSUDA builds CPU-only on Windows and Linux.
- [ ] Vulkan build is optional; Vulkan runtime probe is truthful.
- [ ] At least one real Vulkan compute primitive is differentially tested against CPU.
- [ ] QSTP raw + Q4 block format is versioned, checksummed and corruption-tested.
- [ ] Tiered memory uses bounded, explicit block residency; no false contiguous-VRAM claim.
- [ ] SAT adapter returns only independently checked SAT witnesses and proof-verified UNSAT answers (or UNKNOWN).
- [ ] GPU SAT prototype is marked EXPERIMENTAL until it passes the independent certificate/verification path.
- [ ] hcswaver supports the end-to-end CNF workflow described in Phase 6.
- [ ] Agent proposals and generated code run in a restricted environment, not arbitrary host shell.
- [ ] CQ-HECS and HCS Foundry integrations use versioned APIs/adapters, not copied business logic.
- [ ] HSCL1 contains a real package/launcher/CLI integration and falls back to CPU.
- [ ] VM install and first launch are tested on disposable virtual disks.
- [ ] docs include hardware capability matrix, benchmark methodology, known limitations and provenance examples.
- [ ] public release assets include source, SBOM, checksums, and signed artifacts if signing keys are available.

---

# 13. HOW THE HUMAN OWNER CAN UNDERSTAND AND VERIFY THE RESULTS

The project must make its science and engineering inspectable, even when the owner is not writing every line of C++ or Vulkan.

For every major feature, create a short `docs/PROOF_CARD.md` or evidence entry with:

1. **Question:** What problem is this feature meant to solve?
2. **Claim:** What exact statement are we making?
3. **Assumptions:** Which hardware, data, precision, input class and limits apply?
4. **Mechanism:** What code path carries out the operation?
5. **Reference:** Which paper/specification/upstream implementation is being followed?
6. **Test:** What command reproduces the result?
7. **Oracle:** What independent implementation/checker decides correctness?
8. **Evidence:** Raw output, machine report, code SHA, input SHA, benchmark set and date.
9. **Failure cases:** When should the system refuse, return UNKNOWN or fall back?
10. **Status:** What is verified now, and what remains a hypothesis?

Examples of what counts as evidence:

- **Q4 decoder:** CPU encoder and GPU decoder produce matching values within the declared quantization error; corruption is rejected.
- **GPU GEMM:** all tested shapes match the reference within a declared precision threshold; benchmark report identifies the exact GPU/driver.
- **Hybrid SAT:** SAT assignment is independently checked; UNSAT proof is checked by a separate proof checker; UNKNOWN is not mislabeled.
- **HDD streaming:** raw bytes, stored bytes, logical throughput, per-stage times and repeated trials are published; no synthetic “effective bandwidth” is labeled physical drive speed.
- **Lean theorem:** pinned Lean/Mathlib build succeeds and the kernel accepts the proof term; imported axioms are listed.
- **Agent code evolution:** immutable baseline, candidate commit, isolated tests, held-out benchmark and regression outcomes are published.

A green test badge alone is not proof of a research claim. The user must be able to reproduce the result from the repository and understand exactly what the result does and does not establish.

---

# 14. RESEARCH LEDGER TEMPLATE

Create one dated directory for every substantial experiment, for example `research/2026-11-07-qstp-q4-baseline/`.

```text
README.md                 # short question, method, outcome
HYPOTHESIS.md             # falsifiable statement and assumptions
LITERATURE.md             # sources, revision/date, relevant excerpts/paraphrases
BASELINE.md               # current reference and environment
METHOD.md                 # algorithm, formulas, parameters
TEST_MATRIX.md            # cases, limits and expected outcomes
RESULTS.json              # machine-readable raw results/summary
RAW/                      # permitted benchmark output, not private data
ANALYSIS.md               # interpretation, statistical limits
COUNTEREXAMPLES.md        # failed instances, shrunk reproducers
DECISION.md               # promote / continue / defer / reject
```

Do not overwrite old results. Use a new experiment directory for changed algorithms or materially different settings.

---

# 15. SOURCE REGISTER — START HERE AND RE-CHECK BEFORE RELEASE

## Primary research and SAT practice

1. Osama, Wijs, Biere — *Certified SAT solving with GPU accelerated inprocessing* (2023/2024): https://link.springer.com/article/10.1007/s10703-023-00432-z
2. ParaFROST code, build requirements and license: https://github.com/muhos/ParaFROST
3. Cen, Zhang, Fong — *Massively Parallel Continuous Local Search for Hybrid SAT Solving on GPUs* (AAAI 2025): https://ojs.aaai.org/index.php/AAAI/article/view/33211
4. FastFourierSAT arXiv: https://arxiv.org/abs/2308.15020
5. Yu et al. — *Autonomous Code Evolution Meets NP-Completeness* (SATLUTION, 2025): https://arxiv.org/abs/2509.07367
6. SAT Competition 2026: https://satcompetition.github.io/2026/
7. SAT Competition 2026 benchmarks: https://satcompetition.github.io/2026/benchmarks.html
8. SAT Competition 2025 results: https://satcompetition.github.io/2025/results.html
9. Kissat: https://github.com/arminbiere/kissat
10. CaDiCaL: https://github.com/arminbiere/cadical
11. Lean 4 reference: https://lean-lang.org/doc/reference/latest/
12. Lean learning resources: https://lean-lang.org/learn/

## GPU, Vulkan and memory

13. Vulkan memory specification: https://docs.vulkan.org/spec/latest/chapters/memory.html
14. Vulkan queues: https://docs.vulkan.org/guide/latest/queues.html
15. Vulkan timeline semaphores: https://docs.vulkan.org/tutorial/latest/Advanced_Vulkan_Compute/08_Asynchronous_Compute/03_timeline_semaphores.html
16. Vulkan synchronization/queue ownership: https://docs.vulkan.org/tutorial/latest/Advanced_Vulkan_Compute/08_Asynchronous_Compute/02_concurrent_execution.html
17. Vulkan Buffer Device Address: https://docs.vulkan.org/guide/latest/buffer_device_address.html
18. Vulkan BDA alignment: https://docs.vulkan.org/guide/latest/buffer_device_address_alignment.html
19. Vulkan cooperative matrix: https://docs.vulkan.org/refpages/latest/refpages/source/VK_KHR_cooperative_matrix.html
20. Vulkan cooperative vector: https://docs.vulkan.org/refpages/latest/refpages/source/VK_NV_cooperative_vector.html
21. Vulkan Memory Allocator: https://github.com/GPUOpen-LibrariesAndSDKs/VulkanMemoryAllocator
22. Mesa RADV: https://docs.mesa3d.org/drivers/radv.html
23. AMD Vulkan support notes: https://www.amd.com/en/resources/support-articles/release-notes/RN-RAD-WIN-VULKAN.html
24. LLVM SPIR-V target: https://www.llvm.org/docs/SPIRVUsage.html
25. Windows WDDM TDR: https://learn.microsoft.com/en-us/windows-hardware/drivers/display/timeout-detection-and-recovery
26. POSIX `posix_fadvise`: https://www.man7.org/linux/man-pages/man2/posix_fadvise.2.html
27. LZ4: https://github.com/lz4/lz4

## Quantization and model serving

28. AQPIM (2026, Processing-in-Memory activation quantization): https://arxiv.org/abs/2604.18137
29. Context-intensive KV cache offloading (2026): https://arxiv.org/abs/2604.08426
30. AWQ (MLSys 2024): https://proceedings.mlsys.org/paper_files/paper/2024/hash/42a452cbafa9dd64e9ba4aa95cc1ef21-Abstract-Conference.html
31. llama.cpp build and backend documentation: https://github.com/ggml-org/llama.cpp/blob/master/docs/build.md
32. SKVQ (COLM 2024): https://openreview.net/forum?id=nI6JyFSnyV
33. KIVI (ICML 2024): https://proceedings.mlr.press/v235/liu24bz.html
34. KVQuant (NeurIPS 2024): https://arxiv.org/abs/2401.18079
35. QServe (MLSys 2025): https://proceedings.mlsys.org/paper_files/paper/2025/hash/fbe2b2f74a2ece8070d8fb073717bda6-Abstract-Conference.html
36. FServe (EMNLP Findings 2026): https://aclanthology.org/2026.findings-emnlp.1556/
37. TurboQuant (Google Research, 2026): https://research.google/blog/turboquant-redefining-ai-efficiency-with-extreme-compression/
38. FlexGen (ICML 2023): https://proceedings.mlr.press/v202/sheng23a.html

## Existing HCS projects — inspect live source, do not rely only on this file

39. HSCL1: https://github.com/timfromhcs/HSCL1
40. CQ-HECS: https://github.com/timfromhcs/CQ-HECS
41. HCS Foundry: https://github.com/timfromhcs/hcs-foundry
42. hcswaver target: https://github.com/timfromhcs/hcswaver
43. HCSUDA target: https://github.com/timfromhcs/hcsuda

## Added 2026-11-07 (see section 2.13)

44. SAT Competition 2026 tracks (certificates for SAT and UNSAT in the Main track, Experimental track rule): https://satcompetition.github.io/2026/tracks.html
45. SAT Competition 2026 output and certificate format (DRAT proof.out; DPR, GRAT, VeriPB checkers; read 2026-11-07): https://satcompetition.github.io/2026/output.html
46. TurboSAT (arXiv 2511.07737; read 2026-11-07: SAT only, no code linked, paper CC BY 4.0): https://arxiv.org/abs/2511.07737
47. llama.cpp cooperative-matrix Vulkan PR (disabled on the AMD proprietary driver at the time): https://github.com/ggml-org/llama.cpp/pull/10597
48. Qwen3-4B-Instruct-2507 GGUF (unsloth), local worker model: https://huggingface.co/unsloth/Qwen3-4B-Instruct-2507-GGUF
49. QVAC Fabric LLM LoRA fine-tuning on heterogeneous GPUs (Vulkan; blog): https://huggingface.co/blog/qvac/fabric-llm-finetune
50. QVAC Fabric llama.cpp fork (MIT): https://github.com/tetherto/qvac-fabric-llm.cpp
51. DFloat11, lossless bf16 compression (arXiv 2504.11651): https://arxiv.org/abs/2504.11651
52. Vulkan Memory Allocator usage patterns (unified memory): https://gpuopen-librariesandsdks.github.io/VulkanMemoryAllocator/html/usage_patterns.html
53. AMD ROCm PyTorch for Radeon/Ryzen (supported devices): https://rocm.docs.amd.com/projects/radeon-ryzen/en/latest/docs/install/installryz/native_linux/install-pytorch.html
54. FusionML, CPU+GPU co-execution on unified memory (arXiv 2607.22785): https://arxiv.org/abs/2607.22785
55. FastMTP (arXiv 2509.18362): https://arxiv.org/abs/2509.18362
56. Gated LoRA for multi-token prediction, Apple (arXiv 2507.11851): https://arxiv.org/abs/2507.11851
57. LoftQ (arXiv 2402.05147): https://arxiv.org/abs/2402.05147
58. LowRA, sub-2-bit LoRA fine-tuning (arXiv 2502.08141): https://arxiv.org/abs/2502.08141
59. llama.cpp b9668, Vulkan prefers host-visible buffers on UMA devices (PR 22930): https://github.com/ggml-org/llama.cpp/releases/tag/b9668
60. AMD Ryzen 7 7735HS product page (specs read 2026-11-07): https://www.amd.com/en/products/processors/laptop/ryzen/7000-series/amd-ryzen-7-7735hs.html
61. LISA, layerwise importance sampling (arXiv 2403.17919): https://arxiv.org/abs/2403.17919
62. Reducing activation recomputation in large transformer models (arXiv 2205.05198): https://arxiv.org/abs/2205.05198
63. AMD ZenDNN / zentorch (EPYC/AVX-512 oriented; not applicable to this Zen 3+ chip): https://www.amd.com/en/developer/zendnn.html

---

# 16. FINAL INSTRUCTION TO THE AUTONOMOUS AGENT

Do not merely summarize this plan. First inspect and reconcile it with the current repository state and the user's existing master plans. Then write a concise execution plan with task IDs, file paths, owners, dependencies, acceptance tests and exact next actions. Start with M0 and the CPU-only vertical slice. Build HCSUDA as its own reusable repository, build hcswaver as its own user-facing Studio, and integrate both into HSCL1 through packages and versioned adapters in parallel after the contracts are stable.

At every milestone, leave a durable handoff containing:
- current commit and branch per repository;
- files changed;
- commands and test results;
- hardware/driver report;
- benchmark run IDs and result paths;
- open failures/blockers;
- evidence status for every public claim;
- next exact task.

Never say “done” because the code compiles or the UI looks finished. Say what was implemented, what was independently verified, what was measured, and what remains experimental.

**Ultimate product direction:** HCSUDA provides the measured compute and solver foundation; hcswaver makes it understandable and usable as a research workstation; HCS Foundry supplies local AI agents; CQ-HECS contributes existing scientific and SAT capabilities; HSCL1 makes the environment installable and consistent. The result is a modular, open-source scientific-computing ecosystem that can grow without pretending that every research challenge has already been solved.
