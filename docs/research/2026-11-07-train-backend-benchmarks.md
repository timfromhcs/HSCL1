# LoRA training backends on the Ryzen 7 7735HS / Radeon 680M - raw results (2026-11-07)

Machine: Ryzen 7 7735HS (8C/16T), Radeon 680M (`uma: 1`, AMD proprietary driver 26.6.1, Vulkan API 1.4.315, no cooperative-matrix path used), 24 GB RAM, Windows 11.
Model: Qwen3-4B-Instruct-2507. Host hold set during each run (`tools/hcs_hold.py`), gateway and servers stopped.

| # | Backend | Base format | Setup | Result |
|---|---|---|---|---|
| 1 | HCSUDA CPU slice (C++ AVX2 Q4 decode + torch BLAS, own LoRA wrapper) | Q4 offset codec, group 128, FP32 metadata | r=16 on 7 linear layers, 33.0 M trainable, seq 512, grad checkpointing, 36 layers | **57.6 s/step** (3 steps: 57.58 / 56.47 / 57.58), RSS 6.1 GB, one-time quantization 48 s |
| 2 | QVAC Fabric `llama-finetune-lora` (Vulkan) | GGUF **Q4_K_M** | r=16 all 7 modules, c/b/ub 512, `-fa off`, High priority | 2 of 21 steps after 4:17 min, ETA 40:46, identical in two runs (~2 min/step); GPU engines <1 % utilisation; CPU time 2057 s in ~5 min; RSS 10.4 GB, 9.3 GB shared / ~0 dedicated GPU memory; free RAM 1.8 GB |
| 3 | same, 4.2 KB text (2 datapoints, 1 step) | Q4_K_M | same flags | train + validation + save in 2.6 s (loss 4.07517, same as the first step of run 2) |
| 4 | same, 10 KB text (9 datapoints, 8 steps) | Q4_K_M | same flags | no result after >2 min, stopped by the owner's request |

Isolated kernels (HCSUDA, same machine): multi-threaded AVX2 Q4 decode 3.8-4.2 G weights/s; decode + BLAS matmul 7-10 % slower than dense fp32 matmul for a 512 x 2560 x 9728 layer; hand-written fused Q4 GEMM 40-60 GFLOP/s against 260-360 GFLOP/s dense BLAS. `llama-bench` prefill of Qwen3-4B Q4_K_M on the GPU: 280 t/s (about 2.2 TFLOP/s effective), generation 26.8 t/s.

## Cause found for rows 2-4 (source reading, not yet confirmed by a fast run)
`ggml-vulkan.cpp` (`supports_op`, `GGML_OP_OUT_PROD`): the Vulkan backend supports the output product, which the LoRA backward pass needs for every linear layer, only for source types **F32, F16, Q4_0, Q8_0 and TQ2_0**. A **Q4_K_M** model (K-quants) is therefore executed on the CPU for the backward pass: GPU idle, CPU busy, extra host memory. The fix to test is a **Q4_0** (or Q8_0) GGUF of the same model; Q4_0 file downloaded for that test.
