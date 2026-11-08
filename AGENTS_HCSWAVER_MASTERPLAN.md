# AGENTS.md — HCSWaver

## Autonomous product, research, implementation, self-healing, and HSCL1 integration master plan

> **Product:** HCSWaver Studio — *Weaving the Fabric of Complexity*  
> **Publisher:** HCSMEDIA  
> **Credit:** Made with love by hcsmedia  
> **Primary target:** a standalone, local-first, cross-platform neuro-symbolic complexity and proof workstation  
> **Standalone repository target:** `https://github.com/timfromhcs/hcswaver` (verify/create; it was not returned by the repository lookup on 2026-11-07)  
> **OS integration target:** `https://github.com/timfromhcs/HSCL1`  
> **Existing research engine to integrate:** `https://github.com/timfromhcs/CQ-HECS`  
> **Local model infrastructure:** `https://github.com/timfromhcs/hcs-foundry`  
> **Execution strategy:** inspect → research → architecture → parallel implementation tracks → bounded self-healing loops → independent verification → standalone push/release → HSCL1 integration PR → verified OS image  
> **Platforms:** Windows 11 x64 and HSCL1 / Ubuntu 26.04 LTS x64; Linux development builds first  
> **Languages:** English, German, French (`en`, `de`, `fr`)  
> **Product philosophy:** local-first, open-source, hardware-aware, proof-carrying, reproducible, accessible, honest about limitations

This file is an engineering execution contract, not a brainstorming document. Build a real application, real engines, real data contracts, real tests, and a real package for HSCL1. A UI panel, feature flag, placeholder API, benchmark chart, model card, or README statement is never evidence that a feature works.

The user-provided nine-page PDF, *Jetzt fasse beide Videos und SOTA web Research zu ...*, is the initial product brief. Preserve its core idea and five Studio workspaces, but correct technical overclaims and validate all research references before implementation. The PDF describes: Cook–Levin / Circuit-SAT, 3-SAT reductions and Mario-style gadgets; a local high-performance SAT workstation; reduction visualization; solver experimentation; adversarial counterexamples; Lean 4 proof checking; local LLM/MCP integration; C++20, Rust/Tauri, TypeScript/Three.js; and a staged implementation plan. These are the product inspiration, not proof that the proposed algorithms are correct or that the described performance is attainable.

---

# 0. Operating rules and non-negotiable guarantees

## 0.1 Role and team model

Act as one integrated engineering and research team:

- Principal product / system architect.
- Complexity-theory and SAT researcher.
- C++20 algorithms and performance engineer.
- Rust systems / API / MCP engineer.
- Lean 4 formal verification engineer.
- Vulkan / WebGPU compute engineer.
- React / TypeScript / Three.js UX engineer.
- Database and reproducibility engineer.
- AI-agent / local-model integration engineer.
- Debian packaging / Ubuntu / KDE integration engineer.
- Security, QA, release, documentation, and research-audit engineer.

Use subagents where available, but keep one integration lead responsible for shared contracts, source-of-truth decisions, test gates, versioning, and claims. Subagents must not independently change public APIs, version numbers, release files, shared architecture docs, or Git branches without coordination.

## 0.2 Absolute rules

1. **No fabricated completion.** Do not mark a component complete because code compiles, a page renders, a model responds, or a synthetic test passes. Use the feature's acceptance gates.
2. **No false P vs. NP claim.** HCSWaver is a research workstation. It does not solve P vs. NP merely by integrating SAT, GPU compute, LLMs, evolutionary search, or Lean. No experimental scaling curve proves an asymptotic lower bound or a polynomial algorithm.
3. **Proofs are checked, not admired.** An LLM explanation, a solver log, an unverified DRAT file, a green UI badge, a passing sampled test, or a plotted graph is not a mathematical proof. Formal claims require a trusted checker / proof assistant kernel and a recorded input digest.
4. **SAT results are independently validated.** Every SAT model is checked against the original formula. Every UNSAT claim must include a supported proof artifact and a checker result, or be explicitly reported as unverified / unsupported. Timeouts and resource exhaustion are `UNKNOWN`, not `UNSAT`.
5. **The solver must never silently change semantics.** Preserve original inputs, normalization records, source hashes, canonical hashes, assumptions, bounds, and the exact encoding version.
6. **No unsafe arbitrary execution.** LLM-generated C++, Rust, Python, Lean metaprograms, benchmark scripts, or plugins must not execute on the host with unrestricted filesystem, process, network, or credential access. Use an unprivileged sandbox and explicit capability policy.
7. **No automatic cloud fallback.** Local-first means local by default and local-only unless the user explicitly opts into a named remote provider for a particular task. Never upload formulas, source code, models, datasets, prompts, proof artifacts, or logs silently.
8. **No model weights or large benchmark datasets in Git or the ISO.** Store metadata, pinned revisions, hashes, and download recipes. Download artifacts only after disk-space, license, and provenance checks.
9. **No hardcoded hardware assumptions.** Detect CPU, RAM, GPU, Vulkan, WebGPU, driver, disk, and runtime capabilities. Use CPU reference implementations and graceful fallbacks.
10. **No claiming GPU acceleration from device enumeration.** A Vulkan device being visible does not prove a workload executes correctly or faster. Require end-to-end benchmark evidence on that device.
11. **No unbounded self-healing.** A repair loop has an explicit budget, preserves the first failure, and escalates after three materially different repair attempts for the same root cause.
12. **No disabling tests to get green CI.** Fix the defect or mark the gate blocked with its reproducer and cause. Do not downgrade test assertions, increase timeouts without evidence, skip failing tests, or lower coverage thresholds merely to obtain a release.
13. **Preserve user work.** Inspect `git status`, remotes, branches, tags, and local diffs before changing files. Never run destructive cleanup or overwrite uncommitted work.
14. **No force push / history rewrite.** Work on feature branches. Never push directly to `main` unless the repository policy and explicit task instructions permit it. Never force push.
15. **No security claims without the threat model and evidence.** Use loopback-only networking by default, typed APIs, least privilege, path allowlists, safe temporary directories, and explicit process boundaries.
16. **Every meaningful claim has evidence.** Store tests, machine-readable run metadata, hashes, and research notes. State what was not tested.
17. **Keep the product usable on constrained hardware.** The first release must offer CPU-only mode, modest memory defaults, cancellation, bounded jobs, and an app UI that stays responsive under load.
18. **Third-party licenses are mandatory input data.** Do not vendor or redistribute models, solvers, assets, benchmark sets, or binaries until license, notices, version, and redistribution conditions are recorded.

## 0.3 Evidence labels

Use these exact labels consistently across the UI, docs, database, and release notes:

- `PROPOSED` — not implemented.
- `IMPLEMENTED` — code exists, not yet sufficiently tested.
- `TESTED` — automated tests pass for the declared scope.
- `VM-VERIFIED` — end-to-end checked in a virtual machine.
- `HARDWARE-VERIFIED` — checked on named physical hardware with driver/runtime recorded.
- `FORMALLY-VERIFIED` — proof accepted by the declared trusted checker/kernel for the exact theorem and source revision.
- `BENCHMARKED` — reproducible benchmark completed against a named baseline on recorded hardware.
- `EXPERIMENTAL` — research-only feature with limited evidence or unstable behavior.
- `BLOCKED` — implementation cannot proceed safely or a required dependency is unavailable.
- `DEFERRED` — intentionally postponed with reason.
- `REJECTED` — tested or reviewed and not adopted.

Never use `verified` without stating *what*, *by which checker*, *for which input*, *under which assumptions*, and *at which revision*.

## 0.4 Work-resume protocol

At the start of every new agent session:

```bash
git status --short --branch
git remote -v
git log -8 --oneline --decorate
git branch --all --no-color
git tag --list --sort=-version:refname | head -30
```

Then inspect `AGENTS.md`, `README.md`, `CHANGELOG.md`, the latest research record, open issues/PRs, CI status, and `docs/engineering/EXECUTION_LOG.md`. Do not trust an old handoff over the actual checkout. Record the starting commit SHA, clean/dirty state, toolchain versions, available compute, and current blockers.

---

# 1. Repository strategy and integration contract

## 1.1 Verified starting context (snapshot: 2026-11-07)

The public repositories were inspected read-only during preparation of this plan. Re-verify each fact at execution time.

### HSCL1

- Repository: `timfromhcs/HSCL1`, public, default branch `main`.
- Existing README identifies the product as HSCL1 on Ubuntu 26.04 LTS / Kubuntu with KDE Plasma 6, Rust `hscl` CLI, Qt/QML Control Center, Debian packages, local-AI tooling, and an ISO remaster pipeline.
- The observed public status in its README is **pre-alpha `0.1.2-alpha.0`**, VM-tested only, not physical-hardware verified, and unsigned. Do not silently update these claims.
- Existing package architecture includes `packages/debian`, `cli/hscl`, `apps/control-center`, `ai`, `distro`, and `scripts`.
- Existing CLI documentation shows JSON-capable commands and a read-only-by-default `hscl mcp` server. `hscl hw detect` already inventories CPU, RAM, firmware, PCI devices, GPU render nodes, and AMD VRAM/GTT separately.
- Existing architecture prefers a small native Control Center (Qt 6/QML), Rust CLI, rootless isolation, and constrained privileged helpers. Keep those principles.
- Existing canonical OS master files include `AGENTS.md` and `docs/superpowers/plans/2026-11-06-long-horizon-to-v2.md`. Extend them carefully; do not replace or erase their existing milestones.
- The current connected GitHub session returned read-only permission for HSCL1. If the active agent also lacks push rights, prepare a complete local integration patch and report the exact permission blocker. Never pretend that a PR or merge was created.

### HCS Foundry

- Repository: `timfromhcs/hcs-foundry`, public, default branch `main`.
- Its README describes a local model lab with GGUF import, `llama.cpp`-based inference, Vulkan-aware execution, model management, benchmarking, training workflows, and a local MCP server.
- Its MCP documentation describes typed tools such as `machine_scan`, `machine_budget`, `models_list`, `datasets_list`, `datasets_export`, `vram_status`, training, merge, and GGUF quantization. It explicitly does **not** expose a generic shell/exec tool.
- The MCP server runs over stdio (`foundry mcp serve` or `HCSFoundry.exe --mcp`). The fetched documentation reports protocol version `2025-06-18`; negotiate supported protocol versions and do not assume it already implements a newer MCP revision.
- HCSWaver must reuse Foundry for model discovery and, where an actual generation API/adapter is present and tested, model inference. Do not duplicate the Foundry model catalog, downloader, machine budget, or local `llama.cpp` supervisor.
- Do not assume that the Foundry MCP tools listed above include model text-generation. Inspect the current API and add a narrowly typed generation adapter if necessary. Do not invent an endpoint.

### CQ-HECS

- Repository: `timfromhcs/CQ-HECS`, public, default branch `main`, Apache-2.0 project.
- Its current README snapshot reports version `5.0.0` (dated 2026-11-02) and a provenance contract `hcs.run.v2` with exact input text/hash, engine/mode, seed, version, source revision, error kinds, and stated limits.
- It already has a SAT subsystem: scan DPLL reference, watched-literal DPLL, optional CaDiCaL adapter, exact #SAT/variable elimination, OMNIWAVE research engine, in-repository certificates, DRAT/LRAT toolchain integration, SAT labs, CLI/MCP/API surfaces, and reproducibility tests. The exact current state must be re-audited before reuse.
- It has C++20 / C ABI / Vulkan integration in its broader simulator and web/WASM surfaces. Do not build a second SAT solver just because the hcswaver product concept has a new name.
- Treat CQ-HECS as the existing computational research backend / adapter source. Prefer calling a stable CLI/API/MCP contract or adding a documented library interface there over copying internals into hcswaver.

### HCSWaver standalone repository

- `timfromhcs/hcswaver` did not resolve through the GitHub repository lookup on 2026-11-07 (404). This can mean not yet created or not visible to the current credential. Confirm with the authenticated profile and repository list before creating anything.
- If absent and the user has repository creation permission, create one public standalone repository named `hcswaver` under `timfromhcs`, initialize it with the audited project structure, license, README, AGENTS file, CI, issue templates, security policy, and initial implementation.
- Do not silently create a different repository name or move code into an unrelated project.

## 1.2 Project responsibility matrix

| Project | Owns | Must not become |
|---|---|---|
| HSCL1 | OS, desktop, package integration, launchers, hardware detection, system security, app lifecycle | A second SAT solver or a model-weight warehouse |
| HCS Foundry | Local model discovery, download, runtime management, machine budget, inference/training adapters, model-related MCP tools | The owner of SAT semantics, mathematical proofs, or HCSWaver project history |
| CQ-HECS | Existing circuit simulation and SAT/#SAT research engines, existing solver experiments, provenance surfaces | A second desktop workstation duplicating HCSWaver Studio |
| HCSWaver | Unified complexity research UI, reduction workbench, solver orchestration/adapters, adversarial experiments, formal proof workspace, research provenance | A claim that it has solved P vs. NP or a monolithic rewrite of all three projects |

## 1.3 Parallel delivery: one product, multiple repositories

Run four coordinated workstreams in parallel after contracts are agreed:

- **Track A — HCSWaver standalone:** desktop app, native core, local database, CLI, API, MCP, research notebooks, benchmark UX, proof desk.
- **Track B — HSCL1 integration:** Debian packages, launcher, `hscl hcswaver` commands, Control Center entry, documentation, ISO manifest, VM tests.
- **Track C — CQ-HECS adapter:** stable solver/circuit adapter, run/provenance schema mapping, tests against real fixtures, no code fork unless required and license-reviewed.
- **Track D — HCS Foundry adapter:** capability discovery, machine budget, model registry/model runtime adapter, MCP transport and failure handling.

The integration lead maintains one `integration-contracts/` directory in HCSWaver and a matching versioned contract document in HSCL1. A workstream cannot change a shared schema without updating compatibility tests in the dependent workstreams.

## 1.4 Source of truth and master-plan incorporation

The agent must extend, not replace, the existing HSCL1 master plan:

1. Read the current `HSCL1/AGENTS.md` completely.
2. Read the current `HSCL1/docs/superpowers/plans/2026-11-06-long-horizon-to-v2.md` completely.
3. Add a focused section to the HSCL1 `AGENTS.md` called `HCSWaver Scientific Workstation Integration` with package names, dependency boundaries, security requirements, status vocabulary, and integration acceptance criteria.
4. Add a new milestone/workstream to the existing long-horizon plan without renumbering or deleting completed work. Place HCSWaver work on a parallel track so it does not block the OS critical path.
5. Add `docs/integrations/HCSWAVER.md` (or the existing equivalent) describing install, launch, package dependencies, app lifecycle, MCP configuration, hardware behavior, licenses, and known limitations.
6. Add a package manifest/decision record to the existing HSCL1 packages system; do not invent a package layout before inspecting the actual `.deb` control files and build scripts.
7. Update `docs/CLAIMS.md` and `docs/BUILD_LOG.md` only when evidence exists. Keep PLANNED / IMPLEMENTED / TESTED / VM-VERIFIED / HARDWARE-VERIFIED status accurate.
8. Keep HCSWaver's standalone `AGENTS.md` and README canonical for its own implementation; HSCL1 links to the project instead of copying all of its detailed code plan.

If cross-repository writes cannot be performed in the current environment, create a patch folder in the HCSWaver checkout:

```text
integration/hscl1/
  README.md
  AGENTS_SECTION.md
  MASTERPLAN_MILESTONE.md
  PACKAGE_DESIGN.md
  CLI_DESIGN.md
  TEST_MATRIX.md
```

Those are proposed patches only; do not claim they were merged into HSCL1 until a real commit/PR is visible.

## 1.5 License and third-party code policy

- Audit every repository's actual `LICENSE`, `NOTICE`, and dependency licenses before choosing HCSWaver's license.
- CQ-HECS currently advertises Apache-2.0; HCS Foundry advertises MIT; HSCL1 advertises GPL-3.0-or-later. Apache-2.0 and MIT components may be used in compatible combinations subject to notices and dependency terms. Do not assume every bundled dependency is permissively licensed.
- Recommended starting point for HCSWaver: Apache-2.0 for a standalone reusable tool, **subject to an explicit license compatibility review**. Do not copy GPL-only HSCL1 code into the standalone project under Apache-2.0.
- The HSCL1 package may depend on a separately licensed HCSWaver package; preserve its license and notices. Do not relicense upstream solver code.
- Use SPDX identifiers, a machine-readable third-party notices file, and an SBOM. Record the exact upstream version/commit and local patches for every external solver.

---

# 2. Product vision and users

## 2.1 Product definition

HCSWaver is a **local-first neuro-symbolic complexity and proof workstation**. It combines:

- Interactive reductions and Boolean circuit construction.
- SAT / #SAT / solver orchestration with validated witnesses and proof artifacts.
- Graph and search visualization.
- Solver heuristic experiments and controlled algorithm evolution.
- Adversarial instance and counterexample generation.
- Lean 4 formalization and kernel-checked proof workflows.
- A research notebook, immutable experiment history, and reproducible benchmark database.
- Typed local APIs and MCP tools for approved local AI agents.

It is closer to a research IDE / computational lab than a generic chat application. Its UI can borrow the clarity of a DAW, the visual organization of a node editor, and the navigation of a code IDE, but it must remain a serious scientific tool rather than a decorative simulator.

## 2.2 Primary users and jobs to be done

1. **Complexity researcher:** define a problem family, create or import reductions, inspect structural properties, generate instances, test conjectures, formalize lemmas.
2. **SAT engineer:** compare solver configurations on repeatable benchmarks, inspect conflicts/propagation, tune branching and restart strategies, verify certificates.
3. **Formal methods researcher:** turn definitions and lemmas into Lean 4 files, run the pinned toolchain, inspect goals and diagnostics, preserve kernel-accepted proof artifacts.
4. **Student / educator:** explore Turing machines, Cook–Levin, Circuit-SAT, Tseytin transformations, reductions, gadgets, and proof concepts visually with small reproducible examples.
5. **AI-agent developer:** expose bounded tools to local models; let an agent propose hypotheses or source patches; validate all outputs through deterministic engines and tests.
6. **Open-source contributor:** add a solver adapter, encoding, visualization, benchmark family, checker, or proof formalization with contribution rules and test fixtures.

## 2.3 Five primary Studio workspaces from the user PDF

Retain the five-room concept, but implement in a thin vertical slice order:

1. **Reduction Canvas** — bounded verifier / machine specification → Boolean circuit / AIG → CNF / 3-CNF; editable gate graph; formula and proof-of-equivalence inspection; educational gadget view.
2. **Wavefront Observatory** — clause-variable incidence graphs, propagation events, conflict neighborhoods, branch decisions, solver telemetry, and optional relaxation visualizations. This is an explanatory view, not a claim that a graph layout is a physical model of complexity.
3. **Solver Foundry** — solver adapters, solver portfolios, CPU/GPU experiments, heuristic configuration, repeatable benchmark execution, resource budgets, and safe algorithm candidates.
4. **Adversarial Arena** — generated hard instances, minimization, counterexample shrinking, differential solver testing, and attacks on proposed heuristics/invariants. Label finite empirical survivability as empirical only.
5. **Formal Proof Desk** — Lean 4 project, pinned toolchain, mathlib dependencies where needed, proof goals, diagnostics, proof tree, theorem metadata, and exact source revision.

Additional essential workspaces (may begin as tabs within existing rooms):

- **Research Notebook / Evidence Ledger** — hypotheses, references, experiment plans, negative results, run cards, and versioned research records.
- **Data & Benchmark Library** — local datasets, licenses, hashes, family splits, provenance, benchmark descriptions, and import verification.
- **Agent Console** — active jobs, model/runtime adapter status, allowed tools, approvals, budgets, and audit trail.

## 2.4 Product boundaries

HCSWaver may help discover algorithms, counterexamples, patterns, formal lemmas, and research questions. It may not:

- claim P = NP or P ≠ NP without a complete, independently reviewed mathematical proof;
- convert an observed exponential run into a general lower-bound theorem;
- infer polynomial complexity from a finite number of successful instances;
- treat a neural heuristic, continuous relaxation, tensor contraction, or LLM suggestion as an exact SAT solver;
- treat a visualization as evidence of computational complexity;
- present an educational Mario-style simulation as a valid NP-hardness reduction until every game rule, gadget, and iff-preservation argument is specified and checked;
- silently convert an unsupported case into a plausible-looking success state.

---

# 3. Research grounding and corrections to the initial brief

## 3.1 Cook–Levin / computation tableau

Implement the theorem in stages rather than pretending an arbitrary user Python program can immediately be compiled into a verified Cook–Levin reduction.

**Stage A — bounded Boolean programs:** accept a deliberately small, typed source language or explicit verifier IR. Define deterministic semantics and explicit input/certificate/time bounds. Reject unsupported operations.

**Stage B — circuit compilation:** compile the bounded IR to an AIG or explicit Boolean gate graph. Every compilation pass must emit a mapping from source operations to gates and a machine-checkable equivalence obligation/test.

**Stage C — Tseytin CNF:** encode each gate with definitional clauses, add the output assertion, and preserve a mapping from each auxiliary variable to the source gate.

**Stage D — bounded Turing-machine tableau:** define a deterministic single-tape TM model, finite alphabet, finite state set, head marker, initial row, legal transition relation, and accepting condition. Use local transition constraints only after the neighborhood encoding is formalized. Prove that valid accepting computations correspond to satisfying assignments.

**Stage E — general Cook–Levin result:** formalize size bounds and polynomial-time construction for a clearly declared TM/NP-verifier model. Keep this as a long-term formal research track. Do not label the feature "general Cook–Levin compiler" until the complete theorem and compiler scope are validated.

A common tableau construction uses a space/time grid. The tape window must include every cell reachable within the time bound; an encoding must rule out illegal configurations and transitions. A local cell update can be represented with a fixed neighborhood under an appropriate combined tape-symbol/head/state encoding, but the exact neighborhood and transition clauses are part of the proof, not an undocumented assumption. A rough `T × T` picture alone is not a proof.

The total number of cells/constraints must be bounded polynomially in the verifier time/input length. Record formula size, gate count, clauses, and construction runtime independently.

## 3.2 Tseytin transformation: required gate encodings

Use a single documented variable convention. For a gate `z ↔ (a ∧ b)`, one valid CNF encoding is:

```text
(¬z ∨ a) ∧ (¬z ∨ b) ∧ (z ∨ ¬a ∨ ¬b)
```

For `z ↔ (a ∨ b)`:

```text
(z ∨ ¬a) ∧ (z ∨ ¬b) ∧ (¬z ∨ a ∨ b)
```

For `z ↔ ¬a`:

```text
(¬z ∨ ¬a) ∧ (z ∨ a)
```

Assert the output variable with a unit clause `(z_out)`. Use fresh auxiliary variables per gate unless an explicitly proven sharing optimization is enabled. Test every possible input assignment for each gate and every circuit up to a small exhaustive size. For all small circuits, compare source evaluation, AIG evaluation, and CNF satisfiability under existential auxiliary variables.

## 3.3 Mario / spatial gadget reductions

The Mario-style concept from the PDF is an educational visualization track, not a first-release correctness assumption.

Before calling a target game NP-hard, specify:

- the exact game variant and version;
- allowed player actions and whether the game is deterministic;
- gravity, collision, jump, movement, enemies, timers, power-ups, and reset semantics;
- level representation and size measure;
- variable, clause, wire, crossover, and boundary gadgets;
- how a satisfying assignment maps to a valid playthrough;
- how every valid playthrough maps back to a satisfying assignment;
- why the construction is polynomial in the input formula size;
- whether the target decision problem is reachability, completion, or another precisely defined predicate.

Do not assume a generic 2D graph drawing is a valid game-level embedding. A crossover gadget must preserve signals under the exact mechanics. If exact mechanics cannot be proved, keep the view labelled `EDUCATIONAL / NOT A PROVEN REDUCTION`.

## 3.4 SAT solver integration and proof formats

Start with stable adapters around existing solvers and CQ-HECS capabilities. Evaluate CaDiCaL and Kissat as upstream solvers; do not fork either initially.

- CaDiCaL is a high-performance C++ SAT solver with library/API support; inspect the pinned release, build instructions, proof output options, and licensing.
- Kissat is a compact C SAT solver with an upstream test/build procedure.
- The solver's ability to emit a proof is distinct from the format and the independent checker's ability to validate it.
- DRAT, FRAT, and LRAT are related but not interchangeable. FRAT can preserve additional proof information and can reduce elaboration cost to LRAT; validate the actual toolchain on a pinned revision.
- Do not claim a CaDiCaL run directly emits LRAT unless the selected build and flags demonstrate that exact behavior. A typical route may be solver proof output → converter/elaborator → LRAT proof → independent checker, but record the actual tools and hashes.
- Where supported and tested, use `drat-trim`, `lrat-check`, `cake_lpr`, or a checker already integrated in CQ-HECS. Preserve a second checker/oracle for critical claims where practical.
- For SAT, validate a full model against the original, unnormalized input. For UNSAT, validate the proof against the canonical formula and record the formula mapping.
- A `UNSAT` status without a checked proof may be displayed as `UNSAT (solver-reported; proof not checked)` only when the user has explicitly allowed an unverified mode. Default research-grade export requires proof verification or a clear `UNVERIFIED` label.

## 3.5 Neuro-symbolic and differentiable SAT

The PDF references graph-attention and differentiable SAT research. Keep this as a research adapter track.

Allowed uses:

- predict a branching heuristic or variable ordering;
- rank candidate phases or restarts;
- generate candidate initial assignments;
- analyze incidence-graph features;
- explore continuous relaxations;
- prioritize subproblems or benchmark families.

Not allowed:

- replace exact verification with a neural score;
- label a fractional local minimum as an exact satisfying assignment;
- infer polynomial-time solvability from empirical success;
- claim a differentiable solver is a complete exact SAT procedure unless its proof and worst-case contract support that statement.

A useful clause-penalty energy is:

```math
E(x) = \sum_{C \in F} \prod_{\ell \in C} u_\ell(x), \qquad x_i \in [0,1]
```

where `u_l(x)` is the degree to which literal `l` is false:

```text
u_(x_i)(x)       = 1 - x_i
u_(NOT x_i)(x)   = x_i
```

For Boolean assignments `x_i ∈ {0,1}`, each clause contributes 1 exactly when all literals in that clause are false, and 0 otherwise. Thus `E(x)=0` iff the Boolean assignment satisfies every clause. On fractional values, a zero or low energy is only a relaxation signal; the rounded assignment must be validated by the exact SAT checker. Record the rounding method, seeds, optimizer, step count, and exact solver result.

Use multiple seeds and repeated trials. Compare against random, greedy local search, known SAT heuristics, and the configured CDCL baseline. Report success probability, runtime distribution, and unsolved cases; do not present a single best run as a general result.

## 3.5.1 Current research directions to implement as separate adapters (2026 snapshot)

The SOTA literature suggests that the strongest practical architecture is not “LLM replaces SAT” or “GPU replaces CDCL”. It is a **hybrid portfolio** where learning proposes a search bias or candidate assignment and a mature symbolic solver remains responsible for exact decisions and proof production.

### A. One-shot GNN branching guidance (RLAF, ICLR 2026)

`Learning from Algorithm Feedback: One-Shot SAT Solver Guidance with GNNs` studies a GNN that predicts variable weights/polarities or an initial branching order in one forward pass, using the solver's computational cost as feedback. The ICLR page reports gains on diverse distributions, including over 2× in some settings, while a related March 2026 branching-order preprint explicitly reports that speedups did **not** transfer to some harder industrial instances because the solver's dynamic heuristics can overwrite the initialization.

Implementation experiment:

1. Export a canonical variable-clause graph plus stable variable IDs.
2. Predict an initial variable ranking / phase suggestion once per instance.
3. Pass the suggestion through the least invasive supported adapter hook (e.g. phase hints or initial order); do not patch a CDCL core before a baseline experiment.
4. Compare no guidance, random guidance, classical branching, and GNN guidance.
5. Report inference overhead separately from solver runtime.
6. Evaluate on random 3-CNF, structured synthetic families, and held-out industrial-like benchmarks.
7. Record where the solver overwrites the learned guidance and whether the gain survives.

### B. LLM-guided heuristic evolution (AESAT, IJCAI 2026)

The IJCAI 2026 Main Track paper `Bridging LLMs and SAT Solving: Automated Evolution of High-Performance Heuristics` describes AESAT, combining LLM-guided local heuristic refinement with evolutionary exploration. Its proceedings page reports that the AE-Kissat-MAB derivative won the 2025 International SAT Competition Main Track. This is a concrete, current research direction, but HCSWaver must reproduce exact solver versions, patches, benchmark splits, hardware, and competition records before repeating any performance claim.

Implementation experiment:

- Start with one isolated heuristic parameter/function behind a narrow adapter.
- Generate a small candidate population, not full arbitrary repository rewrites.
- Add mutation, selection, and controlled crossover only after deterministic evaluation works.
- Optimize the declared objective (e.g. PAR-2) with correctness as a hard constraint.
- Keep candidate generation cost and model tokens/time in the evidence report.
- Evaluate on a hidden holdout family; do not evolve prompts or code on that set.
- Publish full patch lineage and AI-generated-change disclosure when a competition or paper requires it.

### C. Hybrid differentiable GPU + classical CDCL (GaloisSAT, 2026 preprint)

`GaloisSAT: Differentiable Boolean Satisfiability Solving via Finite Field Algebra` proposes a differentiable SAT front-end using finite-field algebra on GPUs followed by a traditional CPU CDCL stage. The arXiv preprint reports PAR-2 improvements on the SAT Competition 2024 suite, including very different reported gains for SAT and UNSAT categories. Treat those numbers as the authors' results on their named suite, **not as a promise for other benchmarks or the Radeon 680M**.

Implementation experiment:

- Treat GaloisSAT-like logic as a separate optional backend, not as a replacement for CaDiCaL/Kissat/CQ-HECS.
- Verify the exact mathematical encoding and whether the front-end returns a candidate assignment, a restricted proof, or only a search hint.
- The CPU exact solver must verify any proposed assignment and complete the remaining search.
- For UNSAT, require a normal proof-producing exact path; a differentiable loss is not an UNSAT certificate.
- Measure GPU preprocessing + transfer + CPU solve + verification as one end-to-end time.
- Test CPU-only fallback and small batches. On integrated GPUs, transfer/setup costs may eliminate any benefit.

### D. Large-model code evolution (SATLUTION, 2025 preprint)

SATLUTION describes agent-driven evolution across full SAT solver repositories. Its scope and reported results are important references, but its source paper is an arXiv preprint and the reported computational costs and human-in-the-loop search policy must be evaluated. HCSWaver should begin with heuristic modules and only widen the mutation surface when regression coverage, sandboxing, and benchmark cost controls are mature.

### Research adapter order

Prioritize: (1) static baseline; (2) initial variable order / phase guidance; (3) learned instance classification; (4) limited LLM-guided parameter evolution; (5) optional GPU relaxation/front-end. The exact order may change after replication, but every adapter has a feature flag, capability schema, independent oracle, and rollback path.

## 3.6 GPU and Vulkan role

The initial brief assigns too much of exact CDCL solving to a GPU. Use Vulkan only where measurements show it is useful and the algorithm is appropriate.

**Good first GPU candidates:**

- graph layout and force-directed visualization;
- batched feature extraction on clause-variable graphs;
- batch candidate scoring / neural branching inference;
- continuous SAT relaxation experiments;
- independent large-batch simulations with predictable memory access;
- tensor-network experiments where the workload and contraction pattern genuinely map to GPU compute.

**Do not assume a GPU speedup for:**

- pointer-heavy, branch-heavy CDCL propagation;
- irregular learned-clause management;
- sequential conflict analysis;
- low-latency small formulas;
- proof checking with highly irregular memory access.

The CPU implementation remains the correctness reference. Vulkan builds need runtime device probing, descriptor/buffer validation, synchronization checks, timeout/cancellation, device-loss recovery, and a CPU fallback. Run Khronos validation layers in development; use synchronization validation when available. Benchmark end-to-end, not only kernel time. Record driver, device, compiler, shader hash, dispatch geometry, bytes transferred, memory use, wall time, and CPU baseline.

Do not advertise "Vulkan SAT solving" merely because the GPU computes a relaxation. Name the exact task performed on GPU.

## 3.7 Solver evolution / SATLUTION-inspired research

The PDF cites SATLUTION. The arXiv record `2509.07367` describes a repository-scale evolutionary workflow for SAT solver code and reports improvements on named competition benchmarks. Treat that as a research result to reproduce and scrutinize, not a transferable guarantee.

Build a constrained algorithm-evolution lab:

1. Freeze a known-good baseline source revision and binary hash.
2. Define an explicit mutation surface, initially configuration/heuristic parameters; later allow selected isolated source files.
3. Generate a candidate patch in a disposable worktree / sandbox.
4. Run formatting, compile, unit, differential, fuzz-smoke, and benchmark tests.
5. Reject any candidate with a correctness disagreement, missing model, invalid proof, crash, timeout-policy violation, data leak, or memory breach.
6. Benchmark on public development families and a separately held-out validation set. Never tune and report on the same test set as if it were unseen.
7. Use PAR-2 / solved count / proof-verified count / peak memory / crash rate. Preserve all failures.
8. Promote only through human-readable diff review and a reproducible run card.
9. Keep the baseline available; every candidate can be rolled back.

Never let the LLM directly edit the active production solver or auto-merge to `main`. The evolution engine works on an isolated copy and produces a candidate patch plus evidence bundle.

## 3.8 P vs. NP research guardrails

The workstation can support work on P vs. NP by exploring concrete algorithms, restricted cases, reductions, proof complexity, circuit lower bounds, and formal lemmas. It cannot bypass known barriers with a search heuristic.

For lower-bound research:

- define a specific family of formulas/circuits and a specific proof system/model;
- state the exact complexity measure and quantifiers;
- separate empirical proof-size data from theorem claims;
- test alternative encodings and proof systems;
- look for known barrier applicability (relativization, natural proofs, algebrization) where relevant;
- record counterexamples, failed lemmas, and assumptions;
- formalize each tractable lemma in Lean or cite a peer-reviewed theorem with exact hypotheses.

For algorithm research:

- define a deterministic algorithm and exact input encoding;
- prove correctness independently of runtime measurements;
- bound worst-case runtime in terms of input length;
- count bit complexity, not only high-level operation counts;
- include memory and numeric precision assumptions;
- test against worst-case families and counterexample generators.

Do not turn a finite fit such as `O(n^k)` vs. `O(2^(cn))` into an asymptotic classification. Plot fits only as exploratory descriptive statistics with confidence intervals and explicit model-selection caveats.

---

# 4. Architecture and technology boundaries

## 4.1 Layered architecture

Use four major layers with versioned contracts:

```text
┌──────────────────────────────────────────────────────────────────┐
│ HCSWaver Studio                                                   │
│ React + TypeScript + Three.js/WebGPU + Monaco/CodeMirror          │
│ Reduction Canvas · Wavefront · Solver Foundry · Arena · Proof Desk│
└───────────────────────────────┬──────────────────────────────────┘
                                │ typed local API / events
┌───────────────────────────────▼──────────────────────────────────┐
│ Rust Application Host                                             │
│ Tauri 2 · CLI · REST/WebSocket · MCP stdio · job supervisor       │
│ SQLite metadata · artifact store · permissions · audit events     │
└──────────────┬─────────────────────┬──────────────────────────────┘
               │ FFI / subprocess    │ versioned adapters
┌──────────────▼─────────────┐  ┌────▼─────────────────────────────┐
│ Native Compute Layer        │  │ Existing HCS ecosystem             │
│ C++20 reduction / AIG / CNF │  │ CQ-HECS SAT/circuit engines         │
│ CPU reference / optional    │  │ HCS Foundry local model runtime    │
│ Vulkan compute adapters     │  │ Lean 4 / mathlib toolchain          │
└─────────────────────────────┘  └───────────────────────────────────┘
```

Keep the core independent of Tauri, Qt, React, and HSCL1. The CLI, API, MCP server, and desktop UI must call the same typed application services.

## 4.2 Technology defaults (confirm by repository audit)

- **Native compute:** C++20, CMake, Ninja, CTest; standard library first. Use explicit C ABI/FFI boundaries. Avoid exposing C++ exceptions across FFI.
- **Application host:** Rust stable, Cargo workspace, Tauri 2 for desktop shell, Tokio only where async jobs require it, `serde` schemas, `tracing` structured logs, typed error enums.
- **UI:** React + TypeScript, project-native package manager/lockfile, Three.js for graph/geometry, WebGPU where supported, Canvas/WebGL/CPU fallback. Use Monaco or CodeMirror for code/Lean editing after bundle-size and accessibility review.
- **Database:** SQLite for local metadata, run index, events, and settings. Keep large formula/proof/log/model artifacts in a content-addressed filesystem store, not database BLOBs.
- **Formal proofs:** Lean 4 with pinned `lean-toolchain`; use mathlib only where it provides real value. Never permit `sorry` in any theorem labelled verified.
- **Solver adapters:** CQ-HECS first; external CaDiCaL/Kissat adapters next; native experimental solver only where it contributes distinct research value.
- **Model adapter:** HCS Foundry first; local OpenAI-compatible server support as a separate adapter only after capability discovery. LLM calls are optional and never part of exact correctness.
- **Packaging:** Windows installer/bundle and Debian `.deb` for HSCL1; do not make Docker mandatory for end users.

Do not pin a dependency to `latest`. Pin tested versions or commits and update through a deliberate compatibility PR.

## 4.3 Suggested repository layout

Adapt to a verified current tree; do not create empty placeholders solely to match this diagram.

```text
hcswaver/
├── AGENTS.md
├── README.md
├── README.de.md
├── README.fr.md
├── LICENSE
├── NOTICE
├── CONTRIBUTING.md
├── CODE_OF_CONDUCT.md
├── SECURITY.md
├── CHANGELOG.md
├── VERSION
├── .editorconfig
├── .gitignore
├── .gitattributes
├── CMakePresets.json
├── CMakeLists.txt
├── Cargo.toml
├── Cargo.lock
├── package.json
├── pnpm-lock.yaml                 # or existing lockfile; one package manager only
├── rust-toolchain.toml
├── lean-toolchain
├── .github/
│   ├── workflows/ci.yml
│   ├── workflows/nightly-research.yml
│   ├── workflows/release.yml
│   ├── ISSUE_TEMPLATE/
│   └── PULL_REQUEST_TEMPLATE.md
├── core/
│   ├── include/hcswaver/
│   │   ├── formula.hpp
│   │   ├── circuit.hpp
│   │   ├── reduction.hpp
│   │   ├── result.hpp
│   │   └── engine_api.h
│   ├── src/
│   │   ├── dimacs/
│   │   ├── circuit/
│   │   ├── reduction/
│   │   ├── tseytin/
│   │   ├── tableau/
│   │   ├── graph/
│   │   ├── arena/
│   │   └── vulkan/
│   ├── shaders/
│   └── tests/
├── app/
│   ├── src-tauri/
│   │   ├── src/main.rs
│   │   ├── src/api/
│   │   ├── src/jobs/
│   │   ├── src/mcp/
│   │   ├── src/storage/
│   │   ├── src/adapters/
│   │   └── capabilities/
│   └── ui/
│       ├── src/features/reduction/
│       ├── src/features/wavefront/
│       ├── src/features/solver/
│       ├── src/features/arena/
│       ├── src/features/proof/
│       ├── src/features/research/
│       ├── src/features/data/
│       └── src/i18n/
├── cli/
│   └── hcswaver/
├── formal/
│   ├── HCSWaver.lean
│   ├── HCSWaver/Logic.lean
│   ├── HCSWaver/Tseytin.lean
│   ├── HCSWaver/Reductions.lean
│   └── README.md
├── schemas/
│   ├── hcswaver.run.v1.schema.json
│   ├── formula.v1.schema.json
│   ├── reduction.v1.schema.json
│   └── benchmark.v1.schema.json
├── integration/
│   ├── cq-hecs/
│   ├── hcs-foundry/
│   └── hscl1/
├── db/migrations/
├── datasets/manifests/
├── benchmarks/manifest/
├── tests/
│   ├── fixtures/
│   ├── property/
│   ├── differential/
│   ├── integration/
│   ├── e2e/
│   └── visual/
├── research/
│   ├── v1/LITERATURE_MAP.md
│   ├── v1/HYPOTHESES.md
│   ├── v1/EXPERIMENTS.md
│   ├── v1/EVIDENCE_LEDGER.md
│   ├── v1/BLOCKERS.md
│   └── v1/FINAL_REPORT.md
├── docs/
│   ├── ARCHITECTURE.md
│   ├── API.md
│   ├── MCP.md
│   ├── CLI.md
│   ├── BUILDING.md
│   ├── TESTING.md
│   ├── SECURITY.md
│   ├── DATA_AND_PROVENANCE.md
│   ├── BENCHMARKS.md
│   ├── FORMAL_PROOFS.md
│   ├── LIMITATIONS.md
│   ├── ROADMAP.md
│   ├── ADR/
│   └── integrations/HSCL1.md
└── packaging/
    ├── windows/
    └── debian/
```

## 4.4 Core service boundaries

Define versioned interfaces before implementing multiple clients:

- `FormulaService`: parse, validate, normalize, hash, inspect, export.
- `CircuitService`: create/edit gates, topological order, evaluate, export AIG/JSON.
- `ReductionService`: compile supported source IR to circuit/CNF and return mapping/proof obligations.
- `SolverService`: list capabilities, solve, cancel, inspect telemetry, validate model, verify proof.
- `BenchmarkService`: create family, import manifest, run batch, aggregate PAR-2 and summary statistics.
- `ArenaService`: generate instances, mutate candidate, minimize counterexample, preserve seed/reproducer.
- `FormalService`: create/check Lean project, build file, capture diagnostics, attach proof artifact.
- `ModelService`: query Foundry capabilities, list models, request model generation through approved adapter, cancel, record model/revision/config.
- `ResearchService`: hypothesis, citations, experiment design, evidence entry, report export.
- `ArtifactService`: content-addressed storage, checksums, safe download/import, artifact retention.
- `JobService`: run state, resource budget, cancellation, retry policy, audit log.

All service methods must return typed results and explicit status; no untyped text-only success responses.

## 4.5 Typed result contract

Use a versioned result structure similar to:

```json
{
  "schema": "hcswaver.run.v1",
  "run_id": "uuid",
  "input": {
    "original_sha256": "...",
    "canonical_sha256": "...",
    "format": "dimacs-cnf",
    "normalization": "cnf-normalize.v1"
  },
  "engine": {
    "id": "cq-hecs.omniwave",
    "version": "pinned-version",
    "source_revision": "git-sha",
    "device": "cpu"
  },
  "status": "SAT|UNSAT|UNKNOWN|TIMEOUT|RESOURCE_LIMIT|ERROR",
  "model_artifact": null,
  "proof_artifact": null,
  "proof_status": "NOT_APPLICABLE|NOT_EMITTED|UNVERIFIED|VERIFIED|FAILED",
  "limits": {
    "wall_time_ms": 10000,
    "memory_limit_bytes": 1073741824,
    "max_workers": 1
  },
  "seed": 42,
  "metrics": {},
  "created_at": "RFC3339"
}
```

This is an illustrative contract, not a final schema. Finalize in `schemas/` with JSON Schema, versioning, compatibility tests, and cross-language fixtures. Never assume that `UNKNOWN` means unsatisfiable or that an engine result is proof-carrying by default.

Preserve the spirit of CQ-HECS `hcs.run.v2` provenance. Map rather than fork provenance conventions where practical. Store both original and canonical digests; never overwrite the original input with normalized content.

---

# 5. Mathematical and code reference implementations

The following are starting examples for tests and implementation. They are not a substitute for full formal specifications.

## 5.1 DIMACS CNF mini-example

Input:

```text
c tiny SAT example
p cnf 3 2
1 -2 0
2 3 -1 0
```

This represents:

```math
(x_1 \lor \neg x_2) \land (x_2 \lor x_3 \lor \neg x_1)
```

A satisfying assignment is `x1=true, x2=true, x3=false`. The result must be re-evaluated against the original clauses by an independent verifier.

A trivial UNSAT fixture:

```text
p cnf 1 2
1 0
-1 0
```

The only variable must be true and false simultaneously. Use this fixture for parser, solver, and proof-checker smoke tests.

Parser acceptance rules:

- ignore blank/comment lines beginning with `c`;
- require exactly one valid `p cnf <vars> <clauses>` header;
- parse signed non-zero literals and clause terminator `0`;
- reject literal magnitudes greater than declared variable count;
- validate exact declared clause count;
- accept duplicate literals and tautological clauses at the parser layer (normalization may remove them, but must preserve original hash and normalization report);
- reject malformed tokens, unterminated clauses, integer overflow, and unexpected trailing data;
- stream large inputs with explicit byte/variable/clause limits.

## 5.2 C++20 data model sketch

Use an explicit type for literal and clauses; do not store arbitrary signed integers without checked bounds.

```cpp
#pragma once
#include <cstdint>
#include <vector>
#include <stdexcept>

namespace hcswaver {

struct Literal {
    std::uint32_t variable; // one-based variable index; 0 is invalid
    bool negated;
};

using Clause = std::vector<Literal>;

struct CnfFormula {
    std::uint32_t variable_count{};
    std::vector<Clause> clauses;
};

inline void validate(const CnfFormula& f) {
    for (const auto& clause : f.clauses) {
        for (const auto& lit : clause) {
            if (lit.variable == 0 || lit.variable > f.variable_count) {
                throw std::invalid_argument("literal variable out of range");
            }
        }
    }
}

} // namespace hcswaver
```

Production parser APIs should return structured errors with line/column/byte offset and avoid exceptions as normal control flow. The sketch exists to show invariants, not to dictate a final ABI.

## 5.3 Python reference for gate-to-CNF equivalence tests

A small, slow reference is useful as an oracle. It should be independent of the optimized C++ implementation.

```python
from itertools import product


def and_gate_cnf(a: int, b: int, z: int) -> list[tuple[int, ...]]:
    # z <-> (a AND b)
    return [(-z, a), (-z, b), (z, -a, -b)]


def or_gate_cnf(a: int, b: int, z: int) -> list[tuple[int, ...]]:
    # z <-> (a OR b)
    return [(z, -a), (z, -b), (-z, a, b)]


def not_gate_cnf(a: int, z: int) -> list[tuple[int, ...]]:
    # z <-> NOT a
    return [(-z, -a), (z, a)]


def literal_value(lit: int, assignment: dict[int, bool]) -> bool:
    value = assignment[abs(lit)]
    return not value if lit < 0 else value


def cnf_value(cnf, assignment) -> bool:
    return all(any(literal_value(l, assignment) for l in clause) for clause in cnf)


def test_and_gate_truth_table():
    a, b, z = 1, 2, 3
    cnf = and_gate_cnf(a, b, z)
    for av, bv, zv in product([False, True], repeat=3):
        assignment = {a: av, b: bv, z: zv}
        assert cnf_value(cnf, assignment) == (zv == (av and bv))


def test_or_gate_truth_table():
    a, b, z = 1, 2, 3
    cnf = or_gate_cnf(a, b, z)
    for av, bv, zv in product([False, True], repeat=3):
        assignment = {a: av, b: bv, z: zv}
        assert cnf_value(cnf, assignment) == (zv == (av or bv))


def test_not_gate_truth_table():
    a, z = 1, 2
    cnf = not_gate_cnf(a, z)
    for av, zv in product([False, True], repeat=2):
        assignment = {a: av, z: zv}
        assert cnf_value(cnf, assignment) == (zv == (not av))
```

Build a further circuit-level test that exhaustively enumerates primary inputs and existentially searches auxiliary variables for all circuits up to a declared tiny size. This tests the exact mapping between circuit output and CNF satisfiability.

## 5.4 Lean 4 starter definitions

Use Lean as the proof checker, not as a place to hide unverified automation. Pin the Lean toolchain and mathlib revision.

```lean
inductive Lit where
  | pos : Nat → Lit
  | neg : Nat → Lit
  deriving DecidableEq, Repr

def evalLit (ρ : Nat → Bool) : Lit → Bool
  | .pos v => ρ v
  | .neg v => !(ρ v)

def evalClause (ρ : Nat → Bool) (c : List Lit) : Bool :=
  c.any (evalLit ρ)

theorem positive_literal_true
    (ρ : Nat → Bool) (v : Nat) (h : ρ v = true) :
    evalLit ρ (.pos v) = true := by
  simp [evalLit, h]

theorem negative_literal_false_when_variable_true
    (ρ : Nat → Bool) (v : Nat) (h : ρ v = true) :
    evalLit ρ (.neg v) = false := by
  simp [evalLit, h]
```

The initial Lean file should compile with a pinned Lean toolchain without `sorry`, `admit`, `axiom` (except explicitly documented foundational axioms), `unsafe`, or untrusted external plugins in theorem code. Add tests that scan formal sources for forbidden placeholders. A theorem is not complete merely because it appears in an editor; it must pass the pinned `lake build` in CI.

Later, formalize:

- literal/clause/CNF semantics;
- model verification correctness;
- normalization preserving satisfiability;
- each Tseytin gate equivalence;
- circuit-to-CNF equisatisfiability;
- correctness of bounded IR compilation;
- the chosen bounded TM transition encoding;
- size bounds for the declared construction;
- reduction composition.

Do not label the full Cook–Levin theorem formalized until all the formal obligations in its declared scope compile and are reviewed.

## 5.5 Differential and property tests

Use independent implementations:

- Python reference evaluator vs C++ evaluator.
- C++ DIMACS parser vs a second parser or a canonical reference.
- HCSWaver CNF output vs CQ-HECS parser/normalizer.
- HCSWaver solver adapter vs CaDiCaL/Kissat where installed.
- Model verifier vs direct clause evaluation.
- Proof checker A vs independent proof checker B where possible.
- Lean theorem statements vs executable truth-table tests for small finite domains.

Property tests must generate reproducible seeds, preserve minimized counterexamples, and print a command that replays each failure.

---

# 6. Data model, database, and artifact storage

## 6.1 Storage architecture

Use SQLite for metadata and relationships; use a content-addressed filesystem store for large immutable artifacts.

Suggested paths:

```text
%LOCALAPPDATA%/HCSWaver/          # Windows default
~/.local/share/hcswaver/          # Linux default
  hcswaver.sqlite3
  artifacts/sha256/ab/cd/<digest>
  datasets/<dataset-id>/
  models/                         # references or links to Foundry-managed model roots; no duplicate copies
  workspaces/<workspace-id>/
  jobs/<job-id>/logs/
  cache/
  backups/
```

Support `--data-dir` and an environment override for tests. Do not assume paths or case sensitivity. Use platform APIs / known directories, not string concatenation with untrusted values.

Do not store model weights in SQLite. Do not store large proof files inline in JSON. Save artifact bytes atomically, hash them, and then commit the metadata row. If metadata commit fails, garbage-collect only unreferenced temp objects after a safe retention interval.

## 6.2 Core SQLite tables

Implement migration files with forward-only numbered migrations. Example starting schema (adapt and normalize before production):

```sql
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS workspaces (
  id TEXT PRIMARY KEY,
  name TEXT NOT NULL,
  root_path TEXT NOT NULL,
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS artifacts (
  sha256 TEXT PRIMARY KEY CHECK(length(sha256) = 64),
  kind TEXT NOT NULL,
  size_bytes INTEGER NOT NULL CHECK(size_bytes >= 0),
  media_type TEXT,
  relative_path TEXT NOT NULL UNIQUE,
  created_at TEXT NOT NULL,
  source_url TEXT,
  license_spdx TEXT,
  source_revision TEXT
);

CREATE TABLE IF NOT EXISTS formulas (
  id TEXT PRIMARY KEY,
  workspace_id TEXT NOT NULL REFERENCES workspaces(id),
  original_sha256 TEXT NOT NULL REFERENCES artifacts(sha256),
  canonical_sha256 TEXT NOT NULL,
  format TEXT NOT NULL,
  variable_count INTEGER NOT NULL CHECK(variable_count >= 0),
  clause_count INTEGER NOT NULL CHECK(clause_count >= 0),
  normalization_version TEXT NOT NULL,
  created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS reductions (
  id TEXT PRIMARY KEY,
  workspace_id TEXT NOT NULL REFERENCES workspaces(id),
  source_artifact_sha256 TEXT REFERENCES artifacts(sha256),
  output_formula_id TEXT REFERENCES formulas(id),
  compiler_id TEXT NOT NULL,
  compiler_version TEXT NOT NULL,
  mapping_artifact_sha256 TEXT REFERENCES artifacts(sha256),
  proof_obligation_status TEXT NOT NULL,
  created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS solver_runs (
  id TEXT PRIMARY KEY,
  formula_id TEXT NOT NULL REFERENCES formulas(id),
  engine_id TEXT NOT NULL,
  engine_version TEXT NOT NULL,
  source_revision TEXT,
  status TEXT NOT NULL CHECK(status IN ('SAT','UNSAT','UNKNOWN','TIMEOUT','RESOURCE_LIMIT','ERROR')),
  proof_status TEXT NOT NULL,
  model_sha256 TEXT REFERENCES artifacts(sha256),
  proof_sha256 TEXT REFERENCES artifacts(sha256),
  seed INTEGER,
  wall_time_ms INTEGER,
  peak_memory_bytes INTEGER,
  device_json TEXT NOT NULL,
  config_json TEXT NOT NULL,
  created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS proof_checks (
  id TEXT PRIMARY KEY,
  solver_run_id TEXT NOT NULL REFERENCES solver_runs(id),
  checker_id TEXT NOT NULL,
  checker_version TEXT NOT NULL,
  result TEXT NOT NULL CHECK(result IN ('PASS','FAIL','UNSUPPORTED','ERROR')),
  checked_formula_sha256 TEXT NOT NULL,
  proof_sha256 TEXT NOT NULL,
  log_sha256 TEXT REFERENCES artifacts(sha256),
  created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS benchmark_families (
  id TEXT PRIMARY KEY,
  name TEXT NOT NULL,
  source_url TEXT,
  license_spdx TEXT,
  description TEXT NOT NULL,
  generator_version TEXT,
  manifest_sha256 TEXT REFERENCES artifacts(sha256),
  created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS benchmark_instances (
  id TEXT PRIMARY KEY,
  family_id TEXT NOT NULL REFERENCES benchmark_families(id),
  formula_id TEXT REFERENCES formulas(id),
  source_instance_id TEXT,
  split TEXT NOT NULL CHECK(split IN ('train','validation','test','holdout','regression')),
  seed INTEGER,
  description TEXT,
  created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS benchmark_jobs (
  id TEXT PRIMARY KEY,
  name TEXT NOT NULL,
  config_json TEXT NOT NULL,
  baseline_run_id TEXT,
  status TEXT NOT NULL,
  created_at TEXT NOT NULL,
  finished_at TEXT
);

CREATE TABLE IF NOT EXISTS benchmark_job_items (
  job_id TEXT NOT NULL REFERENCES benchmark_jobs(id),
  instance_id TEXT NOT NULL REFERENCES benchmark_instances(id),
  solver_run_id TEXT REFERENCES solver_runs(id),
  PRIMARY KEY(job_id, instance_id)
);

CREATE TABLE IF NOT EXISTS hypotheses (
  id TEXT PRIMARY KEY,
  title TEXT NOT NULL,
  statement TEXT NOT NULL,
  scope TEXT NOT NULL,
  status TEXT NOT NULL,
  assumptions_json TEXT NOT NULL,
  falsification_condition TEXT NOT NULL,
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS experiments (
  id TEXT PRIMARY KEY,
  hypothesis_id TEXT REFERENCES hypotheses(id),
  protocol_artifact_sha256 TEXT REFERENCES artifacts(sha256),
  status TEXT NOT NULL,
  seed INTEGER,
  environment_json TEXT NOT NULL,
  created_at TEXT NOT NULL,
  finished_at TEXT
);

CREATE TABLE IF NOT EXISTS experiment_runs (
  experiment_id TEXT NOT NULL REFERENCES experiments(id),
  solver_run_id TEXT NOT NULL REFERENCES solver_runs(id),
  role TEXT NOT NULL,
  PRIMARY KEY(experiment_id, solver_run_id)
);

CREATE TABLE IF NOT EXISTS model_invocations (
  id TEXT PRIMARY KEY,
  provider_id TEXT NOT NULL,
  model_id TEXT NOT NULL,
  model_revision TEXT,
  prompt_sha256 TEXT NOT NULL,
  output_sha256 TEXT REFERENCES artifacts(sha256),
  config_json TEXT NOT NULL,
  consent_scope TEXT NOT NULL,
  created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS agent_jobs (
  id TEXT PRIMARY KEY,
  agent_profile TEXT NOT NULL,
  task_json TEXT NOT NULL,
  state TEXT NOT NULL,
  sandbox_root TEXT NOT NULL,
  budget_json TEXT NOT NULL,
  created_at TEXT NOT NULL,
  finished_at TEXT
);

CREATE TABLE IF NOT EXISTS events (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  timestamp TEXT NOT NULL,
  actor TEXT NOT NULL,
  job_id TEXT,
  event_type TEXT NOT NULL,
  severity TEXT NOT NULL,
  payload_json TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_solver_runs_formula ON solver_runs(formula_id, created_at);
CREATE INDEX IF NOT EXISTS idx_solver_runs_status ON solver_runs(status);
CREATE INDEX IF NOT EXISTS idx_benchmark_instances_family ON benchmark_instances(family_id, split);
CREATE INDEX IF NOT EXISTS idx_events_job ON events(job_id, timestamp);
```

Before shipping, review table normalization, indexes, constraints, WAL configuration, migration rollback/recovery, and privacy retention. Add an FTS5 virtual table only if full-text notebook/reference search justifies it. SQLite FTS5 is an optional capability and must be detected at runtime/build.

## 6.3 Database reliability requirements

- Enable foreign keys on every connection.
- Use parameterized queries only; no SQL string concatenation from user/LLM data.
- Use transactions for multi-row updates and job state changes.
- Consider WAL for concurrent readers/writers; define checkpoint and backup policy.
- Use SQLite backup API or a consistent snapshot method; never copy an active WAL database blindly.
- Run migrations on a copy in integration tests; keep backups before irreversible migrations.
- Use a schema version table; refuse unsafe downgrades.
- Encrypt sensitive user data only if there is a defined key-management design; do not invent home-grown encryption.
- Never persist API tokens, raw credentials, SSH keys, or model-provider secrets in the research database.
- Store prompt content only if the user enabled the relevant research logging scope. Default to storing prompt hash and necessary metadata, not full prompt text.
- Provide export/delete controls for user projects and artifacts, subject to referential integrity and immutable evidence logs.

## 6.4 Dataset and benchmark manifest

Each imported dataset/benchmark must have a manifest with:

```yaml
schema: hcswaver.dataset.v1
id: satcomp-2026-example-family
name: Example family
source:
  url: https://...
  retrieved_at: 2026-11-07T00:00:00Z
  revision: <tag-or-commit-or-release>
license:
  spdx: <verified-id-or-NOASSERTION>
  notes: <redistribution and citation notes>
files:
  - path: instance-001.cnf
    sha256: <64-hex>
    size_bytes: 12345
    format: dimacs-cnf
    split: validation
families:
  - random-3sat
  - pigeonhole
provenance:
  generator: <name/version/commit or null>
  seed: 12345
  transformations: []
```

Do not infer the license from a website being publicly downloadable. If the license is unknown, mark `NOASSERTION` and avoid redistributing the data until clarified. Keep source citation and exact file hashes.

---

# 7. Local AI, HCS Foundry, models, and MCP

## 7.1 The model is a research assistant, not an oracle

LLMs may:

- explain formulas and proof diagnostics;
- propose candidate reductions or branching heuristics;
- suggest test cases and counterexamples;
- draft C++/Rust/Python/Lean code in a sandbox;
- summarize literature with source references;
- classify benchmark families;
- propose experiment protocols;
- convert natural-language tasks into typed workflows.

LLMs must not:

- set SAT/UNSAT status;
- validate a satisfying assignment;
- validate an LRAT/DRAT proof;
- decide a theorem is proven;
- silently update the research evidence ledger;
- execute arbitrary shell commands or unrestricted source code;
- modify a benchmark holdout set or its manifest;
- promote their own code or model candidate.

Every model output that affects an experiment is stored with provider, model ID, revision, quantization/runtime where known, prompt/output hashes, settings, tool calls, and consent scope. The deterministic verifier decides correctness.

## 7.2 HCS Foundry adapter

Reuse `hcs-foundry` rather than rebuilding model lifecycle management.

First implementation tasks:

1. Inspect the Foundry current README, API docs, CLI, MCP schemas, and tests from the checked-out revision.
2. Verify `machine_scan`, `machine_budget`, `models_list`, and `vram_status` using the live service.
3. Verify whether an OpenAI-compatible text-generation endpoint exists in the current code. Do not infer from product copy alone.
4. If it exists, use the exact discovered endpoint and typed request/response schema. Test streaming, cancellation, errors, model-not-loaded, OOM, and server shutdown.
5. If it does not exist, implement a narrowly scoped adapter in HCS Foundry or a new adapter process; do not add a generic `shell` / `exec` MCP tool.
6. Use MCP stdio for typed Foundry operations; do not treat MCP as a general-purpose job shell.
7. Negotiate protocol version and capabilities; keep compatibility with the actual Foundry protocol currently shipped.
8. Keep HCSWaver runnable without Foundry. Model features display `MODEL_BACKEND_UNAVAILABLE` but all deterministic functionality continues to work.

MCP HCSWaver tools should be finite and typed. Initial proposed tools:

- `hcswaver.machine_capabilities` — read-only, delegates to Foundry/HSCL1 capability probes.
- `hcswaver.formula_import` — imports a formula into an approved workspace path.
- `hcswaver.formula_inspect` — parse/normalize/statistics without solving.
- `hcswaver.compile_reduction` — compile only a declared supported source IR/version.
- `hcswaver.solve_instance` — launch a solver with explicit timeout/memory/workers.
- `hcswaver.verify_model` — deterministic model validation.
- `hcswaver.verify_proof` — invoke an allowlisted proof checker.
- `hcswaver.benchmark_run` — execute a named manifest/configuration with resource budget.
- `hcswaver.benchmark_report` — return aggregate machine-readable results.
- `hcswaver.generate_counterexample` — constrained instance generation and minimization.
- `hcswaver.lean_check` — build a specified Lean project/file in a sandbox.
- `hcswaver.research_log` — append a structured evidence event, requiring a source or explicit `model_generated` provenance.

Do not initially expose file deletion, arbitrary process creation, shell, unrestricted network, package installation, OS modification, or `git push` through MCP. Add write tools only with explicit workspace roots, schema validation, and approval boundaries.

## 7.3 OpenAI-compatible local API adapter

Where a runtime genuinely provides an OpenAI-compatible API, support a configuration such as:

```toml
[models]
provider = "hcs-foundry"
base_url = "http://127.0.0.1:<discovered-port>/v1"
model = "<model-id-from-foundry>"
timeout_seconds = 90
max_output_tokens = 2048
allow_remote = false
```

Do not hardcode an undocumented Foundry port. Discover it from the service configuration/health response or use Foundry's own typed SDK/client. Validate `base_url` as loopback unless the user explicitly authorizes remote use. Never accept a URL from an LLM without user approval.

## 7.4 Model selection and current hardware fit

For the known development target, assume only as an initial profile: Windows 11 x64, Ryzen 7 7735HS, Radeon 680M RDNA2 iGPU with Vulkan capability to be detected, approximately 24 GB system RAM in the current profile, and a separately reserved UMA allocation (the OS may report shared and dedicated values differently). Re-scan the actual machine; do not bake these values into code.

Initial model strategy:

- A tiny model such as `ggml-org/Qwen3.5-0.8B-GGUF` can serve as a smoke-test model for the Foundry adapter and tool-call plumbing, not as the production research orchestrator.
- A 4B-class Q4 GGUF may be a practical experiment if its exact model card, architecture support, tool template, context, hash, quantization, and measured memory fit are verified. A community-uploaded GGUF is not automatically official or trustworthy; compare with the publisher's source revision and file hashes.
- Do not target Qwen3-Coder-Next 80B GGUF for the local mini-PC. The current model card reports about 48.4 GB for Q4_K_M weights alone, before KV cache and runtime overhead. It may be an optional remote/workstation model, never a requirement for the product.
- Larger models are optional adapters, not dependencies. The core should work without a model.
- Model recommendation must be driven by Foundry's runtime fit measurement and HCSWaver's task evaluation, not leaderboard rank alone.

Candidate model links for agents to re-evaluate at execution time:

- `llama.cpp` example small GGUF model: https://huggingface.co/ggml-org/Qwen3.5-0.8B-GGUF
- Qwen GGUF 4B model listing (verify uploader, exact model card, revision, and license before recommending): https://huggingface.co/gguf/Qwen3.5-4B-GGUF
- Qwen3-Coder-Next official model card / GGUF link: https://huggingface.co/Qwen/Qwen3-Coder-Next-GGUF — not a local 24 GB workstation target; use only on suitable hardware or an explicitly approved remote endpoint.
- Qwen3-Coder family repository and model documentation: https://github.com/QwenLM/Qwen3-Coder
- llama.cpp inference server and backend support: https://github.com/ggml-org/llama.cpp
- Hugging Face model download documentation: https://huggingface.co/docs/hub/models-downloading

Do not bundle any model in the installer or ISO. Provide a user-triggered model chooser that shows license, provider, revision, quantization, file size, hardware fit, and whether the selected backend has been tested.

## 7.5 Model safety and prompt/data security

- Treat model output, imported repositories, and benchmark files as untrusted.
- The prompt may contain formulas, source code, or local filenames; never send it remotely by default.
- Use an explicit consent dialog for any remote provider; show exactly what data is sent.
- Use a system prompt with strict tool schemas, but never rely on prompting as a security boundary.
- Validate tool names, arguments, paths, timeouts, memory, and output sizes in code.
- Prevent model-driven prompt injection from data comments, READMEs, solver output, web snippets, and issue text from escalating privileges.
- Keep secrets outside prompts and logs.
- Record local model revision and inference backend settings when practical; do not claim a model's identity based on its display name alone.

---

# 8. User interface and interaction design

## 8.1 Product feel

Retain the PDF's cybernetic dark mode direction but use a restrained and accessible design system:

- Background: deep graphite / obsidian.
- Primary highlight: cyan for selected/active/valid states.
- Conflict/error: crimson, never used as the only signal.
- Warning/experimental: amber.
- Text: high-contrast neutral scale.
- Optional light theme with equal functionality.
- Dockable or resizable multi-panel layout with saved layouts.
- Global command palette (`Ctrl+K`) with accessible keyboard navigation.
- Reduced motion, keyboard-only use, visible focus, semantic labels, and scalable font sizes.
- EN/DE/FR localization from the beginning; no hardcoded UI strings in components.

Avoid excessive neon, animated backgrounds behind data, misleading green success states, and huge empty hero panels.

## 8.2 Five-room UX specification

### Room 1 — Reduction Canvas

- Left: source IR / machine definition / formula tree.
- Center: node graph or tableau grid.
- Right: compiler passes, gate properties, variable map, proof obligations.
- Bottom: diagnostics, CNF preview, formula digest, export.
- Actions: parse, validate, compile, undo/redo, compare stages, save version, run exhaustive small-instance check.
- Every generated node must have source mapping and stable ID. Selection highlights corresponding clauses and proof obligations.

### Room 2 — Wavefront Observatory

- Show clause-variable incidence graph or selected subgraph.
- Stream real solver events only when engine adapter exposes them; never synthesize telemetry to keep the graph moving.
- Provide pause/resume/cancel, event sampling, filter and focus neighborhood.
- Include non-3D table/log fallback for accessibility and low-GPU devices.
- Distinguish solver telemetry from post-hoc visualization.
- Preserve input hash and event timestamps.

### Room 3 — Solver Foundry

- Choose solver, version, capabilities, timeout, memory cap, workers, seed, CPU/GPU mode, proof output, and benchmark suite.
- Show capability matrix per engine and clear refusal reasons.
- Separate exact, heuristic, relaxation, and experimental paths.
- Show baseline vs candidate results with confidence intervals, repetitions, PAR-2, solved count, resource metrics, and failed instances.
- Never show a single number without the hardware/config/benchmark context.

### Room 4 — Adversarial Arena

- Generate candidates from a named family and seed.
- Define the target property: wrong model, runtime blow-up on measured budget, heuristic failure, invalid proof, violated invariant, or parser disagreement.
- Minimize failing examples with a deterministic reducer while preserving the property.
- Save seed, generator version, raw instance, minimized instance, target build, command line, and replay instructions.
- Label a search that found no counterexample as “none found within budget”; never as proof that no counterexample exists.

### Room 5 — Formal Proof Desk

- Show Lean file, project dependencies, toolchain, goals, diagnostics, and build status.
- Display theorem assumptions and dependency graph.
- Run Lean in an unprivileged sandbox with bounded time/memory/disk.
- Record `lean-toolchain`, `lake-manifest.json`, mathlib commit, compiler version, file hash, and build log.
- Do not mark a theorem formally verified if `sorry`, `admit`, unreviewed custom axioms, or non-kernel proof shortcuts are involved.

## 8.3 UX acceptance gates

- Every control has real behavior, disabled/loading/success/failure states, and an accessible name.
- No fake charts, mock API responses, placeholder buttons, or invented solver events in release mode.
- Keyboard-only paths through all five rooms.
- Reduced-motion setting disables nonessential motion.
- Visual checks at 1366×768, 1920×1080, and 390px responsive width where the desktop shell supports it.
- EN/DE/FR long strings do not clip.
- High-DPI and fractional scaling tested.
- UI stays responsive during long jobs; jobs run outside the UI thread.
- All heavy work supports cancellation and shows the resource budget.
- Empty states show a useful action; errors show a recovery path and diagnostic ID.

---

# 9. API, MCP, CLI, and application security

## 9.1 Local API

- Bind only to `127.0.0.1` / `::1` by default. If using a Unix domain socket or Windows named pipe, prefer it where supported.
- Avoid fixed port collisions; allow configured port or ephemeral port and publish the actual endpoint only to local app clients.
- Require a per-session random token for local HTTP APIs if a browser/webview boundary exists. Do not put persistent secrets in query strings.
- Use CORS allowlists, strict Content Security Policy, origin checks, bounded request sizes, and schema validation.
- Use WebSocket event streams only for job progress and explicitly typed events.
- Every endpoint has authentication, authorization, timeout, max body, and cancellation behavior documented.
- API is not an internet-facing service. Remote access is a future opt-in feature with its own threat model and auth, not a bind-address switch.

## 9.2 CLI

Provide a CLI that uses the same services as the UI. Proposed commands:

```text
hcswaver doctor
hcswaver status --json
hcswaver formula import FILE.cnf
hcswaver formula inspect ID --json
hcswaver formula normalize ID --output FILE.cnf
hcswaver circuit new
hcswaver reduction compile --input FILE --target 3sat
hcswaver solve ID --engine cq-hecs --timeout 30s --memory 2GiB
hcswaver verify model ID
hcswaver verify proof RUN_ID
hcswaver bench run MANIFEST.yaml --config CONFIG.toml
hcswaver arena generate FAMILY --seed 123 --output-dir PATH
hcswaver lean check PROJECT
hcswaver mcp serve
hcswaver ui
```

Use `--json` for automation, stable exit codes, helpful stderr diagnostics, and no success output when the action did not happen.

## 9.3 Exit codes (initial proposal)

- `0` success.
- `1` general runtime / IO failure.
- `2` invalid arguments or invalid input.
- `3` verification failed (model/proof/certificate).
- `4` unsupported capability / typed refusal.
- `5` timeout or resource budget reached.
- `6` dependency/backend unavailable.
- `7` cancellation.

The exact code map must be documented and tested; never overload an exit code to conceal UNKNOWN.

## 9.4 MCP policy

- MCP stdio output must contain only JSON-RPC protocol messages; logs go to stderr.
- Tool schemas must be strict and bounded.
- Use finite tool names and typed argument contracts. Do not expose generic shell/exec.
- Read-only tools should be separate from mutation tools.
- Mutations create new artifacts or append versioned records; destructive overwrite/delete is excluded from initial MCP scope.
- All tools enforce configured workspace roots and file size limits.
- Tool errors are structured; a failed tool does not crash the MCP host.
- Negotiate MCP version/capabilities with clients; do not hardcode a future version unsupported by Foundry/clients.
- Provide an example config for Foundry/OpenCode/Claude-compatible clients only after testing the actual command and schema.

## 9.5 Process sandbox

Candidate code and untrusted benchmark generators run:

- as a dedicated unprivileged child process;
- in a temporary directory under the selected workspace or sandbox root;
- with read-only source/fixture mounts and separate output directory;
- with no credentials, SSH agent, browser profile, model cache, or host secrets mounted;
- with network disabled by default;
- with CPU time, wall time, memory, process count, disk, and output-size caps;
- with an allowlist of executables and environment variables;
- with process-tree cancellation and cleanup.

On Linux, evaluate bubblewrap / systemd-run restrictions / seccomp depending on availability. On Windows, use a low-privilege process and available Job Object / AppContainer mechanisms where practical. Docker/Podman may be an optional test sandbox but must not be a required runtime dependency for HSCL1 users.

---

# 10. Build and test architecture

## 10.1 Build profiles

Support these build profiles:

- `dev` — fast local build, assertions, sanitizers when supported, verbose logs.
- `test` — deterministic dependencies and test instrumentation.
- `release` — optimized, stripped as appropriate, reproducible metadata, no debug endpoints.
- `cpu-only` — no Vulkan dependency required; primary fallback and CI baseline.
- `vulkan` — optional compute backend with validation tooling.

CMake should expose capability options such as `HCSWAVER_ENABLE_VULKAN=ON|OFF`, not silently auto-assume Vulkan. Build configuration writes a machine-readable capability manifest.

## 10.2 CI matrix

Minimum CI matrix:

| Target | Build/test |
|---|---|
| Ubuntu 26.04 x86_64 | CMake CPU core, Rust app/CLI, UI build, unit/integration tests |
| Windows 11 x64 | MSVC or clang-cl CPU core, Rust app/CLI, UI build, unit tests |
| Linux Vulkan job | compile shaders and run available headless tests; real GPU test is separately labelled |
| Lean | pinned toolchain `lake build`, placeholder scan, theorem smoke suite |
| Web | TypeScript typecheck, lint, unit tests, bundle build, e2e smoke |
| Packaging | `.deb` build, package metadata/lint, install/uninstall test in disposable Ubuntu VM |

Pin GitHub Actions by commit SHA per existing HSCL1 supply-chain policy. Use minimal permissions. Do not download model weights in standard CI.

## 10.3 Native core tests

- parser positive and negative fixtures;
- boundary integers / overflow;
- duplicate literals, tautologies, empty clauses, empty formula;
- SAT model evaluator;
- CNF normalization preservation;
- AIG topology and topological sort;
- all Tseytin gate truth tables;
- source IR to circuit equivalence for tiny inputs;
- deterministic serialization and digest stability;
- FFI safety: null, invalid length, malformed UTF-8 where relevant, buffer size, ownership, repeated init/shutdown;
- fuzz targets for DIMACS, JSON schema, reduction IR, and FFI.

Use ASan/UBSan on supported compilers; add TSan only for relevant concurrent components. Never pass raw C++ exceptions over C ABI.

## 10.4 Solver integration tests

- known SAT model fixtures;
- known UNSAT fixtures with expected certificate path;
- solver timeout -> UNKNOWN/TIMEOUT, never UNSAT;
- memory cap -> RESOURCE_LIMIT;
- cancellation -> CANCELLED / documented status;
- solver crash -> ERROR and diagnostic bundle;
- independent model verification;
- proof check success and deliberate proof corruption failure;
- formula hash mismatch refusal;
- deterministic seed replay where engine supports it;
- absent optional backend -> explicit unavailable, not silent skip or fallback unless a declared portfolio policy says so.

## 10.5 Lean tests

- `lean-toolchain` pinned.
- `lake update` and cache retrieval pinned to a committed manifest.
- `lake build` on CI.
- scan for `sorry`, `admit`, placeholder axioms, `unsafe`, and unreviewed theorem escapes.
- ensure all theorem files are included by the Lake project.
- build from a clean checkout.
- verify recorded theorem source hash equals the checked file.

A formal proof test must fail when the proof is intentionally broken; add a negative CI fixture or a script-level mutation test.

## 10.6 UI / E2E tests

- launch app and check each route/room;
- parse/import a formula and inspect the displayed variable/clause counts;
- run the tiny SAT and UNSAT fixtures;
- verify a SAT model and display proof status for UNSAT;
- compile one small circuit via Tseytin and compare against exhaustive evaluation;
- submit/cancel a job and verify UI state;
- simulate absent Foundry, absent Vulkan, absent Lean and show actionable states;
- verify database persistence after restart;
- open a stored run card and confirm hashes/config/status;
- check keyboard navigation, focus return, reduced motion, contrast, EN/DE/FR;
- visual snapshots should be deterministic and avoid time-sensitive metrics.

## 10.7 Benchmark rules

- Use named benchmark families with published provenance and license.
- Freeze the baseline solver and hardware profile before comparisons.
- Use multiple repetitions where runtime noise matters.
- Record warmup policy, timeout, memory, thread count, CPU governor/power mode if known, OS, compiler, flags, and solver versions.
- Report PAR-2 for competition-style comparisons; also report solved count, median, quartiles, timeouts, proof verification, memory, and crashes.
- Do not mix train/validation/test/holdout families.
- Do not tune candidate algorithms on holdout data.
- Keep raw JSON/CSV and manifests. Store a summary chart only as a derivative.
- Compare on the same machine and conditions. Do not compare a laptop run to a workstation run without clearly separating them.
- If a benchmark suite changes, bump its manifest version and preserve old data.

---

# 11. Self-healing loops and agent orchestration

## 11.1 General repair loop

For each failed gate:

1. Preserve the first failing log, command, machine profile, commit SHA, and minimal reproducer.
2. Classify the layer: specification, dependency, compiler, code, data, integration, resource, GPU driver, UX, package, or infrastructure.
3. Reduce to the smallest reproducer without changing the expected result.
4. Add a regression test before or with the fix.
5. Form one root-cause hypothesis and state what observation would falsify it.
6. Implement the smallest reversible fix.
7. Run the focused test.
8. Run adjacent subsystem tests.
9. Run the relevant full gate.
10. Inspect the diff for regressions, security, licensing, and generated files.
11. Update docs / evidence only after results exist.
12. Commit a coherent checkpoint on the feature branch.

Allow at most three materially different repair hypotheses for the same root cause. After three failures, mark `BLOCKED`, preserve artifacts, and continue independent tasks. The agent must not keep retrying the same command, repeatedly increase timeouts, or mask the failure.

## 11.2 Build loops

**Loop B0 — environment discovery**

- inspect OS/compiler/Rust/Node/Python/CMake/Ninja/Vulkan/Lean/available RAM/free disk;
- write `artifacts/environment.json` (local only or sanitized CI artifact);
- calculate build concurrency and memory budget;
- choose CPU-only if Vulkan or driver support is uncertain.

**Loop B1 — native core**

- configure CMake → compile → CTest → sanitizers/fuzz smoke → ABI test;
- on fail: reproduce → patch → focused test → CTest → build again;
- preserve compile cache only when build graph is trustworthy.

**Loop B2 — Rust app/CLI**

- `cargo fmt --all -- --check`;
- `cargo clippy --all-targets -- -D warnings`;
- `cargo test --workspace`;
- API/MCP schema tests;
- dependency audit and license scan.

**Loop B3 — UI**

- install from lockfile only → typecheck → lint → unit tests → production build → e2e smoke;
- inspect bundle-size budget and accessible controls.

**Loop B4 — formal proof**

- `lake build` → placeholder/axiom scan → negative mutation check → clean-checkout build.

**Loop B5 — system integration**

- build `.deb` → inspect control/dependency fields → install in disposable VM → launch → test CLI/MCP → uninstall/upgrade path.

**Loop B6 — ISO**

- do not run full remaster for every UI change;
- use HSCL1 Workshop loop / VM incremental update for short iteration where available;
- perform full ISO remaster at milestone cuts;
- boot exact artifact in QEMU; install to disposable virtual disk; run smoke tests;
- hash and archive the exact tested artifact.

## 11.3 Research loop

1. State the hypothesis with explicit scope and assumptions.
2. Cite the prior work and record exact source/revision/date.
3. Define a falsification condition before running experiments.
4. Choose a baseline and independent oracle.
5. Generate or import test data with pinned seed/revision.
6. Run candidates under fixed resource budgets.
7. Validate outputs (models/proofs/theorems) independently.
8. Analyze failures, negative results, variance, and possible confounders.
9. Repeat with a held-out family or independent checker.
10. Update the evidence ledger with raw artifact hashes and limitations.
11. Promote status only when its evidence threshold is reached.

Never let an LLM write the final evidence ledger without a deterministic provenance check and human-readable review. The LLM can draft an entry; the integration agent verifies its source and run IDs.

## 11.4 Evolution loop

```text
baseline source + config + benchmark manifest
    ↓
LLM / search proposes a candidate patch or parameter set
    ↓
patch parser + scope allowlist + static checks
    ↓
sandbox build (network off, bounded resources)
    ↓
unit + differential + model/proof validation
    ↓
public development benchmarks
    ↓
held-out validation family
    ↓
PAR-2 / solved-count / correctness / memory report
    ↓
reviewable candidate artifact + diff
    ↓
human approval before upstream integration
```

Candidate patches that fail correctness are archived as failures with a minimized reproducer, not deleted. A benchmark improvement with a proof regression is a rejection. A code patch that wins only on one benchmark family is family-specific, not a general improvement.

## 11.5 GPU repair loop

- first reproduce on CPU reference;
- enable Vulkan validation layer;
- capture device/driver/shader/build metadata;
- run the smallest shader fixture;
- use synchronization validation and bounds assertions;
- inspect descriptor sets, memory barriers, queue ownership, and buffer lifetimes;
- reproduce on a second backend/device if available;
- fallback to CPU when device lost or unsupported;
- never mark the CPU reference broken merely to make GPU output match.

## 11.6 Database repair loop

- copy database snapshot;
- run `PRAGMA integrity_check` and foreign key checks;
- identify the failing migration/query;
- create a fixture reproducing the issue;
- test migration on both clean and previous-version databases;
- preserve a backup and verify restoration;
- never run automatic destructive schema repair on the user's original DB.

## 11.7 Release loop

- clean checkout on a new worktree;
- pin toolchains and dependencies;
- run all release gates;
- build signed/unsigned artifact status honestly;
- create SBOM, licenses, checksums, source archive, release notes;
- install package in disposable VM and run exact release smoke;
- produce run cards and logs;
- push feature branch;
- wait for remote CI result (no blind merge); repair remote failures via bounded loop;
- create PR with test matrix and limitations;
- merge only after all required checks and repository branch rules pass;
- tag release only after the merged commit is verified;
- never mutate an existing release tag.

---

# 12. Parallel planning and milestone roadmap

Parallelize low-coupling tasks while keeping the dependency graph explicit. Do not create parallel branches that change the same schema or API without an assigned integrator.

## Phase 0 — audit, research, and design freeze

**Goal:** establish what already exists, agree contracts, and avoid duplicate systems.

- [ ] Clone/audit HSCL1, CQ-HECS, HCS Foundry; verify branches, tags, licenses, build commands, package layouts, API/MCP contracts, tests, and current evidence.
- [ ] Create standalone HCSWaver repo if absent and authorized; otherwise produce local scaffold and blocker report.
- [ ] Read the user PDF as the product brief and map every feature to `PROPOSED`, `EXPERIMENTAL`, or existing verified capability.
- [ ] Re-check SOTA source links and all cited claims.
- [ ] Write ADRs for UI stack, native core, solver reuse, API/MCP, database, licenses, GPU role, package strategy.
- [ ] Create contract schemas and tiny fixtures before parallel implementation.
- [ ] Create `research/v1/LITERATURE_MAP.md`, `HYPOTHESES.md`, `EVIDENCE_LEDGER.md`, `BLOCKERS.md`, and `TEST_MATRIX.md`.

**Gate P0:** no code duplication plan, repository owners and package boundaries clear, every major claim has source or is explicitly marked as a hypothesis.

## Phase 1 — MVP vertical slice (first demonstrable application)

**Goal:** a user can import a tiny CNF, inspect it, solve it via CQ-HECS adapter or an available baseline solver, validate a model, record a run card, and view it in the UI.

- [ ] app shell + five-room navigation with working first room and solver flow;
- [ ] DIMACS parser / canonicalizer / original+canonical digest;
- [ ] CQ-HECS adapter or typed subprocess interface;
- [ ] model verification;
- [ ] SQLite migrations + content-addressed artifact store;
- [ ] typed CLI + local API + read-only MCP tools;
- [ ] CPU-only baseline works without Vulkan, Foundry, or Lean;
- [ ] Windows and Linux clean builds;
- [ ] first HSCL1 `.deb` integration skeleton.

**Gate P1:** tiny SAT and UNSAT cases work end to end; SAT model is independently checked; UNSAT is only marked verified if an actual proof checker passes; run is persisted with hashes and replay command.

## Phase 2 — Reduction Canvas and Tseytin correctness

- [ ] versioned AIG / circuit format;
- [ ] AND/OR/NOT gate semantics and topological validation;
- [ ] Tseytin encoder with variable mapping;
- [ ] exhaustive truth-table tests for gates and tiny circuits;
- [ ] export DIMACS and run external parser/solver oracle;
- [ ] compiler pass visualization and source mapping;
- [ ] formal Lean gate equivalence lemmas.

**Gate P2:** no reduction result promoted without exhaustive small-case equivalence tests and a recorded encoding version. Lean lemmas compile.

## Phase 3 — Solver Foundry and benchmark database

- [ ] solver capability model and adapter interface;
- [ ] CQ-HECS integration for currently supported engines;
- [ ] optional CaDiCaL and Kissat adapters with pinned versions;
- [ ] proof artifact pipeline and checker adapters;
- [ ] benchmark manifest importer;
- [ ] PAR-2 and repeated-trial statistics;
- [ ] experiment comparison UI;
- [ ] baseline benchmark suite and held-out test split.

**Gate P3:** every run records machine, build, solver, input, seed, limits, output, proof status, and source revision. Incorrect model and corrupted proof tests must fail.

## Phase 4 — Wavefront Observatory and Vulkan research path

- [ ] graph model based on real CNF incidence structure;
- [ ] telemetry adapter and event stream;
- [ ] CPU graph layout reference;
- [ ] optional Three.js/WebGPU visualization;
- [ ] optional Vulkan compute for layout/feature batches/relaxation;
- [ ] CPU fallback and Vulkan validation tests;
- [ ] performance comparisons on real supported hardware.

**Gate P4:** graph values and solver events match raw records; no fabricated activity; GPU claims only after end-to-end benchmark on named hardware.

## Phase 5 — Adversarial Arena and safe algorithm evolution

- [ ] instance families with seedable generators;
- [ ] deterministic counterexample shrinking;
- [ ] solver differential fuzzing;
- [ ] controlled heuristic parameter evolution;
- [ ] sandboxed code candidate path;
- [ ] held-out validation;
- [ ] rollback and promotion review;
- [ ] immutable failure archive.

**Gate P5:** candidate code cannot access secrets, user files, network or production branch. No candidate is promoted without correctness and held-out evidence.

## Phase 6 — Formal Proof Desk and bounded Cook–Levin work

- [ ] Lean project / LSP / build integration;
- [ ] formula and model semantics;
- [ ] Tseytin formalization;
- [ ] bounded circuit compiler spec;
- [ ] finite TM model and tableau encoding;
- [ ] formal equivalence lemmas for each transition constraint;
- [ ] polynomial size bound for the declared compiler model;
- [ ] proof viewer and diagnostics.

**Gate P6:** all labelled formal claims pass the pinned Lean kernel. Full Cook–Levin label remains blocked until all declared theorem scopes are completed.

## Phase 7 — HCS Foundry agent integration and HCS research loops

- [ ] capability-discovery adapter;
- [ ] local model list and resource budget display;
- [ ] supported text generation adapter;
- [ ] strict MCP tools and JSON schemas;
- [ ] agent planning / proposal / test / critique workflow;
- [ ] model safety, prompt injection, sandbox and cancellation tests;
- [ ] no-network default and explicit remote consent;
- [ ] long-running research job resume and handoff.

**Gate P7:** a small local model can propose a heuristic or test, but all results are checked by deterministic code. Foundry unavailable does not break the rest of HCSWaver.

## Phase 8 — HSCL1 integration and ISO verification

- [ ] package `hcswaver-core` (if separate package is needed) and `hcswaver-studio` / `hscl-hcswaver` following existing package conventions;
- [ ] add app launcher and icon;
- [ ] add CLI discovery and `hscl hcswaver` status/launch/doctor commands;
- [ ] add Control Center entry using existing Qt/QML patterns without embedding the full app into the Control Center;
- [ ] set conservative resource defaults and no model auto-download;
- [ ] add optional Lean/Vulkan/benchmark assets as first-run downloads;
- [ ] update HSCL1 AGENTS, long-horizon plan, architecture, package manifest, CLI docs, handbook EN/DE/FR, claims, and build log;
- [ ] build package and install in disposable Ubuntu/Kubuntu VM;
- [ ] build ISO at milestone cut and verify it boots;
- [ ] test installed app, CLI, local API, MCP and uninstall/upgrade path.

**Gate P8:** package is installable in the target HSCL1 environment, can run CPU-only, does not introduce network listeners by default, and does not break existing OS checks. ISO feature status is VM-verified only after exact image tests.

## Phase 9 — v1.0.0 release candidate

- [ ] security review and threat model;
- [ ] license and notices audit;
- [ ] dependency/SBOM scan;
- [ ] performance and memory review;
- [ ] complete visual and accessibility QA;
- [ ] Windows/Linux packaging and install/uninstall test;
- [ ] clean checkout build;
- [ ] PR / review / CI / merge;
- [ ] release tag, checksums, SBOM, source archive, notes;
- [ ] public limitations and research evidence report.

**Gate P9:** all v1 claims have code/test evidence; known blockers are visible; no high-severity unmitigated security issue in HCSWaver-owned code.

---

# 13. HSCL1 operating-system integration specification

## 13.1 Integration philosophy

HCSWaver is an application, not a new desktop shell or privileged OS subsystem. Keep the OS stable and the scientific application modular.

- HSCL1 should launch HCSWaver as a normal unprivileged desktop application.
- The desktop app, CLI, API, MCP and compute workers must never run as root.
- No privileged service is required for ordinary use.
- No daemon starts automatically at boot unless a later ADR demonstrates a need.
- Do not auto-download models, Lean toolchains, solver data, or benchmark corpora as part of ISO boot.
- The app must have a CPU-only profile and function if Foundry/Vulkan is absent.
- The integration must preserve existing `hscl doctor`, security checks, and default network exposure.

## 13.2 Package design

Inspect existing `.deb` packages before finalizing package names and dependencies. Candidate package split:

- `hcswaver-core` — native shared libraries / CLI backend if needed.
- `hcswaver-studio` — desktop UI, app icon, `.desktop` launcher, translations.
- `hscl-hcswaver` — optional thin HSCL1 integration plugin/CLI commands.

A single `hcswaver` `.deb` is acceptable if the codebase and dependency graph make splitting unnecessary. Do not create package boundaries just for aesthetics.

Package requirements:

- correct `Architecture: amd64` unless multiarch is actually supported;
- dependency versions compatible with Ubuntu 26.04 `resolute`;
- no uncontrolled curl-pipe-shell postinst;
- no root post-install model download;
- no unexpected systemd service enablement;
- files in FHS-compliant paths;
- desktop launcher with correct icon/name/categories;
- app data under the user data directory;
- desktop settings do not require root;
- package lint + clean install + upgrade + remove tests;
- preserve user data on package upgrade/removal by default and document how to remove it separately.

The ISO package manifest may include HCSWaver Studio if the measured size and desktop baseline allow it. If not, include the launcher/integration package and offer one-click install from the approved HCS source. Do not ship large models or benchmark sets.

## 13.3 HSCL1 CLI integration

Use the current Rust `hscl` command architecture and conventions. Candidate commands:

```text
hscl hcswaver status --json
hscl hcswaver launch
hscl hcswaver doctor
hscl hcswaver backend list
hscl hcswaver mcp-config --client <supported-client>
```

Commands must do actual discovery/actions, use fixed executables and typed arguments, and never shell-evaluate strings supplied by the UI/model. `status` and `doctor` remain read-only. `launch` executes the installed app as the current user. `mcp-config` writes only a new config file after preview and explicit approval; never overwrite existing client configuration silently.

## 13.4 Control Center integration

Add an HCSWaver card/page using the existing Control Center UI conventions:

- installed/not installed;
- version and build revision;
- CPU / Vulkan capability status;
- Foundry connected/unavailable;
- Lean toolchain detected/not installed;
- disk space / artifact store path;
- launch / open data folder / doctor actions.

Do not duplicate the entire HCSWaver Studio UI inside the Control Center. Control Center is a launcher and integration surface, not a second front end.

## 13.5 Live ISO and security

- HCSWaver must not auto-start in the Live session.
- Do not run research jobs in the Live session by default; ephemeral storage and RAM limits make this inappropriate.
- If launched in Live mode, show an explicit warning that saved artifacts may be lost at shutdown.
- Keep local HTTP listeners disabled until user launches a workflow that needs them; bind loopback only.
- Add no privileged helper unless a specific OS function requires it, and if so define one narrow Polkit action with finite typed operations.
- AppArmor profile is optional for first release but must be evaluated and documented. Never claim confinement without a tested profile.

## 13.6 OS acceptance tests

- package install in clean disposable VM;
- launcher starts correct binary;
- `hscl hcswaver status --json` reports real package and runtime state;
- CPU-only tiny SAT path works;
- Foundry absent state is graceful;
- Vulkan absent state is graceful;
- no unexpected listening TCP socket when app is closed;
- no privileged daemon starts;
- desktop stays responsive under solver load;
- package upgrade preserves workspace and settings;
- package removal does not delete user research data;
- exact HSCL1 ISO boots and app launches in the image if bundled.

---

# 14. Performance, resource governance, and hardware compatibility

## 14.1 Resource governor

Every job must declare:

- max wall time;
- CPU worker cap;
- memory cap;
- temporary disk cap;
- GPU memory/buffer budget if used;
- network policy;
- artifact output cap;
- cancellation behavior.

The governor should query HSCL1 / Foundry hardware services where available and use conservative local detection otherwise. Reserve RAM for OS, desktop, browser/webview, database, and the user. Prevent simultaneous large jobs from exceeding the configured budget. Do not kill unrelated user processes.

## 14.2 Initial profiles

- **Constrained / CPU-only:** one solver worker, low concurrency, small graph rendering, no model required, no Vulkan required.
- **Integrated GPU:** CPU reference still enabled; GPU only after tested capability; limit VRAM and use small batches.
- **Discrete GPU:** allow higher visual/relaxation batch sizes after hardware benchmark; exact solver remains independent.
- **Workstation:** parallel portfolio solving and larger graph datasets when disk/RAM/driver allow.

Profiles must be measured and overrideable within safety thresholds. Do not infer dedicated VRAM by adding UMA/shared memory as if it were dedicated capacity. HSCL1 currently reports AMD dedicated VRAM and GTT separately; preserve that distinction.

## 14.3 Performance metrics

Record:

- parse / normalize / compile time;
- formula variables, clauses, literals, max clause width;
- gate count, depth, source IR size;
- propagation count/rate where available;
- decisions, conflicts, restarts, learned clause count/bytes where adapter exposes them;
- wall time, CPU time, peak RSS, GPU memory, disk IO;
- proof bytes and checker time;
- model load time / TTFT / generation speed if AI was used;
- UI frame-time only for the visualization task being benchmarked.

Do not conflate variables per second, clauses per second, propagation rate, solver wall time, proof verification time, or LLM tokens/sec.

---

# 15. Documentation, open-source community, and research records

## 15.1 Required public documents

- English canonical README plus German and French translations.
- Product overview and truthful feature matrix.
- Architecture and decision records.
- Build and development guide for Windows/Linux.
- CLI/API/MCP docs and example configs.
- Data import, license, and provenance docs.
- Solver adapters and proof formats.
- Lean formal proof workflow.
- Benchmark design and reproducibility protocol.
- Security/threat model and responsible vulnerability reporting.
- HSCL1 integration guide.
- Limitations and non-goals.
- Contribution guide with small tasks, test requirements, code style, and review expectations.
- Release notes with exact verified status.

## 15.2 Research ledger

Every research item must record:

- question/hypothesis;
- exact statement and scope;
- assumptions and definitions;
- related work and sources;
- source publication date and accessed date;
- candidate method;
- falsification criteria;
- benchmark/instance family;
- seed and environment;
- raw artifact hashes;
- positive and negative results;
- uncertainty and confounders;
- status and reviewer notes;
- next experiment.

An LLM-generated citation must be checked against the source page/paper before it is added. Do not cite search-result snippets as if they were papers. Where the source is arXiv/preprint, label it as a preprint and do not claim peer review unless verified.

## 15.3 Contribution model

- Keep issues scoped and reproducible.
- Add `good first issue`, `research`, `solver-adapter`, `formal-proof`, `visualization`, `benchmark`, `documentation`, `security` labels.
- Require CI green for merge.
- Require a research description for benchmark/algorithm changes.
- Preserve third-party attribution.
- Accept negative results and benchmark families, not just speedups.
- Do not reward unsupported P vs NP claims or unverifiable benchmark screenshots.
- Publish the exact proportion/description of AI-assisted changes when preparing competition submissions or research publications that require this disclosure.

---

# 16. State-of-the-art references and implementation links

These links are a starting research map as checked on 2026-11-07. Re-check every URL, release, version, API, and claim before implementation or release. A link is not proof that a dependency is installed, compatible, licensed for redistribution, or performant on the user's hardware.

## 16.1 SAT / proof logging / competitions

- CaDiCaL SAT solver: https://github.com/arminbiere/cadical
- Kissat SAT solver: https://github.com/arminbiere/kissat
- SAT Competition 2026 benchmark format and benchmark process: https://satcompetition.github.io/2026/benchmarks.html
- SAT Competition 2026 rules, UNSAT proof requirements, and solver description disclosures: https://satcompetition.github.io/2026/rules.html
- FRAT paper/toolchain (DRAT/FRAT/LRAT and proof elaboration): https://pmc.ncbi.nlm.nih.gov/articles/PMC7979213/
- SATLUTION preprint (repository-scale autonomous SAT solver evolution; reproduce independently): https://arxiv.org/abs/2509.07367
- AESAT, IJCAI 2026 Main Track: https://ijcai.org/proceedings/2026/257
- RLAF / one-shot GNN guidance, ICLR 2026: https://proceedings.iclr.cc/paper_files/paper/2026/hash/a04c50c0bd6937760a3b89ee10010c96-Abstract-Conference.html
- Learned initial branching order (March 2026 preprint; includes limits on hard industrial instances): https://arxiv.org/abs/2603.07176
- GaloisSAT hybrid differentiable GPU/CPU SAT (March 2026 preprint): https://arxiv.org/abs/2603.28796
- DIMACS Implementation Challenges (benchmarking and algorithm implementation context): https://dimacs.rutgers.edu/programs/implementation-challenges/

Implementation rules: pin solver source commits, build flags, checker version, benchmark revision, machine, and all mutations. Do not copy benchmark files without checking their licenses.

## 16.2 Lean 4 / formal mathematics

- Lean official documentation: https://lean-lang.org/
- Lean official releases: https://lean-lang.org/doc/reference/latest/releases/
- Lean 4 GitHub: https://github.com/leanprover/lean4
- Mathlib 4: https://github.com/leanprover-community/mathlib4
- Lake build tool in Lean repo: https://github.com/leanprover/lean4/tree/master/src/lake
- Lean package registry: https://reservoir.lean-lang.org/

Research note: retrieved sources surfaced Lean 4.34.0 release notes and a Reservoir page listing a 4.35.0 stable toolchain at the time of lookup. Resolve the current stable release and use a pinned toolchain in the project; do not install an unpinned nightly in release CI. Use `lake-manifest.json` to pin dependency revisions.

## 16.3 MCP / desktop / native compute

- MCP specification updates: https://modelcontextprotocol.io/specification/
- MCP 2026-07-28 release notes: https://blog.modelcontextprotocol.io/posts/2026-07-28/
- Tauri security capabilities: https://tauri.app/security/capabilities/
- Tauri v2 documentation: https://v2.tauri.app/
- CMake documentation: https://cmake.org/cmake/help/latest/
- CMake presets: https://cmake.org/cmake/help/latest/manual/cmake-presets.7.html
- Khronos Vulkan tutorial: https://docs.vulkan.org/tutorial/latest/index.html
- Vulkan synchronization guide: https://docs.vulkan.org/guide/latest/synchronization.html
- Vulkan validation layers: https://github.com/KhronosGroup/Vulkan-ValidationLayers
- Three.js documentation: https://threejs.org/docs/
- WebGPU specification: https://www.w3.org/TR/webgpu/

## 16.4 Database / storage

- SQLite documentation: https://www.sqlite.org/docs.html
- SQLite FTS5: https://www.sqlite.org/fts5.html
- SQLite WAL: https://www.sqlite.org/wal.html
- SQLx SQLite (if selected): https://docs.rs/sqlx/latest/sqlx/sqlite/
- rusqlite (alternative if synchronous access is simpler): https://github.com/rusqlite/rusqlite

Choose one Rust database layer. Do not add SQLx and rusqlite without an explicit architecture decision.

## 16.5 Local models / model distribution

- llama.cpp: https://github.com/ggml-org/llama.cpp
- llama.cpp releases: https://github.com/ggml-org/llama.cpp/releases
- Qwen3-Coder project: https://github.com/QwenLM/Qwen3-Coder
- Qwen3.5 0.8B GGUF candidate: https://huggingface.co/ggml-org/Qwen3.5-0.8B-GGUF
- Qwen3.5 4B GGUF listing (verify uploader/manifest/license): https://huggingface.co/gguf/Qwen3.5-4B-GGUF
- Qwen3-Coder-Next GGUF (80B; not recommended for the known mini-PC): https://huggingface.co/Qwen/Qwen3-Coder-Next-GGUF
- Hugging Face Hub download guide: https://huggingface.co/docs/hub/models-downloading

## 16.6 Existing HCS repositories

- HSCL1 OS: https://github.com/timfromhcs/HSCL1
- HSCL1 current long-horizon plan: https://github.com/timfromhcs/HSCL1/blob/main/docs/superpowers/plans/2026-11-06-long-horizon-to-v2.md
- HCS Foundry: https://github.com/timfromhcs/hcs-foundry
- HCS Foundry MCP docs: https://github.com/timfromhcs/hcs-foundry/blob/main/docs/MCP.md
- CQ-HECS: https://github.com/timfromhcs/CQ-HECS
- CQ-HECS AGENTS: https://github.com/timfromhcs/CQ-HECS/blob/main/AGENTS.md

---

# 17. Required research questions and experiments

The agent must maintain a prioritized research backlog. Do not prematurely implement every idea from the PDF.

## Priority A — correctness and immediate utility

1. Can the existing CQ-HECS solver and provenance APIs provide the initial SAT workflow without duplication?
2. What are the exact adapter capabilities and failure semantics for each solver?
3. Can the C++ reduction core emit CNF whose satisfiability is equivalent to every small source circuit under exhaustive checking?
4. Can SAT models be independently validated and UNSAT proof artifacts checked in a reproducible pipeline?
5. Can SQLite and content-addressed storage safely preserve experiments and large proof artifacts across app restarts and upgrades?
6. Can HCSWaver run without a local model backend and still provide a complete deterministic research workflow?

## Priority B — performance and new capabilities

1. Which telemetry fields can each solver actually expose without invasive hooks?
2. Which graph features correlate with branching difficulty on held-out families?
3. Does Vulkan improve graph layout, batch feature scoring, or relaxation on the actual Radeon/other GPUs?
4. Can the Arena find and shrink useful heuristic counterexamples within a declared budget?
5. Which candidate branch/restart/phase policies improve PAR-2 on held-out families without degrading proof reliability?
6. Is a local model's candidate generation rate high enough to justify the compute cost vs. deterministic search?

## Priority C — formal complexity research

1. Which finite machine/verifier model is the first tractable Lean formalization target?
2. Which existing Coq/Isabelle Cook–Levin developments can be cited or ported, subject to licenses and formalization differences?
3. Can the compiler correctness and polynomial-size bound be separated into manageable lemmas?
4. Which explicit graph/formula families are suitable for proof-complexity experiments?
5. Which results are empirical only, and which admit formal statements with precise hypotheses?
6. Which known barriers apply to the specific line of attack, and at what point must the research strategy change?

Every experiment needs baseline, independent oracle, repeatability, a falsification criterion, and raw data. Negative results count as results.

---

# 18. Definition of done and release checklist

## 18.1 Standalone product definition of done

- [ ] Clean clone builds on Windows 11 x64 and Ubuntu 26.04 x64.
- [ ] CPU-only path works without Vulkan, Foundry, Lean, or internet access.
- [ ] DIMACS parser validates positive and negative fixtures, limits, edge cases, and fuzz corpus.
- [ ] Model checker independently validates every SAT witness.
- [ ] UNSAT proof verification is real, pinned, and recorded; unverified results are labelled.
- [ ] Circuit/AIG/Tseytin pipeline passes exhaustive small-instance tests and has stable source mappings.
- [ ] Solver adapters have capability discovery and typed failure states.
- [ ] SQLite database survives clean restart, upgrade migration, backup, and restore tests.
- [ ] All five rooms have working, accessible core functionality; no placeholder controls remain in release UI.
- [ ] Lean Desk builds pinned proof projects; no formal claim contains `sorry`/unreviewed axioms.
- [ ] AI backend is optional, local by default, sandboxed, and cannot decide formal correctness.
- [ ] MCP has strict typed tools, no shell/exec, path boundaries, cancellation, and tests.
- [ ] Benchmark suite includes public sources, provenance, held-out split, raw results, and PAR-2.
- [ ] Security review, dependency licenses, notices, SBOM, checksums, and artifact hashes are complete.
- [ ] README/CLI/API/MCP/architecture/limitations/release notes match the actual code and evidence.

## 18.2 HSCL1 integration definition of done

- [ ] HCSWaver package builds through the existing HSCL1 package pipeline.
- [ ] App launcher, icon, and `hscl hcswaver` commands work in a clean VM.
- [ ] No root service or background listener is enabled by default.
- [ ] CPU-only smoke test passes inside the installed VM.
- [ ] Foundry/Vulkan/Lean absence is handled honestly.
- [ ] HCSWaver documentation is integrated into HSCL1 docs and handbook EN/DE/FR.
- [ ] HSCL1 master AGENTS and current long-horizon plan contain a non-destructive HCSWaver milestone.
- [ ] `docs/CLAIMS.md` identifies the exact tests and image SHA.
- [ ] The exact ISO has booted in QEMU after package inclusion; only then label ISO integration `VM-VERIFIED`.
- [ ] No existing HSCL1 critical-path tests or security gates were weakened.

## 18.3 Release package

Every standalone release must include:

- executable/package artifacts for supported platforms;
- source archive / exact source tag;
- checksums and signed provenance where signing is configured;
- SPDX SBOM;
- third-party notices and license report;
- version, source commit, toolchain metadata;
- test matrix and benchmark scope;
- known limitations and unsupported hardware/backend matrix;
- migration notes;
- no model weights or private user data.

Release tags are immutable. Never retag a build after publication to make the code match the binary.

---

# 19. First executable task list for the agent

Do these in order. Do not jump directly into building the entire vision.

1. [ ] Inspect the local checkout and current GitHub state of all three existing repositories. Verify each current default branch, tag, license, file tree, tests, package scripts, and CI.
2. [ ] Check whether `timfromhcs/hcswaver` exists; if not and authorized, create it. If not authorized, create local repo files and report the creation blocker.
3. [ ] Extract the PDF feature list into a traceability matrix: PDF requirement → HCSWaver feature → owning module/repository → proof/test → phase → status.
4. [ ] Read CQ-HECS's current SAT code, current APIs, tests, and provenance schema. Decide the first adapter contract by actual code, not README alone.
5. [ ] Read HCS Foundry's current service/API/MCP implementation. Identify a real model-generation interface or document the gap.
6. [ ] Read HSCL1 `AGENTS.md`, package build scripts, CLI implementation, `docs/ARCHITECTURE.md`, `docs/CLI.md`, and current long-horizon plan. Prepare a precise integration proposal that does not block OS work.
7. [ ] Write ADRs: `ADR-0001-project-boundaries.md`, `ADR-0002-core-and-ffi.md`, `ADR-0003-solver-reuse.md`, `ADR-0004-data-and-provenance.md`, `ADR-0005-mcp-security.md`, `ADR-0006-gpu-scope.md`, `ADR-0007-license.md`, `ADR-0008-hscl1-packaging.md`.
8. [ ] Create the tiny DIMACS SAT/UNSAT fixtures and Python reference verifier.
9. [ ] Implement only the first vertical slice: import → inspect → solve via existing CQ-HECS adapter → verify SAT model → persist run → display run card.
10. [ ] Add Tseytin gates and exhaustive correctness tests before building the full Reduction Canvas.
11. [ ] Run all loops, save logs and evidence, and make a reviewable first feature branch.
12. [ ] Push the standalone project only after local gates pass and credentials/permissions exist. Create HSCL1 integration changes on a separate branch and PR; do not merge incomplete OS integration.
13. [ ] End the session with a precise handoff: commits, tests actually run, results, blockers, and next one-to-three tasks.

---

# 20. Final engineering principle

Build HCSWaver as a **scientific instrument**, not as a promise that AI will solve every mathematical problem.

Its value comes from making difficult research workflows more accessible, faster to explore, easier to reproduce, harder to fool, and easier for other people to extend. A local model may suggest the next idea; a solver may test an instance; an adversarial search may find a counterexample; a proof checker may validate a certificate; Lean may accept a theorem. Each system has a distinct job and a distinct boundary.

The product succeeds when users can move from a question to an inspectable experiment, from a candidate to a reproducible benchmark, and from a mathematical claim to an independently checked proof artifact — while keeping the entire workflow open-source, local-first, and honest about what remains unknown.

**HCSWaver — Weaving the Fabric of Complexity. Made with love by hcsmedia.**
