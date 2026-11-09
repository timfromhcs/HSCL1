# HSCL1 project assessment and visual QA — 2026-11-09

Scope: repository `timfromhcs/HSCL1` at `d817093` (main), verified on the Windows development host plus
Ubuntu 26.04 WSL for the POSIX-only gates. VM boot/install was **not** re-run in this session; all image
statements below come from committed screenshots, BUILD_LOG and the release assets, and are labelled
accordingly.

This document is the honest picture: what works, what is fragile, what is broken, and what the next
queue is. Every fixed item names the test that now guards it.

---

## 1. What is genuinely good

| Area | Evidence |
|---|---|
| Automated gate breadth | `python scripts/forge.py check` runs pytest (Windows), changed-test pytest in WSL, `bash -n`, `shellcheck`, secret scan and the doc-command test. All six steps PASS today. |
| Rust CLI quality | `cargo test --all` → **245 passed, 0 failed**; `cargo clippy --all-targets -D warnings` clean; `cargo fmt --check` clean. 26 real subcommand groups exist, no stubs in help. |
| Python suite size | 887 passed / 22 skipped / 53 deselected in the fast tier. Skips are explicitly justified (no KVM, no Qt test runner, no clone/interpreter for the differential parser test). |
| Release reality | Tag `v0.1.4-alpha.0` exists, is a prerelease, and its three parts + `SHA256SUMS` + SBOM match the README checksums and the GitHub API digests. No fake download button. |
| Honesty of claims | `docs/CLAIMS.md` and `docs/KNOWN_LIMITATIONS.md` are unusually candid (upstream Calamares defects, unverified Vulkan, DRAT RAT gap, "not Tails", `/boot` unencrypted). |
| Security defaults in code | UFW/AppArmor checks, forbidden-APT-repository detection, redaction in `hscl doctor`, mandatory `--yes` attestation in `hscl lab`, loopback-only AI server, path-traversal rejection in appearance/theme handling. |
| Documentation surface | Trilingual README, handbook EN/DE/FR, CLI reference generated from the clap tree, SHORTCUTS, THREAT_MODEL, installer facts. |

## 2. What is weak or fragile

1. **Evidence and documentation drift.** `docs/CLAIMS.md` opens with source `0ef918a` and the
   `0.1.3-alpha.0` image (`2e30b750…`), `README.md` claims `0.1.4-alpha.0` (`a7e055a7…`), and the last
   BUILD_LOG entry describes a *third* candidate (`5,027,004,416` bytes, `aa9a5200…`) that is not present
   in `artifacts/` any more. Three artifacts, one undated reconciliation rule.
2. **Visual identity is only skin deep in the shipped image.** The Plasma shell is dark; Qt apps are light
   (see §4). The design tokens are generated correctly, so this is an application/default-selection gap,
   not a palette gap.
3. **Localization coverage is narrower than the README implies.** Control Center strings are EN/DE/FR and
   the handbook is complete, but the launcher categories were visibly mixed (English + French) and the
   installer is English-only.
4. **Screenshot evidence quality.** One showcase image (`13_offline_handbook.png`, captioned "Trilingual
   Offline Handbook") contains no handbook window — just the desktop. The claims table links that image.
5. **Test-harness portability.** The suite only went green on Windows after fixing binary selection and
   UTF-8 decoding; three product defects were hidden behind it (see §3). A developer on this host could
   not have trusted "all tests pass".
6. **No Qt/QML test execution on this host.** `qmltestrunner`/`qmllint` are absent from both Windows and
   the WSL image, so QML edits are only statically reviewed here. That is a real gate hole.

## 3. Bugs found and fixed in this session

| # | Bug | Root cause | Fix | Guard |
|---|---|---|---|---|
| 1 | 21 pytest failures, 5 of them `WinError 193` | `_find_hscl()` preferred the Linux ELF `target/debug/hscl` over `hscl.exe`; `hscl ai storage set /tmp/…` was rejected by `Path::is_absolute()` on Windows; `subprocess(text=True)` decoded UTF-8 with cp1252 | Platform-aware binary lookup in `test_{ai,appearance,dev,system}_cli.py`; `is_absolute_any_platform()` in `cli/hscl/src/ai.rs`; `encoding="utf-8", errors="replace"` in 11 CLI test modules | full suite now 0 failures |
| 2 | Clipped health-check row in Control Center | `RowLayout` sizes from implicit height, wrapped `Text` reports one line | `Layout.preferredHeight` bound to `valueItem.contentHeight` in `components/Row2.qml` | QML test would catch a regression when a runner is available |
| 3 | Raw check ids (`arch`, `apt-sources`, `secure-boot`) shown to users | page bound `modelData.id` directly | `checkLabel()` maps known ids to `qsTr` labels, unknown ids fall through | `tst_pages.qml` asserts "Architecture" is rendered |
| 4 | `hscl ai detect` reported 0 CPU threads on non-Linux hosts | `/proc/cpuinfo`-only detection | falls back to `std::thread::available_parallelism()` | `ai::ai_subcommand_tests::test_plan_setup_dry_run` |
| 5 | Shell dark / Qt apps light (from screenshots) | new users inherit Kubuntu's light `ColorScheme`; the LnF default alone did not change widget palettes | hook patches `ColorScheme=HCSMidnight` in `kubuntu-default-settings/kf5-settings/kdeglobals`; image gate verifies it | `tests/unit/test_theme_defaults.py` |
| 6 | Missing FR strings for the new labels | catalogue only had the old set | `Architecture` / `Mémoire` / `Sources APT` added to `hscl-cc_fr.ts`, DE equivalents too | `tests/unit/test_cc_i18n.py` (fails on any missing qsTr translation) |

Verification after the fixes: `forge check` → 6/6 PASS; `cargo test --all` → 245 PASS; clippy/fmt clean.

## 4. Visual QA (screenshots in `docs/img/showcase/`)

Reviewed at native 1280×800 (the capture resolution). Findings are grouped by severity.

### Critical

| Finding | Evidence | Note |
|---|---|---|
| Desktop icon labels are illegible (dark navy on near-black, italic, no plate) | `01_desktop_clean.png`, `13_offline_handbook.png`, `10_app_dolphin.png` | Affects the three shipped desktop entries (`HSCL1 Control Center`, `HSCL1 Handbook`, `Install HSCL1`). This is the first thing a new user sees. |
| Qt applications ignore the HCS dark palette | `10_app_dolphin.png` (white content, light sidebar), `08_terminal_hscl_status_doctor.png` (light Konsole toolbar) | Addressed by fix #5; needs a remaster + VM screenshot to confirm. |

### Major

| Finding | Evidence | Note |
|---|---|---|
| Launcher shows duplicate categories in mixed languages (`Development` **and** `Développement`, `Graphics` **and** `Graphisme`, `Bureau`) | `03_app_launcher_kickoff.png` | The session was French, so the English entries come from the merged HSCL1 menu while the French ones come from the stock menu. Two menus, one list. |
| Installer sidebar logo is clipped by the top bar | `11_installer_welcome.png` | Calamares is fullscreen and does not reserve the panel strut; the hexagon logo loses its top. |
| Captioned handbook screenshot shows no handbook | `13_offline_handbook.png` | Release evidence is misleading; must be recaptured or the caption changed. |
| Installer content stays in the light Calamares palette and English step labels | `11`, `12` | Consistent with KNOWN_LIMITATIONS, but visually the installer looks like a different product. |

### Minor

| Finding | Evidence |
|---|---|
| Search placeholder "Search…" and category names are not localized in the launcher | `03` |
| Dolphin ships stock Breeze blue folder icons and lacks the documented "Projects" section | `10` |
| Wallpaper "matrix rain" makes the desktop look like a broken terminal; the hex-digit field is visually noisy behind icons | `01` |
| Security page offers no action (no firewall profile switch) — read-only by design so far | `06` |
| Notification-area icons are monochrome and small but consistent; no issue | `01` |

### Contrast measurements

Sampled from the real PNGs (Pillow, `scripts/dev/visual_qa_probe.py`):

| Region | Brightest/darkest pixel contrast | Verdict |
|---|---|---|
| Top bar text vs bar | 14.9:1 | pass |
| Dock icons vs dock | 18.4:1 | pass |
| Control Center cards | 15.9:1 | pass |
| Installer sidebar | 15.9:1 | pass |

Card/shell contrast is fine. The illegible desktop labels are **not** a contrast-ratio failure of the
palette but a wrong foreground colour for that surface, which is why they need a targeted fix rather
than a token change.

## 5. Open defects and gaps (queue seeds)

1. Desktop icon label colour/shadow (Plasma FolderView) — needs a `plasma-org.kde.plasma.desktop-appletsrc`
   or desktop-theme fix plus a screenshot in a booted VM.
2. Launcher duplicate sections — decide between (a) `.directory`-based localization of the merged menu and
   (b) dropping the merged menu and relying on the stock menu. Verify in a bilingual VM run.
3. Recapture `13_offline_handbook.png` with the handbook window visible; re-check every showcase caption
   against its pixels.
4. Installer top-bar clipping and EN/DE/FR installer labels.
5. Reconcile `CLAIMS.md` header (0.1.3) with `VERSION`/README (0.1.4) and record which artifact each row
   refers to.
6. Install a Qt/QML test runner in WSL (`qt6-declarative-dev-tools`) so QML gates actually execute.
7. Rebuild a candidate from the fixed tree and re-run the UEFI/BIOS/Secure Boot + LUKS matrix.

## 6. Status vocabulary used here

`PLANNED` → `IMPLEMENTED` → `TESTED` (unit/integration) → `VM-VERIFIED` (booted artifact) →
`HARDWARE-VERIFIED`. Nothing in this document promotes a row without the matching evidence; the theme
fix is `IMPLEMENTED` and explicitly not `VM-VERIFIED`.
