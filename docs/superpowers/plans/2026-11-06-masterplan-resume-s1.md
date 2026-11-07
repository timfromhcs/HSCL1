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
- [x] Man pages (clap_mangen) - DONE 2026-11-07: `clap_mangen` 0.3, `hscl man --out DIR` erzeugt `hscl.1`, `hscl1.1`
      und `hscl-<command>.1` aus dem clap-Baum (3 Rust-Tests, einer davon Determinismus); `build-deb.sh` installiert nach
      `/usr/share/man/man1` und gzip -9n; Paket-Test prueft `hscl.1.gz`/`hscl1.1.gz`; `docs/CLI.md`-Zeile (Drift-Gate)
- [x] Commit

### Task 3: Menue-Datei + Doc-Command-Test
- [x] Alle in README/docs als Codeblock genannten `hscl ...`-Befehle laufen als `--help`-Probe (Test), unbekannte Befehle = rot
      DONE 2026-11-07: Rust-Test `documented_hscl_commands_resolve_in_the_cli` (clap-Baum statt Prozessstart) scannt README/PROJECT-md,
      `docs/*.md` (ohne BUILD_LOG) und `handbook/**` - fenced blocks **und** Inline-Codepsans; `docs/CLI.md` (G12) bleibt der Gegentest.
      Vier echte Drifts gefunden und korrigiert: `hscl hw suggest` (nicht existent), `hscl workshop enable` (ADR-004), und zweimal
      `hscl appearance layout set` in ADR-006 + KNOWN_LIMITATIONS, wo das sogar als IMPLEMENTED stand - jetzt PLANNED (W5.5).
- [x] Commit (6b9f1c0-nachfolgend)

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

## 9. Stand 2026-11-07 (R2): gemessener Ist-Zustand, Research-Antworten, naechste Aufgaben

### 9.1 Was seit dem letzten Eintrag passiert ist (mit Evidenz)
| Punkt | Evidenz |
|---|---|
| `v0.1.2-alpha.0` veroeffentlicht (Prerelease, 4 ISO-Teile, Manifest, SHA256SUMS, CLI-SBOM, unsigniert) | `gh release list` |
| Branch `codex/hscl1-v1` = `origin` + 2 neue Commits; 39 Commits vor dem Tag | `git log --oneline` |
| PR #22 offen, mergeable, alle 10 Checks gruen - **Merge bleibt Owner** | `gh pr list` |
| Dependabot #1-#4 offen und gruen - Merge bleibt Owner | `gh pr list` |
| **G1 erledigt:** `scripts/stress_vm.sh` (Interlock `HSCL_IN_DISPOSABLE_VM=1` + Marker, JSON-Evidenz, 8 Tests zuerst rot) | Commit `ba1216e`, BUILD_LOG |
| **G24 erledigt:** Doc-Command-Gate, 4 echte Drifts gefunden (2 davon falsche IMPLEMENTED-Claims) | Commit `055d778`, BUILD_LOG |
| Offen aus S1: Man pages, Governor (G27a), forge `build/boot/diff` (G30), Menue-Datei (G26a), G3 proptest | `docs/superpowers/plans/2026-11-06-ai-api-updates-stress.md`, dieses Dokument |

### 9.2 Recherche-Runde 2026-11-07 (6 Fragen, Quellen im Agentenbericht; Kurzfassung)
| Frage | Antwort | Konsequenz / Aufgabe |
|---|---|---|
| `clap_mangen` | 0.3.3, **MIT OR Apache-2.0**, braucht clap ^4.6.6; upstream empfiehlt xtask statt build.rs | Task 2 fortsetzen: `hscl man --out DIR` (wie `completions`), Paketbau ruft es auf; `cargo deny` erlaubt die Lizenz |
| Calamares-Bug bei mehreren LUKS-Devices | **nicht** 2143847; das ist der Software-DB-Crash (Fix Released 3.3.14-0ubuntu21). Der LUKS-Bug ist **#2156681**, Fix Released in 3.3.14-0ubuntu25.26.04.1; betrifft nur mehrere Devices, nicht Single-LUKS | **Korrekturaufgabe:** Bug-Nummer in Plaenen/Docs richtigstellen, KNOWN_LIMITATIONS-Zeile praezisieren (Fix ist im Archiv, aber Verhalten im Image ungemessen) |
| Kubuntu-26.04-Support | "bis April 2029" (Monat, kein Tag); Plasma-6.6-LTS-Announcement nennt kein Datum | Kein Datum in Docs drucken, das genauer ist als "April 2029"; pruefen, ob irgendwo ein Tag steht |
| `help2man` / `pandoc` in resolute | beide vorhanden (1.49.3 / 3.7.0.2, universe); `man-db` im Default-Set = MEASURE | Man pages brauchen kein Fremdtool (clap_mangen); `man-db` im Rootfs pruefen, wenn die Pakete gebaut sind |
| llama.cpp Tool-Calls | `--jinja` default an, `--reasoning-format auto|none|deepseek|deepseek-legacy`, XML-Autoparser listet **Qwen3-Coder**; upstream nennt **kein "Qwen3.5"** | Unser eigener Parser (D2) bleibt der Vertrag; die Aussage "der gepinnte Build parst Qwen3.5-XML" bleibt MEASURE (Test mit dem echten Modell), nicht Claim |
| Secure Boot + Remaster | Kette Firmware -> MS-signierter shim -> Canonical-GRUB -> signierter Kernel; **initrd und squashfs werden nicht signaturgeprueft** | Squashfs-/initrd-Aenderungen koennen die Kette nicht brechen; Beweis trotzdem noetig: `sbverify --list` auf `EFI/BOOT/BOOTX64.EFI` und casper-`vmlinuz` des gebauten ISO (Task 9) |

### 9.3 Reihenfolge ab jetzt (jede Aufgabe: Test zuerst, Gate, Commit)
1. **Task 2b Man pages** (host-only): `clap_mangen` + `hscl man --out DIR`, Test gegen den clap-Baum, `build-deb.sh` erzeugt
   `hscl.1`/`hscl1.1`, Paket-Test; CLI.md-Zeile (Drift-Gate erzwingt sie).
2. **Task 4a Governor** (host-only): Parser/Zustandsmaschine mit Fixtures (`/sys/class/drm`, `/proc/*/fdinfo`), G27a.
3. **Task 4b forge `build|boot|diff`** (host-only): Subkommandos + Fake-Tests + `docs/DEV_LOOP.md`, G30.
4. **Task 6 Menue-Datei (G26a)** + `hscl hw modaliases` (B1) - letzteres ist im S2-Image sichtbar.
5. **G3 proptest** fuer `redact.rs`, `toolcall.rs`, `hw.rs` + zeitboxiger Fuzz-Workflow.
6. **Task 9 Secure-Boot-Evidenz** am vorhandenen ISO (sbverify + `--list`) - billig, schliesst F1 teilweise.
7. **Korrekturen aus 9.2** (Calamares-Bugnummer, Kubuntu-Datum) - kleine Doku-Commits, sofort.
8. Dann **S2**: ein Image mit allen S1-Aenderungen, Boot + e2e + Screens -> `0.1.3-alpha.0` (Owner-Merge/Release-Regeln beachten).

### 9.4 Owner-Items (unveraendert, nicht raten)
Merge PR #22 und Dependabot #1-#4, Signing-Key fuer `SHA256SUMS`, Hardware-Testgeraete (Radeon 680M), native DE/FR-Review,
Vercel-Produktions-Deploy, Rechtsrahmen RE-Lab (O5), AREX-Turbo-Freigabe (G39).
