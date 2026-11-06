# HSCL1 expansion plan: UI/UX, desktop, local AI, hardware and driver detection, GPU/RAM bridges (long-horizon, self-healing)

> **For the autonomous agent.** This plan EXTENDS `2026-11-06-autonomous-to-stable-hardened.md` (hardening, installer, release) and does not replace it.
> Both plans use the same loop (section 2 of the hardened plan), the same resource policy (section 3) and the same evidence vocabulary
> (PLANNED, IMPLEMENTED, TESTED, VM-VERIFIED, HARDWARE-VERIFIED, EXPERIMENTAL, BLOCKED). Written 2026-11-06 after a research round (sources in section 1).
> A box is ticked only with evidence in `docs/CLAIMS.md` or `docs/BUILD_LOG.md`. Security work (workstream W0) always goes before features.

**Goal.** A desktop that is pleasant and fast to use with mouse and keyboard, detects its hardware and offers the right drivers and AI backend without surprising
the user, generates its own wallpapers and colour themes, ships a local AI coding setup that runs on modest hardware, and explains truthfully what it measured.

**Non-goals / hard limits** (from AGENTS.md and this session's research):

- No decompilation or disassembly of proprietary binaries, drivers or firmware. "Reverse engineering in another language" in this plan means **porting open-source
  algorithms** and **reading public documentation/specs** into Rust, with attribution and a licence check (GPL-3.0-or-later project; GPL-2+/Apache/MIT sources are compatible).
- No automatic installation of proprietary drivers, no kernel parameter changes, no `curl | sudo bash`. Every system change is a typed, allow-listed action with a dry run,
  a visible summary and an explicit confirmation; kernel/boot changes additionally state the reboot and the way back.
- No claim of a speed-up, a "GPU from RAM" or a driver bridge that was not measured on the machine in question. Estimates are labelled as estimates.
- ZLUDA and similar CUDA-translation layers are **documented, not shipped** (maintenance and licensing risk, see R-AI-4).
- Original design only: no copied artwork, icons, layouts or code from other desktops without a licence check.

---

## 1. Research findings (2026-11-06) and what each changes

Each item: finding, source, consequence for this plan. Unverified items say so.

### UI/UX and desktop

**R-UX-1 KWin tiling is native but limited.** Plasma has custom tile layouts with shortcuts; layouts do not persist across virtual desktops/activities, odd-number splits are
awkward, users hand-edit `[Tiling]` in `kwinrc`; third-party scripts (Polonium, Krohnkite) exist, Fluid Tile is no longer developed. Sources: KDE bugs 466019, 465862, 513246.
*Consequence:* ship a small **default tile layout set** through `kwinrc` (version-controlled), document the shortcuts we actually bind, do not depend on a third-party tiling script.
We could not find an official list of native tiling default shortcuts -> measure them from a booted image (`kglobalshortcutsrc`) instead of quoting.

**R-UX-2 Plasma 6.6 adds relevant accessibility/input features.** Reduced Motion setting, Slow Keys on Wayland, grayscale colour-blind filter, desktop-zoom tracking mode, push-to-talk,
redesigned on-screen keyboard (source: Linuxiac/OSTechNix release coverage). *Consequence:* our "reduced motion stops all animation" rule can use the standard setting; accessibility
test plan covers these switches. No evidence found of a built-in shortcut cheat-sheet overlay -> we build one (W5).

**R-UX-3 Launcher/command-palette landscape.** KRunner is Plasma's built-in command surface; Vicinae (Raycast-style, extensible with scripts/React), Albert (Qt) and Ulauncher exist.
*Consequence:* extend **KRunner** with a small, allow-listed HSCL1 runner (actions, settings, theme/graphics/lab status) instead of adding a second launcher; learn from Vicinae's
"script command" model for the action format (typed, no shell).

**R-UX-4 Shader wallpapers in Plasma 6.** Plugins (kde-shader-wallpaper, glmatrix, Boingwave) use QML `ShaderEffect` with **`.qsb` shaders baked by Qt's `qsb` tool**; plain GLSL no longer loads
in Qt 6; multipass buffers are reported not to work in pure QML (may need C++). *Consequence:* shader presets need a build step (`qsb`, package `qt6-shadertools-dev` / tools on the builder);
heavy effects get a CPU-baked static fallback; no multipass promised.

**R-UX-5 Procedural wallpaper algorithms.** fBm, turbulence and **domain warping** (fBm fed into fBm, time-driven offsets for flow) are the standard building blocks; cost is controlled by
octave count, half-resolution rendering and baking static fields to textures. Sources: The Book of Shaders, GameDev.net shader lab. Flow fields, Truchet tiles and colour harmony were not covered
by the search (to be read from primary sources while implementing, see W6).

**R-UX-6 Dynamic colour.** Several Rust crates implement Google's Material Color Utilities (HCT, tonal palettes, schemes; some include image quantisation, some do not): `material-color-utils`,
`mcu-material-color` (2026), `material-color-rs` (new), `frust-material` (scheme only). MCU uses CAM16/HCT, not OKLCH. *Consequence:* evaluate crates for **quantiser presence, licence and size**
before adopting; fallback is a small in-tree implementation (seeded k-means in OKLab + tonal ramps) with tests. Licence gate: `cargo deny`.

### Local AI

**R-AI-1 Decode is memory-bound, prefill compute-bound** (roofline): decode tokens/s is approximately effective memory bandwidth / bytes read per token; prefill is dominated by batched GEMM.
Small decode kernels can additionally be launch-bound. Sources: Arm "llama-roofline" learning path, roofline write-ups. *Consequence:* `hscl ai estimate` = measured bandwidth (STREAM-style) and
measured GEMM throughput -> tokens/s **range**, validated against a real `llama-bench` run on the same machine; the number is never shown without "estimate".

**R-AI-2 Model memory estimation exists as open source.** gguf-parser-go (MIT) reads GGUF metadata (even remotely in chunks) and estimates RAM/VRAM for a given context size, offloaded layers and flash attention.
*Consequence:* port the **idea** (metadata -> weights + KV cache + compute buffers) to Rust (`hscl ai fit`), attribution to gguf-parser-go, tested against known GGUF fixtures and a real load on the builder.

**R-AI-3 "GPU memory from RAM" is mostly a kernel-parameter and flag matter.** On AMD APUs the iGPU can use system RAM through TTM/GTT; the old `amdgpu.gttsize` is deprecated in favour of
`ttm.pages_limit` (counted in 4 KiB pages); llama.cpp's auto-fit can misjudge unified memory; `mmap` on can hurt Vulkan/ROCm loads; Vulkan is usually the better backend for these iGPUs. Sources: Framework forum,
Jeff Geerling, llama.cpp issue 18159, Fedora notes. Nothing verified for the Radeon 680M specifically. *Consequence:* `hscl ai tune-memory` **suggests** a `ttm.pages_limit` value with the formula, the reboot warning and
the rollback, never applies it silently; measured effect recorded on the owner's machine (task owner-dependent).

**R-AI-4 MoE offload is the practical "RAM instead of VRAM" technique.** llama.cpp `--n-cpu-moe N`, `--cpu-moe`, `-ot/--override-tensor` keep expert weights in RAM and attention on the GPU; a recent mainline expert
cache (`--moe-cache-mib`) exists; ik_llama.cpp and KTransformers are separate engines with large claimed speed-ups (project claims, unverified here). *Consequence:* `hscl ai profile` gains MoE-aware flags using
the pinned llama.cpp's real `--help` (never flags it does not advertise); forks are EXPERIMENTAL entries only. ZLUDA (CUDA on AMD/Intel, mostly Rust) is hobby-funded since v6 and legally contested; documented, not integrated.

**R-AI-5 Speculative decoding.** EAGLE-3 is the production default in server engines (vLLM, SGLang, TensorRT-LLM); Medusa needs trained heads; prompt-lookup/n-gram needs no draft model; llama.cpp support for
EAGLE variants is unclear (sources conflict). *Consequence:* only features the pinned llama.cpp advertises are enabled; measure speed before/after on the same model; no claims otherwise. KV-cache quantisation was not covered
by the search; read llama.cpp docs for `--cache-type-k/v` when implementing.

**R-AI-6 Agent landscape.** OpenCode (MIT, provider-agnostic), Aider (best terminal agent for larger local models per one guide), Cline (VS Code), Goose (Apache-2.0, Linux Foundation), Continue. Qwen3-Coder/Devstral comparisons
were not found. *Consequence:* the `hscl code` catalog gains Aider and Goose entries with licence + install method; model entries are added only after reading real repository metadata (licence, size, sha256) from Hugging Face.

**R-AI-7 Matrix-multiply simulators.** SCALE-Sim v2/v3 (Python, cycle-accurate systolic arrays, GEMM via M,N,K) and Timeloop (analytical) are the open references. *Consequence:* a small **tiny-systolic model** in Rust
(`hscl ai gemm-sim`) with closed-form checks and a cross-check against SCALE-Sim's published formulas; presented as a teaching/diagnostic model, not as a driver or benchmark.

**R-AI-8 CPU GEMM building blocks.** `matrixmultiply` (ndarray's kernel, FMA path 10-15 % faster than AVX), `gemm` (faer's backend), `gemmkit` benches compare them; a from-scratch AVX2 blocked GEMM reached ~32 GFLOPS single-thread on a WSL2 laptop.
*Consequence:* use `matrixmultiply` for the on-device GEMM probe (licence MIT/Apache, no unsafe code of our own), do not write a new kernel.

### Hardware and drivers

**R-HW-1 How Ubuntu detects drivers.** `ubuntu-drivers-common` maps hardware to packages via **modalias patterns** read from sysfs and `Modaliases:` headers in packages (generated by `dh_modaliases`); lookups use python-apt;
special cases are plugins; on 26.04 `ubuntu-drivers install` replaces the deprecated `autoinstall`, and `ubuntu-drivers list --include-dkms` shows DKMS-only drivers. *Consequence:* `hscl hw detect` reads `/sys/bus/*/devices/*/modalias`
and asks **apt** (`apt-cache show` Modaliases / `ubuntu-drivers list` as the oracle) - we do not reinvent package selection; our Rust port covers detection + presentation + safe confirm, the install step calls the distro tool.

**R-HW-2 Secure Boot and NVIDIA.** Sources disagree on whether MOK enrolment is still needed (Canonical says it builds/signs modules to avoid it; third-party guides describe MOK prompts for DKMS). *Consequence:* we do not promise either; the flow is
"read `mokutil --sb-state`, run `ubuntu-drivers list --include-dkms`, install, then verify `modinfo`/`nvidia-smi` and report"; MOK enrolment instructions are shown only when the tool asks for it. Needs a physical NVIDIA machine to verify (owner).

**R-HW-3 Rust building blocks for detection.** `pci-ids` (vendored PCI ID database, MIT/Apache), direct sysfs reads (`/sys/bus/pci/devices`, `/sys/class/drm`), `ash` for Vulkan properties (unverified here), `devs` is immature, `hardware`/`elinux-hwdetect`
are poor fits. *Consequence:* sysfs + `pci-ids` (+ parsing `vulkaninfo --summary` output as a first step, `ash` later if needed); no root, no PCI port I/O.

**R-HW-4 Virtual GPUs for testing.** QEMU `virtio-gpu` 2D needs a software renderer in the guest (Mesa llvmpipe/lavapipe); `virtio-gpu-gl` + virglrenderer gives OpenGL; **Venus** (virglrenderer >= 1.0) gives Vulkan with `-device virtio-gpu-gl,hostmem=...,blob=true,venus=true`;
gfxstream via rutabaga is another path. Venus/virgl need a Linux host with a real GPU; our Windows/WHPX harness cannot use them. *Consequence:* the AI/graphics detection logic is tested in the VM against **lavapipe (CPU Vulkan)**
to exercise the Vulkan code path (slow, correctness only); Venus testing is an owner task on a Linux host.

### Installer and packages

**R-IN-1 Installer landscape.** Ubuntu moved to a Flutter/subiquity-based desktop installer; Anaconda is moving to a web UI (Cockpit); Kubuntu (and HSCL1) uses Calamares. We stay on Calamares (measured: LUKS2 layout already correct). Hardware/driver
choices belong **after first boot** in the Control Center (re-runnable, shows real state) rather than in new Calamares code; the installer gets only the localised unencrypted-`/boot` notice and the slideshow.

### Not yet researched (do while implementing, from primary sources)

Flow fields/Truchet/colour-harmony algorithms (W6); `qsb` flags and build integration (W6); KRunner D-Bus runner API (W5); W3C Design Tokens (DTCG) format (W7); `--cache-type-k/v` and speculative flags in the pinned llama.cpp (W2);
Hugging Face metadata for coder models (W8); Flatpak/snap trade-offs for the default browser (W9).

---

## 2. Working rules for this plan

Same loop as the hardened plan (observe -> classify -> hypothesis -> cheapest experiment -> fix -> verify -> record; max 3 fix attempts per failure; never weaken tests or protections). Additional rules:

1. **Host-testable first.** New logic is written in Rust/Python with unit tests that run on Windows and Linux (CI), then verified once in a VM. Anything that needs real hardware is an explicit owner task, with a one-page report template, and stays PLANNED/EXPERIMENTAL until reported.
2. **Typed actions only.** Anything that changes the system is an enum variant with validated arguments, a `--dry-run`, a printed summary, and `--yes` that never bypasses destructive confirmations. No shell strings.
3. **Estimates are labelled** and carry their inputs (what was measured, when, on what). A prediction that disagrees with a measurement by more than 25 % opens a task to fix the model, it is not hidden.
4. **Ports keep attribution.** Each ported algorithm has a header comment naming the source project, licence and what was and was not taken; `docs/LICENSES.md` is updated.
5. **Performance budgets.** Wallpapers/effects must degrade first under load (existing graphics profile and memory budget); a new always-running component needs a measured idle cost (CPU % and MiB) in the VM, recorded.
6. **Every user-visible string** goes through the existing i18n (EN/DE/FR); new strings without DE/FR fail the translation gate.

---

## 3. Workstreams

Effort: S = under 2 h, M = a few hours, L = a day or more. "Gate" = proof; "Evidence" = where it is recorded. `[ ]` open.

### W0 - Security carry-over (first)

- [~] **W0.1 Root directory owned by the desktop user (found 2026-11-06, high severity) - ROOT CAUSE FOUND AND FIXED IN SOURCE, image re-verification pending.** Cause: `scripts/remaster-iso.sh` created the overlay dirs as the build user, so the squashfs root inode (copied by Calamares to `/`) belonged to uid 1000. Fix: dirs created as root, `verify-image` and post-squash owner checks, e2e `system_tree_owner` check. On the LUKS install `/` is `tester:tester` (755); `ufw` warns "uid is 0 but '/' is owned by 1000"; the live session is root-owned. A uid-1000 process can rename or replace top-level directories (e.g. move `/etc` away and put its own in place) -> local privilege escalation primitive. **Gate:** cause found in the installer log/config, fix in the image or the install path, a VM install shows `/` as `0:0 755`, a test pins it (`stat /` in the e2e set), and `ufw status` prints no warning. **Evidence:** `artifacts/luks-boot-owner`, new e2e check. 
- [ ] **W0.2 Other uid-1000 files outside /home on the installed system** (5 crash files in `/var/crash`): decide whether they matter (crash reports of the live session copied into the target) and whether the installer should drop `/var/crash/*` from the copy.
- [ ] **W0.3 Add "root-owned system tree" checks to the e2e set and `verify-image.sh`** (`/`, `/etc`, `/usr`, `/var`, `/boot` owned by 0:0 and not group/world-writable) so the live image and the installed system are both covered.

### W1 - Hardware and driver detection (`hscl hw`)

- [~] **W1.1 (M) Detection core - IMPLEMENTED + unit-tested (`cli/hscl/src/hw.rs`, 8 tests incl. fixtures for an AMD APU and Secure Boot states, seeded fuzz); added to the VM check set; VM output not yet reviewed.** `hscl hw detect [--json]`: PCI devices from `/sys/bus/pci/devices` with class, vendor, device, driver in use (sysfs `driver` link), names via `pci-ids`; GPUs, network, storage controllers, audio; USB summary; CPU features; firmware/Secure Boot state (cross-checked: `mokutil`, EFI variable, kernel log). Pure parsing functions tested with fixture sysfs trees (including AMD APU, Intel iGPU, NVIDIA, virtio-gpu/bochs). **Gate:** unit tests on fixtures; VM run output reviewed; `doctor` includes it. **Evidence:** tests, `artifacts/hw-vm.json`.
- [ ] **W1.2 (M) Driver suggestions.** Read modaliases from sysfs and ask apt what package covers them (`ubuntu-drivers list --include-dkms` as oracle when present; fallback: `apt-cache` Modaliases headers). Output: device -> candidate packages -> licence class (free/proprietary/firmware) -> download size -> needs reboot -> Secure Boot note. **Never installs.** Fixtures for NVIDIA (open/proprietary/DKMS), AMD (in-kernel, ROCm), Intel (media/compute).
- [ ] **W1.3 (M) Safe install action.** `hscl hw install PACKAGE... [--dry-run]`: allow-list of package sources (the pinned Ubuntu pockets only), shows the apt simulation (removals included) and requires confirmation; proprietary packages need an extra `--accept-proprietary` and a licence line; logs to `/var/log/hscl/hw-install.log`; refuses on battery < 30 % or low disk. Privilege through the existing helper pattern or a Polkit action with fixed argv (no free text). **Gate:** unit tests for validation/refusals, VM test installs a harmless firmware/microcode package from the archive and rolls it back.
- [ ] **W1.4 (M) Control Center "Hardware & drivers" page** (read from `hscl hw detect --json`, actions call `hscl hw install --dry-run` first). First-boot hint: one dismissible notice if a proprietary driver is suggested. EN/DE/FR. Visual QA at both resolutions.
- [ ] **W1.5 (S) Vulkan/OpenCL/ROCm/CUDA presence report** (`vulkaninfo --summary`, `clinfo -l`, `rocminfo`, `nvidia-smi -L` parsed when present; "not installed" is a result, not an error); lavapipe presence recorded as "software Vulkan".
- [ ] **W1.6 (owner) Physical-hardware reports** for AMD (Radeon 680M laptop), and any Intel/NVIDIA machine available: output of `hscl hw detect --json` plus whether the suggested driver actually worked. Template in `docs/HARDWARE_REPORT_TEMPLATE.md`.

### W2 - Local AI: fit, estimate, tune (`hscl ai fit|estimate|tune-memory`)

- [~] **W2.1 (M) GGUF metadata reader in Rust - IMPLEMENTED + tested (`cli/hscl/src/gguf.rs`: bounded parser, 9 tests incl. a 6000-case seeded fuzz); verified on the real 2B model: data region 1259846912 B == type-table sum (exact).** (header, KV pairs: architecture, layers, heads, KV heads, embedding length, context, file type; tensor table for sizes). Fixtures: tiny synthetic GGUFs built by a test helper + the real 2B model from the builder. **Gate:** parsed values equal `llama-server`'s loaded values on the real model.
- [~] **W2.2 (M) `hscl ai fit MODEL --ctx N` - IMPLEMENTED for standard attention; the real default model (`qwen35`, hybrid) is flagged "KV estimate NOT valid" - hybrid support in progress against measured llama.cpp buffer sizes.**: weights + KV cache (by cache type) + compute buffer estimate -> RAM/VRAM need, per-layer offload suggestion, MoE hint (`--n-cpu-moe`); idea from gguf-parser-go (attribution). **Gate:** estimates within 15 % of the real resident size measured on the builder for the 2B model at 3 context sizes; errors recorded.
- [ ] **W2.3 (M) Bandwidth and GEMM probes**: STREAM-style triad (bytes/s) and an f32/f16-ish GEMM via the `matrixmultiply` crate (GFLOPS, single and multi thread); both with warm-up, repeat count and noise report. **Gate:** repeatability (coefficient of variation recorded), sane vs `lscpu`/DIMM facts.
- [ ] **W2.4 (M) `hscl ai estimate MODEL`**: roofline from W2.3 + W2.2 -> decode tokens/s range and prefill tokens/s range, with inputs printed. **Gate:** compare with `llama-bench` on the builder for the 2B model (CPU): within 25 % or a task opens to fix the model. Documented limits (launch-bound small models, mmap effects).
- [ ] **W2.5 (S) Unified-memory advice** (`hscl ai tune-memory`): detect APU + TTM limits (`/sys/module/ttm/parameters`, `amdgpu` params, `/sys/class/drm/card*/device/mem_info_*`), print the suggested `ttm.pages_limit` with the formula, reboot warning, rollback line; **apply is a separate, confirmed, reversible action** writing a clearly named file under `/etc/modprobe.d/` or kernel cmdline drop-in; never run in the VM.
- [ ] **W2.6 (M) MoE-aware profile**: `hscl ai profile` adds `--n-cpu-moe`/`-ot` suggestions only when the pinned backend's `--help` lists them (existing `backend_caps` mechanism); tests with fake help texts.
- [ ] **W2.7 (S) mmap/`--no-mmap` and `-ngl` guidance** for iGPU Vulkan from R-AI-3, as profile notes (no silent flag changes).
- [ ] **W2.8 (M) Vulkan path test on lavapipe in the VM**: install `mesa-vulkan-drivers` in the live VM (or confirm present), run the pinned `llama-server` Vulkan build (if the backend pin offers one) with the tiny model, confirm the log names the lavapipe device; this verifies the code path, not speed. If the pin has no Vulkan build, add one to the pin generator (verified by `--list-devices`).
- [ ] **W2.9 (owner) Radeon 680M Vulkan run** on Windows host (`llama-server --list-devices`, backend log line) and later on Linux; results into CLAIMS.

### W3 - GPU/RAM bridges and virtual GPUs (documentation + safe tooling)

- [ ] **W3.1 (S) `docs/GPU_BRIDGES.md`**: honest matrix of what exists and what we do: lavapipe/llvmpipe (CPU rendering), virtio-gpu 2D/virgl/Venus/gfxstream (VMs), Zink/DXVK/VKD3D (API translation, not shipped by default), ZLUDA (not integrated; reasons), TTM/GTT unified memory (advice only), MoE expert offload (supported via flags), RAM-backed swap/zram (already in the image). Each row: what it does, what it does not, our status.
- [ ] **W3.2 (M) VM test mode with a software GPU**: harness option to boot with `-vga virtio` and, on a Linux host with GL, `virtio-gpu-gl,venus=true` as an optional profile; Windows harness keeps `-vga std`. Output of `vulkaninfo --summary` recorded in each mode.
- [ ] **W3.3 (S) Graphics profile table update**: add `virtio`, `lavapipe/llvmpipe` as classified software renderers (minimal profile) with tests, so the desktop picks the right tuning under any VM GPU.
- [ ] **W3.4 (L, EXPERIMENTAL, last) "RAM-backed device-local heap" study**: read how Mesa exposes a host-visible device-local heap on UMA and how llama.cpp's Vulkan backend chooses buffer types; write findings; implement nothing unless a measured need exists.

### W4 - Matrix-multiplication / systolic simulator (`hscl ai gemm-sim`)

- [ ] **W4.1 (M) Analytical model**: given M,N,K, element size, peak FLOP/s, memory bandwidth, cache size -> arithmetic intensity, bound (memory/compute), predicted time; closed-form unit tests; includes the LLM decode/prefill shapes from R-AI-1.
- [ ] **W4.2 (M) Tiny cycle model of an output-stationary systolic array** (array rows x cols, tile loop, fill/drain latency, simple SRAM bandwidth stall model) producing cycles, utilisation, stalls; cross-checked against SCALE-Sim's published cycle formulas for small cases (read the paper/docs for the exact formula; record the source in the test comment). Not a clone of SCALE-Sim; a clear model with its assumptions listed.
- [ ] **W4.3 (S) CLI + JSON + a simple text visualisation** (utilisation per tile row); Control Center "AI" page shows the roofline for the machine with the measured points from W2.3 (QML canvas, no new dependency).
- [ ] **W4.4 (S) Teaching notes** in `docs/LOCAL_AI.md`: what decode vs prefill mean, why bandwidth dominates, how to read the numbers.

### W5 - Mouse and keyboard UX

- [ ] **W5.1 (M) Shortcut inventory from the real system**: boot image, dump `kglobalshortcutsrc` + KWin tiling/overview/window shortcuts, store as `docs/SHORTCUTS_MEASURED.md` (generated, not typed); diff against the table in AGENTS.md 4.5; every documented shortcut must be bound or removed from the docs. **Gate:** a test fails when the doc lists an unbound shortcut.
- [ ] **W5.2 (M) Default shortcut set** shipped as a versioned file (`hscl-desktop`): Meta+Space launcher, Meta+Enter terminal, Meta+E files, Meta+, control centre, Meta+K cheat sheet, Meta+Left/Right/Up/Down snapping (use native), Meta+1..9 deterministic behaviour (documented), Ctrl+Alt+T fallback; conflicts resolved against Plasma defaults, resolution table in the doc.
- [ ] **W5.3 (M) Shortcut cheat sheet (Meta+K)**: small QML overlay reading the **effective** bindings (via `kreadconfig6` on `kglobalshortcutsrc` + our defaults file), searchable, keyboard-closable (Esc), focus restored, EN/DE/FR. **Gate:** VM key-injection test opens it, types a query, Esc closes; screenshot at 1366x768 and 1920x1080.
- [ ] **W5.4 (M) KRunner runner for HSCL1 actions** (D-Bus runner API; read the KRunner runner docs first): results for `hscl theme set ...`, `graphics detect`, `lab status`, `hw detect`, `ai estimate`; each result maps to a fixed argv from an allow-list; no free-text execution. Idle cost measured. **Gate:** unit tests for the allow-list, VM test that typing "theme nord" offers exactly one action and runs it.
- [ ] **W5.5 (M) Tiling layouts**: ship 3 tile layouts (halves, thirds with a wide centre, quarters) in `kwinrc`; verify applied via config read; document keyboard and mouse use (shift-drag to tile); note the persistence limits (R-UX-1).
- [ ] **W5.6 (S) Mouse**: hot corners / edge actions defaults (Overview top-left, show desktop bottom-right, both off in the "classic" preset), touchpad gestures documented; no gesture is advertised unless it is configured and tested.
- [ ] **W5.7 (M) Focus and keyboard-only path** through launcher, Control Center, installer: tab order, visible focus ring, accessible names; script-driven keyboard walk in the VM with screenshots; findings fixed at the component.
- [ ] **W5.8 (S) Reduced-motion switch** wired to Plasma 6.6's standard setting (animations off in KWin, wallpaper pauses); tested by reading the setting and by screenshot differences between two frames.

### W6 - Wallpaper maker

- [ ] **W6.1 (M) CPU generator `hscl wallpaper generate`**: deterministic (seed) PNG via fBm + domain warping (+ optional flow-field lines, Truchet tiling) with a palette from the active theme tokens or a given colour; sizes up to 3840x2160; speed budget (4K in < 5 s on the builder, recorded); output to `~/Pictures/HSCL1` and applied through the existing `hscl wallpaper apply`. Read primary sources for flow fields, Truchet tiles and palette harmony before coding; cite them in the module header. **Gate:** same seed -> byte-identical file; unit tests for noise determinism; contrast check that text-bearing wallpapers keep the panel readable (luminance statistics).
- [ ] **W6.2 (M) Shader presets** in the existing wallpaper plugin: fbm-flow, domain-warp, starfield variants as `.qsb`; build step documented and automated (`qsb` from `qt6-shadertools`); half-resolution render option; pause on battery/low memory (graphics profile); VM idle-cost measurement (CPU %, MiB) at 1366x768.
- [ ] **W6.3 (S) Studio UI in the Control Center** (Wallpaper page): style, seed (shuffle), palette source (theme/accent/image), preview, "apply", "save", live cost badge ("static / light / heavy"). EN/DE/FR. Keyboard operable.
- [ ] **W6.4 (S) Static fallback**: any animated wallpaper has a CPU-baked still used when the graphics profile is minimal; tested by profile switch.
- [ ] **W6.5 (L, PLANNED) Local image-model wallpapers** (FLUX-class GGUF via the media catalogue) only after licences and one real generation are verified; not part of the stable promise.

### W7 - Look and feel (colour, tokens, theme engine)

- [ ] **W7.1 (M) Evaluate colour crates** (`material-color-utils`, `mcu-material-color`): licence, size, quantiser, maintenance, `cargo deny`; decision record in `docs/DECISIONS.md`; fallback in-tree implementation sketched.
- [ ] **W7.2 (M) `hscl appearance theme from-wallpaper IMAGE`**: quantise -> seed colour -> tonal palette -> HCSMidnight/HCSLight-compatible scheme, contrast-checked (WCAG AA for text pairs, 3:1 for non-text), written as a **user** theme (never touches system defaults, backs up, one-command restore as already required).
- [ ] **W7.3 (S) Token format**: map `themes/tokens/tokens.json` to the W3C Design Tokens (DTCG) shape (read the spec first) with a converter and a round-trip test; keep our generator outputs (QML theme, colour schemes, website CSS) green.
- [ ] **W7.4 (S) Accent sync**: Plasma accent colour follows the wallpaper when enabled (opt-in), including Qt apps; tested via config reads and screenshots in light and dark.
- [ ] **W7.5 (S) Typography and icon audit**: one UI font stack with a licence check (OFL/Apache), sizes for 1366x768 and HiDPI; icon set consistency (HSCL1 app icons vs Breeze); list in `docs/DESIGN.md`.
- [ ] **W7.6 (M) Visual QA matrix** (from the hardened plan P7.5) extended with the new pages (Hardware, Wallpaper, Shortcuts, AI estimate).

### W8 - AI coding tools

- [ ] **W8.1 (S) Catalogue additions**: Aider and Goose entries (licence, install method via `pipx`/`uv`/Flatpak/release binary, official URL, status), OpenCode kept; each entry licence-gated like the existing ones.
- [ ] **W8.2 (M) Config writers** pointing each tool at the local OpenAI-compatible endpoint (`127.0.0.1:<port>`, `--api-base` style), written as managed files with backups; verified against the real tool's `--help`/config docs, then one real round trip with the tiny local model (the tiny model may be too weak for agent work - recorded honestly).
- [ ] **W8.3 (M) Model recommendations from facts**: query Hugging Face (MCP tool) for the coder models' real licence, size, quantisation files and checksums; add catalogue entries only with verified fields; fit them with W2.2 against the machine tiers (tiny/small/medium/large). No benchmark claims.
- [ ] **W8.4 (S) `hscl code doctor`**: checks server up, endpoint reachable, context large enough for the tool's system prompt, model fits (W2.2), GPU/CPU backend, and prints one-line fixes.
- [ ] **W8.5 (S) Safety boundary** restated in docs: agents run as the desktop user, never root; MCP server read-only by default (existing); write tools opt-in.

### W9 - Installed packages and sources

- [ ] **W9.1 (M) `hscl packages list --json`**: installed desktop apps with source (apt/snap/flatpak), trust class (distro-signed archive / Flathub / snap store / local), version, size; tested on fixtures and in the VM. (AGENTS.md 5.2: show source and trust type.)
- [ ] **W9.2 (M) Default-app policy with evidence**: measure `snapd` + Firefox snap (idle memory, listening sockets, units) in the VM; compare with a Flatpak Firefox option; decide keep/offer/replace and record the decision (no silent removal of Kubuntu's choices without evidence and a rollback).
- [ ] **W9.3 (S) Bundles**: Developer / Creator / Security Lab / Local AI bundles as manifests (`packages/manifests/*.txt`) with sizes (measured via apt simulation) and licence notes; `hscl dev setup BUNDLE` uses the typed install action from W1.3.
- [ ] **W9.4 (S) Licence table** for everything in the default image generated from `dpkg-query` + copyright files (summary only; SBOM says NOASSERTION until audited).

### W10 - Installer polish

- [ ] **W10.1 (S) Localised notice** that `/boot` is unencrypted when encryption is chosen (EN/DE/FR, our own text, shown on the partition page or summary); `showNotEncryptedBootMessage` stays false.
- [ ] **W10.2 (S) Slideshow** content honest and short (what HSCL1 is, shortcuts that are actually bound, "Security Lab is planned"); screenshots at both resolutions.
- [ ] **W10.3 (S) Post-install first-boot page** (Control Center): language check, hardware & drivers suggestions (W1), firewall status, update check, recovery key reminder when LUKS is present. Skippable, re-openable.
- [ ] **W10.4 (M) Recovery key flow (hardened plan P2.5)**: `hscl security recovery add` (typed: generates a high-entropy key, `cryptsetup luksAddKey` via the helper, shows it once, never logs it), unlock test in a VM.
- [ ] **W10.5 (S) Installer log hygiene**: confirm the unique-marker passphrase is absent from the installer's own session log in the live session before the shutdown (the earlier leak scan covered only the installed system).

### W11 - Docs, website, translations

- [ ] **W11.1** Handbook pages (EN/DE/FR) for: shortcuts, wallpaper maker, hardware & drivers, local AI estimate/fit, Security Lab; link check; translation coverage report.
- [ ] **W11.2** Website: features page with only verified features; "How HSCL1 decides" (measurements) page for the AI estimate; download page keeps the honest limits.
- [ ] **W11.3** `docs/DESIGN.md` (UX principles actually applied: Fitts/Hick-style reasoning for dock and launcher, focus order, progressive disclosure; cite sources when used).

### W12 - Quality gates for this plan

- [ ] **W12.1** Every new CLI command appears in `docs/CLI.md`, has `--json`, stable exit codes and a test that runs the binary.
- [ ] **W12.2** Every new QML page has a QML test and a VM screenshot at 1366x768 and 1920x1080 in EN/DE/FR (long German strings).
- [ ] **W12.3** Idle-cost budget table (CPU %, MiB) for each new always-on component; nothing new runs when the user did not enable it.
- [ ] **W12.4** Fuzz/property tests for all new parsers (GGUF, sysfs modalias, `vulkaninfo`, wallpaper parameters) with seeded generators, mutation-checked.

---

## 4. Order of work (critical path)

1. W0 (root ownership) -> verified fix in a VM install.
2. W1.1-W1.2 (detection, suggestions) and W2.1-W2.4 (GGUF, fit, probes, estimate): host-testable, highest user value, no image rebuild needed until W1.4.
3. W5.1-W5.3 (measured shortcuts, cheat sheet) and W6.1 (CPU wallpaper generator): host-testable, visible UX gains.
4. One image rebuild for everything touching packages (podman from the hardened plan P4.0, new QML pages, KRunner runner, wallpaper presets), then the VM matrix.
5. W7 (colour from wallpaper), W8 (coding tools), W9 (packages policy), W10 (installer polish), W4 (simulator) in parallel as capacity allows.
6. W3.4 and anything marked EXPERIMENTAL last.

## 5. Owner tasks (cannot be completed by the agent)

Physical-hardware reports (W1.6, W2.9), NVIDIA/Secure Boot driver test (R-HW-2), Venus/virgl test on a Linux host with a GPU (R-HW-4), native-speaker review of DE/FR strings, production deployment decision for the website, trademark review. Each has a template or exact command in the docs.

## 6. Risk register (additions)

| Risk | Mitigation |
|---|---|
| A driver action bricks graphics on a real machine | dry-run + summary + confirmation, only archive packages, rollback line printed, never run in CI; owner reports before any "supported" claim |
| The roofline estimate is wrong for small/launch-bound models | validation task W2.4 with a 25 % threshold, documented limits, never shown without "estimate" |
| `ttm.pages_limit` advice starves the OS of RAM | cap at a fraction of RAM in code, reboot warning, rollback, advice only |
| New always-on components slow the desktop | idle-cost budget W12.3, off by default, degrade-first policy |
| Ported algorithms violate a licence | header attribution, `docs/LICENSES.md`, `cargo deny`, only GPL-compatible sources |
| Shader wallpapers drain battery | pause on battery, half-resolution option, CPU static fallback |
| Scope too large | critical path in section 4; EXPERIMENTAL items cannot block a release |

## 7. Tracking

Per task: `[x]` only with an `Evidence:` line (path or run URL). Update `docs/BUILD_LOG.md` after every loop and `docs/CLAIMS.md` for each status change. Commit on `codex/hscl1-v1`, PR to `main` on green CI, no force pushes, no secrets.


---

# ADDENDUM 2026-11-06 (second request round): naming, release path, HCS shell, viewers, office/creative suite, pentest API/MCP

Interpretation notes (stated so they can be corrected): "HCS taste mit Menue und Ordner und Fenster wie Windows 11" is read as an **HCS taskbar with a start button and start menu, a folder-centred file manager and Windows-11-like window behaviour** (centred floating taskbar, rounded windows, snap layouts, searchable start menu). "Alle Pentesting-Tools" is read as **a curated, growing set** in the isolated Security Lab, never "everything, enabled by default". "Eigene Viewer" is read as **HCS-branded image and video viewers built on proven libraries**, not new codecs.

## A1. Research findings of this round

**R-BR-1 Name.** HSCL1 stands for **Hypercharged Supreme Computing Layout 1** (owner decision). The product name stays written `HSCL1`; the long form appears in README, About screens, CLI, website, installer slideshow, `os-release` (`HSCL1_NAME_LONG`) and the handbook. `hscl1` is also a program name (same binary as `hscl`, bare call prints an overview). Research on argv[0] dispatch: clap has no default subcommand, the established pattern is `Option<Command>` with a `None` arm; BusyBox-style names use symlinks; Cargo cannot install one binary under two names, so the package ships `/usr/bin/hscl1 -> hscl`.

**R-REL-1 GitHub release limits.** Each release asset must stay below 2 GiB (a file of exactly 2 GiB was reported rejected, keep parts well below); the total size per release is not capped; one source mentions up to 1000 assets per release (unverified); upload actions have been reported to load assets into memory (upload one by one). Our 1500 MiB parts are within limits. Workflow artifacts have no 2 GiB cap, are billed by raw size, keep 1-90 days and need a GitHub login, and compression is useless on already-compressed parts (`compression-level: 0`, which the bundle job already sets). *Consequence:* keep split parts for the public download; the "Bundle one-file ISO" job is the **online merger** and its single ISO is an artifact; the release notes must say plainly that the single-file artifact needs a GitHub login and expires.

**R-REL-2 README structure for distributions.** Logo and badges, one-line description with the full name, screenshots/GIF, table of contents, download with a checksum table and a verify command, usage examples, contributing, maintenance status. *Consequence:* README overhaul (W14) with real screenshots only, a checksum table generated from `release.json`, and an honest status box.

**R-HARD-1 More hardening tools in the 26.04 archive.** `kernel-hardening-checker` 0.6.17.1-1 is in `universe` (checks kernel config, cmdline and sysctl against hardening recommendations); `lynis` is available; typical Lynis scores quoted by blogs (50s-60s fresh, 70s-80s after CIS Level 1) are not authoritative. No CIS benchmark or USG profile for 26.04 was found. *Consequence:* run `kernel-hardening-checker` and `lynis` in the VM as **measurement**, store the output, fix what is cheap and safe, document what is deliberately left; never quote blog numbers.

**R-SHELL-1 Windows-11-like shell on Plasma 6.** Plasma 6 already floats the panel and Kickoff floats above it (you cannot have a screen-edge-glued panel and a floating menu at once); centring icons is manual; a complete GPL-3+ theme (NeoWin) shows what is possible but its sounds and icons derive from Windows assets and must not be reused; rounded corners for window decorations needed an extra shader effect in older themes; KWin custom tiling provides snap-style layouts. *Consequence:* build the HCS shell from **Plasma's own components plus original assets** (our tokens, icons, sounds), chosen options verified on a booted image; no Microsoft artwork, sounds or fonts.

**R-VIEW-1 Viewers.** Gwenview (KDE) is the native image viewer; qimgv gets JPEG XL/AVIF/HEIF/RAW through plugins; nomacs covers RAW; KDE's `kimageformats` supplies Qt image-format plugins. Haruna (KDE) is a Qt/QML player on libmpv through the `MpvQt` binding (the model for a native Qt Quick video app); hardware decoding is an mpv option (`hwdec`). Architecture documentation for the viewers themselves was not found. *Consequence:* ship **HCS Image** and **HCS Video** as thin Qt Quick apps on `QImageReader`+`kimageformats` and `MpvQt`/libmpv respectively, with HCS look, keyboard-first controls, a metadata/privacy panel (EXIF view and strip) and a sandboxed decode path; verify licences (MpvQt, libmpv) before linking; keep Gwenview/Haruna installable as alternatives.

**R-OFFICE-1 Office suite.** LibreOffice 26.2 improved native Qt theming (weld) under Qt6/KF6; the 26.2 branch ends in Nov/Dec 2026; Ubuntu's own packaging historically lagged on KF6 (verify what the image really contains: `libreoffice-plasma`/`-qt6`/`-gtk3`). Collabora Office and OnlyOffice Desktop licences and sizes were not found. *Consequence:* keep **LibreOffice** as the built-in suite (measure its size on the ISO and its VCL plugin in the booted image), apply an HCS colour scheme/icon pairing, no second suite until licences and sizes are read from primary sources.

**R-IMG-1 Creative suite.** Ubuntu 26.04 test coverage names GIMP 3.2, Krita 6.0, darktable 5.4, RawTherapee 5.12; Pinta only as a snap; Krita AI Diffusion (GPL-3) is a Python plugin using ComfyUI as its backend and can manage a local ComfyUI server; GIMP has no built-in AI. *Consequence:* Creator bundle = GIMP + Krita + Inkscape + darktable as **optional bundles** (not on the ISO), Krita AI as an opt-in extra with its model/licence prompts, no snap packages in the default path.

**R-PENTEST-1 AI-driven pentest tooling.** Community MCP servers for nmap/Burp/Kali exist; one aggregator labels a Burp server "official, maintained by PortSwigger" (unverified), others are WIP and treat scope as a prerequisite, not an enforced control. Kali metapackages were renamed to `kali-tools-*` (`kali-tools-top10`, `kali-tools-wireless`, `kali-tools-web`, `kali-linux-headless` ...); `kali-linux-everything` stays forbidden. *Consequence:* we write **our own thin, typed tool layer**; community servers are treated as untrusted code and are not shipped. Scope is enforced by us: the target allow-list is part of the container spec and of the network policy, not an agent promise.

**R-MCP-1 MCP security.** The spec says tools represent arbitrary code execution; tool annotations (`readOnlyHint`, `destructiveHint`, ...) are a **risk vocabulary, not enforcement** and are untrusted unless the server is trusted; consent/elicitation must not treat silence as consent and should expire with the session; HTTP transports use OAuth 2.1. The official Rust SDK is `rmcp` (modelcontextprotocol/rust-sdk, `#[tool]` macros, stdio and Streamable HTTP). Primary spec pages (Tools, Security Best Practices, Elicitation, Authorization) were not retrieved yet and must be read before the HTTP transport is built. *Consequence:* one tool registry feeds both the local OpenAPI/REST API and the MCP server; destructive or active tools need an explicit confirmation step we implement ourselves; evaluate `rmcp` (licence, size, MSRV) against our hand-rolled stdio server.

**R-MEDIA-1 Untrusted media.** ImageMagick's `policy.xml` is default-allow (last match wins) with presets `open/limited/secure/websafe` since 7.1.1-16; restricting coders (MVG, URL fetch, PS/PDF) is the standard hardening. Nothing was found on ffmpeg protocol whitelisting or libvips for this round. *Consequence:* media tools in the API/MCP run with `secure`/`websafe`-class policies, explicit format allow-lists, resource limits, no network, in a rootless container or equivalent sandbox; ffmpeg flags and libvips behaviour are to be read from primary docs when implementing.

## A2. New workstreams

### W13 - Brand and the program `hscl1`

- [~] **W13.1 Full name everywhere (S).** `EXPANSION` constant, `hscl about`/`version --json`, overview, `os-release` `HSCL1_NAME_LONG`, README, website (EN/DE/FR), handbook intro, installer slideshow first slide, Control Center About page. **Gate:** a test greps each user-visible place for the exact string; translation parity test stays green. *CLI part implemented and tested; other places in progress.*
- [~] **W13.2 `hscl1` is a program (S).** Same binary; bare invocation prints the overview; `/usr/bin/hscl1 -> hscl` shipped by `hscl-base`; usage text shows the name actually used; `verify-image.sh` checks the symlink; a VM check runs `hscl1` and `hscl1 version --json`.
- [ ] **W13.3 `HSCL1` app entry (S).** A desktop entry named "HSCL1" (the Control Center) with the HSCL1 icon, so the name is also a launcher entry, a start-menu item and a KRunner result.
- [ ] **W13.4 Brand rules doc (S).** `docs/BRAND.md`: how the name is written (`HSCL1`), the long form, tagline, what is never claimed (not Tails, not official Kali, not Microsoft/Apple), logo usage.

### W14 - Release path and README

- [ ] **W14.1 Release `v0.1.1-alpha.0` (L).** Built from a clean WSL clone with the fixes (root-owned `/`, package modes, KDE Connect off, daemon watchdog, baseline sandbox, `hscl1`, hw/ai fit); VM checks 3x23/23 on the exact artefact; plain and LUKS2 install re-verified including `stat /` = `0:0 755`; parts of 1500 MiB + `SHA256SUMS` + manifest + SBOM; prerelease; verify workflow green; **online merger** (`Bundle one-file ISO`) run and its artifact checked (name, size, sha256 equals the manifest); notes that list what is fixed, what is verified, what is not (physical hardware, signing, Secure Boot state) and a warning on `v0.1.0-alpha.0` (world-writable payload files, `/` owned by uid 1000).
- [ ] **W14.2 Warning banner on the old release (S).** Edit only the notes of `v0.1.0-alpha.0` to add the warning; no deletion, no asset change.
- [ ] **W14.3 README overhaul (M).** Logo + badges, full name in the first line, status box, real screenshots with captions (installer encrypted layout, unlock prompt, wrong-passphrase rejection, desktop, Control Center pages, wallpaper, shortcuts overlay when it exists), feature table with VERIFIED/IMPLEMENTED/PLANNED markers, download table with sizes and SHA-256 generated from `website/data/release.json`, verify commands (`sha256sum`, `scripts/release-join.sh`, `gh attestation verify` once attestations exist), quick start for the CLI (`hscl1`), table of contents, honest limits. Tests: every image link exists, every number in the download table equals `release.json`, forbidden-claim scan, link check.
- [ ] **W14.4 Screenshot program (M).** A script that boots the image and captures the same named set at 1366x768 and 1920x1080 (installer pages, unlock prompt, desktop, launcher, each Control Center page, wallpaper studio, Security Lab, hardware page, AI fit); curated copies (small PNG/WebP, < 200 KB each) in `docs/img/`; manifest `docs/img/MANIFEST.md` with image sha256, date, resolution and what each shows.
- [ ] **W14.5 Website refresh (S).** Same screenshots and facts, EN/DE/FR, full name in the hero, verified download table.

### W15 - HCS Shell ("Windows-11-like", original)

- [ ] **W15.1 Taskbar (M).** Centred, floating, pinned + running apps, grouped windows, clock/tray at the right; implemented with Plasma's panel + our layout script; options chosen from measurement on a booted image (R-SHELL-1); touch-friendly sizes; configurable position (bottom default).
- [ ] **W15.2 Start menu (M).** Searchable, keyboard-first (`Meta`), pinned grid + recommended (recent apps only; no recent documents in privacy mode), power menu, user card; built from Plasma components (Kickoff variant or Application Dashboard) styled with our tokens; no Microsoft assets.
- [ ] **W15.3 Folders and file manager (M).** Dolphin with HCS sidebar places (Home, Documents, Downloads, Pictures, Videos, Music, Projects, SecurityLabs when enabled, Network, Trash), rounded look, breadcrumb, preview pane, quick actions (open with HCS Image/Video); file associations point to the HCS viewers.
- [ ] **W15.4 Windows (S).** Rounded corners where the compositor supports it without breaking apps, title bar buttons right, snap layouts from W5.5, Alt+Tab switcher, Overview; all verified by screenshots and key-injection tests.
- [ ] **W15.5 Settings/Control Center parity (S).** One place for appearance, display, network, security, apps; real values only.
- [ ] **W15.6 Performance guard (S).** Blur/translucency/animations follow the graphics profile and Reduced Motion; idle cost recorded (W12.3).

### W16 - HCS Image and HCS Video

- [ ] **W16.1 HCS Image (L).** Qt Quick app: open folder as a filmstrip, zoom/pan/rotate, slideshow, keyboard + mouse + touch gestures, formats via `QImageReader` + `kimageformats` (JXL, AVIF, HEIC, WebP, TIFF; RAW only if a library with a verified licence is present), EXIF panel with one-click **strip metadata and save a copy**, copy to clipboard, "open in editor" (GIMP/Krita). Decoding runs with size limits; fuzz tests on the file-opening path with malformed files; no network access. **Gate:** unit tests for the model layer, QML tests, VM screenshots, a corrupt-file corpus that must not crash the app.
- [ ] **W16.2 HCS Video (L).** Qt Quick app on MpvQt/libmpv: playlist, subtitles, audio/subtitle track menus, speed, A-B loop, thumbnails on the seek bar if cheap, hardware decoding option (`hwdec=auto-safe`), HCS controls overlay, keyboard-first; licence check first (MpvQt, libmpv); codecs only from the distro archive. **Gate:** plays a generated test clip (ffmpeg testsrc) in the VM, seek and pause verified by screenshots and mpv's own state, software decode path works on the virtual GPU.
- [ ] **W16.3 Alternatives stay installable (S):** Gwenview and Haruna entries in the Creator/Media bundles.
- [ ] **W16.4 Association and thumbnails (S):** default apps, thumbnailers (Dolphin/Plasma) still work.

### W17 - Office and creative suite

- [ ] **W17.1 Office (M).** Measure what the ISO contains (`dpkg -l libreoffice*`, VCL plugin, size); HCS colour scheme and icon theme pairing for Writer/Calc/Impress in light and dark; templates (CV, letter, report) in EN/DE/FR; default-app associations; a document round-trip test in the VM (headless convert docx -> pdf) as a smoke test; note the branch end-of-life (Nov/Dec 2026) and the update path.
- [ ] **W17.2 Creator bundle (S).** GIMP 3.2, Krita 6, Inkscape, darktable as an opt-in bundle (apt packages only, sizes measured by apt simulation, no snaps); `hscl dev setup creator` uses the typed install action (W1.3).
- [ ] **W17.3 Krita AI Diffusion (M, opt-in).** Install flow with licence/model prompts, local ComfyUI backend using our backend detection (CPU/Vulkan/ROCm), clear VRAM/RAM expectations from `hscl ai fit`; EXPERIMENTAL until one real generation is recorded.
- [ ] **W17.4 Quick image tools (S).** Context-menu actions (resize, convert, strip metadata) in Dolphin through a typed, sandboxed helper (W19.2), not shell strings.

### W18 - Pentest suite, API and MCP (authorized testing only)

- [ ] **W18.1 Typed tool registry (M).** One registry (Rust) describing each tool: id, container image/toolset, fixed argv template with typed parameters (target, ports, rate, wordlist from an allow-list), risk class (passive, active, intrusive), required scope, default timeout, output parser, annotations. Initial tools: nmap (ping/service scan with rate limit), whois, dig, tcpdump (on a lab interface only), tshark (read a given pcap), nikto/ffuf/gobuster (web, active), sqlmap (intrusive, off by default), john/hashcat identify-only; more groups follow the Kali `kali-tools-*` metapackages inside the container image, installed on request, never `kali-linux-everything`.
- [ ] **W18.2 Scope and authorization engine (M).** A project has a scope file (hosts/CIDRs the user typed, default: loopback and the lab network only); every active tool call is checked against it **before** the container starts and the container network is limited to the scope (user-mode network with an allow-list or a lab bridge); first use per project shows the authorization reminder and requires a typed confirmation (EN/DE/FR); intrusive tools need a second confirmation each time; all calls are logged locally (who/what/target/time, no secrets). **Gate:** tests that out-of-scope targets, wildcard scopes outside lab ranges, DNS-rebinding style names resolving outside scope, and chained commands are refused; a VM test shows the container cannot reach an out-of-scope address.
- [ ] **W18.3 Job API (M).** Local REST API (OpenAPI document generated from the registry), loopback only, bearer token in the user's runtime directory, job lifecycle (create -> confirm -> run -> result -> delete), size and time limits, structured results (JSON), artefacts stored in the project's lab folder.
- [ ] **W18.4 MCP server for the same registry (M).** Tools mirror the registry; passive tools are marked `readOnlyHint`; active/intrusive tools are **not directly executable**: the MCP call creates a pending job and returns "awaiting user confirmation" (the human confirms in the HSCL1 UI or CLI), because annotations are only hints; elicitation is used where the client supports it, never treating silence as consent; stdio first, Streamable HTTP with OAuth 2.1 only after the spec pages are read; evaluate `rmcp`.
- [ ] **W18.5 Control Center "Security Lab" page (M).** Projects, scope editor, tool picker with risk badges, running jobs, results, the authorization state; EN/DE/FR; keyboard operable.
- [ ] **W18.6 Safety review (S).** Threat model section: prompt injection through tool output (results are data, never instructions), tool poisoning, scope bypass, container escape assumptions, log hygiene; fuzz the parameter validators.
- [ ] **W18.7 Not shipped (statement).** Community pentest MCP servers (including any labelled official without verification), exploit frameworks enabled by default, anything that can run without a scope.

### W19 - Desktop API and MCP for AI (premade, safe)

- [ ] **W19.1 Registry for desktop tools (M).** Typed tools: `image.info/convert/resize/strip_metadata`, `video.info/probe/extract_thumbnail`, `office.convert` (headless LibreOffice to PDF), `files.search` (inside allowed roots), `system.status/hw/ai_fit`, `wallpaper.generate`, `theme.set` (existing); each with limits, allow-listed formats and paths, read-only by default; write tools require `--allow-write` or a UI confirmation like the existing MCP.
- [ ] **W19.2 Sandboxed media helper (M).** Image/video/office conversions run in a rootless container or an equivalent sandbox without network, with `policy.xml`-class limits for ImageMagick or libvips, `-protocol_whitelist file` style limits for ffmpeg (read from primary docs when implementing), time/memory caps; hostile-file tests (decompression bombs, oversized dimensions, polyglots, odd containers) must fail safely.
- [ ] **W19.3 OpenAPI + MCP generated from one source (S).** Single registry -> OpenAPI JSON and MCP `tools/list`; a test compares them; docs page generated, no hand-written drift.
- [ ] **W19.4 Local-agent recipes (S).** `docs/AI_API.md` with copy-pasteable configs for OpenCode/Aider/Goose pointing at the local endpoint and the MCP server, and a short "what an agent may and may not do" section.

### W20 - Hardening addendum

- [ ] **W20.1 Measure with the archive's tools (S).** `kernel-hardening-checker` against the booted image's kernel config, cmdline and sysctl; `lynis audit system` (read-only); results stored under `artifacts/`; a findings table in `docs/THREAT_MODEL.md` with decision per item (fix / accept / not applicable).
- [ ] **W20.2 Cheap fixes first (M).** Apply only items that demonstrably change a measured value and do not break the desktop, one commit each with the before/after, re-measure.
- [ ] **W20.3 Release gate (S).** The measured scores and the list of accepted findings are part of the release notes; no number is quoted without the command that produced it.

## A3. Updated order of work

1. W0 verified fix (rebuild + fresh install shows `/` as `0:0`), W13 (name and `hscl1`), W14.1-W14.2 (release `v0.1.1-alpha.0` with the online merger) - **before further features**, because the published alpha carries two security defects.
2. W14.3-W14.5 (README, screenshots, website) while the VM matrix runs.
3. Host-testable core work: W1, W2, W5.1-W5.3, W6.1, W18.1-W18.2 (registry and scope engine), W19.1 (registry), W16.1 model layer.
4. One image rebuild for the new packages/apps (podman, viewers, shell layout, KRunner runner), then the VM matrix and screenshots.
5. Remaining shell/office/creative work and the HTTP/MCP transports after the primary spec pages are read.
