# HCSUDA — measured results

All numbers below were produced on the machine described here, by the commands
shown, with the JSON evidence committed next to this file. Anything not listed
here has not been measured.

## Device (probe output, not marketing)

| Field | Value |
|---|---|
| Device | AMD Radeon(TM) Graphics (integrated, Rembrandt) |
| Vendor / device ID | `0x1002` / `0x1681` |
| Driver | AMD proprietary driver 26.6.1 (AMD proprietary shader compiler) |
| Vulkan API | 1.4.315 (instance 1.4.357) |
| Subgroup size | 64 |
| Max invocations / workgroup | 1024 |
| Max shared memory | 32 KiB |
| Storage buffer range | 4 GiB |
| Timestamp period | 10 ns |
| Heaps | 9.10 GiB device-local, 4.55 GiB host-visible, 0.25 GiB device-local + host-visible |
| Accelerated dot products | 8-bit signed/unsigned, 4×8-bit packed signed/unsigned, 16-bit |
| `VK_KHR_cooperative_matrix` | present |
| `VK_EXT_shader_float8` | **absent** — FP8 is storage + conversion here |

Evidence: `benchmarks/amd-radeon-680m/caps.json`.

## Differential test (GPU vs CPU oracle)

Command: `cargo run -p hcsuda-cli -- selftest --out benchmarks/amd-radeon-680m/selftest.json`

| Op | Path | Max error | Tolerance | Deterministic |
|---|---|---|---|---|
| saxpy | `vulkan_scalar` | 2.384e-7 | 7.400e-5 | yes |
| triad | `vulkan_scalar` | 2.384e-7 | 7.400e-5 | yes |
| gemv | `vulkan_scalar` | 1.907e-6 | 3.263e-5 | yes |

Tolerance is `rel 1e-5 + abs 1e-6·√len`, i.e. f32-appropriate, not bit-exact.

## Benchmark, f32, 2026-11-07

Command: `cargo run -p hcsuda-cli -- bench --runs 7 --out benchmarks/amd-radeon-680m/bench-f32.json`

Method: one warm-up dispatch, then 7 samples, each the mean of **50**
dispatches. `gpu_ms` is the median of the timestamp-query measurements.

| Op | Shape | Path | gpu_ms (spread) | GFLOP/s | GB/s | CPU oracle ms |
|---|---|---|---|---|---|---|
| saxpy | 4 Mi f32 | `vulkan_scalar` | 0.762 (0.07) | 9.49 | 56.95 | 28.70 |
| triad | 4 Mi f32 | `vulkan_scalar` | 0.725 (0.02) | 9.96 | 79.69 | 49.75 |
| gemv | 512×8192 | `vulkan_scalar` | 1.303 (0.19) | 5.89 | 11.81 | 68.30 |

Interpretation, with the caveats attached:

- saxpy and triad are **bandwidth-bound** on this shared-memory integrated GPU:
  57–80 GB/s of the ~9 GiB device-local pool. That is the realistic ceiling for
  an APU whose GPU and CPU share DDR5, not a compute ceiling.
- gemv is a **correctness-first** kernel: one invocation per row with a
  sequential inner reduction, chosen so the reduction order matches the oracle
  and the differential test is meaningful. It is *not* an optimised GEMM and its
  5.9 GFLOP/s must not be quoted as HCSUDA's matrix throughput. Tiled and
  cooperative-matrix variants are H2 and will get their own rows.
- The CPU oracle is single-threaded by design (deterministic reference), so the
  ratios above (≈13–38×) say nothing about GPU versus a tuned multi-threaded
  BLAS.

## Measurement finding: the iGPU clock ramp

Short bursts measure the clock ramp, not the kernel. Same command, only the
dispatch count per sample changed:

| Reps per sample | saxpy GPU spread | triad GPU spread |
|---|---|---|
| 5 | 0.87 | 1.15 |
| 50 | 0.07 | 0.02 |

Consequence, now encoded in the tool: `--reps` defaults to 50, and a benchmark
row with a GPU spread above 0.25 is called noisy rather than reported as a
result.

## H2: tiled GEMM and row-wise ops (2026-11-07)

New kernels `gemm_tiled` (16x16 tiles, shared memory), `softmax`, `layernorm`,
`rmsnorm` (one 256-lane workgroup per row, tree reduction). All f32. Differential
test against the CPU oracle, 3 runs each, determinism checked:

| op | shape (selftest) | max error | tolerance | deterministic |
|---|---|---|---|---|
| gemm | 67x131x95 (not multiples of 16, exercises edge masking) | 2.4e-7 | 2.1e-5 | yes |
| softmax | 8x1024 | 3.3e-9 | 4.2e-5 | yes |
| layernorm | 8x1024 | 2.9e-6 | 4.2e-5 | yes |
| rmsnorm | 8x1024 | 4.8e-7 | 4.2e-5 | yes |

Benchmark (`--runs 15 --warmup-s 3`, release build, `bench-f32.json`):

| op | shape | GPU ms (spread) | wall median ms | oracle ms | note |
|---|---|---|---|---|---|
| gemm | 256x1024x256 | 0.291 (0.21) | 0.416 | 114.6 | 134.2 MFLOP: 461 GFLOP/s kernel-side, 323 GFLOP/s wall |
| softmax | 32x4096 | 0.015 (0.12) | 0.105 | 0.373 | wall dominated by submit latency |
| layernorm | 32x4096 | 0.017 (0.05) | 0.105 | 0.231 | same |
| rmsnorm | 32x4096 | 0.013 (**0.37**) | 0.102 | 0.109 | **noisy, not a result** |

What this does and does not say:

- Tiled GEMM is about 70x faster than the single-threaded oracle and ~55x faster
  than the H1 `gemv` in GFLOP/s. Against a tuned multi-threaded CPU BLAS or the
  680M's roughly 3-4 TFLOP/s f32 peak (estimate from CU count and clock, not
  measured) this is a modest fraction; no optimisation beyond the 16x16 tile has
  been tried.
- The row-wise kernels run in 13-17 us on the GPU, but a single 512 KiB dispatch
  costs about 100 us wall including submit and fence. At this size the GPU path
  is **not** faster than the CPU in wall time (rmsnorm: 0.102 vs 0.109 ms, i.e.
  equal). They only pay off fused or batched into a larger graph, which H2 does
  not do yet.
- The oracle numbers in this table come from a release build and are not
  comparable with the H1 table (debug build, saxpy 28.7 ms there, 4.6 ms here).
  Compare GPU against oracle only within one table.

Bugs found while building this (test and glue, not shader defects):

- `softmax` push block is 8 bytes `{cols, rows}`; the runner first sent the
  12-byte norm block and the kernel guard refused it ("expects 8 push-constant
  bytes, got 12").
- The CPU reference `softmax` works on one row; the selftest and the bench
  baseline passed the whole matrix as one row, giving a 6e-3 "error" and an
  unfair CPU baseline. Both now go row by row.
- GEMM spread was 0.61 without a warm-up and 0.21 with `--warmup-s 3`.

## Not measured (do not infer it)

- No f16, bf16, int8, int4 or FP8 kernel has been run yet — only f32.
- No conv, attention or training step has been executed on the GPU (GEMM and row-wise ops: see H2 above, f32 only).
- No comparison against `llama-bench`, rocBLAS, hipBLASLt or a CUDA baseline.
- No discrete GPU, and no Linux measurement yet.
- No power or thermal instrumentation; the machine ran on its normal power plan.

Each of those becomes a row here only after the corresponding gate passes.

## int8 dot-product GEMM versus tiled f32 (2026-11-07, Radeon 680M, driver 26.6.1)
`hcsuda bench --suite gemm,gemm_i8dot --runs 15 --warmup-s 3`, 256x1024x256, release build, no VM or model running; JSON in `benchmarks/amd-radeon-680m/bench-gemm-i8.json`.

| op | path | GPU ms | GFLOP/s (wall) |
|---|---|---|---|
| gemm f32 | vulkan_tiled | 0.382 (spread 0.00) | 274 |
| gemm i8 | vulkan_i8dot (untiled) | 0.814 (spread 0.00) | 144 |

Finding: the first correct int8 kernel is **2.1x slower** than the tiled f32 kernel. It reads A and B words straight from global memory (no shared-memory tiling), so it is memory-bound, not compute-bound; the accelerated 4x8 dot unit is not the limit. This is not evidence against the int8 path, only against this kernel. Hypothesis to test next: a 16x16 shared-memory tile over packed words (4x fewer bytes per MAC than f32). Promotion rule: the planner may select int8 only after it beats f32 by >= 1.05x here.

### Follow-up: shared-memory tiling of the int8 kernel (same day, same shape and settings)
Hypothesis confirmed. `gemm_i8dot_tiled` (16x16 tile, 16 packed words per k step) in one run next to the f32 kernel:

| op | path | GPU ms | GFLOP/s (wall) |
|---|---|---|---|
| gemm f32 | vulkan_tiled | 0.269 (spread 0.01) | 350 |
| gemm i8 | vulkan_i8dot (untiled) | 0.816 (0.01) | 144 |
| gemm i8 | vulkan_i8dot_tiled | **0.195** (0.00) | **464** |

Same-run ratio int8 tiled / f32 tiled = 0.269 / 0.195 = **1.38x faster** on GPU time (1.33x on wall time), above the 1.05x promotion rule; the untiled kernel is 4.2x slower than the tiled one. Caveat: the f32 kernel itself measured 0.382 ms in the earlier run and 0.269 ms here (iGPU clock state), so only same-run ratios are quoted. Correctness: bit-equal to the oracle on 48x128x40 and on a tail shape 37x132x29. Not measured: other shapes, int4, accuracy cost of quantising real model weights (this is a kernel speed, not a model-quality claim).

## f16-storage GEMM (f32 math) versus f32 tiled (2026-11-07, Radeon 680M)
`gemm_f16_tiled`: A and B stored as packed halves (`unpackHalf2x16`), widened to f32 in the shared tile, so half the input bytes and identical arithmetic. Correct on the odd shape 37x65x29 (max error 0, same accumulation order as the oracle, which sees f16-rounded inputs). 256x1024x256, 15 runs, 3 s warm-up, four suite runs in different orders:

| kernel | GPU ms over runs |
|---|---|
| f16 storage, tiled | 0.257, 0.257, 0.257, 0.257 (spread <= 0.01 in three runs, 0.16 in one) |
| f32 tiled | 0.269, 0.295, 0.382, 0.383 |

Finding: the f32 kernel is **bimodal run to run (0.27-0.38 ms) regardless of suite order**, so the order hypothesis (first row at a low clock) is refuted; the cause is not identified (candidate: buffer placement or cache state; untested). The f16 kernel is stable. Best-case f32 vs f16 is 0.269 / 0.257 = 1.05x, i.e. no speed claim beyond "not slower, half the input memory". Not measured: cooperative-matrix f16 GEMM (the planner still prefers it for f16 only after it is verified), bf16, larger shapes.

## Cooperative-matrix GEMM (2026-11-07, Radeon 680M, driver 26.6.1)
`hcsuda coopmat` (new) lists what the driver reports: 11 shapes, all 16x16x16 at subgroup scope, including f16 x f16 -> f32 and int8 -> i32 (evidence: `benchmarks/amd-radeon-680m/coopmat-shapes.json`). `gemm_coopmat.comp` uses the f16xf16->f32 one: one 64-invocation subgroup per 16x16 output tile, `coopMatMulAdd` over k in steps of 16, reading the same packed-half buffers as the f16 tiled kernel. It requires m, n, k divisible by 16; the host refuses other shapes and the planner only selects it for them.
Correctness: selftest 48x80x64, max error 2.4e-7 (tolerance 1.9e-5), deterministic. Speed, 256x1024x256, 15 runs, two full suite runs, GPU timestamps:

| kernel | GPU ms (run 1 / run 2) |
|---|---|
| gemm coopmat f16->f32 | **0.167 / 0.168** |
| gemm f16 storage tiled | 0.257 / 0.257 |
| gemm f32 tiled | 0.269 / 0.282 (bimodal, see above) |
| gemm i8 dot untiled | 0.776 / 0.812 |
| gemm i8 dot tiled | 0.195 / 0.194 |

Coopmat is 1.53x faster than f16 tiled and 1.17x faster than int8 tiled on GPU time, consistently over both runs; that is about 0.45 TFLOP/s on wall time and 0.8 TFLOP/s on GPU time. No peak figure was measured, so no efficiency is claimed. This is a first kernel without register blocking or multi-tile subgroups. Wall time shows a smaller gap (0.30-0.35 ms) because submit and fence overhead is a floor at this size. Not measured: larger shapes, int8 coopmat, bf16, multi-tile blocking.
