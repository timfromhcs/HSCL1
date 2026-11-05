# Claims and their evidence (2026-11-05)

Rule: nothing is stated as working without evidence. "unit-tested" means only the code logic ran in tests; it is **not** a claim that the feature works on real hardware or in the image.

| Feature | Status | Evidence / what is missing |
|---|---|---|
| Main ISO boots to the HCS desktop (UEFI/BIOS, QEMU+WHPX) | VM-VERIFIED | screenshots in `artifacts/` (not in git), BUILD_LOG |
| Installer installs to a 40 GiB virtual disk and the installed system boots and logs in | VM-VERIFIED (QA build of an earlier image) | BUILD_LOG "Install verification" |
| Workshop daemon starts through udev when the hypervisor provides the `hscl.api` port, answers `status`, accepts hook-pushed files | VM-VERIFIED | `artifacts/e2e1/report.json`, `artifacts/e2e2` run log in BUILD_LOG |
| Respin: squashing the live state | VM-VERIFIED (373 s, first run) | BUILD_LOG |
| Respin: a new ISO that boots and contains an API-pushed change | **NOT YET VERIFIED** (the xorriso source-device bug was fixed; proof run in progress) | `scripts/workshop/e2e_respin.py` |
| Number-rain wallpaper and the other effects: animation logic, stop when animations are off, parameter clamping | unit-tested (QML tests, 14 pass) | `tests/qml_plugin` |
| Rain/effects rendering on the real desktop, CPU cost in a VM | **NOT VERIFIED** | needs a VM screenshot series |
| `hscl ai` hardware profile, model catalog, download with sha256 check | unit-tested (49+ tests); download + verify also run against the real file | smoke test |
| Real local inference: pinned llama.cpp b12130 (CPU build, sha256 verified) with `qwen3.5-2b-abliterated` Q4_K_M, 127.0.0.1 only, chat completion answered | VERIFIED on the WSL builder (CPU, 4 threads) | `scripts/ai-smoke-test.sh`; server reported 21.55 tokens/s for one 2-token reply - a sanity number, **not a benchmark** |
| Vulkan/GPU inference, MTP, TurboQuant | **NOT VERIFIED**; the profile engine only enables TurboQuant/MTP if the backend's `--help` lists them (the pinned upstream build was not checked to), no speed is claimed | needs a GPU host and a fork/build that advertises them |
| `hscl graphics` autodetect and apply | unit-tested | not run in a VM with a real session |
| `hscl wallpaper` presets/apply | unit-tested | not run against a live Plasma session |
| `hscl mcp` stdio server | unit-tested + one real stdio round trip (initialize, tools/list, one tool call) | not yet driven by a real agent |
| `hscl code` / HCS Coder: catalog, licence gate, install command generation, OpenCode config writer | unit-tested | **the OpenCode config format and the installs were not run against the real tools**; licences marked "not confirmed" stay gated |
| Abliterated models | catalogued with a warning; the real 2B model answered a prompt | quality and safety are not assessed |
| Memory manager (zram, earlyoom, slices), media AI (image gen, image-to-3D, rigging), Blender/Godot MCP, RSI loop | **PLANNED, not implemented** | see the plans in `docs/superpowers/plans/` |
