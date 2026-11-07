# APU offload, VRAM limits and the SSD question (research, 2026-11-07)

Owner request: better GPU offload, more system RAM usable as VRAM, CPU compute alongside the GPU, an SSD-backed
"VRAM backup", and a second fast model used as an offload. Every statement below was checked against primary sources
(Linux and llama.cpp sources, upstream issues/docs). WebSearch was unavailable in that session, so GitHub API and raw
source were read instead; anything that is not primary is labelled as such. **Nothing here is a measurement on our own
machine** - the numbers section says what to measure and with what.

## 1. More memory for the GPU on an APU: `ttm.pages_limit`, not `gttsize`

- The GTT (system RAM the GPU may map) is sized from `ttm_tt_pages_limit()`; `ttm_pages_limit` **defaults to half of
  total system RAM** (`drivers/gpu/drm/ttm/ttm_device.c`). On 24 GB that is ~12 GiB - so "more RAM to VRAM" means
  raising this, not hunting for a driver setting.
- `amdgpu.gttsize` is **deprecated**: `amdgpu_ttm.c` warns "Configuring gttsize via module parameter is deprecated,
  please use ttm.pages_limit", and on APUs GTT is additionally capped at total physical RAM.
- Set it on the **kernel command line** (`ttm.pages_limit=<pages>`, e.g. `4718592` = 18 GiB) or in
  `/etc/modprobe.d/`; it is read once when TTM initialises a heap. The sysfs node exists but does not resize a live
  heap. `ttm.page_pool_size` is a *pool size*, not a cap, and buys nothing.
- Caveats: exceeding the limit leads to eviction/`ENOMEM`, not graceful growth; RADV can return "Not enough memory for
  command submission" and the device can be lost (llama.cpp #27360). On a single 24 GB pool, keep ≥ 4 GB headroom for
  the Plasma compositor before telling the model it may use the rest.

## 2. Partial offload: the flags changed, and our profile text is stale

Confirmed in `common/arg.cpp` and `tools/server/README.md`:

| Purpose | Flag |
|---|---|
| layers on GPU | `-ngl/--n-gpu-layers N|auto|all` |
| per-tensor placement | `-ot/--override-tensor PATTERN=BUFT` |
| split across GPUs | `-ts/--tensor-split`, `-mg/--main-gpu` |
| **KV cache stays in host RAM** | `-nkvo/--no-kv-offload` (default: KV *is* offloaded) |
| KV precision | `-ctk/-ctv` = `f32,f16,bf16,q8_0,q4_0,q4_1,iq4_nl,q5_0,q5_1` |
| experts on CPU | `-cmoe/--cpu-moe`, `-ncmoe/--n-cpu-moe N` |
| flash attention | `-fa/--flash-attn [on|off|auto]` |
| **load mode (replaces mmap/mlock)** | `-lm/--load-mode auto|none|mmap|mlock|mmap+mlock|dio` |
| auto-fit unset args | `-fit/--fit` |
| lazy streaming of huge CPU tensors | `-lzm/--lazy-mode` |

Two things matter for us: **`--mmap`, `--no-mmap` and `--mlock` no longer exist** (replaced by `--load-mode`), and
`--load-mode auto` deliberately disables mmap on Vulkan iGPUs (PR #26081). `-nkvo` is exactly the "weights on GPU, KV in
system RAM" mode - `llama-kv-cache.cpp` picks the CPU buffer type for the cache when the flag is off.

## 3. A second fast model as "offload" = speculative decoding

Current names: `-md/--spec-draft-model`, `--spec-type` (`none|draft-simple|draft-eagle3|draft-dflash|draft-dspark|draft-mtp|ngram-*`),
`--spec-draft-n-max` (default 3), `--spec-draft-n-min`, `--spec-draft-p-min`, `--spec-draft-ngl`, `--spec-default`.
`--draft-max`/`--draft-min` are **removed** and error out with a pointer to the new names. Constraints: the draft model
must share the tokenizer; specialised draft checkpoints are target-specific; a second model costs its own weights and
KV. Acceptance is printed as "draft acceptance rate". **No primary speedup figures for iGPUs were found** - upstream
documents the mechanism, not the gain.

## 4. SSD as "VRAM backup": not supported, and should not be claimed

There is **no supported mechanism** to put Vulkan weights or the KV cache on NVMe. The Vulkan backend allocates its own
device memory and copies into it (`ggml-vulkan-buffers.cpp`); `mmap` only concerns host-side CPU tensors. What does
involve disk:

- the OS page cache and swap (ordinary kernel behaviour),
- TTM `ttm_tt_swapout` when GTT is over its limit - eviction/thrashing, not an extension,
- `--load-mode dio` (bypass page cache),
- `--lazy-mode`, which streams certain very large CPU-resident tensors from disk - never VRAM.

CUDA has `GGML_CUDA_ENABLE_UNIFIED_MEMORY`; the Vulkan backend has no equivalent. So an "SSD-backed VRAM" feature would
be a new implementation, and any product text claiming it today would be false.

## 5. Vulkan on a UMA APU: GTT is the ceiling, with two known iGPU defects

The Vulkan backend detects integrated devices as `uma` and prefers `DEVICE_LOCAL|HOST_VISIBLE|HOST_COHERENT` allocations,
i.e. GTT-backed system RAM - the limit is `ttm.pages_limit`, not the BIOS carve-out. Env knobs found in
`ggml-vulkan.cpp`: `GGML_VK_VISIBLE_DEVICES`, `GGML_VK_PREFER_HOST_MEMORY`, `GGML_VK_DISABLE_HOST_VISIBLE_VIDMEM`,
`GGML_VK_ALLOW_SYSMEM_FALLBACK`, `GGML_VK_FORCE_MAX_ALLOCATION_SIZE`, `GGML_VK_FORCE_MAX_BUFFER_SIZE`,
`GGML_VK_DISABLE_INTEGER_DOT_PRODUCT`, `GGML_VK_DISABLE_COOPMAT[2]`, `GGML_VK_MEMORY_LOGGER`, `GGML_VK_PERF_LOGGER`.

Two iGPU reports on the same 7735HS/680M class (user reports, not our measurement):
- all-NaN logits on Mesa 26.1.4/RADV, fixed by `GGML_VK_DISABLE_INTEGER_DOT_PRODUCT=1` (llama.cpp #31509);
- `--load-mode auto` causing a device-lost/OOM on a 14 GB model where `--load-mode mmap` worked (#27360).

## 6. What the numbers are, and what they are not

| Case | Value | Source quality |
|---|---|---|
| 680M, Gemma-4-E4B Q5_K_S, full offload, Vulkan | ~20.9 t/s generation, 232-262 t/s prompt | upstream issue #31509, same CPU |
| 780M, Llama-2-7B Q4_0, `-ngl 100` | pp512 245.8 t/s, tg128 20.1 t/s | upstream discussion #10879 |
| 7-9B Q4_K_M on 680M/DDR5-4800 | **≈8-16 t/s gen, ≈120-200 t/s pp** | our extrapolation - MEASURE |
| same model, CPU-only AVX2, 8C/16T | **≈4-6 t/s gen, ≈30-50 t/s pp** | our extrapolation - MEASURE |

No credible published 7735HS CPU-only 7-9B figure was located. Any number shown in the product must come from
`llama-bench` on the user's machine.

## Consequences for HSCL1 (tracked in `docs/superpowers/plans/2026-11-06-own-gpu-backend.md`)

1. **`hscl ai tune-memory`** (new): print the current GTT/VRAM numbers, compute a suggested `ttm.pages_limit` with a
   fixed ≥4 GB desktop reserve, show the exact cmdline/modprobe line, require an explicit confirmation to write it, and
   state that it takes effect after a reboot. Never write it silently.
2. **Profile flags**: replace any `--mmap/--mlock` in our docs/profiles with `--load-mode`, add `-nkvo` and
   `-ctk/-ctv q8_0` as *options* with their trade-off, and offer `--spec-draft-model` only with the measured
   acceptance rate. Everything gated on the pinned build actually accepting the flags (MEASURE).
3. **Do not sell SSD-VRAM.** `docs/KNOWN_LIMITATIONS.md` now says plainly that llama.cpp has no SSD-backed VRAM or KV
   spill, and that the only disk involvement is the page cache/swap.
4. **iGPU workarounds** are recorded as opt-in environment settings with their bug references, not as defaults.
5. **Measure first**: `llama-bench` on this machine for the CPU and Vulkan paths before any t/s claim reaches the UI.
