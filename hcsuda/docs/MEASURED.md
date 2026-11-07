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

## Not measured (do not infer it)

- No f16, bf16, int8, int4 or FP8 kernel has been run yet — only f32.
- No GEMM, conv, attention or training step has been executed on the GPU.
- No comparison against `llama-bench`, rocBLAS, hipBLASLt or a CUDA baseline.
- No discrete GPU, and no Linux measurement yet.
- No power or thermal instrumentation; the machine ran on its normal power plan.

Each of those becomes a row here only after the corresponding gate passes.
