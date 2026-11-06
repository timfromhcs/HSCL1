# HSCL1 plan: freeze a working OS into a new ISO, dev mode inside the OS, memory tiering ("fake VRAM"), KV-cache compression, safe RSI

Owner request 2026-11-06: search open questions on (1) "update ISO to new ISO: freeze this state into the OS and keep working inside that OS: improve, install, patch in a dev mode",
(2) "fake VRAM from RAM, SSD or storage, decided after a speed test", automatic KV-cache compression, RSI, and making all of it faster; then plan in detail, then work smarter.
This file extends the master plan (`2026-11-06-autonomous-to-stable-hardened.md`, phases P15-P17 there). The master plan wins on conflicts. Status words as in the master plan;
**UNVERIFIED** marks a research claim not yet checked against a primary source or a measurement on our machine.

---

## 1. Research digest (what the sources say, what they do not)

### 1.1 Freezing a running system and developing inside the OS
| # | Finding | Source | Consequence for HSCL1 |
|---|---|---|---|
| F1 | `systemd-sysext` overlays an extension image's `/usr` and `/opt` onto the host with overlayfs ("merge"/"unmerge"), `systemd-confext` does the same for `/etc`. Extensions are meant to be **additive**, are all activated at boot (no enable/disable), cannot ship services, and need `/usr/lib/extension-release.d/extension-release.NAME` matching the host `os-release`. The man page's own dev example: `DESTDIR=/var/lib/extensions/mytest make install && systemd-sysext refresh` | https://manpages.ubuntu.com/manpages/resolute/man8/systemd-sysext.8.html | Candidate mechanism for a reversible **dev mode** for tools, libraries, themes, binaries. Needs checking on our image: is it shipped and enabled, how `extension-release` must match our `os-release` (`ID=ubuntu`, `VERSION_ID=26.04`, or `ID=_any`) |
| F2 | ostree "unlock" gives a writable overlay on `/usr`: development mode is discarded on reboot, **hotfix** mode persists and keeps a rollback deployment, transient mode keeps `/usr` read-only afterwards. Committing such changes into a new image is a separate build step; this search did not cover it | https://man.archlinux.org/man/ostree-admin-unlock.1.en | We do not use ostree; the lesson is the **three lifetimes** (throw-away, persisted-with-rollback, baked into the image) and that baking is an explicit, reviewed step |
| F3 | Ubuntu-family live ISOs mount the read-only squashfs as `/rofs` (lower) and a writable layer as `/cow` (upper) in overlayfs; a persistence partition is found by label `casper-rw`. The upperdir holds only changes since boot, plus whiteouts and runtime files (logs, machine-id, caches) that must be excluded | https://sigwait.org/~alex/blog/2026/05/28/smdBC8.html , https://gist.github.com/gdamjan/62ccd8a4878112e35456 | The live session's upperdir **is** the diff. Capture needs strict exclusions and a reviewed manifest. No single guide covers capture-from-running-system end to end |
| F4 | penguins-eggs remasters a running system into an installable ISO (own installer krill or Calamares); `--clone` keeps accounts and data, `--cryptedclone` keeps user data in a LUKS volume; user data stripped by default | https://www.github.com/pieroproietti/penguins-eggs | Prior art for the "freeze" idea and for the rule "user data out by default". We keep our own scripted path (reproducible, our gates) |

### 1.2 Memory tiering for local models
| # | Finding | Source | Consequence |
|---|---|---|---|
| M1 | On AMD APUs the BIOS "VRAM" is a small fixed carve-out; the useful pool is GTT in system RAM, default about 50 % of RAM. `amdgpu.gttsize` is deprecated; use the TTM limits `ttm.pages_limit` / `ttm.page_pool_size` in 4 KiB pages (GB x 262144). The parameter prefix (`ttm.` vs `amdttm.`) depends on the kernel: check `/sys/module/*/parameters/` and `dmesg \| grep -i gtt`. Strix Halo doc: the needed patches are in kernel 6.18.4+ | https://mvysny.github.io/amd-igpu-gtt-llm/ , https://www.jeffgeerling.com/blog/2025/increasing-vram-allocation-on-amd-ai-apus-under-linux/ , https://rocmdocs.amd.com/en/develop/how-to/system-optimization/strixhalo.html | "Fake VRAM from RAM" on an APU is just **raising the GTT/TTM limit** (unified memory), not emulation. Our kernel is 7.0.0-30. **No 680M-specific figures were found**; the 780M examples are the closest (same RDNA family reasoning is ours) |
| M2 | llama.cpp's Vulkan backend pools VRAM + GTT; one 780M user reports Vulkan sees about 24.5 GiB while ROCm sees about 15 GiB | https://www.k8s.it/posts/running-a-local-llm-on-amd-radeon-780m-gfx1103-rocm-and-the-gpu-that-wasnt-supposed-to-work/ | Vulkan is the right backend for APUs (matches the master plan R15); report dedicated and shared memory separately (already a project rule) |
| M3 | llama.cpp `--fit` (default on) allocates automatically: shrinks the context first (default minimum 4096), then moves tensors to RAM, keeps dense tensors on the GPU first for MoE models; explicit `-c`, `-ngl`, `-ts`, `-ot` are left untouched; margin `--fit-target` (default 1024 MiB). Known limits: about 85-90 % utilisation, a Qwen3-Next context accounting bug, slow fitting | https://gh.r-mj.com/ggml-org/llama.cpp/discussions/18049 | Our own estimator (`hscl ai fit`) should not fight `--fit`: it should predict, explain and cross-check, and let `--fit` do the allocation unless the user pins values |
| M4 | MoE offload flags: `--n-cpu-moe N`, per-tensor `-ot`; a newer GPU expert cache `--moe-cache-mib N` (default 0); one report measured about 2.4x slower decode with idle experts on the CPU; another (PR author) 2.2x faster with the cache on an RTX 5090. Anecdotal | https://www.developersdigest.tech/blog/llama-cpp-moe-offload-n-cpu-moe-vs-moe-cache-2026 | Offer these only if the **pinned** llama.cpp advertises them in `--help` (rule already in the master plan); measure before recommending |
| M5 | SSD tier: llama.cpp's default mmap already gives most of the benefit for weights larger than RAM; **no measured NVMe tokens-per-second figure was found**. Reports of 100B models on a 24 GB card at 1-2 tok/s are anecdotal | https://viblo.asia/p/running-moe-llms-larger-than-your-ram-a-practical-guide-to-mmap-expert-offloading-and-ssd-streaming-with-llamacpp-pPLkNQQNJRZ | SSD "memory" is **streaming**: speed is bounded by sequential read bandwidth; we can compute that bound (roofline) and then measure |
| M6 | KV offload tiers exist in vLLM (GPU -> CPU DRAM native, async path in 0.11.0) and LMCache (adds local disk/NVMe); vLLM core does not do NVMe itself; **nothing found for llama.cpp disk KV** | https://vllm.ai/blog/2026-01-08-kv-offloading-connector , https://docs.lmcache.ai/getting_started/quickstart/offload_kv_cache.html | A disk KV tier is not available in our backend: do not promise it. In-RAM KV and KV quantisation are the real levers |
| M7 | KV quantisation in llama.cpp: q8_0 about halves KV memory with very small loss; q4_0 about a quarter but can collapse quality (one 7B coder at 8K: q8_0 output about 82 % similar to f16, q4_0 about 8 %, single model and metric); quantised V needs flash attention (`-fa`); an asymmetric K=q8_0 / V=lower split is a common anecdote; model sensitivity varies. KIVI / SnapKV / H2O accuracy was **not** covered | https://llmhardware.io/guides/kv-cache-quantization-ollama-llama-cpp , https://inventivehq.com/blog/kv-cache-quantization-quality-benchmark | Default f16; fall back to q8_0/q8_0 only when the context would not fit; q4_x only as an explicit opt-in with a quality warning. Read the primary papers before any eviction feature |
| M8 | CUDA unified-memory oversubscription thrashes: one study reports about 24 % average slowdown at 125 % oversubscription and crashes at 150 % (older hardware); hints/prefetch help or hurt depending on the platform. **Nothing found for Vulkan or ReBAR/SAM spill** | https://arxiv.org/pdf/2204.02974 , https://ar5iv.labs.arxiv.org/html/1910.09598 | Do not build a "transparent spill" layer on faith. For NVIDIA, document UM as an option with measured limits only |
| M9 | Swap/zram/zswap for models: community advice is low `vm.swappiness` (10 in one post) and an NVMe swapfile as a safety net, not as a working tier; zram compresses poorly for already quantised weights and mmap'd weights are normally dropped from the page cache instead of swapped (**both statements are our reasoning, UNVERIFIED**) | https://dev.to/vonusma/creating-a-50-gb-swap-file-on-jetson-agx-orin-root-on-nvme-ijd | Never recommend swap as "more VRAM". Measure page-cache behaviour with `--mlock`/`--no-mmap` on a real run before writing guidance |

### 1.3 RSI (recursive self-improvement) for coding agents
| # | Finding | Source | Consequence |
|---|---|---|---|
| R1 | The Darwin Goedel Machine (ICLR 2026) edits its own code and **validates each change empirically on coding benchmarks** (not by proof), keeps an **archive** of agent variants as stepping stones; reported SWE-bench 20.0 % to 50.0 %, Polyglot 14.2 % to 30.7 % | https://arxiv.org/abs/2505.22954 , https://sakana.ai/dgm/ | The pattern is: variants + benchmark gate + archive. The gate must be something the agent **cannot edit** |
| R2 | A survey describes SICA as a fully self-referential coding agent with independent verification after a sub-agent implements a change. A claim that the public DGM release removes privileged components and defaults to a sandbox is **UNVERIFIED** (secondary) | https://arxiv.org/pdf/2607.13104 | Treat "sandboxed by default" as our requirement, not as something the literature gives us |
| R3 | No source found on human-approval gates or evaluation-harness design in these systems | search gap | Our own design (section 4) |

---

## 2. Design: freeze, dev mode, bake (HSCL1 Dev Mode)

**Principle.** A change moves through three lifetimes, each explicit and reversible until the last: **throw-away** (gone at reboot) -> **kept with rollback** (survives reboot, can be removed) -> **baked** (part of the next ISO, via a reviewed repository change). Nothing is baked from a raw filesystem snapshot without review.

1. **Throw-away (exists today):** the live session's overlay upperdir; Workshop `guest_put_file`/`guest_hook`/`guest_restart_shell` (tier T2 of the master plan).
2. **Kept with rollback (to build, experiment first):** a **dev sysext**: a directory/image `hscl-dev` under `/var/lib/extensions/` with its own `extension-release`, merged by `systemd-sysext refresh`, removed by deleting it and refreshing. Covers binaries, libraries, themes, QML, desktop files; **not** services, maintainer scripts, `/etc` (use confext for `/etc`), kernel or initrd. Experiment E1 below decides if it works on this image (F1).
3. **Baked (the only way into an ISO):** `hscl dev freeze` is **not** a disk snapshot. It produces a **reviewable patch for the repository**:
   - *package-level*: `dpkg-query` diff against the image's own manifest, written as a proposed addition to the package manifest;
   - *file-level*: the upperdir restricted to an **allow-list** (`/etc/skel`, `/usr/share/hscl`, `/usr/share/plasma`, `/usr/share/applications`, `/etc/xdg`, `/usr/libexec/hscl*`, our package trees) turned into files under `packages/debian/<pkg>/` or `distro/overlay/` in a **git branch**, with a manifest (path, size, sha256, owner, mode);
   - **hard exclusions** that cannot be overridden by flags: `/home` (except `/etc/skel`), `/root`, `/etc/machine-id`, `/etc/ssh/ssh_host_*`, shell histories, browser/KDE wallet/keyring data, `/var/log`, `/var/cache`, `/tmp`, `/run`, any file matching the secret patterns of `forge.py`, the Workshop token, whiteouts outside the allow-list;
   - a **dry run** (`freeze plan`) prints what would be exported and what was excluded and why; export refuses on any secret hit; size cap; all modes normalised by content as `build-deb.sh` does; ownership forced to `root:root` (the `/` ownership defect is the reason);
   - the result goes through the normal PR, `forge check`, build and boot gates. Reproducibility stays with the repository, not with a blob.
4. **Why not "ISO from the running system" directly** (the penguins-eggs style): it bakes machine identity, caches and user data by accident, cannot be reviewed, is not reproducible and bypasses our gates. Allowed only for a **private** developer image labelled `qa_image`, never for a release (the manifest field already exists).

**Dev mode switch.** `hscl dev` (planned, listed in `--help` only when implemented) shows state: which lifetime each change is in, what sysext is merged, what the freeze plan would export. It runs unprivileged; privileged steps go through the narrow helper with fixed operations (`sysext refresh`, `sysext remove NAME`), never a shell string.

### Experiments (cheap first, all in a live VM, no rebuild)
- **E1 sysext on our image:** `systemd-sysext --version` and `status`; create `/var/lib/extensions/hscl-test/usr/lib/extension-release.d/extension-release.hscl-test` with `ID=_any`; add one file under `usr/share/hscl-test/`; `refresh`; check the file is visible; `unmerge`; check it is gone; then repeat with a matching `ID=ubuntu`/`VERSION_ID=26.04` release file. Record which variant works, whether `dpkg`/`apt` are affected, and what happens at reboot (all installed extensions auto-merge).
- **E2 upperdir anatomy:** after a typical session (install one package, change a theme setting) list the upperdir at `/cow` (or where casper puts it), count whiteouts/opaque dirs, size, and which paths are noise. Output feeds the allow-list and exclusion list.
- **E3 freeze plan prototype** against E2's output: prove that the exclusions remove machine-id, host keys, histories and caches, and that a planted fake secret makes the export refuse (mutation check).

---

## 3. Design: memory tiering, speed test, KV compression (`hscl ai tier`, planned)

**What it is, honestly.** There is no "fake VRAM". There are tiers with different bandwidth: GPU-local memory, GTT (system RAM the GPU can address; on an APU the same physical RAM), CPU RAM, page cache over NVMe (mmap streaming). The advisor measures the machine, predicts where a given model+context fits and how fast each option can be at best, recommends flags, and verifies the recommendation with a short real run. It never claims a speed it did not measure.

**Inputs (all measured on the machine, none assumed):**
- sizes: dedicated VRAM, GTT limit, free RAM (already in `hscl hw`; dedicated and shared stay separate);
- bandwidth: RAM (a bounded memory-copy test), SSD sequential read (a bounded read of a scratch file with cache bypass where possible, otherwise labelled "page-cache affected"), optionally GPU copy via the backend's own bench;
- model: GGUF metadata (already parsed: weights, layers, KV bytes per token; hybrid models flagged as not estimable yet, master plan P6.6).

**Model (roofline, stated in the output):** decode speed is bounded by bytes read per token divided by the bandwidth of the tier where those bytes live; prefill is compute-bound. For a dense model whose weights sit in a tier with bandwidth B, `tokens/s <= B / weight_bytes` (plus KV reads). That gives the *ceiling* per option: all-GTT, partial offload, mmap-from-SSD. The real run then reports the measured value next to the ceiling.

**Output:** recommended `llama-server` flags for the **pinned** build (only flags its `--help` lists), the predicted ceiling per option, warnings ("SSD streaming bound: about X tok/s ceiling"), and the exact kernel parameter snippet if the GTT limit is the bottleneck.

**TTM/GTT change:** advice and a reviewed config snippet only (`ttm.pages_limit` or `amdttm.pages_limit` depending on what `/sys/module` shows). Applying it is a privileged, reboot-requiring change through the narrow helper after explicit confirmation, with a cap (never above a stated share of RAM, so the OS is not starved) and a one-command revert. Default: **advise, do not apply**.

**KV cache policy (automatic, conservative):**
1. f16 when the context fits with `--fit`'s margin.
2. If it does not fit and the user asked for that context: q8_0 K and V (requires `-fa`), and say so.
3. q4_x or an asymmetric K/V split only as an explicit opt-in with a warning that quality can collapse (M7).
4. A **quality gate before any compressed type is recommended for a model**: run llama.cpp's perplexity/KLD tool on a small fixed text with f16 and with the candidate type, store both numbers in the model profile, refuse the recommendation above a stated threshold. If the tool or the threshold cannot be applied, recommend nothing.
5. Eviction/compression research (KIVI, SnapKV, H2O) is **out of scope** until the primary papers are read; no feature, no claim.

**Where it can be tested:** unit tests with synthetic hardware profiles (pure functions: roofline, fit, KV choice); the CLI on the owner's Windows host with the real Radeon 680M for the Vulkan device lines (master plan P6.2); Linux-on-metal GTT numbers need the owner to boot the image on the machine (stop-and-ask item). In VMs only the logic is testable, not the GPU.

---

## 4. Design: safe RSI loop for HSCL1 tooling

Goal: let an agent improve our own scripts and tools in a loop **without being able to weaken what judges it**.
1. **Protected paths** (a list in `scripts/protected_paths.json`): `tests/`, `.github/`, `distro/live/verify-image.sh`, `scripts/forge.py` gates, `scripts/boot_classify.py` rules, `docs/CLAIMS.md`, `AGENTS.md`, `deny.toml`, the master plans. A script `scripts/protected_paths.py` compares a branch against `main` and **fails** when any protected path changed outside a branch explicitly labelled for human review. CI runs it on every PR from an RSI/agent branch. (The agent that edits the code does not edit the judge.)
2. **Variants, not in-place edits:** each candidate is a git branch; an **archive** file records branch, parent, commit, `forge check` result, test counts, boot-test result, timing (DGM archive idea, R1).
3. **Evaluation set held out:** gates must include tests the candidate has not seen (e.g. fixture logs for the boot classifier, unseen synthetic hardware profiles); the candidate's own new tests count, but only alongside the old suite.
4. **Disposable execution:** candidates that run code run in a disposable VM or container with no secrets, no network unless needed, and no access to release credentials.
5. **Human approval to merge** (the PR plus green CI already is that gate); no auto-merge for protected-path or release changes.
6. **Honest scope:** this is a process and a guard, not autonomy. The existing `rsi-capture` MCP tools and the LoRA loop of the owner's wider setup are out of this repository's scope until the owner asks; nothing here trains or merges model weights.

---

## 5. Work order (smarter, in this order; each step has a test or a measurement)
1. **Now:** record r5/r6 evidence in BUILD_LOG/CLAIMS; PR the branch; full release build of the fixed commit and all release gates (master plan section 7).
2. **E1/E2/E3** (live VM, minutes each, no rebuild): sysext on our image, upperdir anatomy, freeze-plan prototype with a planted secret.
3. `scripts/protected_paths.py` + test + CI step (small, host-only, valuable immediately).
4. Pure-function core of `hscl ai tier` in Rust with synthetic-hardware tests (roofline, fit, KV choice); no GPU needed.
5. Bounded RAM/SSD speed tests (host-side, bounded, labelled when the page cache affects them).
6. `hscl dev` status + freeze plan (read-only) after E1-E3 results; export only after the exclusion mutation tests pass.
7. Owner-dependent: Windows-host Vulkan smoke test on the 680M, Linux-on-metal GTT test, any change to inherited network defaults.

## 6. Open questions (how each gets answered)
| # | Question | Answer by |
|---|---|---|
| D1 | Is `systemd-sysext` present and active on the image; which `extension-release` match works with our `os-release` | E1 |
| D2 | Where exactly is the live upperdir and how noisy is it after a normal session | E2 |
| D3 | Do dev sysext merges conflict with `dpkg`/`apt`/Calamares install (installer copies the squashfs, not the merged view) | E1 + an install test; assume sysext content is **not** installed to disk until proven |
| T1 | `ttm.` or `amdttm.` prefix on kernel 7.0.0-30, default GTT share, effect on the Radeon 680M | owner's hardware (Linux boot) |
| T2 | Real NVMe streaming tokens/s for our model sizes on the owner's SSD | bounded speed test + real run |
| T3 | `llama-perplexity`/KLD availability in the pinned llama.cpp build and a sensible threshold | read the pinned build's `--help`, calibrate on the 2B model |
| T4 | Does our pinned llama.cpp advertise `--fit`, `--n-cpu-moe`, `--moe-cache-mib`, MTP flags | `--help` of the pinned binary (P6.3) |
| T5 | KIVI / SnapKV / H2O trade-offs | read the primary papers (research tools) before any feature |
| S1 | Which protected-path list is complete enough | review with the owner once, then enforce |
