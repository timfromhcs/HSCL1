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
| Q-01 | Desktop icon label legibility (Plasma FolderView foreground/shadow) | static config test + VM screenshot | OPEN |
| Q-02 | Launcher duplicate/mixed-language sections | `test_menu_file.py` + bilingual VM screenshot | OPEN |
| Q-03 | Recapture `13_offline_handbook.png` with a visible handbook window | pixel check of the caption subject | BLOCKED (needs booted candidate) |
| Q-04 | Installer top-bar clipping + localized step labels | VM screenshot at 1280×800 | OPEN |
| Q-05 | Reconcile `CLAIMS.md` artifact identity with `VERSION`/README | `docs/CLAIMS.md` header matches `VERSION` and release assets | DOING |
| Q-06 | Qt/QML test runner in WSL (`qt6-declarative-dev-tools`) | `qmltestrunner` + `qmllint` execute `tests/qml_plugin` and `tst_pages.qml` | OPEN |
| Q-07 | Theme fix from fix #5 needs booted-artifact proof | VM screenshot of Dolphin/Konsole dark | VM-PENDING |
| Q-08 | Add `hscl doctor`/Control Center guard for the new palette default | `test_theme_defaults.py` extended | OPEN |

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
