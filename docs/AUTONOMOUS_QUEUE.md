# Autonomous work queue — live

Updated: 2026-11-09. Owner: the autonomous agent loop (2-minute tick). This is the single ordered
queue; each item states the smallest verifiable slice and the exact gate that closes it. A tick takes
the **first open item that fits the remaining time**, never weakens a test, and records the result in
`docs/BUILD_LOG.md`.

Status: `OPEN` · `DOING` · `BLOCKED` (with reason) · `DONE` (with evidence) · `VM-PENDING` (code done,
booted-artifact evidence missing).

## Now

| ID | Item | Gate | Status |
|---|---|---|---|
| Q-01 | Desktop icon label legibility (Plasma FolderView foreground/shadow) | static config test + VM screenshot | **VM-VERIFIED 2026-11-09** — labels are white and legible on the new candidate; same root cause as Q-07 |
| Q-02 | Launcher duplicate/mixed-language sections | `test_menu_file.py` + bilingual VM screenshot | **VM-VERIFIED (English) 2026-11-09** — one entry per category, no duplicates; DE/FR titles come from `.directory` files and are untested in a running session |
| Q-03 | Recapture the handbook screenshot with a visible handbook window | pixel check of the caption subject | **VM-VERIFIED 2026-11-09** — the candidate run opened the desktop handbook icon; the capture (Firefox on `/usr/share/doc/hscl-handbook/en/index.html`) replaces the false one, is listed in the manifest with `source_iso`, and is back in the README |
| Q-04 | Installer top-bar clipping + localized step labels | VM screenshot at 1280×800 | **VM-VERIFIED 2026-11-09** — centred 1104×668 window, top bar visible, logo fully visible; "Notes" step present. Step labels follow Calamares' own translation once a language is chosen (not exercised). Truncated `shortVersionedName` fixed and guarded. |
| Q-05 | Reconcile `CLAIMS.md` artifact identity with `VERSION`/README | `docs/CLAIMS.md` header matches `VERSION` and release assets | DONE (2026-11-09, header names v0.1.4-alpha.0 and marks every row artifact-bound) |
| Q-06 | Qt/QML test runner in WSL (`qt6-declarative-dev-tools`) | `qmltestrunner` + `qmllint` execute `tests/qml_plugin` and `tst_pages.qml` | DONE (2026-11-09: tools live in `/usr/lib/qt6/bin`; `scripts/dev/qml-gate.sh` runs both suites + qmllint, wired into `forge check` as `qml (WSL)`) |
| Q-07 | Theme fix needs booted-artifact proof | VM screenshot of Dolphin/Konsole dark | **VM-VERIFIED 2026-11-09** — Dolphin 27.2 and Konsole 37.1 mean luminance (dark) vs 230.1 before |
| Q-08 | Palette guard in `hscl doctor` and the Control Center | Rust tests + `test_theme_defaults.py` | DONE (2026-11-09: `doctor` gained a `theme` check — pass on `HCS*`, warn on any other scheme, skip when no kdeglobals is readable; `SecurityPage` labels it EN/DE/FR) |
| Q-09 | `forge check` false red on a transient WSL launcher failure | retry-once-on-empty-stderr + 2 tests | DONE (2026-11-09, `test_bash_gate_retries_a_launcher_failure_with_empty_stderr`) |
| Q-21 | `hscl appearance mode` / `dock position` were no-ops that reported success | Rust tests + docs | DONE (2026-11-09: mode now applies `plasma-apply-colorscheme` (dark→HCSMidnight, light→HCSLight, auto records only), dock position scripts the non-top Plasma panel through `qdbus6`; both fail loudly instead of pretending). Live-desktop result `VM-PENDING`. |
| Q-22 | Docs link gate | `tests/unit/test_doc_links.py` | DONE (2026-11-09, 148 Markdown files, 0 broken links) |
| Q-23 | Website build accepted unknown flags as an output path (`--help` created a directory) | `tests/unit/test_website_build.py` | DONE (2026-11-09, argparse + EN/DE/FR page check) |
| Q-24 | WCAG AA contrast for every text/surface token pair | `tests/unit/test_token_contrast.py` | DONE (2026-11-09, four themes × four foregrounds × three surfaces, all ≥ 4.5:1; selected text on accent ≥ 4.5) |
| Q-25 | Miner CLI slice with guards | Rust + Python tests | DONE (2026-11-09: `status`, `probe`, `plan`, `ota`, `flash`; private hosts only; SHA-256; authorization phrase; 13 tests) |
| Q-26 | Miner facts from current upstream sources | `docs/miner/FIRMWARE_RESEARCH.md` | DONE (2026-11-09: v2.15.4 upstream, fork 4.0.2-rc1, OTA limits documented with sources) |
| Q-27 | MCP exposure for the miner | `test_hscl_mcp.py` (20 read-only tools) | DONE (2026-11-09: `hscl_miner_status`, `hscl_miner_probe`) |
| Q-28 | Hardware flash on a real device | device transcript + hash before/after | **DONE 2026-11-09** — `timsminer` (board 201) flashed to `v4.0.2-rc1` via `hscl miner ota`, SHA-256 `ecb7463…`, 263 s, MAC/board unchanged; pre/post telemetry recorded |
| Q-29 | ESP-Miner fork README/flashing docs on par | its own repo branch + honest WiFi/USB section | DONE (2026-11-09: `docs/FLASHING.md` rewritten with both paths, limits and recovery; `flashing.md` is a pointer; pushed to the fork branch) |
| Q-30 | Firmware build reproducible on Windows | build script + IDF env vars | DONE (2026-11-09: `build_hscl.bat` documents `IDF_TOOLS_PATH=E:\esp\tools`, UTF-8, submodule init) |
| Q-31 | Miner telemetry baseline | `docs/miner/TELEMETRY.md` | DONE (2026-11-09: pre/post flash snapshot + series, HTTP timeout observation) |
| Q-32 | Recovery build after NVS loss (display + network) | serial log + mining resumed | DONE (2026-11-09: `ESP_MINER_BOARD_VERSION=201` fixed `Display init failed`; `ESP_MINER_CONFIG_AP_STUCK=1` keeps `Bitaxe_DD3C` up; pool restored via `pools[]`, 466 GH/s after restart) |
| Q-33 | Network discovery + local data API | `hscl miner discover`, `hscl miner serve`, MCP `hscl_miner_discover` | DONE (2026-11-09: found `.61/.66/.80` by MAC; `/v1/health`, `/v1/miners`, `/v1/miner?host=` with background polling) |
| Q-34 | Diagnostics bugs | probe retry, series gaps, reset capture, stale-binary guard | DONE (2026-11-09) |
| Q-35 | Native `miner series` + full metrics in the API | Rust tests + live run | DONE (2026-11-09: `DeviceInfo` carries hashrate/1m/10m/1h, power, shares, best diff, uptime, RSSI, pool; `hscl miner series --count/--interval/--out`) |
| Q-36 | WebSocket push (`/api/ws/live`) instead of polling | client + tests | **DONE 2026-11-09** — dependency-free client (handshake, SHA-1 accept check, frame parser, pong) + `hscl miner watch`; live run streamed the full snapshot and ~500 ms diffs |
| Q-37 | Per-device builds for `.66` and `.80` | firmware + flash log | **DONE (images built, deliberately not flashed) 2026-11-09** — recovery images for board 201 and 601 with AP fallback and baked credentials; the healthy miners keep their NVS |
| Q-39 | Discovery robustness on busy single-threaded devices | two-pass scan + settle + retry | DONE (2026-11-09) — burst collects open ports, sequential pass with delays and one retry; residual flakiness documented (`probe <ip>` is authoritative) || Q-38 | Pool slot API (`PUT /api/system/pools/<n>`) in the CLI | command + tests | **DONE 2026-11-09** — `hscl miner pool list|set` with validation (index 0–7, bare host, SV1/SV2), masked wallet, authorization phrase, dry-run; 4 Rust + 3 CLI tests |
| Q-20 | Prevent QML lint regression | `QML_WARN_BUDGET` ratchet in `scripts/dev/qml-gate.sh` | DONE (2026-11-09, budget 152, verified to fail at 10) |
| Q-19 | Reduce `qmllint` `[unqualified]` warnings in the Control Center (23 of 152) | `qml-gate.sh` warning budget lowered | OPEN — 23 come from `Main.qml`'s C++ context property `cli` and from Repeater delegates reading outer ids; the rest are PlasmaCore imports in the wallpaper plugin |

## Next (after Now)

| ID | Item | Gate | Status |
|---|---|---|---|
| Q-10 | Build a candidate from the fixed tree (`forge build`) and boot it UEFI | BUILD_LOG entry with source commit, ISO sha256, boot result | **VM-VERIFIED 2026-11-09** — `HSCL1-qa-2026-11-09-amd64.iso` (`118029de…`, source `c8a433a`), desktop reached in 251/257 s under UEFI+WHPX |
| Q-11 | LUKS2 install on a disposable disk from the same candidate | installed boot + wrong/correct passphrase | OPEN |
| Q-12 | Re-run the 12 in-guest tracks against the new candidate | `verify_in_guest_tracks.py` output | OPEN |
| Q-13 | Regenerate all showcase screenshots from that candidate | manifest.json with source commit | OPEN |
| Q-14 | Accessibility pass: focus order, labels, reduced motion (QML + docs) | review notes + QML test | OPEN |
| Q-15 | `hscl` docs ↔ CLI drift check for every new subcommand | `cli_doc_lists_every_command` | OPEN |
| Q-16 | Secure Boot guest state read (`mokutil`/efivars) in the VM | recorded evidence hash | OPEN |
| Q-17 | Privacy mode: packet-capture evidence for DNS/IPv6/Tor-unavailable | capture artefact + doc row | BLOCKED (needs candidate VM) |
| Q-18 | Security Lab: in-guest rootless Podman run from the candidate | `hscl lab` in-guest transcript | OPEN |

## Rules for every tick

1. Read the diff first (`git status`, `git diff`); never overwrite unrelated work.
2. One item per tick. Smallest patch that is provable.
3. Run the narrowest gate first, then `python scripts/forge.py check` when the change touches Python,
   shell, docs or packaging; `cargo test --all` when it touches `cli/`.
4. Never mark a row `DONE` without the command output that proves it. `skipped` is not a pass.
5. Write the result into `docs/BUILD_LOG.md` (phase, command, counts, artifact hash) and flip the row here.
6. If an item needs a booted VM and no candidate exists, mark `BLOCKED` with the reason and move on.
7. Three failed remedies on one item → write the blocker, then continue with the next independent item.
