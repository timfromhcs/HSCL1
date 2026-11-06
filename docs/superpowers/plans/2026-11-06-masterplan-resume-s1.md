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

## 6. Research rounds (3 rounds, 2026-11-06) und neue Tasks
Ergebnis: `docs/research/2026-11-06-arex2-autodetect-reverse-engineering.md`. **AREX-2 = 27B-Agentenmodell der BAAI (Apache-2.0), kein Chip**; wir uebernehmen das Muster *propose-measure-reflect-revise* mit pruefbarem Score, nicht das Modell. Subplan: `2026-11-06-autodetect-arex-loop-re-lab.md` (Tracks A Loop, B Autodetect v2 modalias, C RE-Lab).

| Task | Inhalt | Gate |
|---|---|---|
| 5 (B1) | `hw.rs` modaliases + Report-Felder | cargo test, JSON stabil |
| 6 (B3/B2) | Treiberhinweise + hwdb-Generator | Fixtures, `test_gen_hwdb` |
| 7 (A1/A2) | `round_log.py`, `round_report.py` | pytest |
| 8 (C1/C2) | `docs/RE_LAB.md`, `re_capture.sh` | Doc-Gate, shellcheck |

Offene MEASURE-Punkte (kein Web-Ergebnis moeglich): 680M tok/s, WebGPU in QtWebEngine, llama.cpp-Architektur der gepinnten Version (Qwen3.5/3.8), sysext auf dem Image, hwdb-postinst. Owner-Items neu: Rechtsrahmen fuer RE-Lab (O5), Freigabe einer optionalen AREX-Turbo-Bundle-Pruefung.

## 7. Final master plan state after the 4-round loop (2026-11-06)
Research: `docs/research/2026-11-06-arex2-autodetect-reverse-engineering.md` (3 rounds) and `docs/research/2026-11-06-four-round-loop-arex-api-updates-stress.md` (4 rounds). Subplans: `2026-11-06-autodetect-arex-loop-re-lab.md` (A loop, B autodetect, C RE lab) and `2026-11-06-ai-api-updates-stress.md` (D AI API and agent runner, E abliterated policy, F updates/freeze, G stress, H resilience).

**Gaps closed with evidence:** AREX-2/Turbo identity and licence (Apache-2.0), harness protocol (XML tool calls, caller executes), GGUF availability, llama.cpp `qwen35` on master, llama-server API surface (official README), abliteration method plus one measured cost, bootc-on-Ubuntu status, archive availability of 23 tools.
**Gaps left open on purpose (MEASURE):** pinned `b12130` parses Qwen3.5 XML tool calls; 680M tok/s; WebGPU in QtWebEngine; `sched_ext`/fault-injection/`dm-flakey` in the Ubuntu kernel config; sysext on the image; Calamares `@`/`@home` on btrfs; systemd-oomd for user apps.
**Owner items added:** legal frame for the RE lab (O5); approval to evaluate AREX-Turbo / Apex-35B for the optional bundle (G39); confirmation that abliterated models stay opt-in and out of the ISO.

**Execution order (S1, host-only, one PR):** Task 5 B1 modaliases -> D2 toolcall parser -> D3 runner -> A1/A2 round log -> D1 serve spec -> E1 delta-card gate -> F1 claim gate -> G1 stress script -> B3/B2 driver hints and hwdb -> C1/C2 RE lab. Then S2: one image with H, G2, G4, autodetect and completions, all VM gates, release 0.1.3-alpha.0.

## 8. Local subagents (owner request, 4 research rounds done)
Plan: `2026-11-06-local-subagents.md` (L1-L8). Research: `docs/research/2026-11-06-local-subagents-prism-bonsai-turboquant.md`. Summary: keep the LocalAI Gateway and the verified PrismML Vulkan build; no TurboQuant fork binary (mainline KV rotation already on); local subagents are a verify-patch worker exposed as one MCP tool to Claude Code and OpenCode; executors compared on our own tasks before any default is chosen; memory gate before every model start. Runs in parallel with Section 7 (HSCL1 tasks stay: D1 serve spec next, then E1, F1, G1, B1...). Owner items: rotate the plaintext GitHub token and OpenCode password; confirm autostart policy.
