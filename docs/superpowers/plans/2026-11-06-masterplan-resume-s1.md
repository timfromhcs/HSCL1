# HSCL1 Masterplan R1: Wiederaufnahme nach 0.1.2-alpha.0 (S0 abschliessen, S1 ausfuehren)

> **For agentic workers:** REQUIRED SUB-SKILL: superpowers:executing-plans (oder subagent-driven-development). Checkboxen = Fortschritt.

**Goal:** Aus dem gemessenen Ist-Zustand den kuerzesten sicheren Weg zu `0.1.3-alpha.0` (S2) und weiter zu `v1.0.0` festlegen und S1 (host-only) abarbeiten.

**Architecture:** Dieser Plan ersetzt die Plaene nicht. Scope: `AGENTS.md` + `2026-11-06-autonomous-to-stable-hardened.md`. Reihenfolge/Gates: `2026-11-06-finish-line-self-heal.md` (Sprints S0-S8, G0-G46). Dieser Plan fixiert nur **Startposition, naechste Aufgaben, Stoppregeln**.

**Tech Stack:** Rust (clap) CLI, Python 3 Tools/Tests (pytest), Bash (WSL) Image-Build, QEMU, GitHub Actions.

**Spec:** `AGENTS.md` §14.2/§20, `docs/superpowers/plans/2026-11-06-finish-line-self-heal.md`.

## Global Constraints
- Kein Fake-Status: ein Haken nur mit Evidenz (Statuswoerter PLANNED..VM-VERIFIED).
- Kein Force-Push, keine Datei-Ueberschreibung fremder Arbeit; Branch `codex/hscl1-v1`, Landung per PR mit gruener CI.
- Nie auf echte Platten installieren; Image-Builds nur einer zugleich (Host-RAM, drei Reaps dokumentiert).
- Keine Geheimnisse im Git; Windows-Host- und Linux-(WSL)-Pytest muessen beide gruen sein.
- Max. 3 Fix-Iterationen je Gate, dann Blocker dokumentieren.

## Review Focus
- `hscl --help`-Baum und `docs/CLI.md` driften auseinander (Befehle fehlen in der Doku) -> Task 1.
- Test-Dateien mit Shebang ohne Exec-Bit brechen nur in CI (heute passiert) -> `forge check` deckt es ab; bei neuen Skripten `git update-index --chmod=+x`.
- Gate gruen, Boot kaputt (r5): jede Image-Aenderung braucht Boot-Test, nicht nur Datei-Gates.
- Windows-vs-WSL-Pfade in Skripten (Release-Packaging scheiterte daran).
- Veroeffentlichte 0.1.0-Notes tragen Defektwarnung; 0.1.2 darf keine ungeprueften Claims erben.

---

## 1. Startposition (gemessen 2026-11-06)
| Fakt | Evidenz |
|---|---|
| `v0.1.2-alpha.0` ist veroeffentlicht (Prerelease, 19:58Z) | `gh release list` |
| Website-Metadaten zeigen auf 0.1.2, gegen SHA256SUMS+Manifest geprueft | Commit `b699ec0` |
| Letzter Agent stoppte nach Trademark-Gate/Legal-Commit; PR #22 offen, CI rot nur wegen `scripts/check_trademarks.py` ohne Exec-Bit | `gh run view`, `test_exec_bits.py` |
| Fix `0985ed5` gepusht (Exec-Bit), lokal 14 Tests gruen | dieser Lauf |
| Dependabot #1-#4 offen, gruen; Merge-Entscheidung beim Owner (#2 erst nach Release-Dry-Run) | BUILD_LOG |
| Brand-v2-Generator, PACKAGES.md-Gate, Ledger, Forge-Check, Boot-Classifier existieren | `scripts/` |
| **Fehlt (S1):** CLI-Doku-Drift-Gate, man pages/Completions, Menue-Datei, Governor-Parser (Rust), forge `build/boot/diff`, Doc-Command-Test | `tests/unit`, `cli/hscl/src` |

## 2. Reihenfolge
1. **S0 abschliessen:** PR #22 gruen -> mergen (Owner-Merge-Regel beachten), `main` enthaelt Plaene.
2. **S1 host-only (kein Image):** Task 1-4 unten, danach PR.
3. **S2:** *ein* Image-Build mit allen S1-Aenderungen, Boot + 28 e2e + Screens -> Release `0.1.3-alpha.0`.
4. Danach strikt die Leiter S3..S8 aus dem Finish-Line-Plan; Owner-Items (Signing-Key, Hardware, Lizenzentscheidung, Dependabot-Merge) sammeln, nicht raten.

## 3. S1-Tasks

### Task 1: CLI-Doku-Drift-Gate (G12)
**Files:** Modify `cli/hscl/src/main.rs` (Test), `docs/CLI.md`
**Produces:** Rust-Test `cli_doc_lists_every_command`, der den clap-Baum (`CommandFactory`) durchlaeuft und je Blattbefehl `hscl <pfad>` in `docs/CLI.md` verlangt.
- [x] Test geschrieben, rot (36 fehlende Befehle) gesehen
- [x] `docs/CLI.md` um fehlende Befehle ergaenzen (Quelle: `--help`, nichts erfinden)
- [x] cargo test 117 passed, clippy -D warnings, fmt gruen; Commit

### Task 2: Man pages + Shell-Completions
**Files:** Create `scripts/gen_cli_extras.py` oder `hscl completions SHELL` (clap_complete nur, wenn `cargo deny` sie erlaubt)
- [x] `hscl completions SHELL` (clap_complete), Test deckt alle Top-Level-Befehle fuer hscl+hscl1 ab; build-deb.sh erzeugt bash/zsh/fish-Dateien aus dem Paket-Binaer; Test `test_package_completions.py` (WSL gruen)
- [ ] Man pages (clap_mangen) - offen, naechster Weckruf
- [x] Commit

### Task 3: Menue-Datei + Doc-Command-Test
- [ ] Alle in README/docs als Codeblock genannten `hscl ...`-Befehle laufen als `--help`-Probe (Test), unbekannte Befehle = rot
- [ ] Commit

### Task 4: Governor-Parser (Rust, P27a) und forge `build/boot/diff`
- [ ] Parser + Zustandsmaschine mit Fixture-Tests (Spec: Finish-Line-Plan G27a)
- [ ] `forge.py build|boot|diff` dokumentiert in `docs/DEV_LOOP.md`, getestet mit Fakes
- [ ] Gate-Lauf: WSL pytest, Windows pytest, `forge check --strict`; PR oeffnen

## 4. Stoppregeln
- Jede Image-/Boot-Behauptung braucht Artefaktpfad in `docs/BUILD_LOG.md`.
- Drei rote Iterationen am selben Gate -> Blocker eintragen, naechsten Task nehmen.
- Release erst, wenn Entry-Gate des Sprints gruen ist; Label bleibt alpha/beta bis §20 komplett.

## 5. Owner-Entscheidungen (offen, nicht geraten)
Dependabot-Merges #1/#3/#4 (+#2 spaeter), Signing-Key fuer `SHA256SUMS`, Hardware-Testgeraete, Merge von PR #22.
