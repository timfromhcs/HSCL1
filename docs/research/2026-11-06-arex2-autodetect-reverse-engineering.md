# Research: AREX-2, better hardware autodetect, reverse engineering of single parts (3 rounds, 2026-11-06)

Method: round 1 = questions from the open-questions register + "what is AREX2"; round 2 = questions that round 1 created; round 3 = questions that round 2 created.
Status words: ANSWERED (source read), PARTIAL (source says something, gap named), UNKNOWN (not found; needs a measurement). Nothing here is a measurement on our hardware.

## Round 1 - what is AREX2, and the register items that can be closed on the web

| # | Question | Answer | Status |
|---|---|---|---|
| 1.1 | What is "AREX2 from China"? | **AREX-2** = 27B open-weight (Apache-2.0) agent model of the Beijing Academy of Artificial Intelligence (BAAI), base Qwen3.8-27B, 262,144-token context, paper arXiv 2609.38288 (29 Sep 2026). Not a chip. Idea: *self-improvement at test time* = propose, measure, reflect, revise, trained on synthesised long-horizon trajectories from ML engineering and algorithmic programming (tasks with verifiable feedback), which then transfer to deep research. Reported: MLE-bench Lite 81.8, Frontier-CS 70.7, BrowseComp 84.0, GAIA 92.2 (author numbers, not reproduced by us). | ANSWERED |
| 1.2 | F23: does `llama-server` constrain output by grammar? | Yes: per-request `grammar` (GBNF), `--grammar-file`, and JSON Schema through `response_format` on `/v1/chat/completions`; unsupported schema keywords are ignored, so always re-validate the parsed object. Exact fields depend on build version. | PARTIAL (probe our pinned build) |
| 1.3 | Q18: is `systemd-sysext` usable for a dev-mode layer? | The resolute man page describes overlay of `/usr` and `/opt` from extension images, read-only by default, matched against `os-release` (`ID=`, `SYSEXT_LEVEL=`); `/etc` and `/var` content is not merged; `systemd-confext` does the same for `/etc`. Whether the package/boot wiring works on our remastered image is untested. | PARTIAL (VM test) |
| 1.4 | Q21: how to judge KV-cache quantisation? | Compare against an f16 reference with KL divergence and top-1 agreement, not perplexity alone: community numbers show q8_0 KV near lossless for some models and not for others (a Gemma 26B MoE had KL 0.377), q4_0 is model dependent. Our own check must run on the shipped models. | PARTIAL (calibrate on our 2B/4B) |
| 1.5 | F21: WebGPU in QtWebEngine? | No source confirms WebGPU in Qt 6.10's WebEngine on Linux/Wayland; an NXP thread on 6.7 says it did not work. Do not assume it. | UNKNOWN -> measure; default renderer WebGL/CPU |

Sources: <https://huggingface.co/BAAI/AREX-2>, <https://arxiv.org/abs/2609.38288>, <https://github.com/VectorSpaceLab/AREX-2>, <https://github.com/ggml-org/llama.cpp> (grammars README), <https://manpages.ubuntu.com/manpages/resolute/man8/systemd-sysext.8.html>, <https://localbench.substack.com/p/kv-cache-quantization-benchmark>.

## Round 2 - questions created by round 1

| # | Question | Answer | Status |
|---|---|---|---|
| 2.1 | Does the AREX-2 repository contain a harness we can reuse? | No agent harness: it holds **evaluation runners** and dataset definitions (`evaluate.py`, per-dataset `config.json`/`prompt.py`/judge) and, for deep research, a tool set `search`, `visit`, `update_context`, `finish`. The method is in the *trained model* and in the loop shape, not in shipped orchestration code. | ANSWERED |
| 2.2 | Is there a small variant for a 24 GB laptop? | **AREX-Turbo**: dense 4B on Qwen3.5-4B, Apache-2.0, 256K context, deep-research tuned (BrowseComp 70.7), official serving paths Transformers/vLLM/SGLang; HF lists 5 community quantisations, GGUF not confirmed by the official card. AREX-2 (27B) in BF16 is ~54 GB and does not fit; a 4-bit quantisation would be ~16 GB and run mostly on CPU. | PARTIAL |
| 2.3 | Which data would we need to copy the approach for our own loop? | Verifiable feedback per round: scores, logs, errors, timings. We already have such signals (pytest, clippy, verify-image gates, boot classifier, e2e check counts). | ANSWERED (design below) |
| 2.4 | Speed of a 7B Q4 on the Radeon 680M with Vulkan? | No 680M figure found. Neighbouring 780M reports are 8-15 tok/s for 7B-class dense models and 6.5 tok/s for a 14B; 680M is likely at the low end. A proxy, not a result. | UNKNOWN -> `llama-bench` on the machine |
| 2.5 | How do others detect hardware and find drivers? | `hw-probe` (Linux Hardware Database) uploads anonymised probes; the OpenBSD port warns the upload can contain UIDs and serial numbers. | ANSWERED |

Sources: <https://huggingface.co/BAAI/AREX-Turbo>, <https://github.com/ggml-org/llama.cpp/discussions/10879>, <https://flathub.org/apps/org.linux_hardware.hw-probe>.

## Round 3 - questions created by round 2

| # | Question | Answer | Status |
|---|---|---|---|
| 3.1 | Does llama.cpp run the Qwen3.5/3.8 families (needed for AREX-Turbo/2 GGUF)? | Qwen3.5 GGUFs are in circulation and run with `llama-server`; no merged-PR or release note naming the architecture was found, Qwen3.8 not found at all. Check `convert_hf_to_gguf.py` and `src/models` of our **pinned** build before promising anything. | PARTIAL |
| 3.2 | How does Ubuntu pick drivers (to improve our autodetect without a network)? | `ubuntu-drivers-common`: hardware exports a **modalias** in sysfs; driver packages carry modalias patterns (`dh_modaliases`); matching is pattern comparison and needs only python-apt (no root); special cases use small detection plugins in `/usr/share/ubuntu-drivers-common/detect/`; `gpu-manager` handles hybrid graphics. | ANSWERED |
| 3.3 | Where do per-device quirks belong? | `udev hwdb`: modalias-matched files in `/etc/udev/hwdb.d` (or `/usr/lib/udev/hwdb.d` for packages), compiled by `systemd-hwdb update`, applied with `udevadm trigger`. Caveat: the boot-time update service has a `ConditionNeedsUpdate` that may skip edits, so packages run the update in `postinst`. | PARTIAL (verify on the image) |
| 3.4 | May we reverse engineer a single part? | EU: Directive 2009/24/EC art. 6 allows reproducing/translating code **only if indispensable for interoperability** of an independently created program, with limits (no other purpose, no hand-over beyond need, no substantially similar program); contract terms against it are void. CJEU C-13/20 (Top System, 2021): error correction by a lawful acquirer is governed by art. 5(1), not by art. 6. Firmware/driver specifics are not covered by these sources. This is not legal advice; the owner decides (register O5/Q15). | PARTIAL |
| 3.5 | Technical method for undocumented USB devices? | `usbmon` + Wireshark capture of the vendor tool's traffic, then a userspace driver (libusb); caveats: root or a udev rule for usbmon, no capture filters on usbmon. ACPI/DSDT override steps were not covered by this search. | PARTIAL |

Sources: <https://github.com/canonical/ubuntu-drivers-common>, <https://www.legislation.gov.uk/eudr/2009/24/article/6>, <https://www.cuatrecasas.com/en/latam/art/decompilation-of-software-for-error-correction-cjeu-judgment-in-top-system>, <https://www.flashrom.org/USB_Sniffing>, <https://crescentro.se/posts/wireshark-usb/>.

## What changes in our plans (decisions)

1. **AREX-2 as a pattern, not a dependency.** Re-build its loop in our harness: `propose -> measure -> reflect -> revise` with a *verifiable score per round* and a round budget (see subplan A). No 27B model in the ISO; AREX-Turbo is a *candidate* for the optional AI bundle only after a GGUF + licence + eval check (G39).
2. **Autodetect v2 = modalias-first.** Collect modaliases from `/sys` (we already read `/sys`), map them to (a) driver packages through `ubuntu-drivers` when present, (b) our own quirk table, (c) a "needs attention" list. Everything offline, redacted by default (existing `redact.rs`), upload never default (subplan B).
3. **Reverse engineering is a lab workflow, not a feature.** Own hardware only, interoperability purpose, capture with `usbmon`, document in `docs/re/<device>.md`, ship only our own driver/quirk code under our licence, never vendor firmware or decompiled code; legal wording is an owner item (subplan C).
4. Open measurements stay open and are tagged MEASURE: 680M tok/s, WebGPU in QtWebEngine, llama.cpp arch support in the pinned build, sysext on the image, hwdb postinst.
