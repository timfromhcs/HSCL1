# Auto LoRA/GGUF merge for the local subagents: feasibility (2026-11-07)

Owner request: an RSI loop feeds the local subagents and new GGUF/LoRA weights are merged automatically.

## What exists (checked on this machine)
- `rsi-capture` holds **27 verified sessions / 27 pairs / 164 events** (`rsi_stats`).
- `~/.config/opencode/rsi-autotrain-daemon.js` is running, but by its own header it "computes low-rank weight updates ... and merges them into the subagent weights representation **manifest**". It writes a JSON manifest; it does **not** produce a trained adapter or a GGUF.

## What the sources say (web, 2 searches, tutorial-grade sources, not papers; status PARTIAL)
- llama.cpp consumes LoRA, it does not train it: adapters are trained with PEFT in full precision/BF16, converted with `convert_lora_to_gguf.py`, applied with `--lora`/`--lora-scaled`, or folded into a base GGUF with `tools/export-lora`. No source covered Vulkan training or training on an already quantized or ternary (PQ2_0) GGUF. UNVERIFIED for our model.
- Few-shot LoRA is described as workable with tens to ~100 diverse examples but fragile; below ~8 it overfits; use rank 8, 1-3 epochs, a held-out validation set. Diversity matters as much as count.

## Consequences (decision, not yet built)
1. With 27 pairs, mostly from one repo and one kind of task, an automatic merge would be noise at best and a regression at worst. **No auto-merge now.**
2. A real pipeline needs: >= a few hundred verified, diverse pairs; a held-out set; training outside this PC (the Ternary-Bonsai base is not a PEFT-trainable fp16 model here; check whether an fp16/BF16 parent exists); `export-lora`; then **a gate**: the 10-task `tools/local_worker/bench.py` must be >= the current 10/10 at <= 10.6 s/task before the new weights replace the old ones, with the old GGUF kept for rollback.
3. Until then the daemon's manifest must not be described as a merged model anywhere in the docs.
