# AGENTS.md — HCSPNP als integrierte Solver- und Forschungsplattform in HSCL1

> **Owner companion contract · Stand: 2026-11-07 · Sprache: Deutsch**  
> **Ziel:** Die HCSPNP-Funktionen in die vorhandenen Programme integrieren, nicht ein weiteres Parallelprodukt bauen.  
> **Primäre Repositories:** `timfromhcs/CQ-HECS` und `timfromhcs/HSCL1`  
> **Optional:** `timfromhcs/hcs-foundry` als vorhandene Modell-/Inference-Umgebung, nur nach Prüfung seiner realen Schnittstellen.  
> **Nicht vorhanden:** `timfromhcs/HCSPNP` lieferte bei der Prüfung am 2026-11-07 HTTP 404.  
> **Leitsatz:** *Reuse first. Measure second. Verify every claim. Integrate once.*

---

## 0. Verbindlichkeit, Scope und Umgang mit dem bestehenden HSCL1-Vertrag

Diese Datei ist eine **ergänzende Agenten-Anweisung für die HCSPNP-Arbeit**. Sie ersetzt und überschreibt nicht die vorhandene Root-`AGENTS.md` von HSCL1. Der Agent MUSS zuerst die Root-`AGENTS.md`, den aktuellen README-Status, `docs/CLAIMS.md`, `docs/KNOWN_LIMITATIONS.md`, `docs/BUILD_LOG.md`, die einschlägigen Tests und die aktuellen Pläne lesen. Bei Konflikten gilt:

1. Sicherheits- und Datenintegritätsregeln aus der Root-`AGENTS.md`.
2. Tatsächlicher Quellcode und reproduzierbare Tests.
3. `docs/CLAIMS.md`, `docs/BUILD_LOG.md`, Capability-Matrizen und aktuelle Pläne.
4. Diese HCSPNP-Ergänzung.
5. Ältere Forschungsnotizen, Skizzen, Marketingtexte oder nicht ausgeführte Roadmaps.

Die Agenten dürfen die bestehende Root-`AGENTS.md` nicht eigenmächtig ersetzen oder deren Inhalt zusammenfassen. Diese Datei bleibt zunächst ein separates, versionierbares Owner-Companion-Dokument. Eine spätere Übernahme einzelner Regeln in die Root-Datei erfordert einen expliziten Owner-Entscheid.

### 0.1 Produktentscheidung

**HCSPNP ist eine Funktionsfamilie innerhalb der bestehenden CQ-HECS- und HSCL1-Architektur, kein eigenständiges weiteres Desktop-Programm.**

- **CQ-HECS** besitzt Solver, #SAT, Solver-Portfolio, Zertifikatsprüfung, OMNIWAVE, Forschungsprototypen, CLI, Studio und bereits vorhandene Integrationspunkte.
- **HSCL1** besitzt das Betriebssystem, den `hscl`-CLI-Einstieg, Control Center, MCP-Host, Debian-Pakete, ISO-Pipeline und den vorhandenen CQ-HECS-Paketpfad.
- **HCSUDA** ist die optionale allgemeine Compute-/Vulkan-Schicht. Sie ist kein SAT-Solver und wird nur benutzt, wenn ein konkreter Kernel fachlich passt und auf dem Zielgerät verifiziert ist.
- **HCS Foundry** kann optional lokale Modellunterstützung liefern. Es darf weder Solver-Wahrheit entscheiden noch einen zweiten Modellserver oder zweiten MCP-Einstieg erzwingen.

Kein separates HCSPNP-GUI, kein zweiter Tray-Prozess, keine zweite Paketfamilie, kein neuer Modellruntime-Dienst und kein paralleles MCP-System, solange die bestehenden Oberflächen ausgebaut werden können.

### 0.2 Nicht-Ziele und wissenschaftliche Grenzen

Die Arbeit darf **nicht** behaupten oder suggerieren, dass:

- Tensor-Netzwerke, GNNs, Reinforcement Learning, Quantisierung, Vulkan oder mehr RAM `P = NP` beweisen oder NP-vollständige Probleme allgemein polynomial lösen.
- NP-Härte eine eigene Komplexitätsklasse sei.
- ein endlicher SHA- oder SAT-Benchmark die Frage `P = NP` entscheidet.
- eine Heuristik, ein Sprachmodell oder ein neuronales Netz einen SAT-/UNSAT-Beweis ersetzt.
- eine #SAT-Zahl ohne vollständigen exakten Algorithmus und reproduzierbare Verifikation bewiesen sei.
- ein `mmap` auf SSD/HDD automatisch GPU-Zero-Copy oder „SSD als VRAM“ bereitstellt.
- HCSUDA-Transformer-Kernels automatisch ein GNN, ein SAT-Solver oder eine Tensor-Network-Engine wären.

Allgemeines TQBF ist PSPACE-vollständig. Das ist eine spätere getrennte Forschungsrichtung, kein Beleg für eine Lösung aller NP-harten Probleme. `NP != PSPACE` ist nicht bewiesen.

---

## 1. Verifizierter Repository-Stand am 2026-11-07

Der Agent muss diese Tabelle bei jedem neuen Arbeitsbeginn aktualisieren. Ein neuer Commit kann einen Stand verändern; niemals Status aus dieser Datei als ewig aktuell behandeln.

| Repository | geprüfter Main-Stand | Beobachtung | Konsequenz |
|---|---|---|---|
| `timfromhcs/CQ-HECS` | `30c7f1484af01cf71a8843cca56ff38786eeaf92` · 2026-11-02 17:44 UTC | Release 5.0.0 / `hcs.run.v2`-Provenienz für CLI, Studio und Browser; vorhandene SAT- und #SAT-Infrastruktur | HCSPNP-Funktionen zuerst hier ergänzen |
| `timfromhcs/HSCL1` | `37d2f6dc1b4d92477d77d67d146d362257e6e54f` · 2026-11-07 21:52 UTC | Merge PR #28; Root-README: `0.1.3-alpha.0`, pre-alpha, VM-getestet, nicht auf physischer Hardware verifiziert | Vorhandene HSCL1-Einstiege ausbauen; keine Stabilitätsclaims |
| `timfromhcs/hcs-foundry` | `cfea6fab4ea4bd0ffb1517dc59e98a80f830096a` · 2026-11-02 | Separates Foundry-Projekt vorhanden | Nur optionale Integration nach API-Prüfung |
| `timfromhcs/HCSPNP` | 404 am 2026-11-07 | Repository konnte nicht aufgelöst werden | Nicht blind erstellen; HCSPNP als Feature-Set behandeln |

### 1.1 CQ-HECS: bereits vorhandene Basis

Im aktuellen CQ-HECS-Main sind unter anderem vorhanden:

- `cqhecs/sat.py`: DIMACS-CNF, CNF-Modell, DPLL-Referenzpfad, watched-literal-Variante, SAT-Modellprüfung und ein separater Tree-Resolution-Zertifizierungspfad.
- `cqhecs/sat_external.py`: optionaler CaDiCaL-Adapter über `python-sat`; SAT-Modelle werden gegen die Original-CNF geprüft, DRAT-Beweise können mit dem CQ-HECS-Checker geprüft werden.
- `cqhecs/drat.py`: unabhängiger DRAT-Checker im Repository.
- `cqhecs/unified.py`: bestehende Solver-Portfolio-API mit `hcs.sat.unified.v1`, Fähigkeiten, Reihenfolge, Budgets, Attempts, Resultat und Beweisstatus.
- `cqhecs/sat_separator.py`: exaktes #SAT über deterministische Variablen-/Bucket-Elimination mit Min-Fill-Planung, induzierter Breite, Tabellen- und Zeitbudget sowie `UNKNOWN` bei Überschreitung.
- `cqhecs/omniwave/`: Cube-/Front-Suche, Propagation, Nogoods, CPU-Batch-BCP, Vulkan-BCP, Branch-Policy und Lern-/Scoring-Experimente.
- `cqhecs/omniwave/gpu.py`: vorhandener Vulkan-C-ABI-Pfad für gebatchte BCP; optionales Prüfen gegen CPU-Referenz. Keine pauschale Beschleunigungsbehauptung.
- `cqhecs/omniwave/learned.py`: vorhandene `BranchPolicy`, `FeatureScorer` und optionaler `HfScorer`; ohne konfiguriertes Modell bleibt JW-Branching aktiv.
- `cqhecs/studio/app.py` und `cqhecs/studio/static/`: vorhandenes CQ-HECS Studio einschließlich SAT-Lab-Oberfläche.
- `cqhecs/provenance.py`: `hcs.run.v2` für reproduzierbare Laufkarten.
- `cqhecs/mcp_server.py`: vorhandener CQ-HECS-MCP-Server für standalone/dev-Nutzung.
- `web/src/sat.ts`, `web/src/satcert.ts`: Browser-SAT-/Zertifikatsfunktionen; separat gegen die tatsächliche Python-/Server-Referenz testen.
- native C++20-/Vulkan-Komponenten unter `src/` und Shader-/Build-Infrastruktur.

**Wichtig:** `cqhecs/unified.py` beschreibt vier Engines: `watched`, `omniwave`, `cadical`, `scan`. Die Engines sind nicht beweisgleich. Die genaue Vertrauensstufe muss im Ergebnis sichtbar bleiben.

### 1.2 HSCL1: aktueller OS-Integrationsstand

Der aktuelle HSCL1-README-Stand beschreibt:

- Ubuntu 26.04 LTS / Kubuntu-Basis und KDE Plasma 6.
- HCS Hybrid Desktop, `hscl` CLI, Control Center, Offline-Handbuch EN/DE/FR, Security-Baseline, Speicherverwaltung, Local-AI-/Coding-Tools und Workshop.
- Status `0.1.3-alpha.0` / pre-alpha.
- VM-Verifikation, aber keine physische Hardware-Verifikation und unsignierte Releases.
- Keine Tails-Äquivalenz, keine Anonymitätsgarantie und keine offizielle Kali-Affiliation.

Für CQ-HECS existiert bereits:

- Paketverzeichnis `packages/debian/hscl-cqhecs/` mit Debian-Metadaten, Launcher- und Desktop-Integration.
- zugehörige Pakettests, darunter `tests/unit/test_pkg_cqhecs.py` und `tests/unit/test_cqhecs_in_image.py` (vor jedem Eingriff Pfade/Status im aktuellen Tree erneut verifizieren).
- Einbindung in `scripts/remaster-iso.sh` und Image-Prüfungen über `distro/live/verify-image.sh`.
- Runtime-/Datenpfade im User-Kontext, keine automatisch gestartete Root-Dienstarchitektur und keine Model-Weights in der ISO.

Der aktuelle Integrationsstand bedeutet **nicht automatisch**, dass jeder Launcher eine vollständige Studio-Session startet oder dass die installierte Version auf einem installierten System end-to-end geprüft wurde. Die vorhandene Launcher-Implementierung und die Claims-Tabelle müssen vor jeder Aussage zur UI geprüft werden. Ein bestehender Launcher, der lediglich Status/Doctor in einem Terminal aufruft, wird verbessert; es wird kein zweites „HCSPNP“-Desktop-Programm daneben gestellt.

### 1.3 HCSUDA-Stand nach HSCL1 PR #28

Der am 2026-11-07 um 21:52 UTC gemergte HSCL1-Commit `37d2f6d` aktualisiert den HCSUDA-Dokumentations- und Implementierungsstand. Der Merge-Text dokumentiert:

- H2-Compute-Arbeit ist in den Capability-Dokumenten als getestet bzw. hardware-verifiziert nachgezogen worden; ältere Dokumentationsstellen hatten H2 noch fälschlich als geplant geführt.
- GGUF-Header-Lesen und sieben Dequantisierungsvarianten sind bereits vorhanden bzw. getestet, mit ausdrücklich benannten noch fehlenden Typen.
- H3c-2: GPU-Transformer-Block aus vorhandenen RMSNorm-/GEMM- und zusätzlichen Elementwise-, RoPE- und Causal-Attention-Kernels; die beschriebene Referenzprüfung verwendete kleine synthetische Dimensionen und bis zu 256 Tokens. Das ist eine Korrektheitsprüfung, kein Leistungsnachweis.
- H3c-3 Schritt 1: CPU-Qwen3-artige Decoder-Layer-Funktion mit GQA, optionalem QK-Norm, RoPE und GGUF-Weight-Layout; unabhängiger NumPy-Fixture-Test mit gemeldeter maximaler absoluter Abweichung `1.9e-6` im Testfixture.
- Noch nicht fertig laut Merge-Dokumentation: reale Layer aus GGUF streamen, Final-Norm + tied LM head, Tokenizer und Logit-Vergleich mit llama.cpp.

Die Merge-Beschreibung nennt für H3c-3-1 den Dokumentationszeitpunkt `2026-11-08`, während der Git-Commit am 2026-11-07 UTC erfolgte. Agenten müssen solche Datumsabweichungen markieren und für Repository-Zustand auf Commit-SHA und tatsächliche Tests verweisen.

**Folgerung für HCSPNP:** HCSUDA nicht als neue SAT-Laufzeit erfinden und nicht mit der noch offenen Qwen3-/LLM-Schicht vermischen. CQ-HECS hat bereits einen direkten, workload-spezifischen Vulkan-BCP-Pfad. HCSUDA ist nur eine mögliche optionale Compute-Schicht, wenn eine präzise Schnittstelle und ein echter Vorteil gezeigt werden.

### 1.4 Parallel laufende HSCL1-Arbeit: HCSEASYMATH

PR #28 enthält auch den Start der HCSEASYMATH-Spur:

- `apps/hcseasymath/` ist **geplant**, nicht bereits umgesetzt.
- Research Ledger und Plan für Track E sind angelegt; der Planstand wurde mit M0 abgeschlossen / M1 als nächster Schritt beschrieben.
- Architekturentscheidung: portable Mathe-App zunächst in HSCL1 in-tree, OS-Einstieg über `hscl math`, Rust-`hscl mcp`, Control-Center-Karte und separates kleines Debian-Paket erst nach Plan.
- Kein zweiter Python-MCP-Server; kein unsicheres `eval`/`sympify` auf Benutzereingaben; lokaler HTTP-Server muss Loopback, Host/Origin und Sitzungstoken prüfen.
- Ein-Hard-Job-Regel: keine zeitgleichen schweren GPU-/VM-/Modelljobs ohne bewusste Freigabe.

HCSPNP-Agenten müssen diese Arbeit respektieren. Keine parallelen unkoordinierten Änderungen an denselben `hscl`-CLI-, Control-Center-, MCP-, Paket- oder Image-Dateien. Für konkurrierende Aufgaben zuerst Merge-/Planstatus lesen und mit klaren Dateigrenzen arbeiten.

---

## 2. Zielarchitektur: vorhandene Programme erweitern

### 2.1 Zielbild

```text
                         HSCL1 DESKTOP
                              │
                  Control Center / App Launcher
                              │
                       hscl cqhecs ...
                              │
                vorhandenes hscl MCP (Rust Host)
                              │
             CQ-HECS Launcher / Runtime / API
                              │
                   CQ-HECS STUDIO (bestehend)
              ┌───────────────┴────────────────┐
              │                                │
       SAT / HCSPNP Lab                  Provenance / Runs
              │                           hcs.run.v2
       Solver Portfolio                       │
              │                         Export / Report
      ┌───────┼───────────┬─────────┐          │
      │       │           │         │          │
   watched  OMNIWAVE   CaDiCaL     scan        │
   DPLL     cube/front optional    DPLL        │
      │       │           │         │          │
      │     CPU BCP     DRAT        Tree-      │
      │     Vulkan BCP  checker     Resolution │
      └───────┴───────────┴─────────┘          │
                      │                       │
                 SAT Model / UNSAT Proof / Exact #SAT
                      │
              independent verification + schema
                      │
        optional HCSUDA compute only after evidence
```

### 2.2 Datenfluss und Verantwortungsgrenzen

1. Der Benutzer startet **CQ-HECS** über den bereits vorhandenen HSCL1 Launcher, Menüeintrag oder `hscl cqhecs`.
2. HSCL1 prüft Paket-/Runtime-Status und startet die vorhandene CQ-HECS-Installation im User-Kontext.
3. CQ-HECS Studio zeigt den bestehenden SAT-Lab-Bereich; HCSPNP wird dort als erweiterte Solver-/Forschungsansicht integriert.
4. DIMACS/CNF wird streng eingelesen; der Original-Input-Hash bleibt Teil des Run-Objekts.
5. Solver-Portfolio wählt ausschließlich deklarierte, installierte und verfügbare Backends; jeder Attempt bekommt Budget, Laufzeit, Ergebnis und Proof-Status.
6. SAT-Modelle werden gegen die unveränderte Original-CNF geprüft.
7. UNSAT wird nur als zertifiziert ausgegeben, wenn der jeweilige unabhängige Prüfer den dazugehörigen Nachweis akzeptiert.
8. #SAT wird nur mit exaktem Algorithmus als exakte Anzahl ausgegeben; bei Width-/Memory-/Timeout-Limit `UNKNOWN`, niemals einen Teilwert als vollständige Anzahl tarnen.
9. HCSUDA darf nur über Capability-Detection und CPU-Referenzvergleich beschleunigen.
10. Run-Ergebnis wird über vorhandene Provenienzformate exportiert; CLI, Studio, Browser und MCP verwenden dieselbe Fachlogik bzw. dasselbe Schema.

### 2.3 Kein neues Produkt nebenher

Nicht bauen:

- `hcspnp-gui`, eine zweite Weboberfläche oder ein zweites Studio.
- `hscl-hcspnp` als neue Paketfamilie, solange `hscl-cqhecs` die Funktion tragen kann.
- Einen neuen autonomen Hintergrunddienst, Root-Daemon oder Login-Autostart.
- Ein zweites lokales MCP-Server-Produkt für dieselben CQ-HECS-Funktionen.
- Einen zweiten GGUF-Parser, Model-Downloader oder Inference-Server.
- Einen „GPU-Pool“ oder „VRAM-Spill“-Mechanismus, der nicht im Treiber und auf der konkreten Hardware nachgewiesen wurde.

Erlaubt sind neue interne Module, API-Endpunkte, Studio-Tabellen/Ansichten, CLI-Subcommands, MCP-Tools im bestehenden Host, Tests und ein gezieltes Update des existierenden Debian-Pakets.

---

## 3. Verbindlicher Statuswortschatz

Jede Funktion und jede Behauptung bekommt einen dieser Statuswerte. Kein Status wird aufgrund eines README-Textes, einer erfolgreichen Kompilierung oder eines Demo-Screenshots hochgestuft.

| Status | Bedeutung |
|---|---|
| `PLANNED` | Design/Plan existiert; noch keine implementierte Funktion |
| `IMPLEMENTED` | Code existiert; relevante Tests fehlen noch oder sind nicht vollständig |
| `TESTED` | automatisierte, reproduzierbare Tests bestehen lokal/CI |
| `VM-VERIFIED` | im VM-Gast mit dokumentiertem Image-/Testaufbau geprüft |
| `HARDWARE-VERIFIED` | auf benannter realer Hardware und Treiberversion geprüft |
| `BENCHMARKED` | reproduzierbarer Vergleich mit Baseline und Rohdaten liegt vor |
| `PROOF-CHECKED` | Beweisobjekt wurde von einem separat beschriebenen Checker akzeptiert |
| `EXPERIMENTAL` | Forschung/Prototyp; nicht als stabiler Standardpfad behandeln |
| `BLOCKED` | konkrete offene Voraussetzung, Limit oder fehlende Evidenz |

`BENCHMARKED` ist kein Ersatz für `TESTED` oder `PROOF-CHECKED`. Ein schnelleres Resultat ist nicht automatisch korrekt. `HARDWARE-VERIFIED` gilt nur für das konkret genannte Gerät, nicht für alle Vulkan-Geräte.

---

## 4. SAT-/UNSAT-Vertrauensmodell

### 4.1 Resultatmodell

Jeder Solver muss einen strukturierten Output liefern, der mindestens enthält:

```json
{
  "schema": "hcs.sat.unified.v1",
  "status": "SAT | UNSAT | UNKNOWN",
  "engine": "watched | omniwave | cadical | scan | ...",
  "formula": {
    "original_sha256": "...",
    "canonical_sha256": "...",
    "variables": 0,
    "clauses": 0
  },
  "proof": {
    "kind": "MODEL | DRAT | TREE_RESOLUTION | NONE",
    "checker": "...",
    "checked": false,
    "status": "MODEL_VERIFIED | DRAT_CHECKED | TREE_RESOLUTION_CHECKED | UNCERTIFIED | NONE"
  },
  "attempts": [],
  "limits": {
    "wall_seconds": 0,
    "memory_bytes": 0,
    "node_budget": 0
  }
}
```

Dies ist ein illustratives Zielschema, kein Befehl, das bestehende `hcs.sat.unified.v1` inkompatibel zu verändern. Vor Schemaänderung zuerst reale Dataclasses, Tests, JSON-Consumer, `hcs.run.v2` und Versionierung prüfen. Rückwärtskompatibilität bevorzugen.

### 4.2 Bereits vorhandene Proof-Eigenschaften (nicht verwischen)

| Engine | SAT | UNSAT | HCSPNP-Agentenregel |
|---|---|---|---|
| `watched` | Modell wird gegen CNF geprüft | Exhaustion, aber laut bestehendem Portfolio ohne Zertifikat | Als SAT-verifiziert oder UNSAT-unkertifiziert/exhaustiv kennzeichnen; nicht zu Proof-checked upgraden |
| `scan` | Modellprüfung | Tree-Resolution-Zertifikat kann separat geprüft werden | Zertifikat und Checker-Status mit ausgeben |
| `omniwave` | Modellprüfung | DRAT-Nachweis wird mit `cqhecs.drat` geprüft | Nur bei erfolgreichem Check `DRAT_CHECKED` |
| `cadical` | CaDiCaL via `python-sat`, optional | DRAT-Nachweis wird mit lokalem Checker geprüft, wenn Proof aktiviert | Missing dependency als `unavailable` melden; niemals stillschweigend verstecken |
| native C++ SAT | abhängig vom konkreten Codepfad | nicht automatisch dasselbe Zertifikatsmodell wie der Python-Referenzpfad | Vor Vertrauen getrennt auditieren; keine Übernahme der Python-Proof-Claims |
| GNN/ML/RL-Policy | keine eigene SAT-Wahrheit | keine eigene UNSAT-Wahrheit | Darf nur Auswahl/Branching priorisieren |

**Wichtige Unterscheidung:** Das Python-`scan`-Verfahren in `cqhecs.sat` besitzt einen Tree-Resolution-Zertifizierungspfad. Die `watched`-Variante ist nicht gleichzusetzen mit dem Zertifikat dieses separaten Pfades. OMNIWAVE und CaDiCaL verwenden DRAT, wenn der Nachweis aktiviert und geprüft wird. Der native C++-SAT-Solver hat separat zu beweisen, was er behauptet.

### 4.3 Fail-closed Regeln

- Solver-Widerspruch `SAT` gegen `UNSAT` => `UNKNOWN` / `CONFLICT`, niemals „Mehrheit entscheidet“.
- Modell nicht vollständig oder nicht erfüllend => verwerfen.
- DRAT-/Tree-Resolution-Checker timeoutet, stürzt ab oder lehnt ab => `UNCERTIFIED` bzw. `UNKNOWN` gemäß bestehendem Vertrag, keine Zertifizierung.
- Solver-Timeout, Speicherlimit, Node-Budget, Cancellation => `UNKNOWN`.
- Missing Backend => `unavailable`, eigener Attempt oder Capability-Eintrag.
- Abweichende Eingabedatei, Hash-Mismatch oder nicht reproduzierbare Originalbytes => Resultat an Original-Input binden, nicht still korrigieren.

---

## 5. Bestehendes Solver-Portfolio ausbauen, nicht neu schreiben

### 5.1 Portfolio-Regeln

Der aktuelle Default in `cqhecs.unified` ist dokumentiert als:

`watched → omniwave → cadical → scan`

mit Budgetanteilen aus der Implementierung (in den aktuellen Dokumenten `0.5 / 0.3 / 0.2` plus kleiner Floor/Restbehandlung; im Code verifizieren, bevor Zahlen verändert werden). Das Portfolio hält Attempt-Records und re-verifiziert SAT-Modelle gegen die Original-CNF. UNSAT-Proof-Status wird nicht hochgestuft.

Agenten müssen zuerst bestehende Implementierung und Tests lesen:

- `cqhecs/unified.py`
- `docs/UNIFIED_SOLVER.md`
- `tests/test_unified_solver.py`
- `cqhecs/sat.py`
- `cqhecs/sat_external.py`
- `cqhecs/omniwave/`

Nicht parallel ein zweites `HCSPNPPortfolio` mit eigener Reihenfolge/Budgetlogik erstellen.

### 5.2 Sinnvolle Erweiterungen

- Problem-Metadaten und optionale Profile ergänzen, die keine mathematische Wahrheit behaupten: CNF-Größe, Clause-Längen-Histogramm, Variablenhäufigkeiten, Komponenten, geschätzte induzierte Breite.
- Engine-Capabilities differenzierter modellieren: proof support, incremental support, assumptions, model count, memory requirements, device backend.
- Budgets konfigurierbar machen und im Resultat festhalten.
- Portfoliopolitik als experimentelle Policy hinter Feature-Flag, mit unverändertem deterministischem Default.
- Reproduzierbare Abbrüche/Cancellation und saubere Ressourcenfreigabe.
- Ein Ergebnisvergleich, der Status, Zertifizierungsstufe, Zeit, Peak-RAM, GPU-Kosten und Beweisgröße getrennt zeigt.

### 5.3 Keine versteckte Selbständerung

Ein Agent darf keine Default-Reihenfolge anhand eines einmaligen lokalen Benchmarks ändern. Jede Policy-Änderung benötigt:

1. Benchmarkdatensatz und Baselines.
2. Hold-out-Set, das nicht zum Tuning verwendet wurde.
3. Korrektheits- und Proof-Konformität.
4. Regressionstests auf allen bisherigen Fixtures.
5. klar sichtbare Konfigurations-/Schemaänderung.
6. dokumentierten Grund für Änderung oder Beibehaltung.

---

## 6. GNN, Learned Branching und Reinforcement Learning

### 6.1 Bereits vorhandene Basis

`cqhecs/omniwave/learned.py` implementiert bereits Feature-basiertes Branching und optional einen kleinen HuggingFace-Scorer. Ohne Modell bleibt die bestehende JW-Reihenfolge bestehen. Die Policy bestimmt nur, welche Variable als Nächstes gesplittet wird. Solver und Proof-Checker behalten die Wahrheitshoheit.

Ein dokumentierter negativer Versuch darf nicht gelöscht oder in Marketing umgeschrieben werden: In einem beobachteten Pigeonhole-8-7-Vergleich war JW wesentlich schneller; das gelernte Modell lief in ein 60-Sekunden-Limit und erzeugte erheblich mehr Fronts. Dieses Ergebnis ist ein wichtiges Gegenbeispiel und muss in Benchmark- und Forschungsdokumenten erhalten bleiben.

### 6.2 Forschungsrichtung

Die aktuelle Forschungsrichtung aus der ICLR-2026-Arbeit „Learning from Algorithm Feedback: One-Shot SAT Solver Guidance with GNNs“ ist sinnvoll als **einmalige Solver-Guidance**: GNN erzeugt Branching-Gewichte oder Polaritätsvorschläge, bestehender Solver nutzt diese als Heuristik. Das Modell darf die Suche nicht abkürzen, indem es Antworten behauptet.

GNN-Einbindung als optionales Modul:

```text
CNF -> feature/graph encoder -> variable scores / polarity hints
                                  │
                                  ▼
                      bestehender BranchPolicy
                                  │
                                  ▼
                         OMNIWAVE / DPLL search
                                  │
                     Modell- oder Proof-Prüfung
```

### 6.3 GNN-Arbeitspakete

**GNN-0 — Nullbaseline / Datenvertrag**
- SAT-Instanzdaten nur aus legal nutzbaren, reproduzierbaren Quellen.
- Formelgraph: Variablenknoten, Klauselknoten oder variablenbasierter signed-incidence-Graph.
- Node-/Edge-Features versionieren.
- Train/validation/test nach Instanzfamilie und Generator-Seeds trennen.
- Keine nahezu identischen Varianten derselben Formel über Train und Test verteilen.

**GNN-1 — One-shot Ranking**
- Eingabe: CNF-Graph und zulässige Solverzustandsfeatures.
- Ausgabe: Scores pro unzugewiesener Variable; optional Polarität.
- Integration über `BranchPolicy`, keine eigene Suche.
- CPU-First, optional Vulkan-Inference erst nach gemessenem Mehrwert.

**GNN-2 — Solver-Feedback-Training**
- Trainingssignal aus realen Solverkosten: Conflicts/Decisions/Propagations/Wall time/Memory.
- Keine Reward-Definition, die bloß leicht erkennbare Trainingsfamilien belohnt.
- Reward- und Dataset-Version im Experiment speichern.
- Training außerhalb des Produktionssolve-Prozesses.

**GNN-3 — Portfolio Guidance**
- Optional policy chooses engine/profile or per-engine budget.
- Die Policy darf nur zwischen verfügbaren Backends wählen.
- Backend-Nichtverfügbarkeit und proof capabilities berücksichtigen.
- Einmalige Entscheidung zuerst; Online-RL nur später und nur mit sauberer Sicherheits-/Reproduzierbarkeitsarchitektur.

### 6.4 Pflichtmetriken

- SAT/UNSAT-Korrektheit im Vergleich mit Referenzsolver und unabhängigen Checkern.
- solved instances / timeout rate.
- Decisions, propagations, conflicts, learnt clauses, search nodes/fronts.
- median / p95 runtime, CPU time, peak RSS, GPU time, energy optional.
- Modell-Ladezeit und Inference-Overhead getrennt.
- Ablation: JW, vorhandener FeatureScorer, GNN one-shot, random ranking.
- Generalisierung über Problemfamilien und Verteilungen.

Ein GNN, das in einem Benchmark schneller ist, ist damit nicht „besser“ für alle SAT-Probleme. Der ICLR-2026-Befund zur Ausdrucksstärke von GNNs für SAT unterstreicht zusätzlich, dass Graphmodelle nicht alle SAT/UNSAT-Paare unterscheiden können. Heuristik bleibt Heuristik.

---

## 7. Exaktes #SAT und Tensor-Network-Richtung

### 7.1 Bestehender exakter Kern

`cqhecs/sat_separator.py` ist bereits ein exaktes #SAT-Verfahren über Variablen-/Bucket-Elimination:

- Klauseln werden in Faktoren überführt.
- Variablen werden in deterministischer Min-Fill-Reihenfolge eliminiert.
- Join/Sum-out akkumuliert exakte ganzzahlige Zählwerte.
- freie Variablen ergeben Faktor `2**free`.
- induzierte Breite begrenzt die Größe der benötigten Tabellen.
- bei Überschreitung von Tabellenbudget oder Deadline wird `UNKNOWN` zurückgegeben.
- der Modulvertrag behauptet ausdrücklich keine generelle Beschleunigung; hochbreite Formeln dürfen früh ablehnen.

Daher darf kein neuer „Tensor SAT Solver“ geschrieben werden, ohne den vorhandenen Separator als exakte Baseline zu verwenden und nachzuweisen, welche zusätzliche Funktion er bietet.

### 7.2 Tensor-Netzwerk-Forschung: realistische Einordnung

Tensor-basierte Model-Counting-Arbeit ist eine legitime Richtung für exakte #SAT-/Weighted-Model-Counting-Experimente. Tensor-Kontraktion ist aber nicht automatisch ein Vorteil: Pfadplanung kann selbst schwierig sein, Speicher wächst bei ungünstigen Zwischen-Tensoren stark und geeignete Strukturen/Separators bestimmen die praktische Machbarkeit.

Vorgehen:

1. Bestehende Factor-/Separator-Repräsentation untersuchen.
2. Gleiche CNF als Tensor-/Factor-Graph abbilden.
3. Dtype und Integer-Range exakt halten.
4. Kontraktionspfad planen, ohne die Tabellen-/RAM-Grenzen zu verschleiern.
5. Kleine Fälle gegen Brute Force und `count_models` prüfen.
6. Strukturiert gegen `sat_separator` messen.
7. Erst danach optionalen Tensor-Kontraktionsbackend implementieren.

### 7.3 Exaktheitsanforderungen

- Kein Float32/FP16/INT8 für exakte Modellzahlen.
- Kein saturating arithmetic.
- Bei BigInt-Overflow, fehlendem BigInt-GPU-Support oder Dtype-Verlust muss die Berechnung auf einen exakten CPU-Pfad wechseln oder `UNSUPPORTED` liefern.
- Intermediate-Tensoren müssen begrenzt und messbar sein.
- Jeder Zählwert muss exakt der CNF und allen freien Variablen entsprechen.
- Stichproben oder Monte-Carlo zählen als Approximation und müssen entsprechend benannt sein.

### 7.4 Potenzielle Architektur

```text
CNF
 ├── normalize / components / width plan
 ├── existing exact separator (#SAT baseline)
 └── optional tensor-factor graph
       ├── contraction path planner
       ├── exact CPU contraction (reference)
       ├── optional accelerator for safe integer ranges only
       └── verifier / small-instance enumeration
```

Ein Proof- oder Verifikationsschema für Tensor-#SAT ist als eigenes Arbeitspaket zu definieren. „Wir haben eine Zahl ausgerechnet“ ist noch kein unabhängiger Nachweis, dass sie exakt stimmt.

---

## 8. Speicher, mmap, HDD-/SSD-Tiering und große Formeln

### 8.1 Vorhandener Stand und Grenzen

CQ-HECS enthält Tiered-Storage-Experimente. Der geprüfte native Pfad besitzt einen gemappten Cold-Pool und Page-out/Page-in-Kopien. Das ist nicht gleichbedeutend mit einer GPU, die HDD-Sektoren direkt adressiert.

### 8.2 Korrekte Schichten

```text
CNF file on NVMe / HDD
        │
        ▼
OS page cache + mmap (CPU virtual address space)
        │
        ├── CPU parsing / streaming / clause index
        │
        └── explicit staging buffer / copy
                 │
                 ▼
            Vulkan device memory
```

`mmap` ermöglicht dateigestützte Seiten in CPU-virtuellem Speicher. Das Betriebssystem übernimmt Paging. GPU-Zugriff auf Host Memory erfordert konkrete Vulkan-Erweiterungen, kompatible Geräte, Alignment, Memory-Properties, Synchronisation und Ownership-Regeln. USB-HDD-Zugriffe haben zudem stark andere Latenz-/Durchsatzprofile als VRAM.

### 8.3 Zulässige Arbeitspakete

- Streaming-DIMACS-Parser, der große Dateien inkrementell einliest.
- Bounded Clause Store mit klarer Ownership.
- File-backed Mapped Region für große unveränderliche CNF-Blöcke.
- explizite pinned/host-visible staging buffers, wenn Plattform/Driver sie unterstützen.
- LRU/Page-/Chunk-Cache mit Peak-RSS- und I/O-Metriken.
- Crash-sichere temporäre Artefakte und sauberes Aufräumen.
- Test gegen kurze Reads, abgeschnittene Dateien, Nullbytes, ungültige Header, sehr lange Klauseln und Dateigrößenlimits.

### 8.4 Verbotene Claims

Nicht „zero-copy“, „GPU nutzt HDD als VRAM“, „unbegrenzte VRAM-Erweiterung“ oder „I/O kostet nichts“ schreiben, bevor ein echter Geräte-/Treiberpfad, korrekte Speicherfreigabe, Synchronisation und reproduzierbarer Benchmark vorhanden sind. Keine host-visible External-Memory-Extension voraussetzen. Fallback ist CPU oder explizite Kopie.

---

## 9. HCSUDA / Vulkan als optionaler Compute-Backend

### 9.1 Grundregel

CQ-HECS' bestehender Vulkan-BCP-Pfad bleibt der erste Referenzpunkt für GPU-beschleunigte SAT-Propagation. Nicht neu implementieren, bevor Code, Shader, C-ABI, Build-System, CPU-Referenz und Tests verstanden wurden.

HCSUDA wird nur über einen klaren, kleinen Compute-Vertrag angebunden, wenn:

- ein passender Kernel wirklich existiert;
- Kernel-Input/Output vollständig dokumentiert ist;
- CPU-Referenz dieselbe Semantik besitzt;
- Ergebnis pro Lauf gegen CPU-Referenz geprüft werden kann;
- GPU-Treiber/Device/Extension tatsächlich verfügbar sind;
- Hardware und Softwareversion in jedem Benchmark auftauchen;
- der Overhead nicht den möglichen Nutzen auffrisst.

### 9.2 Abgrenzung vom aktuellen HCSUDA-Transformer-Pfad

HCSUDA H3c-2/H3c-3 bezieht sich auf Transformer-/LLM-Kernels und Qwen3-artige Layer. Das ist keine direkte SAT-Acceleration. Die HCSPNP-Entwicklung darf die LLM-Kernel nicht umetikettieren und muss HCSUDA-SAT-Kernels separat entwerfen und testen, falls sie überhaupt benötigt werden.

### 9.3 CPU-First-/GPU-Optional-Vertrag

- CQ-HECS muss ohne Vulkan und ohne HCSUDA nutzbar bleiben.
- Keine GPU voraussetzen; Software-ICD ausdrücklich als Software deklarieren.
- Gleicher Seed und gleiche CNF müssen einen reproduzierbaren CPU-Pfad besitzen.
- GPU-Ergebnisse müssen bit-identisch sein, wenn das zugrunde liegende Problem dies verlangt; bei nicht identischer Arithmetik eng definierte Semantik und unabhängiger Checker.
- GPU-Ausfall => CPU-Fallback mit sichtbarem Grund.
- Kein automatischer Performance-Claim aufgrund GPU-Namens oder theoretischer FLOPS.

---

## 10. Studio-UX: SAT Lab erweitern statt UI duplizieren

### 10.1 Bestehende Oberfläche

Die aktuelle CQ-HECS Studio-Anwendung und ihr SAT-Lab-Bereich sind die Ausgangsbasis. Agent muss `cqhecs/studio/app.py`, die statischen UI-Dateien, Endpunkte, Resultatschemas und bestehende Browser-SAT-Tests lesen, bevor UI-Code verändert wird.

### 10.2 Zielbereiche innerhalb derselben Studio-Navigation

**SAT Workspace**
- DIMACS-Editor / Import / Drag-and-drop.
- Eingabevalidierung mit Zeilen-/Spaltenhinweisen.
- Originaldatei-Hash, kanonischer CNF-Hash, Variablen- und Klauselzahl.
- Beispiel-Formeln und reproduzierbare Seeds.

**Solver Portfolio**
- Default `Unified` und konkrete Engine-Auswahl.
- verfügbare/nicht verfügbare Backends sichtbar.
- Zeit-, Memory-, Node- und Proof-Budget.
- Attempts-Timeline: Engine, Budget, Laufzeit, Status, Proof-Stufe und Grund.

**Proof & Verification**
- `SAT`: vollständiges Modell mit unabhängiger Verifikationsaktion und erfüllten Klauseln.
- `UNSAT`: Proof-Typ, Prüfer, Checker-Version, Zertifikatsgröße, Checker-Ergebnis.
- `UNKNOWN`: konkrete Ursache wie Timeout, Budget, Backend unavailable, Proof failure.
- `UNCERTIFIED` niemals farblich wie zertifiziert markieren.

**#SAT / Tensor / Separator**
- Count-Mode ausdrücklich von SAT-Decision trennen.
- Width-/Plan-Schätzung vor Ausführung.
- größtes erwartetes Zwischentableau, Tabellenbudget und Zeitbudget zeigen.
- `UNKNOWN` mit Abbruchgrund; kein gerundeter Teilwert.
- Tensor-Experiment als opt-in und mit Label `EXPERIMENTAL`.

**Learned Guidance**
- JW / FeatureScorer / GNN getrennt auswählbar.
- Modellversion, Weights-Hash, Feature-Schema, Trainingsdatensatz und Inference-Kosten zeigen.
- Negative/neutralen Benchmarkausgang nicht verstecken.
- Ohne Modell JW-Fallback als aktiven Modus anzeigen.

**Run Comparison**
- gleiche CNF, gleiche Limits, alle Engine- und Proofdaten vergleichen.
- CPU/GPU-Zeit getrennt ausweisen.
- Model-Load und Warmup getrennt von Solve-Time.

### 10.3 Designanforderungen

- HCS Hybrid Desktop Look and Feel; bestehendes Design-System nutzen.
- Keyboard-first, Bildschirmlesbarkeit, kontrastreiche Statuskennzeichnung, EN/DE/FR.
- Kein interaktives Element ohne echte Aktion.
- Keine fake progress bars, fake GPU stats oder statischen Erfolgsmeldungen.
- Große Solverdetails einklappbar; Kernstatus auf einen Blick.
- Exportierbare JSON-/Markdown-Laufkarte mit Hash und verwendeter Version.
- Studio darf den Solver nicht nur durch UI-Timeout beenden; Backend muss Cancellation/Deadline verstehen.

---

## 11. CLI, APIs, MCP und Provenienz

### 11.1 CLI

Bestehenden `cq-hecs` CLI-Namespace erweitern und über existierenden HSCL1-Einstieg exponieren. Vor Implementierung die aktuelle clap-/argparse-Struktur und Tests lesen. Denkbare UX (Namen an vorhandene Parserstruktur anpassen):

```bash
cq-hecs sat capabilities
cq-hecs sat solve --cnf problem.cnf --engine unified --timeout 60
cq-hecs sat solve --cnf problem.cnf --engine scan --proof tree-resolution
cq-hecs sat count --cnf problem.cnf --method separator --table-budget 1000000
cq-hecs sat benchmark --suite suites/sat-small.json --out results/
hscl cqhecs status
hscl cqhecs open
```

Das sind Designbeispiele. Nicht dieselben Befehle neu bauen, wenn sie bereits unter anderem Namen existieren.

### 11.2 API-Vertrag

- versionierte Endpunkte bzw. stabile JSON-Schemas.
- Input-Limits, Timeout, Memory-Limit, Cancellation.
- Request-ID und Run-ID.
- Originalinput, canonical hash und source revision.
- Engines und Capability-Liste.
- vollständige Attempt-Historie.
- Proof-Metadaten und Checker-Ergebnis.
- Keine stillschweigende Umwandlung ungültiger Eingaben in andere Formeln.

### 11.3 MCP: nur einen primären OS-Einstieg

HSCL1 besitzt einen Rust-`hscl mcp`-Host. CQ-HECS besitzt zusätzlich einen MCP-Server für eigenständige Nutzung/Entwicklung. Bei OS-Integration ist zu entscheiden, ob Rust-Host CQ-HECS-CLI/-API aufruft oder ein direkter MCP-Betrieb für einen ausdrücklich getrennten Dev-Modus angeboten wird. Keine doppelt veröffentlichten Tools mit verschiedenen Namen für dieselbe Aktion.

MCP-Tool-Schnittstellen müssen:

- typisierte, enge Argumente haben (Dateipfad-/Größen-/Zeitlimits einschließen);
- Shell-Injection und beliebige Shell-Strings vermeiden;
- nur deklarierte Aktionen ausführen;
- keine root-Rechte ohne explizite Begründung erhalten;
- Start/Stopp und Fehler transparent zurückmelden;
- bei stdio alle Protokollnachrichten auf stdout und Logs auf stderr trennen;
- bei lokalem HTTP Loopback, Host-/Origin-Validierung und Session-Token nutzen.

### 11.4 Provenienz

CQ-HECS 5.0.0 besitzt `hcs.run.v2`. Dieses existierende Format ist die Basis. Für HCSPNP müssen enthaltene Felder mindestens verlinken auf:

- Originalinput und SHA-256;
- kanonische CNF und SHA-256;
- Engine, Engine-Version, Backend-Version, Proof-System;
- Timeout, Node-/Memory-/Table-Budget;
- Seed und Policy/Model/Weights-Hash;
- Host, CPU, GPU, Vulkan-Device, Driver, ICD;
- Code-Revision/Package-Version;
- komplette Attempts/Checker-Stati.

Schemaänderung ist versioniert und mit Fixtures/Consumer-Kompatibilität zu testen. Keine stillen Field-Renames.

---

## 12. HSCL1-Integration und Paketstrategie

### 12.1 Bestehendes Paket erweitern

Ziel ist die vorhandene `packages/debian/hscl-cqhecs/`-Paketstruktur. Vor einer Änderung zuerst vollständig lesen:

- `DEBIAN/control` und alle maintainer scripts;
- `/usr/bin`-Launcher;
- `/usr/share/applications` Desktop-Dateien;
- runtime configuration und Dependency-/Wheel-Lock;
- XDG Data-/Config-/Cache-Pfade;
- existierende Unit- und Image-Tests;
- `scripts/remaster-iso.sh` und `distro/live/verify-image.sh`.

Verbessere den vorhandenen Launcher, sodass er:

1. `hscl cqhecs status` oder Äquivalent bereitstellt;
2. vorhandene Runtime prüft und sauber startet;
3. das bestehende CQ-HECS Studio öffnet;
4. CPU-Only-Fallback anbietet;
5. Fehlermeldungen und Logs benutzerverständlich zeigt;
6. User-Daten in XDG-Pfaden hält;
7. beim Beenden Prozesse und temporäre Ressourcen freigibt.

Keine zusätzliche App-Verknüpfung mit eigenständiger HCSPNP-Identität, wenn die existierende CQ-HECS-Verknüpfung erweitert werden kann.

### 12.2 ISO-Politik

- Keine großen Modelle, GGUF-Gewichte, Benchmarkkorpora, Downloads von SAT-Suites oder unaufgeforderten Toolchains in die ISO packen.
- Solver-Runtime in Größe, Lizenz und Offline-Fähigkeit dokumentieren.
- optionale Backends separat, mit sichtbarer Benutzerentscheidung.
- keine automatischen Netzwerkaufrufe beim Boot.
- kein Autostart von Studio oder Solverdienst ohne explizite Useraktion.
- keine Root-Dienste für unprivilegierte Solverjobs.

### 12.3 Integrations-Gates

1. Paket-Build und `dpkg-deb --contents`.
2. Pakettests.
3. Unit-Test der Launcher-Argumente und Pfade.
4. Image-Gate: Paket im Live-Image vorhanden und verifiziert.
5. Live-VM: Desktop-Eintrag/CLI funktioniert.
6. Installierte VM: Paket ist nach Installation vorhanden und öffnet das Studio.
7. CPU-only VM: Solver läuft ohne GPU.
8. GPU-VM oder Hardware nur dort, wo echte Capability nachgewiesen ist.
9. Uninstall-/Upgrade-Test; Userdaten bleiben korrekt erhalten.

`VM-VERIFIED` des Live-Images ist nicht automatisch der Nachweis für das installierte System.

---

## 13. Sicherheit, Ressourcen und robuste Fehlerbehandlung

- Solverprozesse grundsätzlich unprivilegiert starten.
- Inputgröße, Variablenzahl, Klauselzahl, Klausellänge, Uploadgröße und Laufzeit begrenzen.
- Timeouts müssen Prozess-/Worker-Ebene durchsetzen, nicht nur UI-Timeout.
- Speicherlimits und cancellation in jeder teuren Operation.
- Temporäre Dateien mit sicheren Rechten in XDG runtime/cache-Verzeichnissen.
- Keine beliebigen Shell-Befehle aus User-Text.
- Keine deserialisierten Python-Objekte aus nicht vertrauenswürdigen Quellen.
- Keine beliebigen Pickle-Modelle ohne klaren Vertrauens-/Formatvertrag.
- GNN-/Modelldateien mit Hash, Herkunft, Lizenz und Größenlimit.
- Download nur nach sichtbarer Zustimmung; HTTPS, Hash/Signatur und atomare Ablage.
- Local HTTP: ausschließlich 127.0.0.1, Host-/Origin-Check, pro Start zufälliger Token, CORS nicht wildcard.
- MCP Tool-Allowlist: keine allgemeine Shell und keine beliebigen Dateisystemzugriffe.
- Logs ohne Geheimnisse oder vollständige vertrauliche Dateien.
- Crash, Kill, Stromausfall und kaputte Cache-Dateien dürfen das System nicht beschädigen.

### 13.1 Hardware-/Speichererkennung

Daten aus `vulkaninfo`, Vulkan-Properties, OS und Treiber nicht als frei nutzbare VRAM-Zahl missverstehen. Shared Memory, UMA und dedizierter VRAM separat darstellen. Keine GPU-Fähigkeit annehmen, weil ein Vulkan-Loader installiert ist. Prüfe echtes Device, Extensions, Memory-Heaps, Limits und Shader-Fähigkeiten.

### 13.2 Windows-/Linux-Entwicklungsumgebung

Der Agent muss die echte Arbeitsumgebung erkennen. Nicht automatisch Docker/WSL/VM voraussetzen. Für HSCL1 Linux-Build-/Image-Tests die im Root-Vertrag dokumentierte WSL-/QEMU-Strategie berücksichtigen; Windows-native QEMU/WHPX und WSL-Kernel-Einschränkungen nicht vermischen. Heavy-Job-Regel beachten: höchstens ein schwerer VM-/GPU-/Model-Inference-Job gleichzeitig, sofern nicht ausdrücklich geplant.

---

## 14. Teststrategie: Korrektheit vor Performance

### 14.1 Minimale SAT-Fixtures

Jeder Solver muss dieselben handverifizierten Instanzen bestehen:

1. leere CNF ohne Klauseln => SAT, Modell vollständig.
2. leere Klausel => UNSAT.
3. triviale Unit-Klausel => SAT.
4. widersprüchliche Units `1` und `-1` => UNSAT.
5. tautologische Klausel `1 -1` => alle Modelle gültig.
6. freie Variablen => korrekte Anzahl im #SAT.
7. Mehrfach-Literale und über mehrere DIMACS-Zeilen laufende Klauseln.
8. ungültiger Header, Literal außerhalb `num_vars`, abgeschnittene Datei => sauberer Parse-Fehler.
9. SAT-Formel mit mehreren Modellen => geliefertes Modell geprüft.
10. UNSAT-Formeln mit akzeptiertem Tree-Resolution-/DRAT-Nachweis.
11. Checker-Negativtests: manipuliertes Proof-Objekt muss abgelehnt werden.
12. widersprüchliche Engine-Ergebnisse => fail closed.

### 14.2 #SAT-Fixtures

- Exhaustive Brute Force als Oracle für kleine `n`.
- zufällige CNF mit festem Seed und kleinem `n`.
- Formeln mit freien Variablen.
- unabhängige Komponenten.
- tautologische und doppelte Klauseln.
- leere Klausel.
- niedrige treewidth/induced width Fälle, wo Separator sinnvoll ist.
- breite zufällige 3-SAT-Fälle, bei denen plan/algorithmus `UNKNOWN`/Budget ablehnen darf.
- BigInt-Ergebnisse über 64 Bit.

### 14.3 GPU-Konformität

- Jede GPU-Kernel-Ausgabe gegen CPU-Referenz prüfen.
- Off-by-one, signed literal, unit propagation, empty clause und batch-boundary cases.
- Device lost / missing Vulkan / software ICD / unsupported extension.
- Repeated runs und determinism.
- Sanitizer/validation layers, soweit das konkrete Setup sie unterstützt.
- CPU fallback muss denselben Resultatvertrag erfüllen.
- Keine Benchmarkauswertung, wenn der Kernel nicht zuvor bestanden hat.

### 14.4 GNN/ML-Tests

- Modell missing/corrupt/wrong schema => JW fallback.
- NaN/Inf/NaN score / empty candidate list.
- Modell gibt variable außerhalb der CNF aus => verwerfen/fallback.
- Out-of-distribution distribution tests.
- train-test leakage checks.
- ML policy cannot claim SAT or UNSAT; checker still verifies.
- infer time and model loading separate.

### 14.5 End-to-end Tests

- CLI → CQ-HECS API/Studio → solver → checker → provenance export.
- Studio and CLI same CNF/hash/status.
- HSCL1 launcher → existing CQ-HECS package → Studio.
- MCP tools → same backend, schema and proof contract.
- installed HSCL1 guest path, not just live ISO.

---

## 15. Benchmark-Protokoll

Jeder publizierte Leistungswert muss reproduzierbar sein.

### 15.1 Pflichtfelder

- Repo commit SHA, package version, Python/Rust/C++ compiler versions.
- OS/kernel, CPU model, total RAM, GPU, Vulkan driver, ICD.
- Formula source, dataset version, SHA-256, generator seed.
- Number of variables, clauses, clause length statistics, component count, induced width when calculated.
- Engine and config, proof-check setting, model/scorer hash.
- Per-engine wall time, CPU time, GPU time, peak RSS, solver nodes/decisions/propagations/conflicts/fronts.
- Proof size and checker duration.
- warmup and cold-run separation.
- all timeouts and failed/aborted runs retained.

### 15.2 Vergleichsregeln

- Vergleiche gleiche Instanzen und Limits.
- Median und p95 ausweisen; keine einzelne „Bestzeit“ als Durchbruch darstellen.
- CPU- und GPU-Zeit trennen; Datentransfer separat messen.
- Trainingstests von Hold-out trennen.
- Solver-Ergebnisse erst nach Korrektheits-/Proof-Check werten.
- kleine Benchmarks nicht als allgemeine Aussage über SAT-Härte darstellen.
- negative Resultate mitveröffentlichen.
- keine künstlich schwache Baseline verwenden, wenn CaDiCaL oder der bestehende CQ-HECS-Pfad verfügbar ist.

### 15.3 SHA / P-vs-NP

SHA-256- oder Reduced-Round-SHA-Instanzen sind nützliche konkrete SAT/CNF-Familien und können zur Messung dienen. Kein endlicher Lauf beweist `P = NP` oder `P != NP`. Reduced-Round-Ergebnisse nie als Angriff auf vollständiges SHA-256 ausgeben. Den existierenden Forschungswarnhinweis zu P-vs-NP beibehalten.

---

## 16. SOTA-Forschungszuordnung und konkrete Nutzung

Die folgenden Arbeiten sind Ansatzpunkte, keine Garantien. Jeder Agent muss Veröffentlichungsjahr, Version, Lizenz, Reproduzierbarkeit und Einschränkungen prüfen, bevor er Code daraus übernimmt.

| Thema | Nutzen für HCSPNP | klare Grenze |
|---|---|---|
| ICLR 2026 — Learning from Algorithm Feedback: One-Shot SAT Solver Guidance with GNNs | GNN schlägt Branching-Hinweise für einen bestehenden Solver vor; feedback-getriebenes Training | nur Guidance, nicht vollständiger Solver; Generalisierung testen |
| ICLR 2026 — On the Expressive Power of GNNs for Boolean Satisfiability | zeigt theoretische Grenzen der Unterscheidbarkeit von SAT/UNSAT-Paaren | Grund, GNN nicht als Wahrheitsorakel einzusetzen |
| AAAI 2026 — Proof Systems for Tensor-based Model Counting | formalere Verbindung von Tensor-basiertem Model Counting und Proof-Systemen | kein automatischer Vorteil; konkrete Beweis-/Checkerarchitektur notwendig |
| SAT Competition 2025/2026 | reale Wettbewerbsmethodik, Tracks, Ressourcen und Zertifikatsregeln | Benchmarks und Ressourcenlimits fair reproduzieren |
| Vulkan External Memory / Host Memory Specs | optionale technische Basis für bestimmte Host-/Device-Memory-Wege | extensions, device support, alignment und sync sind Pflicht; nicht mit HDD-Zero-Copy verwechseln |
| `mmap(2)` / Linux Memory Mapping | CPU-seitige file-backed Speicherbereiche und Paging | kein GPU-RAM und keine garantierte Echtzeit-I/O |
| cotengra / opt_einsum | Kontraktionspfadplanung als Forschungsvergleich | Pfadplanung ist selbst aufwändig; exakte Zählung muss erhalten bleiben |

### 16.1 Referenzlinks

- CQ-HECS: <https://github.com/timfromhcs/CQ-HECS>
- HSCL1: <https://github.com/timfromhcs/HSCL1>
- HCS Foundry: <https://github.com/timfromhcs/hcs-foundry>
- ICLR 2026 GNN Guidance: <https://arxiv.org/abs/2505.16053>
- ICLR 2026 GNN Expressivity: <https://openreview.net/search?q=On%20the%20Expressive%20Power%20of%20GNNs%20for%20Boolean%20Satisfiability>
- Vulkan external host memory: <https://registry.khronos.org/vulkan/specs/latest/man/html/VK_EXT_external_memory_host.html>
- Linux `mmap(2)`: <https://man7.org/linux/man-pages/man2/mmap.2.html>
- cotengra: <https://cotengra.readthedocs.io/>
- opt_einsum: <https://optimized-einsum.readthedocs.io/>
- MCP Security Best Practices: <https://modelcontextprotocol.io/docs/tutorials/security/security_best_practices>

---

## 17. Priorisierte Arbeits-Roadmap

Nicht alle Tracks parallel beginnen. Zuerst Bestandsaufnahme und Integrationspfad stabilisieren. Jede Phase muss abgeschlossen und nachgewiesen sein, bevor die nächste auf dieselben Komponenten baut.

### M0 — Fresh repository audit (Pflicht vor jeder Codeänderung)

- `git status`, branch, remote, `main` SHA für CQ-HECS und HSCL1 notieren.
- Root-AGENTS/README/CLAIMS/BUILD_LOG/KNOWN_LIMITATIONS und einschlägige Tests lesen.
- `HCSPNP`-Repositorystatus neu abfragen; bei 404 nicht neu erstellen.
- CQ-HECS-SAT-/#SAT-/MCP-/Studio-/Vulkan-Verträge lesen.
- HSCL1 CQ-HECS-Paket, Launcher, ISO-Gates und Control-Center-Einstieg lesen.
- HCSUDA-Capability-Matrix nach PR #28 und parallele HCSEASYMATH-Pläne lesen.
- Bestandstabelle aktualisieren und nur dann mit M1 fortfahren.

**Acceptance:** reproduzierbarer Statusbericht, Liste realer existierender Module, offene Fragen und Datei-/Repo-Grenzen.

### M1 — Stabiler integrierter CQ-HECS-Laufpfad

- vorhandene CQ-HECS-Paketintegration reparieren/abrunden.
- Launcher startet vorhandenes Studio statt nur Doctor-/Terminalstatus.
- CPU-only Pfad garantieren.
- CLI, Studio und JSON liefern dieselben Solver-/Proof-Daten.
- Provenienz `hcs.run.v2` vollständig exportieren.

**Acceptance:** Clean-VM / clean user context startet CQ-HECS via HSCL1, löst SAT/UNSAT fixtures und exportiert Run Card; bestehende Tests bleiben grün.

### M2 — Proof UX und SAT/UNSAT-Vertrauen

- SAT-/UNSAT-Vertrauensstufen sichtbar machen.
- `scan` Tree-Resolution, OMNIWAVE DRAT, CaDiCaL DRAT und `watched` ohne Proof sauber abbilden.
- Checker-Failures und widersprüchliche Engines testen.
- native C++ SAT-Claims getrennt auditieren.

**Acceptance:** keine UI-/API-Ausgabe nennt ein nicht geprüftes UNSAT „zertifiziert“.

### M3 — #SAT Separator als erstklassiger Track

- bestehendes `sat_separator` in Studio/CLI nutzbar machen.
- Plan-Only-Preflight, induced width, Table-Budget und Count-Status.
- brute-force oracle tests und 64-bit-overflow tests.
- negative/broad instances cleanly `UNKNOWN`.

**Acceptance:** exakte Counts stimmen für alle kleinen Fixtures; Budget-Refusal liefert nie Teilzählung.

### M4 — Learned Guidance Baseline Upgrade

- bestehende JW und FeatureScorer als Baselines dokumentieren.
- negative Pigeonhole-Ergebnisse aufbewahren.
- GNN one-shot Guidance Prototyp mit reproduzierbarer Dataset-Pipeline.
- Hold-out-Benchmark nach Instanzfamilie.

**Acceptance:** GNN ist opt-in; ohne Modell funktioniert exakt derselbe Solver; SAT/UNSAT/Proof bleibt unabhängig.

### M5 — Tensor-based Model Counting Research

- separator -> factor graph conversion.
- exact CPU tensor reference.
- path planning / memory limits.
- comparison to existing separator.
- proof/verifier approach documented before calling result proof-checked.

**Acceptance:** klar abgegrenzte Problemklasse, für die das tensor backend einen belegten Vorteil oder eine neue Capability besitzt.

### M6 — Streaming / Storage / memory efficiency

- streaming DIMACS parsing.
- file-backed CNF stores, paging tests, cache metrics.
- explicit staging to Vulkan where beneficial.
- no zero-copy claims until hardware-proven.

**Acceptance:** large-formula memory cap works; crash and truncated input recover safely; GPU copy path is explicit.

### M7 — Optional HCSUDA integration

- concrete SAT/BCP kernel proposal.
- CPU oracle and capability gating.
- separate CQ-HECS/HCSUDA adapter.
- compare vs existing CQ-HECS Vulkan BCP.

**Acceptance:** same correctness, measured improvement on named hardware or clear reason not to ship.

### M8 — HSCL1 package and Control Center polish

- update existing `hscl-cqhecs` package.
- upgrade existing menu/Control Center entry.
- docs EN/DE/FR.
- live and installed guest tests.
- no duplicate package unless owner approves separate lifecycle.

**Acceptance:** existing package flow opens Studio reliably with CPU fallback and visible capability/proof statuses.

### M9 — Release hardening

- schema freeze.
- clean checkout install.
- tests, lint, package tests, image tests.
- SBOM/license/security review.
- claims matrix update.
- release notes with only verified features.

**Acceptance:** release artifact reproduces tests from a clean checkout; unsupported claims omitted.

### Later Track Q — QBF / TQBF (separat)

Erst beginnen, wenn SAT/#SAT-Portfolio und Proof-Contracts stabil sind. Eigenes Quantifier-Prefix-Parser-/Prenex-/Dependency-Schema, QBF-Solver, Strategy-Certificate-Format und unabhängiger Checker. Nicht als „NP-solver plus“ verkaufen; PSPACE-Komplettheit separat erklären.

---

## 18. Agentenrollen und Parallelisierung

Mehrere Agenten dürfen arbeiten, aber nur mit klaren Zuständigkeiten und getrennten Dateigrenzen.

| Agent | Verantwortungsbereich | Darf nicht |
|---|---|---|
| A — CQ-HECS Integration | Solver APIs, Portfolio, SAT Lab, Resultatschema | HSCL1 ISO/Paket gleichzeitig ohne Koordination ändern |
| B — Proof & tests | Proof-Verträge, Tree Resolution, DRAT, adversarial tests | Solver-Status ohne Checker hochstufen |
| C — #SAT / Tensor | separator, tensor experiments, width/memory models | SAT-Decision-API umdefinieren |
| D — GNN guidance | dataset, training, scoring, branch policy | Lösung behaupten oder Default ohne Benchmarks ändern |
| E — Vulkan / storage | existing GPU BCP, streaming, memory staging | HCSUDA-LLM kernels als SAT-Kernel deklarieren |
| F — HSCL1 integration | existing launcher, package, CLI, Control Center, ISO gates | neue parallele HCSPNP-App/Paketfamilie bauen |
| G — QA / release | full tests, benchmarks, evidence, changelog | fehlgeschlagene Tests ignorieren oder Belege erfinden |

### 18.1 Parallelisierungsvertrag

- Vor Start: Dateien und Verantwortungsbereiche im Plan reservieren.
- Keine zwei Agenten ändern dieselbe Kern-API gleichzeitig.
- Jeder Agent commits nur seinen klar abgegrenzten Workstream.
- Integrator prüft Branch-Diffs und API-/Schema-Kompatibilität.
- Ein gemeinsamer Integration-Branch; kein ungeprüftes direct push auf `main`.
- CI, Tests und Proof-Checks vor Merge.
- Agentenkommunikation in einem kurzen Log: changed paths, commands, results, blockers.

---

## 19. Self-heal / autonomer Arbeitszyklus

Der Agent darf autonom Probleme beheben, aber nur kontrolliert und belegbar:

```text
INSPECT
  ↓
PLAN one bounded change
  ↓
IMPLEMENT smallest safe slice
  ↓
RUN targeted tests
  ↓
RUN full relevant suite
  ↓
VERIFY proof/model contract
  ↓
COMPARE behavior + benchmark
  ↓
UPDATE docs / claims / changelog
  ↓
COMMIT to scoped branch
  ↓
REVIEW diff and regression evidence
  ↓
MERGE only when gates pass
```

### 19.1 Self-heal-Regeln

- Ein Test schlägt fehl: zuerst Fehler reproduzieren, nicht Tests abschalten.
- Kein `xfail`, Skip, schwächerer Threshold oder geändertes Fixture ohne begründete Erklärung und Review.
- Keine Änderung der Proof-Checker-Logik nur um einen fehlerhaften Proof zu akzeptieren.
- Keine automatische Änderung des Solver-Defaults nach nur einem Benchmark.
- Keine Git-Rebase-/Force-Push-Aktion auf fremde/unklare Branches.
- Kein Löschen nicht versionierter Dateien oder User-Artefakte.
- Build-, Benchmark- und VM-Logs unter `artifacts/` halten und nur committen, wenn Repositorykonvention das vorsieht.
- Nach Änderung der öffentlichen APIs CLI, MCP, Studio und Browser-Konformität erneut testen.

### 19.2 Dokumentationspflicht

Jede substanzielle Arbeit ergänzt:

- `docs/BUILD_LOG.md` oder vorhandenes CQ-HECS-Äquivalent;
- Capability-/Claims-Tabelle;
- Decision Record, wenn Architekturentscheidung fällt;
- Benchmarkresultat (auch negative Resultate);
- README nur mit Features, die ihren Status haben.

---

## 20. Git- und Multi-Repo-Disziplin

### 20.1 Vor jeder Operation

```bash
git status --short --branch
git remote -v
git log -5 --oneline --decorate
```

- Repo-Root sicher erkennen.
- Aktuellen Branch und Remote verifizieren.
- Keine uncommitted Owner-Arbeit überschreiben.
- Keine Repo-Neuanlage, wenn Repo bereits existiert.
- Für CQ-HECS und HSCL1 getrennte Branches/Commits halten.

### 20.2 Branch-/Commit-Stil

Beispiele:

- `codex/hcspnp-proof-ux`
- `codex/hcspnp-counting-lab`
- `codex/hcspnp-guidance-gnn`
- `codex/hscl1-cqhecs-launcher`

Conventional Commits verwenden, z. B.:

- `feat(sat): expose proof status in studio`
- `test(sat): add independent DRAT rejection fixtures`
- `feat(count): integrate exact separator planning`
- `fix(hscl1): launch existing cq-hecs studio from desktop entry`
- `docs(hcspnp): record measured guidance results`

### 20.3 Merge-Sperren

Nicht mergen, wenn:

- relevante Tests fehlschlagen;
- API-/Schemaänderung ohne Migration besteht;
- Proof-Status falsch dargestellt wird;
- CPU fallback defekt ist;
- der Launcher den Runtime-Prozess verliert oder root ausführt;
- ein neues Programm/Paket nur wegen organisatorischer Bequemlichkeit neben den Bestand gesetzt wird;
- docs claims neuer sind als die tatsächlichen Tests.

---

## 21. Definition of Done

HCSPNP gilt nicht als „integriert“, nur weil eine Landingpage, ein Icon oder eine neue Menükarte existiert.

### Technisch

- alle HCSPNP-Funktionen laufen in CQ-HECS-Fachlogik;
- HSCL1 startet das vorhandene CQ-HECS-Paket;
- kein doppelt implementierter Solver/Model runtime/MCP host;
- CPU-only Modus bleibt vollständig nutzbar;
- optional GPU/HCSUDA wird capability-gated und geprüft;
- SAT-Modell wird gegen Original-CNF geprüft;
- UNSAT-Proofstatus ist korrekt und unabhängig geprüft, wo verfügbar;
- exakte #SAT-Zählung wird nicht mit Näherung verwechselt;
- `UNKNOWN`/Unsupported/Timeout wird ehrlich zurückgegeben.

### Nutzererlebnis

- bestehendes Studio erweitert, nicht dupliziert;
- vorhandener HSCL1 Launcher und Control Center führen zur selben Oberfläche;
- Solver, Proof, Count und Policy verständlich erklärt;
- Logs, Runs und Exporte reproduzierbar;
- EN/DE/FR und Keyboard-/Accessibility-Tests berücksichtigt.

### Betrieb / Distribution

- bestehendes Debian-Paket aktualisiert;
- Live-Image und installierte VM getestet;
- kein automatisch gestarteter privilegierter Hintergrunddienst;
- keine Gewichte oder großen Forschungsdaten in ISO;
- Security-/License-/SBOM-Review dokumentiert.

### Wissenschaft

- Vergleich gegen bestehende Baselines;
- sämtliche Seeds, Limits und Hardware dokumentiert;
- negative Resultate erhalten;
- keine Behauptung `P=NP`, `NP-hard solved` oder Zero-Copy ohne mathematischen/technischen Nachweis.

---

## 22. Erste Aufgaben für den nächsten Agenten

Arbeite diese Liste in dieser Reihenfolge ab. Keine neuen Architekturannahmen treffen, bevor diese Dateien gelesen wurden.

### CQ-HECS

1. `README.md`, `pyproject.toml`, `docs/UNIFIED_SOLVER.md`, `cqhecs/unified.py` lesen.
2. `cqhecs/sat.py`, `cqhecs/sat_external.py`, `cqhecs/drat.py` vollständig lesen.
3. `cqhecs/sat_separator.py` und seine Tests/Benchmarks lesen.
4. `cqhecs/omniwave/learned.py`, BCP-CPU, Vulkan-Adapter und Shader lesen.
5. `cqhecs/studio/app.py`, statische Dateien, Browser-SAT-/Proof-Dateien lesen.
6. `cqhecs/provenance.py`, `cqhecs/mcp_server.py` und CLI-Commands lesen.
7. `src/sat_solver.cpp`, Tensor-/Tiered-Storage-Code separat auditieren.
8. Bestehende Test-Suite aus clean checkout ausführen; Ergebnisse, Versionen und Revision protokollieren.

### HSCL1

1. Root `AGENTS.md`, `README.md`, `docs/CLAIMS.md`, `docs/KNOWN_LIMITATIONS.md`, `docs/BUILD_LOG.md` lesen.
2. Merge PR #28 / SHA `37d2f6d` prüfen; HCSUDA-H2-/H3c-2-/H3c-3-1-Änderungen verstehen.
3. `packages/debian/hscl-cqhecs/` komplett lesen, nicht nur Dateinamen.
4. `tests/unit/test_pkg_cqhecs.py` und `tests/unit/test_cqhecs_in_image.py` lesen.
5. `scripts/remaster-iso.sh`, `distro/live/verify-image.sh`, Launcher und Control Center prüfen.
6. Bestehende `hscl` CLI/MCP-Kommandos lesen und HCSEASYMATH-Plan/File Ownership beachten.
7. Den CQ-HECS-Launcher auf Verhalten prüfen: öffnet er Studio tatsächlich? Ist Status/Doctor nur ein Terminal? Belege sammeln.
8. Installed-system-VM-Status separat vom Live-Image-Status bewerten.

### Ergebnisbericht vor Implementierung

Gib einen kompakten Bericht mit:

- aktuellen SHA pro Repo;
- vorhandene Integration, die wiederverwendet wird;
- 5–10 konkrete Lücken mit Datei-/Testbezug;
- wichtigste Proof-/Memory-/API-Risiken;
- genaue Dateien für den ersten kleinen PR;
- Testkommando und Acceptance Criteria.

Erst danach M1 implementieren.

---

## 23. Technische Referenznotizen

### 23.1 Prüffragen für native C++ SAT

- Hat der native Solver eine vollständige DIMACS-Parserprüfung?
- Werden alle Variablen und Klauseln korrekt validiert?
- Ist sein SAT-Modell vollständig und gegen die Original-CNF geprüft?
- Kann er UNSAT unabhängig zertifizieren oder nur Suchraum erschöpft melden?
- Sind Hash-/Dedup-/Collision-Strategien korrekt, keine probabilistische Hash-Kollision als logische Gleichheit?
- Ist Timeout/Memory-Budget thread-safe und fail-closed?
- Sind C ABI und Buffer-Grenzen geprüft?
- Gibt es differential tests gegen Python-Referenz und CaDiCaL?

Erst nach diesen Tests darf native C++ in die offizielle Solver-Capability-Liste.

### 23.2 Prüffragen für Tensor-Code

- Ist die Funktion ein allgemeiner Tensor-Simulator oder nur ein Spezial-/Diagnosemodell?
- Welche Tensorformen/Graphen werden wirklich unterstützt?
- Wie wird Index-/Bitreihenfolge abgebildet?
- Ist jede Operation exakt und integer-safe?
- Wie werden Kontraktionspfad, Peak-Intermediate und Memory-Cap bestimmt?
- Sind Resultate gegen Brute Force und Separator geprüft?

Ein kompakter GHZ-/Parity-Diagnosepfad darf nicht als allgemeine SAT-Tensor-Network-Engine beschrieben werden.

### 23.3 Prüffragen für Storage

- echte File-backed Mapped Region oder nur Buffer mit `memcpy`?
- null-size/empty-file handling?
- short reads / truncation / concurrent mutation?
- alignment und lifetime?
- Page fault und I/O-Metriken?
- GPU host-visible memory property und Vulkan extension support?
- atomare Freigabe, fence/semaphore, queue ownership?

### 23.4 Prüffragen für Learned Model

- feature schema stabil und versioniert?
- model provenance, license, weights hash?
- preprocessing identisch beim Training und Inference?
- deterministic mode/fixed seeds?
- adversarial input robustness?
- out-of-distribution fallback?
- branch ranking beeinflusst nur Suchreihenfolge?
- kann man Baseline ohne Modell reproduzieren?

---

## 24. Entscheidungsprinzip für jeden neuen Vorschlag

Bevor ein Agent neue Architektur implementiert, beantworte schriftlich:

1. **Existiert das bereits?** In welchem Repo und in welchen Dateien?
2. **Was fehlt wirklich?** Ist es eine Engine, ein Adapter, eine UI, ein Proof-Checker, Packaging oder nur Dokumentation?
3. **Warum ist Erweiterung des Bestands unmöglich oder schlechter?** Nur dann neue Komponente erwägen.
4. **Welche exakte Semantik besitzt die Funktion?** SAT, UNSAT, #SAT, Approximation, Heuristik, Simulation?
5. **Wie wird Wahrheit geprüft?** unabhängiger Checker, CPU-Oracle, Brute Force oder nur Self-Report?
6. **Welche Ressourcen benötigt sie?** CPU, GPU, RAM, SSD/HDD, Laufzeit, Netzwerk?
7. **Wie funktioniert sie ohne optionales Backend?** CPU fallback oder `unsupported`.
8. **Welche Oberfläche ist bereits zuständig?** CQ-HECS Studio / HSCL1 Control Center / vorhandene CLI.
9. **Wie wird sie ausgeliefert?** vorhandenes Debian-Paket und ISO-Gates.
10. **Was darf nachher tatsächlich behauptet werden?** Nur die mit Logs, Tests, Hashes und Checker belegte Aussage.

**Endgültige Leitlinie:** CQ-HECS bleibt die Solver- und Forschungs-Engine. HSCL1 bleibt das Betriebssystem und der Integrationsrahmen. HCSUDA bleibt eine optionale, evidenzbasierte Compute-Schicht. HCSPNP erweitert diese bestehenden Systeme zu einer einheitlichen Oberfläche und einem einheitlichen, prüfbaren Run-Vertrag — nicht zu einem weiteren Programm neben ihnen.
