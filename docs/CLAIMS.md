# Claims and their evidence (2026-11-05)

Rule: nothing is stated as working without evidence. "unit-tested" means only the code logic ran in tests; it is **not** a claim that the feature works on real hardware or in the image.

| Feature | Status | Evidence / what is missing |
|---|---|---|
| Main ISO boots to the HCS desktop (UEFI/BIOS, QEMU+WHPX) | VM-VERIFIED | screenshots in `artifacts/` (not in git), BUILD_LOG |
| Installer installs to a 40 GiB virtual disk and the installed system boots and logs in | VM-VERIFIED (QA build of an earlier image) | BUILD_LOG "Install verification" |
| Workshop daemon starts through udev when the hypervisor provides the `hscl.api` port, answers `status`, accepts hook-pushed files | VM-VERIFIED | `artifacts/e2e1/report.json`, `artifacts/e2e2` run log in BUILD_LOG |
| Respin: squashing the live state | VM-VERIFIED (373 s, first run) | BUILD_LOG |
| Development loop: push a file and updated tools into a running live VM through the API, respin inside the guest (420 s), extract the ISO (sha256 matches its manifest), boot it (110 s), the daemon answers with the pushed code (`live: true`) and the pushed proof file is present | VM-VERIFIED, with one limit: the proof was matched by its file-name prefix `hscl-respin-proof-` (the uuid of the first phase was not recorded; later runs record it) | `artifacts/e2e2/report.json`, `respun.manifest.json` (not in git), `scripts/workshop/e2e_respin.py` |
| Wallpaper effects: animation logic, stop when animations are off, parameter clamping | unit-tested (QML tests, 14 pass) | `tests/qml_plugin` |
| Rain/effects rendering on the real desktop, CPU cost in a VM | **NOT VERIFIED** | needs a VM screenshot series |
| `hscl ai` hardware profile, model catalog, download with sha256 check | unit-tested (49+ tests); download + verify also run against the real file | smoke test |
| Real local inference: pinned llama.cpp b12130 (CPU build, sha256 verified) with `qwen3.5-2b-abliterated` Q4_K_M, 127.0.0.1 only, chat completion answered | VERIFIED on the WSL builder (CPU, 4 threads) | `scripts/ai-smoke-test.sh`; server reported 21.55 tokens/s for one 2-token reply - a sanity number, **not a benchmark** |
| Vulkan/GPU inference, MTP, TurboQuant | **NOT VERIFIED**; the profile engine only enables TurboQuant/MTP if the backend's `--help` lists them (the pinned upstream build was not checked to), no speed is claimed | needs a GPU host and a fork/build that advertises them |
| `hscl graphics` detect | VM-VERIFIED (see above) | |
| `hscl graphics apply` / autotune at login | unit-tested; **apply not yet run in a session; autotune is not started automatically at login yet** | |
| `hscl wallpaper apply` against a live Plasma session | unit-tested + dry-run in the VM; **real apply not yet verified** | |
| `hscl mcp` stdio server | unit-tested + one real stdio round trip (initialize, tools/list, one tool call) | not yet driven by a real agent |
| `hscl code` / HCS Coder: catalog, licence gate, install command generation, OpenCode config writer | unit-tested | **the OpenCode config format and the installs were not run against the real tools**; licences marked "not confirmed" stay gated |
| Abliterated models | catalogued with a warning; the real 2B model answered a prompt | quality and safety are not assessed |
| Memory protection in the live VM (4 GB RAM): `earlyoom` active; `/dev/zram0` swap 1.9 G (half of RAM) at priority 100 with zstd selected; `vm.swappiness=100`, `vm.page-cluster=0`; `hscl-ai.slice` MemoryHigh 2456178688 (60 %), MemoryMax 3070222336 (75 %) | VM-VERIFIED (configuration applied and active); **protection effect under real memory pressure not tested** | `artifacts/e2e3/cli-report.json` |
| `hscl` inside the live VM as the desktop user: `version`, `memory status/budget`, `graphics detect` (QEMU standard VGA classified Software -> minimal), `ai model list/profile` (tier tiny, plan computed under the 60 % budget), `wallpaper list/apply --dry-run`, `code list`, `mcp` stdio round trip | VM-VERIFIED (commands run and return the shown data) | `artifacts/e2e3/cli-report.json` |
| `hscl system updates --check` in the live VM printed 0 updates | **Not a statement that the system is up to date**: the image has stale/empty package lists; the same command on the builder found 33 pending packages | |
| Listening sockets in the live VM | observed: KDE Connect on `*:1716` (TCP and UDP), mDNS on `*:5353`, CUPS on loopback `:631`, resolver/NTP on loopback; the firewall denies inbound by default; **KDE Connect should be off by default - open item** | `artifacts/e2e3/cli-report.json` |
| Memory manager apply paths beyond the above, media AI (image gen, image-to-3D, rigging), Blender/Godot MCP, RSI loop | **PLANNED, not implemented** | see the plans in `docs/superpowers/plans/` |
