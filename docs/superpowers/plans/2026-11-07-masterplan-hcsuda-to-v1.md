# MASTERPLAN — HCSUDA first, then HSCL1 to stable v1.0.0

> **Status: ACTIVE. This file supersedes the *ordering* of every earlier plan.**
> The gate definitions, threat model, honesty rules and evidence vocabulary of
> `2026-11-06-autonomous-to-stable-hardened.md`, `2026-11-06-finish-line-self-heal.md`,
> `2026-11-07-genesis-parallel.md` and `2026-11-07-hcswaver-integration.md` stay valid and are
> imported by reference, not repeated. Where this file and an older plan disagree about **what comes
> first**, this file wins.
>
> Written 2026-11-07 after reading: all `AGENTS*.md` (owner contract + three untracked companion
> files), all 19 files in `docs/superpowers/plans/`, `docs/BUILD_LOG.md` (105 KB, to the last entry),
> `docs/genesis/*`, `docs/integrations/*`, `docs/research/*`, `docs/CLAIMS.md`,
> `docs/KNOWN_LIMITATIONS.md`, `README.md`, `VERSION`, the three CI workflows, `scripts/` and
> `tests/` — plus fresh measurements of this machine and toolchain (section 1.2).

---

## 0. Reading protocol for the next agent session

1. Read `docs/BUILD_LOG.md` last 150 lines, then this file, then `docs/CLAIMS.md`.
2. Run `python scripts/forge.py check --strict` (or `python -m pytest tests -q`) before touching code.
3. Take the next unchecked item from **§6 Sprint ladder** in this file, not from memory.
4. A box is ticked only with a path under `artifacts/` or a line in `docs/CLAIMS.md`.
   Vocabulary: `PLANNED`, `IMPLEMENTED`, `TESTED`, `VM-VERIFIED`, `HARDWARE-VERIFIED`,
   `EXPERIMENTAL`, `BLOCKED`, `UNVERIFIED`.
5. When a step needs the owner, it is listed in §13 — never guessed, never faked.

---

## 1. Measured starting position (2026-11-07, this session)

### 1.1 Repository

| Fact | Value |
|---|---|
| Branch | `codex/hscl1-v1`, working tree clean except three untracked owner files (`AGENTS_HCS_GENESIS.md`, `AGENTS_HCSWAVER_MASTERPLAN.md`, `AGENTS_HCSUDA_HCSWAVER_UNIFIED_MASTERPLAN.md`) |
| Distance | **114 commits ahead of `origin/main`**, 77 ahead of `origin/codex/hscl1-v1` (nothing pushed today) |
| `VERSION` | `0.1.3-alpha.0` |
| Open PRs | #22 (`codex/hscl1-v1` → `main`, plan v5 + host parity), 5 Dependabot PRs |
| CI on the branch | last 6 runs **success** (rust, python/shell, qml, cargo-audit, cargo-deny) |
| Local test gate (this session, Windows) | **590 passed, 49 skipped, 1 failed** → `tools/hcs_hold.py` lacked the exec bit in the index; **fixed** (`git update-index --chmod=+x`), targeted test green (3 passed) |
| Release artefacts | `HSCL1-0.1.3-alpha.0-amd64.iso` (5 026 742 272 B, sha256 `fc81ad1d…d1ebb`): boot UEFI 191 s, in-guest e2e 28/28, installer VM-verified, LUKS install VM-verified, Secure Boot file signatures measured |
| Dev image | `0.1.3-dev2` (sha256 `4d04e7ca…9cdc74`): installer version fix + `hscl-cqhecs`, boot 147 s, 31/31 in-guest checks |
| Known open gaps | recovery key, Secure Boot **firmware acceptance** (G6), brand OCR (G10), shortcut audit (G11, nothing bound yet), egress audit (P18), upgrade persistence (P19), SOURCE_OFFER (P22), full ISO SBOM + attestation (P9) |

### 1.2 Hardware and toolchain (measured now, not remembered)

| Item | Value | Consequence for HCSUDA |
|---|---|---|
| CPU | Ryzen 7 7735HS, 8C/16T, no AVX-512 | CPU oracle must be fast enough for differential tests; AVX2 path only |
| GPU | AMD Radeon 680M, `deviceID 0x1681` (Rembrandt, RDNA2), integrated | one memory pool shared with the CPU |
| Vulkan | instance 1.4.357, device API **1.4.315**, AMD proprietary driver **26.6.1** | 1.3+ feature set available |
| Heaps | 9.10 GiB device-local (+9.28 GiB budget), 4.55 GiB host-visible/device-local, 256 MiB | weights + activations must be planned against the **budget**, not the size |
| Compute limits | 1024 invocations/workgroup, **32 KiB** shared memory, storage range 4 GiB, `bufferDeviceAddress` | tile sizes are bounded by 32 KiB, not by CUDA's 48/164 KiB |
| `VK_KHR_cooperative_matrix` | **present**, subgroup size 64 (32–64) | matrix path is possible; must be benchmarked against tiled shared-memory |
| `VK_KHR_shader_integer_dot_product` | **8-bit and 4×8-bit packed accelerated (signed+unsigned)**; 16-bit accelerated; 32/64-bit not | INT8/INT4 dot products are the *fast* quantised path on this GPU |
| `shaderFloat16`, `storageBuffer16BitAccess` | yes | f16 storage + f16 arithmetic available |
| `shaderFloat64` | yes | f64 is correct but slow — reference only |
| `VK_EXT_shader_float8` | **absent** | FP8 is a **storage/quantisation** format here; compute must convert to f16 or use scaled int8 dot |
| Timestamps | `timestampComputeAndGraphics = true`, period 10 ns | GPU-side timing is possible without CPU sync noise |
| Toolchain | Rust **1.96.0** MSVC, Vulkan SDK **1.4.357** (`glslc`, `slangc`), `vulkaninfo`, crates.io reachable (`ash 0.38`) | HCSUDA can be built and run on this machine today, not only in WSL |

### 1.3 What the other plans already decided (imported, not re-litigated)

- Ubuntu 26.04 `resolute` + Plasma 6.6, Calamares, no Kali repo on the host, rootless Podman, LUKS2,
  no Tails-equivalence claim (AGENTS.md §3, §6).
- Speed ladders T0–T5 (build) and S0–S5 (test), one image build per sprint, one VM batch per image
  (finish-line §2, master v3 §3).
- Self-healing loop, max 3 attempts, GATE BUG first (finish-line §4).
- Honest release train: prerelease until AGENTS.md §20 is green (master v3 §0b).
- Genesis/HCSWaver/HCSUDA are **separate repositories**; HSCL1 only packages and integrates
  (`docs/integrations/*`, unified masterplan §2.13).
- Local-model delegation is a hint, never evidence (finish-line §8).

---

## 2. Owner decisions that are now binding (recorded, 2026-11-07)

These were stop-and-ask items in every earlier plan. The owner has now answered them:

| # | Decision | Consequence |
|---|---|---|
| O1 | **Push intermediate work** ("zwischenpushen") | Push `codex/hscl1-v1` after every green gate batch; open/refresh the PR; no force-push |
| O2 | **Merge to `main` at the end** ("am Ende main merge") | Merge only with green CI and the gate table in §7 satisfied; squash or merge-commit per repo setting, never force |
| O3 | **HCSUDA comes first**, then into the OS | Track H (this plan) has priority over Track O until H2 exits |
| O4 | HCSUDA must cover CUDA's capability surface "and better", with ONNX, GGUF, FP8/INT4/FP16/FP32, image + text models, train/infer/edit, automatic conservative gates | §5 capability matrix is the contract; "better" is only ever a measured number on named hardware |
| O5 | HCSUDA should also be usable "as a Vulkan graphics driver" on MSVC and Linux | §4.3 states exactly what is possible (ICD vs layer vs CUDA shim) and what is not; no claim beyond it |

Still owner-only (unchanged): physical-hardware boot, trademark/legal review, signing-key policy,
native-speaker review of DE/FR security strings, production website deployment, repository settings,
changing inherited network defaults.

---

## 3. Vision, synthesised (what we are actually building)

Four layers, one product family:

```
HSCL1 (OS)            Ubuntu 26.04 + Plasma 6.6 + HCS shell + hscl CLI + Control Center
  ├─ HCS-Genesis      orchestration/validation layer for scientific workflows (separate repo)
  ├─ HCSWaver         SAT/verification application (separate repo, not created)
  ├─ HCS Foundry      local AI workbench (separate repo, exists)
  ├─ CQ-HECS          bounded scientific compute (separate repo, exists; packaged as hscl-cqhecs)
  └─ HCSUDA           compute runtime: one API, every dtype, every device (this plan)
```

The OS is the delivery vehicle; HCSUDA is the engine that makes "local AI and science on ordinary
AMD hardware" true instead of marketing. Everything else (Genesis, HCSWaver, Foundry, CQ-HECS)
consumes HCSUDA through typed contracts and never starts its own GPU stack.

**Non-negotiable framing:** HCSUDA is not "CUDA but faster" in general. It is a Vulkan-first compute
runtime that (a) exposes a CUDA-shaped API so existing code can port, (b) beats the available
baselines **on this hardware, for the shapes we measure**, and (c) refuses to run a path it has not
verified against a CPU oracle.

---

## 4. The honesty contract (read before writing a line of HCSUDA)

### 4.1 What "everything CUDA can do" means operationally

CUDA is an API surface plus a toolchain plus libraries. We match it in **capability classes**, each
with its own gate, never with a single checkbox:

| Class | CUDA equivalent | HCSUDA target | Gate |
|---|---|---|---|
| Device/context/stream/event | `cuInit`, `cuCtx*`, `cuStream*`, `cuEvent*` | native API + CUDA-shaped C shim | H-G3 |
| Memory | `cuMemAlloc`, `cuMemcpy*`, `cuMemAdvise`, unified memory | device/host/unified pools, async copy, budget-aware | H-G3 |
| Kernels | PTX/SASS launch, `cuLaunchKernel` | SPIR-V pipelines from our kernels; **PTX translation is a later, separate gate** | H-G4 |
| Dtypes | f64/f32/tf32/bf16/f16/fp8/int8/int4 | all of them, each with a declared path (native / emulated / storage-only) | H-G2 |
| BLAS | cuBLAS | GEMV/GEMM (f32, f16, bf16, int8, int4, fp8-storage) | H-G5 |
| DNN | cuDNN | conv2d, pooling, norm, softmax, attention | H-G6 |
| FFT | cuFFT | out of v1 scope, listed as gap | — |
| Sparse | cuSPARSE | SpMV/SpMM int8/f32 (later) | H-G7 |
| Random | cuRAND | Philox/PCG on device | H-G4 |
| Graphs | CUDA Graphs | command reuse (recorded dispatch lists) | H-G8 |
| Training | cuBLAS + custom | backward ops, AdamW, LoRA merge | H-G9 |
| Model IO | (none) | GGUF read/write/quantise/edit, ONNX graph subset, safetensors | H-G10 |
| Tooling | nvcc, Nsight | `hcsuda` CLI, JSON reports, GPU timestamps | H-G1 |

### 4.2 What is explicitly **not** claimed

- Bit-identical results to CUDA (different reduction order, different rounding).
- Running arbitrary CUDA binaries in v1 (PTX→SPIR-V is H5, `EXPERIMENTAL` until a suite passes).
- Full Vulkan ICD conformance (see 4.3).
- Any performance number that was not measured on named hardware with the JSON evidence attached.
- FP8 *arithmetic* on RDNA2 — the silicon has no FP8 units; we support FP8 as storage with
  convert-and-compute, and we say so in every report.

### 4.3 "HCSUDA as a Vulkan graphics driver" — what is real

A Vulkan **ICD** must implement the whole Vulkan API (thousands of entry points, WSI, memory types,
synchronisation, conformance). Writing one is a multi-year project and would make nothing faster.
The honest, useful construction is three separate products:

1. **HCSUDA as the default Vulkan compute consumer** — device/queue selection, budget-aware
   allocation, pipeline cache, and the fastest verified kernel per shape. This is what our tools use.
2. **HCSUDA Vulkan layer** (`VK_LAYER_HCSUDA_telemetry`, later `_scheduler`) — a loadable layer that
   any Vulkan application can opt into for telemetry and (later) dispatch hints. A layer is supported
   by the loader, does not need to implement the API, and is testable today.
3. **HCSUDA CUDA driver shim** (`nvcuda.dll` / `libcuda.so.1` subset) — the ZLUDA-class capability,
   but Vulkan-backed where a mapping exists and CPU-backed where it does not. Marked `EXPERIMENTAL`
   until the compatibility suite (H5) passes.

On Linux the "different from standard" route is: same three products, plus a documented, unsupported
experiment with a DRM render node. It is never presented as a replacement for Mesa/AMDVLK.

---

## 5. HCSUDA architecture

```
hcsuda/
├── crates/
│   ├── hcsuda-core     dtypes, tensors, layouts, capability model, conservative planner,
│   │                   CPU reference kernels (the oracle), tolerance model, JSON reports
│   ├── hcsuda-vk       Vulkan backend (ash): instance/device, allocator, streams, events,
│   │                   pipeline cache + binary cache, SPIR-V load, specialisation constants,
│   │                   timestamps, validation-layer hook
│   ├── hcsuda-ops      kernels: elementwise, reduce, softmax, layernorm/rmsnorm, rope,
│   │                   GEMV, GEMM (naive → tiled → cooperative-matrix), conv2d, pooling,
│   │                   attention, quantise/dequantise (Q4_0/Q4_K/Q6_K/Q8_0), LoRA, AdamW
│   ├── hcsuda-io       GGUF (read/write/edit/split/merge/quantise), ONNX (graph + initializer
│   │                   subset), safetensors, PPM/PNG image loading for vision tests
│   ├── hcsuda-capi     C ABI + CUDA-shaped driver shim (cu* subset), header, pkg-config
│   ├── hcsuda-cli      `hcsuda caps|plan|bench|selftest|run|gguf|onnx|train|doctor`
│   └── hcsuda-layer    optional Vulkan layer (telemetry first)
├── shaders/            GLSL/Slang sources, compiled by build.rs with glslc/slangc
├── tests/              differential, property, golden, fuzz, benchmark harness
├── benchmarks/         JSON baselines per device/driver/dtype/shape
└── docs/               CAPABILITY_MATRIX.md, PORTING.md, MEASURED.md
```

**Design rules (binding):**

1. **Oracle first.** Every GPU op has a CPU reference implementation and a differential test with a
   declared tolerance per dtype. No op ships without it.
2. **Conservative planner.** For a given (op, dtype, shape, device) the planner returns the fastest
   *verified* path. An unverified path is never selected; the fallback is the reference path.
   Promotion requires: correctness (tolerance), determinism (3 identical runs), speed ≥ 1.05× the
   current best. Evidence is written to `benchmarks/<device>/<op>.json`.
3. **Budget-aware allocation.** Use `VK_EXT_memory_budget` values, never the heap size; leave 512 MiB
   headroom on an integrated GPU; refuse (with a clear error) rather than swap to disk.
4. **No hidden state.** Every CLI command has `--json`; every number carries device, driver, dtype,
   shape, and repetition count.
5. **Determinism is a feature.** Fixed reduction trees where possible; if a kernel is
   non-deterministic, the planner marks it and the report says so.
6. **Small dependencies.** `ash`, `bytemuck`, `serde`, `serde_json`, `clap`, `anyhow`, `thiserror`,
   `sha2`. No ML framework, no Python runtime in the core.
7. **Licence.** HCSUDA is a separate project; its licence is an owner decision (§13). Until then the
   code lives in this repo under GPL-3.0-or-later and is not published separately.

---

## 6. Work order — the sprint ladder

Dependency order, not preference. Track H is the owner's priority; Track O continues in the gaps
(host-only work while a build or VM runs).

### Track H — HCSUDA

| Sprint | Content | Exit gate | Est. |
|---|---|---|---|
| **H0 Scaffold + truth** | workspace, `hcsuda-core` dtype/layout/tensor, capability probe (`caps --json`), CPU oracle for elementwise + GEMV, planner skeleton, `doctor`; CI job for HCSUDA on Linux+Windows | H-G1, H-G2 | 1 session |
| **H1 Memory + dispatch** | `hcsuda-vk`: device/queue, allocator (device-local/host-visible/unified), staging ring, fences/timeline semaphores, SPIR-V pipeline cache, timestamp queries; first real kernel (SAXPY, triad, GEMV f32) vs oracle | H-G3, H-G4 | 1–2 sessions |
| **H2 Fast math** | tiled GEMM f32/f16, cooperative-matrix GEMM (f16→f32 accumulate), **int8/int4 dot GEMM**, fp8 storage + convert path, softmax/layernorm/rmsnorm/rope; measured table vs CPU and vs `llama-bench`-style baseline | H-G5 | 2 sessions |
| **H3 Models** | GGUF read/write/quantise/edit; ONNX graph subset; first text-model forward (tiny transformer) and first image-model forward (small CNN) end to end | H-G6, H-G10 | 2–3 sessions |
| **H4 Training** | backward for the ops used by LoRA, AdamW, LoRA merge; loss decreases on a fixed tiny task; determinism check | H-G9 | 2 sessions |
| **H5 CUDA compat (EXPERIMENTAL)** | `capi` + `nvcuda` subset, PTX subset translation, compatibility suite (vectorAdd → GEMM → a real library call) | H-G11 | 3+ sessions |
| **H6 OS integration** | `hcsuda-runtime`/`hcsuda-cli` debs, `hscl compute` namespace, Control Center card, image gates, docs EN/DE/FR | H-G12 | 1–2 sessions |
| **H7 VM + metal** | run the benchmark suite in the HSCL1 VM (virtio-gpu: CPU fallback expected) and on the real 680M (Windows host + installed Linux), record both honestly | H-G13 | 1 session |

### Track O — HSCL1 release gates (parallel, host-only work first)

Order is fixed by dependency:

1. **O1 Push and land the backlog** — push `codex/hscl1-v1`, refresh PR #22, green CI, merge to `main`
   (O1/O2). This is the first action of the whole plan: 114 unpushed commits are a single point of
   failure.
2. **O2 Close the alpha gaps** — recovery key flow, `/boot` explanation that actually shows, brand
   OCR gate (G10), shortcut implementation **or** removal of the published table (G11), egress audit
   (P18), upgrade persistence (P19), SOURCE_OFFER (P22).
3. **O3 Hardening evidence** — measured report (Lynis/OpenSCAP/systemd-analyze), full ISO SBOM +
   scan, reproducibility statement, attestation.
4. **O4 Product shell** — welcome app, Control Center real pages, handbook DE/FR, governor page.
5. **O5 Modes** — Security Lab runtime (rootless Podman, pinned Kali digest), privacy workflow
   (Tor status, fail-closed), local AI packages on top of HCSUDA.
6. **O6 Release candidate** — Secure Boot firmware acceptance, BIOS/USB boot, plain install, fault
   injection, §20 audit.
7. **O7 v1.0.0** — every §20 gate ticked or written as a gap; README/docs/website match the artefact.

### Track G/P — Genesis, HCSWaver, Foundry, CQ-HECS

Unchanged from `2026-11-07-genesis-parallel.md` and `2026-11-07-hcswaver-integration.md`: read-only
until their standalone slices exist; HSCL1 packages shells, never weights. They consume HCSUDA, so
they start **after H2**.

---

## 7. Gates

Every gate: exact command, pass criterion, evidence path. Evidence lives under
`artifacts/<gate>-<stamp>/` and is never in Git (except small curated JSON).

### 7.1 Local gates

| ID | Gate | Command | Pass |
|---|---|---|---|
| **L0** | Unit + fast suite | `python -m pytest tests -q` | `0 failed`; skips only with an explicit reason |
| **L1** | Strict host gate | `python scripts/forge.py check --strict` | exit 0, summary JSON written |
| **L2** | Rust | `cargo fmt --all -- --check && cargo clippy --all-targets -- -D warnings && cargo test --all` | exit 0 |
| **L3** | HCSUDA caps | `cargo run -p hcsuda-cli -- caps --json` | valid JSON; device, driver, dtype matrix, heaps, limits |
| **L4** | HCSUDA differential | `cargo test -p hcsuda-ops -- --nocapture` | every op within tolerance vs oracle; no skipped without reason |
| **L5** | HCSUDA benchmark | `cargo run -p hcsuda-cli -- bench --suite gemm,gemv,bandwidth --json` | JSON with ≥3 runs, median + spread, device/driver recorded |
| **L6** | Image build | `scripts/remaster-iso.sh --out … --force` (WSL) | exit 0, `verify-image: all checks passed`, `git_dirty: false` |
| **L7** | Boot | `python scripts/qemu_boot_test.py <iso> … --firmware uefi` | `reached_desktop: true`, screenshot, time ≤ 180 s |
| **L8** | In-guest e2e | `python scripts/workshop/e2e_cli.py <iso> …` | 0 errors, ≥ 31 checks, 3 consecutive runs |
| **L9** | Install (disposable disk) | `qemu_boot_test.py … --disk artifacts/…/disk.qcow2 --steps tests/visual/scenarios/install-luks.json` | all scenario screenshots, "All done." |
| **L10** | Installed LUKS boot | `e2e_luks_boot.py …` | wrong passphrase rejected, correct unlocks, desktop, no keyfile |
| **L11** | Secure Boot | `qemu_boot_test.py … --firmware uefi-secureboot` + efivars read | `SecureBoot=1` recorded **or** exact failure documented |
| **L12** | Visual/content | `scripts/ocr_gate.py artifacts/visual-<ver>` | no banned string outside the allow-list |
| **L13** | Doc/CLI drift | `scripts/gen_cli_docs.py --check`, `gen_packages_doc.py --check`, doc-command test | no drift |
| **L14** | Secrets/protected paths | `scripts/scan_credentials.py`, `scripts/protected_paths.py` | clean |

### 7.2 Cloud gates (GitHub Actions)

| ID | Job | Pass |
|---|---|---|
| **C0** | `ci` (rust, python/shell, qml, advisories, licences) | all jobs green on the pushed SHA |
| **C1** | `verify` (release parts) | digests match |
| **C2** | `bundle` (one-file ISO) | joined ISO hash equals manifest |
| **C3** | `attest` (provenance) | `gh attestation verify` succeeds |
| **C4** | `kvm-probe` | reports whether `/dev/kvm` exists; decides if C5 is possible |
| **C5** | `smoke` boot in CI | only if C4 allows; otherwise "not done" is printed |
| **C6** | HCSUDA CI (new) | `cargo test -p hcsuda-*` on ubuntu-latest + windows-latest, lavapipe/CPU fallback |
| **C7** | website build | static build + link check + axe/Lighthouse smoke |
| **C8** | release dry run | draft → digest verify → publish → cloud merge |

**Rule:** a red cloud gate blocks the merge exactly like a red local gate. A skipped job is reported
as "not run", never as green.

---

## 8. Self-healing loop (binding, unchanged in substance)

```
OBSERVE    run the gate; save stdout, exit code, timestamp, artefact path
CLASSIFY   code | test | harness | environment/capacity | upstream | flaky | missing feature | GATE BUG
HYPOTHESIS one falsifiable sentence + what would disprove it
EXPERIMENT cheapest discriminating experiment
           unit < hot-patch in live VM < layer image < dev image < release build
FIX        smallest patch at the root cause + a test that fails without it (revert-and-see-red)
VERIFY     targeted → subsystem → L0/L1 → real artefact (L6–L11) when the claim is about the image
RECORD     CLAIMS.md + BUILD_LOG.md + commit after an explicit exit-code check + push + PR
```

Limits: **3 attempts per distinct failure**, then `BLOCKED` with evidence and the next cheapest
experiment. Never weaken a test, skip a gate, lower a threshold, disable AppArmor/firewall/Secure
Boot/encryption/sandboxing, or retry a code defect blindly. A flaky result is repeated 3× before it is
called flaky. A **GATE BUG** is fixed before the product bug it hid and gets its own test.

**Ersatzwege (in order, record the choice):** reduce squash procs (3→2, `HSCL_SQUASH_MEM=384M`) and
`wsl --shutdown`; use the cached upstream ISO; 4 vCPU/4 GB VM profile; retry uploads per asset with
`--clobber`; downgrade the claim and make it an owner item.

**Delegation rule:** local subagents are hints. Anything a subagent says about the repo is confirmed
with `rg`/`git`/`pytest` before it lands in code, docs or a claim. `system-one-jev` is not a gate.

---

## 9. Push, PR and merge protocol (owner-authorized)

1. **Batch by gate, not by file.** Commit only after L0/L1 (and L2 for Rust, L4 for HCSUDA) are green.
2. **Push after every green batch** (`git push origin codex/hscl1-v1`). Never force-push, never
   rewrite published history.
3. **One PR open at a time** against `main`; refresh its body with the gate table of the batch.
4. **Merge when:** C0 green, the batch's gates green, `docs/BUILD_LOG.md` + `docs/CLAIMS.md` updated,
   and no new `KNOWN_LIMITATIONS` row contradicts the release notes.
5. **After merge:** fast-forward the working branch from `main`, re-run L0/L1, continue.
6. **Release tagging** only per AGENTS.md §17.3 (prerelease until §20 is green).
7. **README rule:** README is updated **only** in the same commit as the evidence that makes the
   statement true (version, hash, verified/unverified table). No README edit ahead of a gate.

---

## 10. Benchmark protocol (HCSUDA and the OS)

- Three runs minimum; report **median and spread**, never a single number.
- Every row records: device name, `deviceID`, driver name+version, Vulkan API version, dtype, shape,
  workgroup/tile, repetition count, wall time, GPU time (timestamps), bytes moved, GB/s or GFLOP/s.
- Baselines: CPU oracle (same machine), `llama-bench` where a comparable shape exists, and the
  previous HCSUDA release. A regression > 5 % fails the gate.
- Thermal/power state recorded once per session (power plan, battery/AC); an integrated GPU that
  shares DRAM with the CPU is labelled as such.
- Results are committed as small JSON under `hcsuda/benchmarks/<device-slug>/` and summarised in
  `docs/MEASURED.md` (generated, never hand-edited).

---

## 11. Time and token economy

- One image build per sprint; one VM batch per image; never build and VM at the same time.
- While WSL builds: host-only work (code, tests, docs). While a VM runs: do not build.
- Context reads capped (≤ 200 lines/call, ≤ 2 files before a plan); logs filtered (`-Last N`, `--json`).
- HCSUDA work is incremental and compiles in seconds; use it as the "cheap experiment" tier.
- The 2-minute reminder loop only triggers a **next action**, never a re-read.

---

## 12. Resume in five minutes (ledger)

| Track | State | Evidence | Next action |
|---|---|---|---|
| O1 push/land | **DONE for H0-H3c**, repeated per batch | PRs #22-#27 merged with merge commits, 14/14 CI checks each | open one PR per green batch |
| H0 scaffold | **TESTED** | `hcsuda-core` (dtype/fp8/quant/tensor/oracle/planner/report), 41 unit tests green | — |
| H1 dispatch | **HARDWARE-VERIFIED** | `caps.json`, `selftest.json` (PASS, det. yes), `bench-f32.json` on Radeon 680M | — |
| H2 fast math | **HARDWARE-VERIFIED** (2026-11-07) | tiled f32/f16/int8 GEMM, cooperative-matrix GEMM, softmax/norm/RoPE: `hcsuda/benchmarks/amd-radeon-680m/selftest.json`, `hcsuda/docs/MEASURED.md` | planner covers gemm/rope; int4 GEMM and multi-tile coopmat remain |
| H3 models | IN PROGRESS | GGUF reader + 7-type dequantisation TESTED (`hcsuda-io`); CPU transformer block and Qwen3-style layer TESTED vs NumPy; GPU block HARDWARE-VERIFIED vs CPU | stream real Qwen3 layers, final norm + tied head, compare logits with llama-server (see 2026-11-08 self-heal masterplan, H3c-3b) |
| O2 alpha gaps | PLANNED | KNOWN_LIMITATIONS rows | recovery key, /boot text, OCR, shortcuts |
| O3 hardening | PLANNED | — | measured report + SBOM |
| O4/O5 product/modes | PLANNED | — | welcome app, lab, privacy |
| O6/O7 rc/stable | PLANNED | — | Secure Boot, BIOS, fault injection, §20 |

---

## 13. Needs the owner (blocking only these)

1. HCSUDA licence (proposed: Apache-2.0 for the runtime so it can be linked widely; HSCL1 stays
   GPL-3.0-or-later). Until decided: in-repo, GPL-3.0-or-later, unpublished.
2. Create `timfromhcs/hcsuda` (public) — not done without an explicit yes.
3. Signing-key policy for releases.
4. Physical-hardware boot session (the 7735HS itself).
5. Trademark/legal review of the Ubuntu-derivative position and the GPL source offer.
6. Native-speaker review of DE/FR security/privacy strings.
7. Production website deployment.
8. Repository settings (immutable releases, secret scanning, branch rules).

Everything else in this plan runs without asking.

---

## 14. Definition of done for this masterplan

1. HCSUDA H0–H4 gates green with JSON evidence on this machine; H5 marked EXPERIMENTAL with a
   compatibility-suite result; H6 packaged into the OS and exercised in a VM; H7 metal numbers
   recorded or explicitly blocked.
2. HSCL1 §20 gates ticked or written as gaps; `v1.0.0` only then.
3. Every gate in §7 exists as a command with a test of the gate itself.
4. `main` contains the work, CI green, README/CLAIMS/KNOWN_LIMITATIONS match the artefact.
5. A fresh session can resume from §12 in under five minutes.
