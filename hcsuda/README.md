# HCSUDA

Vulkan-first compute runtime for HSCL1. One API, every dtype the hardware can
actually execute, and a planner that refuses to run a path it has not verified.

**Made with love by hcsmedia.**

## What is real today

| Piece | State | Evidence |
|---|---|---|
| Capability probe (`caps`) | **TESTED** on AMD Radeon 680M | `benchmarks/amd-radeon-680m/caps.json` |
| Conservative planner | **TESTED** (unit tests, 41 total) | `crates/hcsuda-core/src/planner.rs` |
| CPU oracle (elementwise, GEMV, GEMM, i8 GEMM, softmax, norms, GELU, SiLU) | **TESTED** | `crates/hcsuda-core/src/reference.rs` |
| FP8 E4M3/E5M2 codec (RNE + saturation) | **TESTED** | `crates/hcsuda-core/src/fp8.rs` |
| int8 / packed-int4 quantisation | **TESTED** | `crates/hcsuda-core/src/quant.rs` |
| Vulkan device, memory, dispatch, timestamps | **TESTED** on hardware | `crates/hcsuda-vk` |
| GPU kernels `saxpy`, `triad`, `gemv` (f32) | **HARDWARE-VERIFIED** vs oracle | `benchmarks/amd-radeon-680m/selftest.json` |
| Tiled f32 GEMM (16x16, shared memory) | **HARDWARE-VERIFIED** vs oracle, benchmarked on the 680M | `docs/MEASURED.md` (H2) |
| Softmax, LayerNorm, RMSNorm (f32) | **HARDWARE-VERIFIED** vs oracle; GPU not faster than CPU in wall time at 32x4096 | `docs/MEASURED.md` (H2) |
| Cooperative-matrix GEMM, int8 dot GEMM, f16 kernels | `PLANNED` (H2, next) | — |
| GGUF / ONNX IO | `PLANNED` (H3) | — |
| CUDA driver shim (`nvcuda`) | `PLANNED`, `EXPERIMENTAL` when it lands (H5) | — |

Nothing above is claimed beyond what the linked evidence shows.

## Build

```bash
# Vulkan SDK provides glslc; without it the build still succeeds and GPU
# pipelines are reported as unavailable instead of silently faking them.
cd hcsuda
cargo build --release
cargo test
```

## Use

```bash
cargo run -p hcsuda-cli -- caps                  # device truth, human readable
cargo run -p hcsuda-cli -- caps --json --out benchmarks/<device>/caps.json
cargo run -p hcsuda-cli -- plan gemm f16 --m 4096 --n 4096 --k 4096
cargo run -p hcsuda-cli -- selftest              # GPU vs CPU oracle, 3 runs each
cargo run -p hcsuda-cli -- bench --runs 7 --out benchmarks/<device>/bench-f32.json
```

Every command has `--json`. A benchmark row carries device, driver, dtype,
shape, path, sample count, median, min/max, spread and (when the queue supports
timestamps) the GPU-side median.

## The rules this code follows

1. **Oracle first.** A GPU kernel ships only with a CPU reference and a
   differential test with a declared tolerance per dtype.
2. **Conservative planner.** For (op, dtype, shape, device) it returns the
   fastest *verified* path. Unknown means CPU. Promotion needs correctness,
   determinism (3 identical runs) and ≥1.05× the current best, recorded in
   `benchmarks/`.
3. **No invented numbers.** Every reported figure names its device and driver.
   FP8 on RDNA2 is storage + conversion, never "native FP8 arithmetic".
4. **No hidden privileges.** HCSUDA is a compute runtime, not a root agent.

## Where it is going

See `docs/CAPABILITY_MATRIX.md` for the CUDA capability contract and
`docs/MEASURED.md` for the numbers this hardware actually produced.

Licence: GPL-3.0-or-later while HCSUDA lives inside the HSCL1 repository. A
separate licence for a standalone HCSUDA release is an owner decision.
