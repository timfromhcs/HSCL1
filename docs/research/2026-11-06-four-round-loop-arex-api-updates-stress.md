# Research: four-round loop - AREX-2 harness, abliterated models, AI API, updates/freeze, stress tests (2026-11-06)

Owner request: AREX-2 (the self-learning model from China "with the harness in the model"), more for custom software and a better Linux, abliterated models, a better AI API, better updates from an image freeze, better stress tests. Four rounds; each round's questions came from the previous round's gaps. Part 1 (AREX-2 identity, autodetect, RE) is in `2026-11-06-arex2-autodetect-reverse-engineering.md`.
Status: ANSWERED (source read), PARTIAL (gap named), UNKNOWN -> MEASURE (only our image/machine can answer).

## Loop 1
| Question | Finding | Status |
|---|---|---|
| How is the harness "in the model"? | AREX-Turbo/-2 are trained to emit an **XML tool-call protocol** (`<tool_call>` ... `<tool_response>`) with tools `search`, `google_scholar`, `visit`, `update_context`, `finish`; tool descriptions are in the system prompt; the **caller** executes tools and feeds results back until `finish`. `update_context` lets the model rewrite its working state (verified findings, rejected candidates, open constraints, next plan). Inner loop = research, outer loop = check the provisional answer, then accept / refine / restart. | ANSWERED |
| Abliteration: method and cost? | Arditi et al. 2024: refusal is one direction in the residual stream; orthogonalise it out. Tools differ (Heretic: lowest KL, 30-110 min per model); capability change per benchmark from a small gain to -18.8 points; the "harmless" baseline set matters. | ANSWERED |
| Image-based updates on Ubuntu? | bootc for Ubuntu 26.04 is an *experimental community* effort; official bootc bases are Fedora/CentOS/RHEL and mostly headless; A/B designs depend on upstream tooling (KDE Linux shipped a systemd 260 regression in March 2026 that left some systems unbootable). | PARTIAL |
| Stress tools? | `stress-ng`: stressors, kernel-log watching, fault injection (root + debugfs); "can overheat poor hardware". | PARTIAL |

Sources: <https://huggingface.co/BAAI/AREX-Turbo/blob/main/inference/README.md>, <https://arxiv.org/html/2512.13655v2>, <https://discourse.ubuntu.com/t/bootc-use-your-container-knowledge-and-infrastructure-to-build-and-deploy-your-ubuntu-hosts/79498>, <https://manpages.ubuntu.com/manpages/resolute/man1/stress-ng.1.html>.

## Loop 2
| Question | Finding | Status |
|---|---|---|
| llama-server features (official `tools/server/README.md`) | `--api-key` (comma list, env `LLAMA_API_KEY`), `--metrics` (Prometheus, **off** by default), `--slots` (on by default), `GET /health` public, OpenAI Chat + **`/v1/responses`** + `/v1/embeddings`, **Anthropic Messages API** (tool use needs `--jinja`), function calling with `--jinja`, **router mode** (start without a model; `--models-dir`, `--models-max` default 4, `--models-memory-margin N` MiB LRU unload), slot save/restore, **MCP servers over stdio** via `--mcp-servers-config`. `--host` default `127.0.0.1`. | ANSWERED |
| Does an abliterated AREX-2 keep the agent skill? | Card of BoldingBuilds/AREX-2-Abliterated-GGUF (Apache-2.0, Q4_K_M 16.5 GB): refusals 144/150 -> 6/150; tool use when a tool fits unchanged (548 vs 545); **calls a tool although none fits: 142 vs 95** (p<0.0001); KL vs stock 0.016 chat, 0.009 agent traces, 0.130 harmful text. Code/maths/instruction-following not measured. One author, RTX 3090. | ANSWERED (single source) |
| Ubuntu image-based plans | none beyond the community effort; Canonical's direction is "standard Ubuntu + apt". | PARTIAL |
| GUI/installer testing standard | openQA (QEMU + VNC + PNG needles) is the established approach; no Kubuntu suite found. Our own deterministic harness stays; openQA is reference only. | ANSWERED |
| Desktop memory behaviour | `systemd-oomd` uses kernel PSI and kills cgroups (apps need own cgroups); `earlyoom` polls; Fedora example: kill at 50 % pressure for 20 s; zram is a buffer next to swap. No authoritative 24 GB figures. | PARTIAL |
| Fault injection | QEMU `blkdebug` injects EIO/ENOSPC at the block layer, can target the Nth write; it does not model power loss. | PARTIAL |

Sources: <https://github.com/ggml-org/llama.cpp/blob/master/tools/server/README.md>, <https://huggingface.co/BoldingBuilds/AREX-2-Abliterated-GGUF>, <https://qemu.googlesource.com/qemu/+/refs/heads/master/docs/devel/testing/blkdebug.rst>, <https://www.fedoraproject.org/wiki/Changes/EnableSystemdOomd>.

## Loop 3
| Question | Finding | Status |
|---|---|---|
| Can our agent use the llama-server tool surface? | Use `/v1/chat/completions` or `/v1/responses` with `tools` + `--jinja` and run tools **in our own process** (AREX contract). The README says the `/tools` endpoint is internal to the Web UI: "do NOT use this endpoint in a downstream application". `--mcp-servers-config` runs MCP children inside llama-server: allow-list only. | ANSWERED |
| Crash consistency | `dm-flakey` and `dm-log-writes` with fstests crash tests (2017 origin, found ext4/XFS/btrfs bugs). | PARTIAL |
| Snapshots/rollback with Calamares | Kubuntu's Calamares config creates btrfs subvolumes when btrfs is chosen (24.04 report); pre-created `@`/`@home` could fail in the mount job (2017 issue); snapper + btrfs-assistant are the usual tools. | PARTIAL (verify on our ISO) |
| Rust parser robustness | `proptest` round trips, `cargo-fuzz` on byte-level entry points (scheduled, time-boxed, cached corpus), `cargo-mutants -f` per file on a schedule. | ANSWERED (secondary) |
| Better scheduler? | `sched_ext` (`scx_lavd`, `scx_bpfland`) exists; developer claims better frame pacing than EEVDF in games; no independent desktop benchmark; nothing Ubuntu-specific found. | UNKNOWN -> MEASURE |
| Does llama.cpp parse the model's XML? | Qwen3.5-family format is `<tool_call><function=..><parameter=..>`; llama.cpp has a Qwen3-Coder parser and a template-derived auto-parser (from about b8227); a March 2026 regression report exists, fix unconfirmed. | PARTIAL -> test our pin `b12130` |

Sources: <https://lore.kernel.org/all/1504104706-11965-1-git-send-email-amir73il@gmail.com/>, <https://github.com/calamares/calamares/issues/586>, <https://docs.rs/crate/llama-cpp-sys-4/0.7.0/source/llama.cpp/common/parsers/qwen3-coder.cpp>.

## Loop 4 (measured: `apt-cache policy` in Ubuntu `resolute`, WSL, 2026-11-06)
Available: snapper 0.10.6, btrfs-assistant 2.2, stress-ng 0.20.01, fio 3.41, memtester 4.7.1, systemd-oomd 259.9, earlyoom 1.9.0, zram-tools 0.3.7, bpftrace 0.25.0, autopkgtest 5.55, ubuntu-drivers-common 0.10.9, hwinfo 21.82, inxi 3.3.40, fwupd 2.1.1, lynis 3.1.6, openscap-scanner 1.4.3, debsecan 0.4.20.
**Not in the archive:** grub-btrfs (so *booting into a snapshot* is not available out of the box), xfstests, ltp, scx / scx-scheds, systemd-sysupdate, cargo-fuzz (CI installs it with `cargo install`).
The WSL kernel config is Microsoft's and says nothing about Ubuntu's kernel: `sched_ext`, fault injection and `dm-flakey` stay MEASURE inside the booted image (`/boot/config-*`).
Also: llama.cpp `master` has `qwen35.cpp` / `qwen35moe.cpp`, so AREX GGUFs (architecture `qwen35`) load once the pinned build contains them (our pin `b12130`, 2026-11-05). AREX-2 / AREX-Turbo have community GGUFs (bartowski, mradermacher), Apache-2.0. AREX-2 Q4_K_M is about 16.5 GB (abliterated card figure): too large for comfortable use beside a desktop on 24 GB; AREX-Turbo (4B) is the realistic local size.

## "APEX" detour
Two unrelated things share the name: (1) paper **APEX - Adaptive Principle EXtraction** (arXiv 2606.15363): evolves harness (failure-mode patching), behavioural principles (success-trace distillation), workflow topology (fitness selection); on its own setup a local 32B model raised the authors' health score 0.30 -> 0.57. (2) **Apex Intelligence** (Beijing), **Apex-35B-V1.0**, Apache-2.0, MoE on Qwen3.6-35B-A3B (3B active), built "with automated AI research" (company claim); weights and GGUFs on Hugging Face. Both are patterns / candidates, not dependencies. No "APEX 2" was found; the owner's target was AREX-2.

## Decisions (feed the final master plan)
1. **Own AREX-compatible agent runner** (`hscl agent run`): OpenAI-compatible client, XML/JSON tool protocol, local allow-listed tools only (`read_doc`, `search_repo`, `run_gate`, `update_context`, `finish`), no web unless the user enables it, bounded rounds, every round recorded with a verifiable score.
2. **AI API policy** (`hscl ai serve`): bind `127.0.0.1`, random per-install API key, `--metrics` off, never `/tools` or `--tools`, MCP children only from an allow-listed file, router mode optional with `--models-max` and `--models-memory-margin`; document `/v1/chat/completions`, `/v1/responses`, `/v1/embeddings`.
3. **Abliterated models:** opt-in with the existing `--accept-warning`; never in the ISO; each catalog entry carries a *delta card* (refusal rate, tool over-call rate, KL vs stock) from our own eval; agent mode warns about over-calling.
4. **Updates/freeze:** v1 = APT + optional btrfs/snapper snapshots; state plainly that boot-into-snapshot is unavailable; bootc/image-based = 2.x research; never claim "atomic"; `systemd-sysext` dev layer only after an image test.
5. **Stress/tests:** `stress_vm.sh` (stress-ng + klog check, fio, memtester inside a disposable VM), QEMU `blkdebug` fault cases for the installer, `dm-flakey` where the kernel has it, proptest + scheduled cargo-fuzz + cargo-mutants for Rust parsers, autopkgtest for our debs, lynis/openscap/debsecan reports (S4).
6. **Desktop resilience:** verify `systemd-oomd` for user apps, zram (`zram-tools`, zstd), PSI thresholds starting at 50 % / 20 s; `sched_ext` only if the image kernel has it and a measurement shows a benefit.
