# HCSUDA capability matrix

The contract: every CUDA capability *class* has a HCSUDA target, a status and an
evidence path. A class is never "done" because code exists — only when the gate
named here is green.

Status vocabulary: `PLANNED`, `IMPLEMENTED`, `TESTED`, `HARDWARE-VERIFIED`,
`EXPERIMENTAL`, `BLOCKED`.

| # | Class | CUDA surface | HCSUDA target | Status | Gate / evidence |
|---|---|---|---|---|---|
| 1 | Device / context | `cuInit`, `cuCtx*` | `Device`, capability record | **TESTED** (hardware) | `caps --json` |
| 2 | Streams / events | `cuStream*`, `cuEvent*` | synchronous dispatch now, streams in H2 | `IMPLEMENTED` (sync only) | `dispatch.rs` |
| 3 | Memory | `cuMemAlloc`, `cuMemcpy*` | device-local + host-visible pools, budget-aware | **TESTED** (integrated) | `buffer.rs`, `caps.json` heaps |
| 4 | Unified memory | `cuMemAdvise`, managed | planned: single pool on APU, explicit staging on dGPU | `PLANNED` | — |
| 5 | Kernels | PTX/SASS, `cuLaunchKernel` | SPIR-V from GLSL via `glslc` | **HARDWARE-VERIFIED** (3 kernels) | `selftest.json` |
| 6 | PTX translation | driver JIT | PTX subset → SPIR-V | `PLANNED` (H5, `EXPERIMENTAL`) | — |
| 7 | f32 | native | native | **HARDWARE-VERIFIED** | `bench-f32.json` |
| 8 | f16 | native | native (`shaderFloat16` + 16-bit storage) | f16-storage tiled GEMM and cooperative-matrix GEMM **HARDWARE-VERIFIED** (coopmat only for m, n, k divisible by 16) | `selftest.json`, `docs/MEASURED.md` |
| 9 | bf16 | native | storage native, compute widened to f32 | `IMPLEMENTED` (path); GPU kernel `PLANNED`; CPU dequantisation from GGUF **TESTED** | `caps.json` dtypes, `crates/hcsuda-io` |
| 10 | tf32 | tensor cores | f32 with truncated mantissa | `PLANNED` (H2) | — |
| 11 | f64 | native (slow) | native (`shaderFloat64`) | `IMPLEMENTED` (path), no kernel | `caps.json` dtypes |
| 12 | FP8 E4M3/E5M2 | native on Hopper+ | **storage + conversion** (no FP8 ALU on RDNA2) | `IMPLEMENTED` (codec, **TESTED**) | `fp8.rs` tests |
| 13 | int8 | native DP4A | accelerated 8-bit dot product | tiled int8 dot GEMM **HARDWARE-VERIFIED** (bit-equal to oracle; faster than tiled f32 in the same run, the untiled kernel was slower) | `selftest.json`, `docs/MEASURED.md` |
| 14 | int4 | native | packed 4×8-bit dot product | `IMPLEMENTED` (quant + path), GEMM `PLANNED` | `quant.rs` tests |
| 15 | BLAS | cuBLAS | GEMV/GEMM per dtype | GEMV f32, GEMM f32/f16/int8/coopmat **HARDWARE-VERIFIED** on one iGPU; no comparison with cuBLAS/rocBLAS | `selftest.json`, `bench-gemm-i8.json` |
| 16 | DNN | cuDNN | conv2d, pooling, norm, softmax, attention | softmax/layernorm/rmsnorm/RoPE and a causal attention kernel (at most 256 tokens) **HARDWARE-VERIFIED**; conv2d and pooling `PLANNED` | `selftest.json`, `reference.rs` |
| 17 | FFT | cuFFT | out of v1 scope | `BLOCKED` (declared gap) | — |
| 18 | Sparse | cuSPARSE | SpMV/SpMM | `PLANNED` (post-v1) | — |
| 19 | Random | cuRAND | Philox/PCG on device | `PLANNED` (H4) | — |
| 20 | Graphs | CUDA Graphs | recorded dispatch lists | `PLANNED` (H2) | — |
| 21 | Training | cuBLAS + custom | backward ops, AdamW, LoRA merge | `PLANNED` (H4) | — |
| 22 | Model IO | (none) | GGUF read/write/quantise/edit, ONNX subset, safetensors | GGUF read and dequantisation (7 types) **TESTED**; write, edit, ONNX, safetensors `PLANNED` | `crates/hcsuda-io`, `docs/BUILD_LOG.md` |
| 23 | Tooling | nvcc, Nsight | `hcsuda` CLI with JSON + GPU timestamps | **TESTED** | this repo |
| 24 | CUDA binary compat | — | `nvcuda.dll` / `libcuda.so.1` subset | `PLANNED` (H5, `EXPERIMENTAL`) | — |

## Explicit non-claims

- Bit-identical results to CUDA. Different reduction order, different rounding.
- Arbitrary CUDA binaries running in v1.
- Full Vulkan ICD conformance. HCSUDA is a compute consumer plus (later) a
  Vulkan layer plus a CUDA shim — not a graphics driver replacing Mesa/AMDVLK.
- FP8 *arithmetic* on RDNA2.
- Any throughput number not present in `docs/MEASURED.md` with its JSON.

## Promotion rule

A path is promoted from `PLANNED` to `HARDWARE-VERIFIED` only when, on a named
device: the differential test passes within tolerance, three consecutive runs are
identical, and the median is at least 1.05× the current best verified path. The
promotion writes a row into `benchmarks/<device>/` and a line here.
