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
| Q-01 | Desktop icon label legibility (Plasma FolderView foreground/shadow) | static config test + VM screenshot | VM-PENDING — same root cause as Q-07 (light session palette ⇒ dark text on dark wallpaper); verify together |
| Q-02 | Launcher duplicate/mixed-language sections | `test_menu_file.py` + bilingual VM screenshot | VM-PENDING — root cause was localised `<Name xml:lang>` children preventing KDE from merging our sections with the base menu. Titles now live in six `hscl-*.directory` files (`/usr/share/desktop-directories`), guarded by `test_submenus_carry_only_the_default_name` and `test_every_section_references_a_localised_directory_file`. Bilingual VM run still required. |
| Q-03 | Recapture the handbook screenshot with a visible handbook window | pixel check of the caption subject | OPEN — the false capture (`13_offline_handbook.png`) and `15_desktop_final.png` were removed from README and manifest; `tests/unit/test_showcase_evidence.py` keeps links and manifest consistent. Needs the next candidate. |
| Q-04 | Installer top-bar clipping + localized step labels | VM screenshot at 1280×800 | VM-PENDING — `branding.desc` now uses `windowExpanding: normal`, `windowSize: 1100px,640px`, `windowPlacement: center` (guard: `tests/unit/test_installer_branding.py`). Step labels come from Calamares' own translations and apply after the language is chosen; no code change. |
| Q-05 | Reconcile `CLAIMS.md` artifact identity with `VERSION`/README | `docs/CLAIMS.md` header matches `VERSION` and release assets | DONE (2026-11-09, header names v0.1.4-alpha.0 and marks every row artifact-bound) |
| Q-06 | Qt/QML test runner in WSL (`qt6-declarative-dev-tools`) | `qmltestrunner` + `qmllint` execute `tests/qml_plugin` and `tst_pages.qml` | DONE (2026-11-09: tools live in `/usr/lib/qt6/bin`; `scripts/dev/qml-gate.sh` runs both suites + qmllint, wired into `forge check` as `qml (WSL)`) |
| Q-07 | Theme fix from fix #5 needs booted-artifact proof | VM screenshot of Dolphin/Konsole dark | VM-PENDING |
| Q-08 | Palette guard in `hscl doctor` and the Control Center | Rust tests + `test_theme_defaults.py` | DONE (2026-11-09: `doctor` gained a `theme` check — pass on `HCS*`, warn on any other scheme, skip when no kdeglobals is readable; `SecurityPage` labels it EN/DE/FR) |
| Q-09 | `forge check` false red on a transient WSL launcher failure | retry-once-on-empty-stderr + 2 tests | DONE (2026-11-09, `test_bash_gate_retries_a_launcher_failure_with_empty_stderr`) |
| Q-21 | `hscl appearance mode` / `dock position` were no-ops that reported success | Rust tests + docs | DONE (2026-11-09: mode now applies `plasma-apply-colorscheme` (dark→HCSMidnight, light→HCSLight, auto records only), dock position scripts the non-top Plasma panel through `qdbus6`; both fail loudly instead of pretending). Live-desktop result `VM-PENDING`. |
| Q-22 | Docs link gate | `tests/unit/test_doc_links.py` | DONE (2026-11-09, 148 Markdown files, 0 broken links) |
| Q-23 | Website build accepted unknown flags as an output path (`--help` created a directory) | `tests/unit/test_website_build.py` | DONE (2026-11-09, argparse + EN/DE/FR page check) |
| Q-24 | WCAG AA contrast for every text/surface token pair | `tests/unit/test_token_contrast.py` | DONE (2026-11-09, four themes × four foregrounds × three surfaces, all ≥ 4.5:1; selected text on accent ≥ 4.5) |
| Q-20 | Prevent QML lint regression | `QML_WARN_BUDGET` ratchet in `scripts/dev/qml-gate.sh` | DONE (2026-11-09, budget 152, verified to fail at 10) |
| Q-19 | Reduce `qmllint` `[unqualified]` warnings in the Control Center (23 of 152) | `qml-gate.sh` warning budget lowered | OPEN — 23 come from `Main.qml`'s C++ context property `cli` and from Repeater delegates reading outer ids; the rest are PlasmaCore imports in the wallpaper plugin |

## Next (after Now)

| ID | Item | Gate | Status |
|---|---|---|---|
| Q-10 | Build a candidate from the fixed tree (`forge build`) and boot it UEFI | BUILD_LOG entry with source commit, ISO sha256, boot result | OPEN |
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
