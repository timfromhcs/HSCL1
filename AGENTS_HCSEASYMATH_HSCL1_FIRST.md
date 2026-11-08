# AGENTS_HCSEASYMATH_HSCL1_FIRST.md
## Autonomous engineering contract: build HCSEASYMATH inside HSCL1 first, verify it as part of the OS, then extract it as a standalone open-source repository

> **Primary instruction:** Do not start by creating a new GitHub repository. First implement HCSEASYMATH as a real, integrated application inside the existing `timfromhcs/HSCL1` repository. Reuse the current HSCL1 architecture, its package conventions, HCS Control Center, `hscl` CLI, MCP server, build system, evidence ledger, self-healing process and release gates. Only after the in-tree product and its HSCL1 integration have passed the explicit extraction gate in this document may the portable application be split into `timfromhcs/hcseasymath`, given its own README and workflows, and pushed.
>
> **Parent authority:** The root `AGENTS.md` of HSCL1 remains the repository-wide contract. The active HCSUDA-first masterplan and the current self-heal masterplan remain ordering authorities for their existing work. This document is a companion plan for HCSEASYMATH; it does not replace, silently rewrite or weaken those documents. Where an instruction conflicts, obey the root `AGENTS.md`, record the conflict and update the companion plan through a reviewable change.
>
> **Product credit:** Made with love by hcsmedia.
>
> **Research snapshot:** prepared against the public HSCL1 `main` state observed at commit `56a321432c270244094c0fdea23e33352de2e412` (HCSUDA H2d merge, 2026-11-07). This is a snapshot, not a permanent truth. At the start of every execution session, fetch and inspect the actual current remote state before using any commit, version, branch or test status below.

---

# 0. Mission, scope and non-negotiable rules

## 0.1 Mission

Build **HCSEASYMATH** as a local-first mathematical and scientific workbench that is initially shipped and maintained as part of HSCL1.

The first usable product must allow a user to:

1. Enter mathematical expressions safely.
2. Parse, validate and normalize those expressions.
3. Perform real symbolic operations using a tested computer algebra system.
4. Evaluate expressions numerically with explicit precision and domain information.
5. Plot functions and inspect numerical data in an interactive interface.
6. Run selected scientific simulations with declared units, assumptions, solver settings and numerical error controls.
7. Save experiments locally with parameters, input hashes, software versions and reproducible result records.
8. Ask the existing local HCS agent infrastructure to help formulate or explain a calculation without allowing an LLM to determine mathematical truth.
9. Verify selected claims using independent numerical references or a formal proof checker where the problem is within scope.
10. Work without a cloud account, telemetry, remote inference or an always-running background service.

HCSEASYMATH is not a generic chat interface. It is a **calculation, simulation, visualization and verification environment**. A language model may assist with input formulation, code suggestions, explanation and experiment planning. It must never be the trusted calculator, solver oracle or proof checker.

## 0.2 First priority: in-tree HSCL1 integration

For the first delivery, the source code must live inside the HSCL1 checkout. The preferred source boundary is:

```text
HSCL1/
├── apps/
│   └── hcseasymath/              # portable application source (first built in-tree)
│       ├── backend/
│       ├── frontend/
│       ├── schemas/
│       ├── tests/
│       ├── benchmarks/
│       ├── docs/
│       ├── pyproject.toml
│       ├── lockfile(s)
│       └── README.md
├── cli/hscl/                     # existing OS CLI; add a namespaced math command
├── apps/control-center/          # existing Qt 6 / QML UI; add an integration card/page
├── packages/debian/
│   └── hscl-hcseasymath/         # small OS integration package
├── docs/
│   ├── integrations/HCSEASYMATH.md
│   ├── research/HCSEASYMATH_*.md
│   └── superpowers/plans/...
└── tests/                         # existing repository-level tests and package/image gates
```

The exact folder name may be adjusted only after inspecting existing naming conventions and checking for a conflict. Do not place HCSEASYMATH source inside `hcsuda/`: HCSUDA is a separate compute-runtime concern. Do not turn `hcsuda/` into a Python application. Keep a clear application boundary.

**Portable code belongs under `apps/hcseasymath/`.** OS-specific launchers, Debian metadata, QML integration, `hscl` adapters and ISO verification remain in their existing HSCL1 locations. This boundary is required so the source can later be extracted without losing the OS integration.

## 0.3 Later extraction, not initial repository creation

The future standalone repository is intended to be:

```text
https://github.com/timfromhcs/hcseasymath
```

Do not create it at the beginning. First reach the in-tree acceptance milestone and verify it on a built HSCL1 development image and a disposable VM. Then:

1. Audit which files under `apps/hcseasymath/` are truly portable.
2. Move OS-specific integration out of the portable source boundary if necessary.
3. Add a standalone `README.md`, `AGENTS.md`, `LICENSE`, `NOTICE`, `CONTRIBUTING.md`, `SECURITY.md`, `.gitignore`, CI workflows, lockfiles and release instructions.
4. Run the portable project tests from a clean checkout.
5. Review licensing of every direct and transitive dependency.
6. Use `git subtree split` or another history-preserving extraction method where appropriate; do not copy a stale snapshot while dropping important development history.
7. Create the new repository only after checking that it does not already exist and after the extraction gate passes.
8. Push a feature branch and create a PR if the new repository has a base branch; if it is initialized empty, create the initial branch using the repo's agreed publication process.
9. Keep the HSCL1 integration pointing to an immutable tag or commit of the standalone project only after the standalone release is reproducible and installable.
10. Keep the in-tree integration tests and package tests in HSCL1. The standalone CI must not replace the OS integration gates.

Do not delete the in-tree source immediately after extraction. Retain a transition period with a documented source-of-truth decision. Avoid maintaining two divergent copies.

## 0.4 Non-negotiable engineering rules

1. **No fake mathematics.** A plot is not a proof. A numerical approximation is not an exact result. A successful HTTP response is not mathematical correctness.
2. **No untrusted Python execution.** Never execute user-supplied code, generated patches, expressions or test assertions with `eval`, `exec`, dynamic imports, `runpy`, `pickle`, arbitrary shell calls or an unrestricted notebook kernel inside the backend process.
3. **No unsafe SymPy parsing.** Do not pass raw user text to `sympy.sympify` or `sympy.parsing.parse_expr` without an explicit, reviewed safe parser. SymPy documents that `parse_expr` uses `eval`; unsanitized input must not be used.
4. **No arbitrary agent execution.** There is no generic `shell`, `exec`, Python-code, file-system traversal or arbitrary command MCP tool.
5. **CPU reference first.** Every accelerated path must have a trusted CPU/reference implementation and differential tests before it can be offered to users.
6. **HCSUDA is optional acceleration, not a required dependency.** Unknown operation, unsupported dtype, unverified device/driver or resource risk means use a correct CPU implementation or return a typed refusal.
7. **Do not claim a GPU speed-up from a capability flag.** A device extension being present is not evidence that this application's complete operation is faster or correct.
8. **No arbitrary network listener.** Backend services bind to loopback only and run only when the application is launched. No autostart service, no remote listener and no LAN exposure by default.
9. **No broad CORS.** Do not use `allow_origins=["*"]` for a local math API. Prefer serving the bundled frontend from the same origin; if CORS is required, allow only the exact locally generated frontend origin(s).
10. **No cloud dependency.** No API key, SaaS CAS, hosted LLM, external rendering CDN or telemetry is required for core features.
11. **No huge ISO payload.** Do not bundle model weights, large scientific datasets, full SageMath, Lean toolchains, Macaulay2, micromagnetic software or development SDKs into the standard HSCL1 ISO.
12. **No privileged app.** HCSEASYMATH, its backend, its CLI and its UI run as the logged-in user. Do not add a root service or Polkit helper for mathematical calculations.
13. **No silent data movement.** Runtime downloads, optional solver installation and dataset imports require visible user consent, a size estimate, a source, hashes where available and a clear cancellation path.
14. **Do not mutate the user's system for a demo.** Do not install packages, change GPU drivers, alter APT sources, change firewall rules or create background tasks without an explicit user-facing action.
15. **Preserve existing work.** No `git reset --hard`, `git clean -fdx`, force-push, history rewrite, branch deletion or overwriting unrelated files.
16. **Never weaken an existing gate to make the new feature pass.** Fix the product or the gate itself, with an independent regression test.
17. **Max three focused attempts per distinct failure hypothesis.** Then record `BLOCKED`, include the reproducer and continue with independent work.
18. **Every claim has evidence.** Update the relevant research ledger, build log, claims table and limitations list after the relevant test passes.
19. **No live trading.** Market microstructure functions are educational / analytical / backtesting tools. No broker connection, order routing, automated execution or financial advice.
20. **No physical-device or clinical claims.** Simulations must state their assumptions and scope. HCSEASYMATH is not a clinical device, MRAM design sign-off tool or proof of real-world performance.

---

# 1. Current HSCL1 baseline — observed facts to re-check

## 1.1 Repository snapshot observed on 2026-11-07

The current public GitHub repository observed for this plan is:

- Repository: `timfromhcs/HSCL1`
- Default branch: `main`
- Observed latest commit: `56a321432c270244094c0fdea23e33352de2e412`
- Observed version in root `VERSION` / README: `0.1.3-alpha.0`
- OS basis: Ubuntu 26.04 LTS / Kubuntu 26.04, KDE Plasma 6.6
- Status: pre-alpha; the README still states VM-only validation, no physical-hardware verification and unsigned releases.
- License in the existing HSCL1 tree: GPL-3.0-or-later.

The latest observed commit merged HCSUDA H2d: f16-storage GEMM, a 16×16×16 cooperative-matrix GEMM path and a cooperative-matrix shape probe. The commit's build-log entry reports the new path on the AMD Radeon 680M, with a same-run comparison and numerical self-test. Re-check the current `main` before relying on this snapshot.

## 1.2 Existing masterplans that remain authoritative

At session start, read these files from the real checkout:

1. `AGENTS.md` — repository-wide engineering, security, product and release contract. This always wins over companion instructions.
2. `docs/superpowers/plans/2026-11-07-masterplan-hcsuda-to-v1.md` — HCSUDA-first execution ordering and HCSUDA/HSCL1 roadmap.
3. `docs/superpowers/plans/2026-11-08-selfheal-masterplan.md` — current measured resume state and repair-loop ledger.
4. `docs/superpowers/plans/2026-11-07-genesis-parallel.md` — parallel science-integration track rules.
5. `docs/superpowers/plans/2026-11-07-hcswaver-integration.md` — companion application integration pattern.
6. `docs/BUILD_LOG.md`, `docs/CLAIMS.md`, `docs/KNOWN_LIMITATIONS.md`, `docs/ARCHITECTURE.md`.
7. `docs/genesis/BASELINE.md`, `DECISIONS.md`, `RESEARCH_LEDGER.md`, `TEST_MATRIX.md`, `EXECUTION_LOG.md`, `BLOCKERS.md`.
8. `docs/integrations/HCSWAVER.md` and `docs/integrations/HCSWAVER_AGENTS_SECTION.md`.
9. Existing `scripts/forge.py`, `scripts/build-deb.sh`, `scripts/remaster-iso.sh`, `distro/live/verify-image.sh`, QEMU scripts, existing CI workflows and package tests.

Do not assume that a filename dated 2026-11-08 is newer than the active masterplan just because of its name. The active plan explicitly declares which document controls ordering. Resolve any mismatch by checking the current source, tests and merged commits.

## 1.3 HCSUDA status that changes the plan

The current repository already contains:

```text
hcsuda/
├── Cargo.toml
├── crates/
│   ├── hcsuda-core/
│   ├── hcsuda-vk/
│   └── hcsuda-cli/
├── shaders/
├── benchmarks/
└── docs/
```

The observed HCSUDA workspace currently contains the core tensor/dtype/capability/planner/reference functionality, Vulkan device and dispatch layers, a CLI and measured benchmark evidence. It is not yet a general-purpose Python numerical-computing framework or a finished deep-learning runtime.

**H2d, as observed after the latest merge, includes:**

- Tiled f16-storage GEMM (f32 accumulation).
- Cooperative-matrix GEMM with f16 × f16 → f32 accumulation for compatible aligned shapes.
- A cooperative-matrix capability/shape probe.
- Existing int8 dot-product GEMM work and a planner path based on matching, passing self-test evidence.
- Evidence recorded under `hcsuda/benchmarks/amd-radeon-680m/` and summarized in `hcsuda/docs/MEASURED.md`.

The measured record describes one integrated AMD Radeon 680M, one driver/toolchain and specific matrix sizes. It is not universal evidence. The cooperative path has a shape constraint; the planner must refuse unsupported dimensions and choose a verified fallback.

**Important documentation drift to reconcile:** the latest HCSUDA merge and `docs/BUILD_LOG.md` show H2d completion, while some older roadmap/readme/capability-matrix rows may still call f16/cooperative-matrix kernels planned. Do not blindly inherit stale statuses. Reconcile each file from the latest implementation, exact self-test JSON, benchmark JSON and CI evidence. Update the HCSUDA README, capability matrix and active plan only after confirming the real result. Do not make HCSEASYMATH depend on an unverified future HCSUDA API.

The next HCSUDA item in the observed self-heal ledger is H3, starting with a GGUF reader and then a tiny transformer. HCSEASYMATH must not duplicate model loading or implement its own LLM runtime. Continue HCSUDA's active H3 work in parallel only where it does not compete for the same heavy resources or modify the same files. The first HCSEASYMATH vertical slice must work on CPU without HCSUDA.

## 1.4 Existing HSCL1 integration surfaces

The following components already exist and should be extended rather than replaced:

| Existing surface | Current purpose | HCSEASYMATH integration |
|---|---|---|
| `cli/hscl/src/main.rs` | Rust `clap` CLI with namespaced commands | Add `hscl math ...` after the app's status/doctor contract is stable |
| `cli/hscl/src/mcp.rs` | Local MCP over stdio; typed allow-listed CLI calls; read-only by default | Add a small namespaced, typed `hcseasymath_*` tool set; no shell/exec |
| `apps/control-center/` | Qt 6 / QML desktop Control Center | Add a real HCSEASYMATH card/status page using the existing `CliBackend` pattern |
| `packages/debian/` | Existing small Debian app packages | Add `hscl-hcseasymath`, following the tested `hscl-cqhecs` pattern |
| `themes/tokens/` | Canonical HCS design tokens | Reuse the same visual tokens; do not invent an isolated product theme |
| `handbook/` | Offline EN/DE/FR handbook | Add install, use, privacy and troubleshooting guidance |
| `scripts/build-deb.sh` | Existing package builder | Use this; do not add a competing package build system |
| `distro/live/verify-image.sh` | Image verification gates | Add paired checks for the new package, desktop entry and no-autostart invariant |
| `tests/unit/`, `tests/visual/` | Existing test conventions | Add package, CLI, MCP, UI and image-gate tests following repository style |

The Control Center's current `CliBackend` uses a closed command allow-list and argument vectors, not shell strings. Preserve that safety property. Do not call Python directly from QML and do not duplicate mathematical calculations in QML.

## 1.5 `hscl-cqhecs` is the package pattern to study

The current `packages/debian/hscl-cqhecs/` implementation is a useful reference for a scientific app package:

- It is a small shell package, not a giant environment bundle.
- It ships a launcher, `.desktop` entry, pinned runtime requirements and a small config.
- Runtime data goes into the user's XDG data directory.
- The Python runtime is not installed during `dpkg` maintainer scripts.
- Installation is explicit and user-confirmed.
- It shows the download size and checks available disk space.
- Hash-pinned wheels and `pip --require-hashes --only-binary=:all:` are used.
- It does not start a service on boot.
- It does not silently fall back to the system Python or overwrite user data.
- The package itself does not require the optional `python3-venv` package as a hard `Depends`, because the pristine base image may not include it.

For HCSEASYMATH, inspect the *current* launcher, control file, runtime config and tests before copying the pattern. Do not copy the earlier `hscl-cqhecs` paths, version pins or assumptions verbatim.

## 1.6 User hardware and realistic first target

The historical development hardware context is:

- Windows 11 host with a Ryzen 7 7735HS.
- AMD Radeon 680M integrated GPU (RDNA2).
- Shared system memory; no CUDA.
- Vulkan available on the measured Windows development environment.
- HSCL1's CI/build path also targets Linux/Ubuntu and VM environments.

At the start of every session, detect the actual host and guest. Do not assume the user's current machine has the same free RAM, free disk, driver, Vulkan extensions or Python toolchain as the measured HCSUDA record.

HCSEASYMATH's required baseline is **CPU-only correctness**. Vulkan/WebGPU/HCSUDA are optional acceleration/rendering paths. If the app cannot run without a GPU, it has failed its first compatibility requirement.

---

# 2. Product architecture and boundaries

## 2.1 One product, three layers

The product must be organized as:

```text
HSCL1
├── OS integration
│   ├── hscl-hcseasymath Debian package
│   ├── hscl math CLI namespace
│   ├── HCS Control Center card
│   ├── desktop launcher
│   ├── handbook EN/DE/FR
│   └── image / QEMU / CI gates
│
└── apps/hcseasymath (portable app)
    ├── local frontend
    ├── local API and job manager
    ├── symbolic and numerical engines
    ├── scientific domain modules
    ├── adapters to optional external solvers
    ├── typed schemas and provenance
    ├── tests and benchmarks
    └── portable documentation
```

The app owns mathematical and scientific domain logic. HSCL1 owns operating-system integration, launch and lifecycle controls. HCSUDA owns verified compute kernels and resource-aware dispatch. HCS Foundry owns local model management and inference. Lean 4 owns formal proof checking when a theorem is actually formalized.

## 2.2 Do not duplicate existing systems

- Do not create a second HCS Foundry or model manager.
- Do not implement a new GGUF parser or model runtime in HCSEASYMATH.
- Do not create a second SAT engine merely to run symbolic math.
- Do not create a private Vulkan allocator in HCSEASYMATH if a suitable HCSUDA API exists and its contract is stable.
- Do not copy `hscl mcp` into Python and maintain two divergent OS-level MCP servers.
- Do not create a second theme/token system.
- Do not make the Control Center a second application backend.

Use adapters. If the existing project does not expose the required API yet, record the missing API and implement a narrow adapter after the contract is agreed. Never pretend a not-yet-existing API exists.

## 2.3 Portable application structure

Start with a minimal source tree and grow it only when files have a real implementation:

```text
apps/hcseasymath/
├── README.md
├── pyproject.toml
├── uv.lock or a fully hash-pinned requirements lock
├── backend/
│   └── hcseasymath/
│       ├── __init__.py
│       ├── api/
│       │   ├── app.py
│       │   ├── routes/
│       │   ├── websocket.py
│       │   └── errors.py
│       ├── core/
│       │   ├── expression_ast.py
│       │   ├── symbolic.py
│       │   ├── numeric.py
│       │   ├── units.py
│       │   ├── precision.py
│       │   ├── provenance.py
│       │   └── limits.py
│       ├── domains/
│       │   ├── functions/
│       │   ├── ode/
│       │   ├── dag/
│       │   ├── spintronics/
│       │   └── market_microstructure/
│       ├── adapters/
│       │   ├── hcsuda/
│       │   ├── lean/
│       │   ├── macaulay2/
│       │   ├── sage/
│       │   └── external/
│       ├── jobs/
│       ├── storage/
│       └── mcp/
├── frontend/
│   ├── package.json
│   ├── package-lock.json
│   ├── index.html
│   └── src/
│       ├── app/
│       ├── components/
│       ├── features/
│       ├── api/
│       ├── state/
│       ├── styles/
│       └── i18n/
├── schemas/
│   ├── math-request.schema.json
│   ├── math-result.schema.json
│   ├── simulation-run.schema.json
│   ├── experiment.schema.json
│   └── provenance.schema.json
├── tests/
│   ├── unit/
│   ├── property/
│   ├── differential/
│   ├── integration/
│   ├── security/
│   ├── api/
│   ├── mcp/
│   ├── frontend/
│   └── e2e/
├── benchmarks/
│   ├── baselines/
│   ├── protocols/
│   └── results/
└── docs/
    ├── ARCHITECTURE.md
    ├── MATHEMATICAL_CONTRACTS.md
    ├── API.md
    ├── MCP.md
    ├── SECURITY.md
    ├── BENCHMARKS.md
    └── LIMITATIONS.md
```

The first commit must not create a forest of empty directories. Create the smallest real vertical slice and add folders with the feature that needs them.

## 2.4 Initial product stack

Preferred implementation choices, subject to repository and builder audit:

| Layer | Preferred choice | Rule |
|---|---|---|
| Symbolic math | SymPy | Python CPU reference and exact symbolic expressions |
| Numerical operations | NumPy + SciPy | CPU baseline, validated solvers and statistics |
| API | FastAPI + Pydantic | Local loopback service; typed request/response models |
| Storage | SQLite | Metadata, runs, parameters, hashes, small result summaries |
| Large results | Filesystem artifacts | No giant matrices, plots or datasets stored as SQLite blobs |
| Frontend | React + TypeScript + Vite | Build-time toolchain only; bundled local assets |
| Equation entry | MathLive or a tested equivalent | Keyboard-friendly math-field input |
| Math rendering | KaTeX or MathJax | Local bundled package, no CDN |
| 2D charts | A maintained chart library or SVG | Use the simplest tool that meets the need |
| 3D graphics | Three.js `WebGPURenderer` with WebGL2 fallback | Visualization only; backend remains authoritative |
| Formal proof | Lean 4 + Mathlib | Optional user-installed toolchain, not in ISO |
| Computational algebra | Macaulay2 or SageMath adapter | Optional external local process, version-pinned |
| GPU compute | HCSUDA adapter | Only after stable API and exact operation verification |
| AI assistance | HCS Foundry adapter | Optional; never required for core calculations |

Do not add Docker/Compose as a mandatory user dependency. The HSCL1 product must run as a normal local application with a user-level runtime. Container usage may be a developer/test option only when it simplifies an isolated test.

---

# 3. Product roadmap: build a working vertical slice before expanding domains

## Phase 0 — baseline audit and plan reconciliation

**Goal:** Make sure the agent understands the current repository before changing code.

Tasks:

- Inspect `git status`, current branch, remotes, last commits and all local/untracked files.
- Fetch current `origin/main` and the active feature branch without overwriting local work.
- Read the current root `AGENTS.md` and the active HCSUDA/self-heal plans.
- Inspect the actual HCSUDA H2d implementation, self-test JSON, benchmark JSON, capability probe and measured document.
- Reconcile stale HCSUDA status labels only after confirming code and evidence.
- Inspect `hscl-cqhecs` package structure and its package/launcher tests.
- Inspect `apps/control-center` `CliBackend`, QML pages, translations and tests.
- Inspect the existing `hscl` CLI command enum and MCP tool registry.
- Inspect `scripts/forge.py`, package build scripts, image verification gates, `docs/PACKAGES.md` generators and CI workflow job names.
- Detect Python, Node, Rust, Qt, Vulkan SDK, browser and QEMU availability on the actual build host.
- Record available RAM, disk space and whether the machine is running a local LLM or VM. Do not start a heavy job if another one is already consuming the resource budget.

Required outputs:

```text
docs/integrations/HCSEASYMATH.md
docs/integrations/HCSEASYMATH_AGENTS_SECTION.md
docs/research/HCSEASYMATH_BASELINE.md
docs/research/HCSEASYMATH_RESEARCH_LEDGER.md
docs/research/HCSEASYMATH_DECISIONS.md
docs/research/HCSEASYMATH_BLOCKERS.md
docs/research/HCSEASYMATH_TEST_MATRIX.md
```

If the repo already has a better location or a corresponding file, extend it rather than creating duplicates.

Exit gate:

- Every observed fact has a path, commit SHA, command or source link.
- The proposed product boundary does not overlap HCSUDA source ownership.
- No files have been overwritten.
- Baseline local tests are recorded before feature code is changed.

## Phase 1 — minimal application foundation

**Goal:** Build a local application that starts, reports its actual state and performs one safe symbolic operation.

Implement:

- Python package metadata and a pinned runtime.
- `hcseasymath doctor --json`.
- `hcseasymath serve` bound to `127.0.0.1`.
- API endpoint `/api/v1/health`.
- API endpoint `/api/v1/capabilities`.
- A safe expression parser with an explicit AST allow-list.
- `POST /api/v1/symbolic/differentiate`.
- A tiny UI that sends a request and displays the returned expression, result, error or refusal.
- A SQLite migration/init mechanism.
- A deterministic run ID and provenance record.
- No startup daemon and no background autostart.

Example vertical slice:

```text
User enters: x**3 - 3*x**2 + 2*x
    ↓
safe parser builds validated expression AST
    ↓
SymPy differentiates exactly
    ↓
result = 3*x**2 - 6*x + 2
    ↓
result schema validated
    ↓
run record stored in the local database
    ↓
UI displays expression, derivative, source engine, assumptions and run ID
```

The derivative should be checked by an independent property:
\[
\frac{d}{dx}(x^3-3x^2+2x)=3x^2-6x+2.
\]

The first release does not need 3D graphics, LLM features, Lean or advanced scientific models. Make the first vertical slice correct and pleasant before expanding.

Exit gate:

- CPU-only.
- Offline after installation.
- Safe parsing tests pass.
- No arbitrary code execution path.
- API is local-only and stops when the application exits.
- One end-to-end test starts the app, calls the API, checks the derivative and shuts the app down cleanly.

## Phase 2 — Math Studio MVP

Add features only when there is a symbolic or numerical contract and tests.

Initial supported operations:

- Parse and normalize expressions.
- List free variables.
- Substitute symbol values.
- Simplify within declared resource limits.
- Differentiate.
- Integrate where SymPy can return a result; otherwise return `UNRESOLVED` or an unevaluated symbolic object, not a fabricated primitive.
- Solve equations for supported forms.
- Expand and factor.
- Evaluate numerically with selected precision.
- Plot a one-variable function.
- Plot a two-variable surface from bounded samples.
- Inspect domain, singularities and discontinuities where implemented.

Every operation returns:

```json
{
  "schema_version": "hcseasymath.result.v1",
  "run_id": "opaque-local-run-id",
  "status": "ok",
  "operation": "differentiate",
  "engine": "sympy",
  "input_digest": "sha256:...",
  "normalized_expression": "...",
  "result_expression": "...",
  "exactness": "symbolic_exact",
  "assumptions": [],
  "warnings": [],
  "timings_ms": {},
  "provenance": {}
}
```

Use a typed status enum. Suggested values:

- `ok`
- `partial`
- `unresolved`
- `unsupported`
- `invalid_input`
- `resource_limit`
- `cancelled`
- `engine_unavailable`
- `internal_error`

Do not return HTTP 200 with a green success label for an `unresolved` mathematical result.

## Phase 3 — scientific domains, one at a time

Implement the following domains as independently testable modules. Do not launch all of them in one giant sprint.

### 3.1 Numerical ODE / dynamical systems lab

Use SciPy's `solve_ivp` as the first trusted numerical solver.

Support an initial bounded set:

- Initial-value problems for ordinary differential equations.
- Explicit solver selection.
- Absolute and relative tolerance.
- Step-size limits.
- Dense output when supported.
- Event detection when implemented.
- Solver status, number of evaluations and warning information.
- Reproducible result data.

Reference example:

\[
\frac{dy}{dt}=-ky,\qquad y(0)=y_0
\]
with exact solution:
\[
y(t)=y_0 e^{-kt}.
\]

Test numerical results against the exact solution for known parameters. Record both absolute and relative error:
\[
e_{\mathrm{abs}}=\max_i |y_i-y_{\mathrm{ref},i}|,
\qquad
e_{\mathrm{rel}}=
\frac{\max_i |y_i-y_{\mathrm{ref},i}|}
{\max_i |y_{\mathrm{ref},i}|+\epsilon}.
\]

Use `solve_ivp` method families according to stiffness and accuracy requirements. Do not force a single integrator across all problems. SciPy documents RK45, DOP853, Radau and BDF and their intended use cases.

### 3.2 Market Microstructure / Microprice Lab

This is a data-analysis and educational module. It must never place live orders.

The simple size-weighted midpoint proxy is:

\[
P_{\mathrm{mid}}=\frac{P_b+P_a}{2}
\]

\[
I=\frac{Q_b-Q_a}{Q_b+Q_a}
\]

\[
P_{\mathrm{weighted}}=
\frac{Q_b P_a+Q_a P_b}{Q_b+Q_a}
=
P_{\mathrm{mid}}+\frac{P_a-P_b}{2}I.
\]

Here:

- \(P_b\): best bid price.
- \(P_a\): best ask price.
- \(Q_b\): bid queue size at the best bid.
- \(Q_a\): ask queue size at the best ask.
- \(I\): top-of-book imbalance.

Validation:

- `P_a > P_b` for a non-crossed book.
- `Q_b >= 0`, `Q_a >= 0`.
- Reject `Q_b + Q_a == 0`.
- Prices must use an explicit tick size or decimal representation, never binary float for financial tick arithmetic.
- Quantities must state units (shares/contracts/lots).
- Output must label this as a **weighted midpoint proxy**, not the full predictive microprice estimator.

The full microprice literature (e.g. Stoikov) models expected future midpoint changes using order-book imbalance, spread and a fitted state process. Do not equate the simple weighted midpoint with that full estimator. If implementing the Markov/state-space estimator later, record discretization, training data, evaluation horizon, data splits and leakage checks.

Benchmark and test:

- Invariant: \(P_b \le P_{\mathrm{weighted}}\le P_a\) for nonnegative queue sizes and \(P_a\ge P_b\).
- If \(Q_b=Q_a\), result equals midpoint.
- If \(Q_b\) grows while \(Q_a\) is fixed, weighted proxy moves monotonically toward ask.
- If both queue sizes scale by the same positive factor, result is unchanged.
- Validate against an independent Decimal reference.
- Backtest only with timestamped historical data and a no-lookahead evaluation.
- Do not include broker APIs or order submission.

### 3.3 SOT-MRAM / spintronics simulation

The input demo's current LLG routine is a qualitative toy. Its `alpha`, `tau_dl`, field and time step have no declared physical units or calibration. It cannot be presented as a validated SOT-MRAM model.

First deliverable: a **macrospin demonstration model** with clearly documented simplifying assumptions.

The application must:

- Define a sign convention for gyromagnetic ratio and torque terms.
- Define the effective field and its units.
- Define magnetization vector \(\mathbf m\) and polarization \(\mathbf p\) as normalized vectors.
- Define damping \(\alpha\) as dimensionless.
- Define all torque coefficients with units consistent with the chosen equation.
- State whether temperature/noise, demagnetization, anisotropy, DMI, interfacial spin-orbit coupling and spatial effects are included.
- Track the norm error \(||\mathbf m||-1\).
- Provide solver and time-step convergence tests.
- Compare an analytically solvable or simplified case against a trusted reference.
- Label the output `macrospin_demo` unless experimentally calibrated.

One possible explicit convention for the deterministic macrospin LLG + torque model is:

\[
\frac{d\mathbf m}{dt}
=
-\frac{\gamma}{1+\alpha^2}
\left[
\mathbf m\times\mathbf H_{\mathrm{eff}}
+
\alpha\,\mathbf m\times(\mathbf m\times\mathbf H_{\mathrm{eff}})
\right]
+
\tau_{\mathrm{DL}}\,
\mathbf m\times(\mathbf m\times\mathbf p)
+
\tau_{\mathrm{FL}}\,
\mathbf m\times\mathbf p.
\]

This is only a model contract when the exact definitions and units of \(\gamma\), \(\mathbf H_{\mathrm{eff}}\), \(\tau_{\mathrm{DL}}\) and \(\tau_{\mathrm{FL}}\) have been written down. Different communities use different sign and effective-field conventions. Do not copy a formula and assume its signs match a different solver.

Validation stages:

1. Pure precession with damping disabled, if supported by the parameter model.
2. Damping-only relaxation toward the expected easy-axis equilibrium.
3. Norm preservation or explicitly documented projection error.
4. Time-step halving convergence.
5. Cross-check against a published test case or an open solver with compatible model scope.
6. Only then allow parameter sweeps and switching maps.

For more advanced micromagnetics, evaluate OOMMF and Spirit as reference projects. Evaluate MuMax3 only as a comparison target: its core GPU path is CUDA/NVIDIA-oriented, so it is not a native Radeon 680M/Vulkan dependency. Never market the macrospin demo as a 3D device-level SOT-MRAM simulator.

### 3.4 Derived Algebraic Geometry (DAG) / homological algebra

This domain must be treated as genuine mathematics, not as a graph/mesh visualization label.

The original prototype incorrectly returned:

```python
derived_cohomology_dim = len(expr.free_symbols)
```

That is not a derived cohomology dimension. The number of free symbols in a polynomial says nothing about Tor groups, derived intersections or derived structure sheaves.

First implementation should be a **small educational homological-algebra module** with a Macaulay2 adapter when available.

A canonical test example:

Let \(A=k[x]\) and \(M=N=A/(x)\cong k\). A free resolution of \(M\) over \(A\) is:

\[
0 \longrightarrow A
\xrightarrow{\cdot x}
A
\longrightarrow A/(x)
\longrightarrow 0.
\]

Tensoring with \(N=A/(x)\) makes the differential multiplication by \(x=0\) on \(k\), so:

\[
\operatorname{Tor}^{A}_0(k,k)\cong k,
\qquad
\operatorname{Tor}^{A}_1(k,k)\cong k,
\qquad
\operatorname{Tor}^{A}_i(k,k)=0\quad (i>1).
\]

This is a proper, testable first homological example. The exact cohomological grading convention must be documented when rendering the derived tensor product.

DAG roadmap:

- Start with modules, rings and explicit finite presentations within a bounded domain.
- Represent chain complexes and differentials with typed objects.
- Validate \(d_{n-1}\circ d_n=0\).
- Compute homology for supported finite complexes.
- Verify simple Tor examples through an independent Macaulay2 run.
- Add derived tensor product examples only with precise conventions.
- Do not claim a general DAG engine from a handful of examples.
- Use Macaulay2 as an optional executable adapter, not as an implicit dependency of the ISO.
- Use SageMath only where it contributes a clearly identified algebraic computation and does not duplicate SymPy/Macaulay2 needlessly.

A plotted zero-locus or surface is a visualization of an equation, not evidence of derived intersection or derived cohomology.

## Phase 4 — API, jobs and experiment storage

Build a typed local API around the same service functions that power the CLI, MCP and UI.

Required API groups:

```text
GET    /api/v1/health
GET    /api/v1/capabilities
GET    /api/v1/engines
POST   /api/v1/expressions/parse
POST   /api/v1/symbolic/differentiate
POST   /api/v1/symbolic/integrate
POST   /api/v1/symbolic/solve
POST   /api/v1/numeric/evaluate
POST   /api/v1/plots/sample
POST   /api/v1/simulations
GET    /api/v1/jobs/{job_id}
POST   /api/v1/jobs/{job_id}/cancel
GET    /api/v1/experiments
POST   /api/v1/experiments
GET    /api/v1/experiments/{experiment_id}
POST   /api/v1/experiments/{experiment_id}/export
POST   /api/v1/proofs/lean/check
```

Do not implement an endpoint just because it appears in this list. Each endpoint is added with its schema, tests, cancellation and a real implementation. The first vertical slice only needs health, capabilities, parse, differentiate and a run record.

### 4.1 Job model

Long-running simulations must not block the API event loop.

A job record should include:

```json
{
  "schema_version": "hcseasymath.job.v1",
  "job_id": "opaque-id",
  "kind": "simulation",
  "state": "queued",
  "created_at": "ISO-8601 timestamp",
  "started_at": null,
  "finished_at": null,
  "progress": {
    "completed": 0,
    "total": 0,
    "unit": "steps"
  },
  "cancel_requested": false,
  "input_digest": "sha256:...",
  "engine": "scipy",
  "resource_estimate": {},
  "result_uri": null,
  "error": null
}
```

Job states: `queued`, `running`, `succeeded`, `partial`, `failed`, `cancelled`, `timed_out`, `resource_refused`.

Requirements:

- Every job has a bounded wall-time and memory policy.
- Every job can be cancelled where the worker supports cooperative cancellation.
- A killed worker must not leave the API process corrupt.
- Use a subprocess/worker boundary for untrusted or expensive work.
- Preserve structured logs but do not log source expressions containing potentially private input unless the user explicitly opts in.
- Store large arrays in files in the user's data directory; store hashes and metadata in SQLite.
- Do not keep a result in RAM forever.
- If a job is interrupted, report it as interrupted, not succeeded.

### 4.2 SQLite schema

Use versioned migrations. At minimum:

- `schema_migrations`
- `experiments`
- `runs`
- `jobs`
- `artifacts`
- `engine_profiles`
- `proof_checks`
- `benchmark_runs`
- `source_references`

Every run should store:

- Canonical input JSON.
- Input SHA-256.
- Operation and engine.
- Engine version.
- Software version and source revision.
- Parameter values and units.
- Numerical tolerances and precision.
- Random seed where relevant.
- Start/end times.
- Machine capability record where hardware matters.
- Warnings and limitations.
- Result hashes and artifact paths.

Do not store raw user files, API credentials or model weights in the database.

### 4.3 Provenance and result contracts

Use a versioned provenance schema. It should be conceptually compatible with the project's existing evidence/provenance conventions, including the CQ-HECS `hcs.run.v2` pattern where applicable, but do not copy quantum-specific fields blindly into mathematical and simulation runs.

A result must distinguish:

- Symbolically exact result.
- Numerically evaluated result.
- Numerically approximated / iterative result.
- Estimated result.
- External solver result.
- Formally verified result.
- Unresolved result.

`FORMALLY_VERIFIED` may only be used when a named formal checker accepts the exact theorem/proof artifact at a recorded checker version and source revision. A unit test, symbolic simplification, LLM review or numerical agreement is not formal verification.

## Phase 5 — local API / MCP integration

### 5.1 Reuse HSCL1's local MCP layer

The existing `hscl mcp` implementation is a JSON-RPC stdio server, read-only by default. It maps tools to a finite set of validated CLI arguments and does not expose a shell. Preserve this architecture.

Preferred design:

```text
Local LLM / MCP client
       |
       | stdio, JSON-RPC
       v
existing `hscl mcp`
       |
       | fixed typed argv / local service call
       v
HCSEASYMATH application services
       |
       +--> SymPy / SciPy
       +--> local SQLite / artifacts
       +--> optional Lean / Macaulay2
       +--> optional verified HCSUDA path
```

Do not add a second independent root-level MCP server unless the existing `hscl mcp` architecture cannot support the required app lifecycle. If a separate `hcseasymath mcp` subcommand is justified, it must also use stdio, typed tools, strict schemas and the same service layer; document why both MCP entry points are necessary.

The MCP transport must follow the selected protocol revision exactly. The current HSCL1 `hscl mcp` code has an existing protocol constant; do not silently change the global HSCL1 protocol version as part of this feature. If the app exposes a separate MCP endpoint, select a version supported by the actual client libraries and test handshake, tools/list, tools/call, errors, cancellation and shutdown.

stdio rules:

- `stdin` and `stdout` carry MCP messages only.
- All logs go to `stderr`.
- Never print banners, progress bars, debug output or JSON diagnostics to MCP `stdout`.
- One malformed request must not crash the entire process.
- Validate every input field and reject extra keys.
- The server exposes no generic command execution tool.
- All filesystem paths are rooted in configured HCSEASYMATH data/artifact directories.

Initial tool set (read-only by default):

| Tool | Purpose | Write? |
|---|---|---|
| `hcseasymath_status` | installed/runtime/engine status | No |
| `hcseasymath_capabilities` | available operations and backends | No |
| `hcseasymath_parse` | validate and normalize an expression | No |
| `hcseasymath_differentiate` | exact symbolic differentiation in supported scope | No |
| `hcseasymath_evaluate` | bounded numeric evaluation | No |
| `hcseasymath_plot_sample` | bounded plot sample data | No |
| `hcseasymath_run_get` | retrieve an existing run | No |
| `hcseasymath_simulate` | submit a validated, bounded simulation | Writes a new run |
| `hcseasymath_run_cancel` | cancel a running job | Writes job state |
| `hcseasymath_lean_check` | run a selected local Lean project/check | Reads/writes a bounded temp workspace |

Write-capable tools must be hidden or rejected unless the explicit write permission is enabled. `--allow-write` must not become an arbitrary file-write or command-execution permission; each tool remains path- and operation-limited.

### 5.2 Local FastAPI security

- Default bind host: `127.0.0.1`; do not bind `0.0.0.0`.
- Prefer serving the bundled frontend from the same origin as the API, avoiding CORS entirely.
- If CORS is necessary, allow only explicit exact origins and only required methods/headers.
- Do not allow wildcard origins with credentials.
- Validate `Host` and `Origin` for browser-facing state-changing routes and WebSocket handshakes.
- Use a per-process random local token or another appropriate local session mechanism for state-changing HTTP requests.
- Do not put a long-lived secret into a static JavaScript bundle.
- Do not expose the service via LAN.
- Do not accept unauthenticated state-changing requests merely because the destination is loopback; DNS rebinding and hostile local browser origins must be considered.
- Use an ephemeral port or a collision-safe local port reservation; do not assume port 8000 is free.
- The launcher owns lifecycle: start backend, wait for health, open UI, stop backend on exit.
- Do not register a systemd service enabled at boot.
- Do not write a network-accessing maintainer script.
- WebSocket events are job progress and log summaries only; do not stream arbitrary local file content.
- Set request size, expression length, node-count, depth, matrix dimensions, plotting grid and simulation-step limits.

### 5.3 HCS Foundry / local model integration

The LLM is an optional assistant:

- First inspect the current HCS Foundry source and documented API; do not assume the MCP tool list exposes text generation.
- If generation is not exposed by the public MCP tool set, use a documented local OpenAI-compatible endpoint only after verifying it is actually present and enabled.
- Do not launch a second llama-server.
- Do not silently switch to cloud inference.
- If Foundry is unavailable, the entire mathematical product remains usable without it.
- LLM output is an untrusted draft. All equations must be parsed by the safe parser; all code must be separately sandboxed; all claims must be checked by the actual engine or proof checker.
- Looped Transformers, Q-Exit and other adaptive reasoning mechanisms are optional model-level research adapters. They are not required mathematical backends and must not be presented as a property of arbitrary GGUF models.

---

# 4. Mathematical correctness and safe computation

## 4.1 Safe mathematical expression parser

The original prototype's `sympify(expr_str)` and `parse_expr`-style approach must not receive arbitrary user input. Implement a restricted parser.

Allowed syntax in the first release:

- Numeric constants: integer, rational literal syntax, decimal literal.
- Declared symbol identifiers.
- Parentheses.
- Unary `+` and `-`.
- Binary `+`, `-`, `*`, `/`, `**`.
- A finite allow-list of functions, e.g. `sin`, `cos`, `tan`, `exp`, `log`, `sqrt`, `abs`.
- A finite allow-list of constants, e.g. `pi`, `E`.
- Optional explicit rational syntax such as `Rational(1, 3)` only if parsed as a special safe AST node, not as a generic call.

Reject:

- Attribute access (`x.__class__`).
- Subscripts and slices.
- Comprehensions and generators.
- Lambda expressions.
- Imports.
- Assignments.
- Function definitions.
- F-strings.
- `__dunder__` identifiers.
- Arbitrary function names.
- Keyword arguments unless explicitly permitted.
- Python statements.
- `eval`, `exec`, `compile`, `open`, `__import__`.
- Huge exponents or unbounded expression depth.
- Matrix dimensions outside configured budgets.

Implementation method:

1. Tokenize and parse into a Python AST or a dedicated parser tree.
2. Walk the AST manually.
3. Check each node against an allow-list.
4. Check identifiers against declared symbols/functions/constants.
5. Enforce max source length, max AST nodes, max recursion depth and exponent bounds.
6. Construct SymPy expressions using explicit Python code that maps a validated node to a SymPy node.
7. Never evaluate the original string.

The safe parser must have a fuzz/property suite for malformed inputs and adversarial syntax. `sympify` may be used only on trusted internal expressions or already validated structures where the source provenance is clear.

## 4.2 Exactness and numerical precision

Do not silently convert exact expressions to binary floats.

Rules:

- Keep integers and rationals exact as long as possible.
- When decimal numeric evaluation is requested, record the precision.
- If a float is used, record dtype and relevant tolerance.
- Distinguish symbolic equality from numerical closeness.
- For interval/bounded output, show the bound source and how it was obtained.
- Do not label a float64 answer "exact".
- Report overflow, underflow, division by zero, invalid domains and non-convergence explicitly.

Use separate result flags:

```text
exactness:
  - symbolic_exact
  - integer_exact
  - rational_exact
  - floating_point
  - numerical_approximation
  - stochastic_estimate
  - unresolved
```

## 4.3 Independent verification

For supported operations, use at least one independent check:

- Differentiate known polynomials and compare to hand-derived fixtures.
- For symbolic differentiation, verify the difference simplifies to zero on a bounded set of test expressions.
- For numerical derivatives, compare finite-difference or high-precision references within declared tolerances.
- For ODEs, compare analytic solutions or a second integrator.
- For microprice, use a Decimal reference and invariant properties.
- For LLG, compare with known simplified cases and an external solver where model assumptions match.
- For Tor computations, compare to a known resolution and Macaulay2 output.
- For Lean proofs, run the local Lean compiler/kernel and record its exit status and toolchain hash.

A result returned by the same function that produced it is not an independent oracle.

---

# 5. HCSUDA adapter and capability-aware acceleration

## 5.1 First implementation must work without HCSUDA

The initial HCSEASYMATH Math Studio, ODE solver and scientific modules use CPU reference implementations.

Only connect to HCSUDA after inspecting its actual public API and crate boundaries. The currently observed HCSUDA repository state is a Rust workspace in `hcsuda/`; do not invent a Python import interface.

Possible adapter routes, to be decided by measurement:

1. A stable Rust library API exposed through a small C ABI.
2. A stable command-line JSON interface.
3. A local typed IPC interface, only if required by performance or process isolation.
4. A Python binding only if the ABI, packaging, lifetime and platform behavior are tested.

Do not call `cargo run` for every numerical operation in production. If a process boundary is required, use a supervised long-lived worker with typed requests and bounded queues.

## 5.2 HCSUDA selection rule

The HCSEASYMATH planner may select a GPU path only when all of the following match:

- Operation.
- Dtype.
- Dimensions / shape.
- Device identity.
- Driver identity/version.
- Required Vulkan features.
- Self-test evidence.
- Memory budget.
- Current runtime resource budget.

The selected path must appear in an explainable execution plan. Unknown or changed device/driver evidence is rejected. CPU reference remains available.

HCSUDA's existing H2d results prove specific GEMM paths on the measured Radeon 680M environment; they do not prove that symbolic mathematics, ODE solvers, LLG solvers, matrix exponentials, arbitrary SciPy operations or Macaulay2 workloads accelerate automatically.

Do not offload a tiny calculation to a GPU if host/device dispatch cost dominates. Benchmark wall time and device time separately.

## 5.3 Resource budget

Integrate with HSCL1's existing memory and AI governor rather than building a second OS-level governor.

Before starting a calculation estimate:

- Maximum symbol count and expression-tree nodes.
- Matrix/tensor dimensions.
- Expected memory.
- Plot grid size.
- Number of simulation steps.
- Worker count.
- GPU memory budget if selected.
- Disk artifact size.

For unknown-size computations:

- Apply a hard budget.
- Provide a cancel option.
- Return a typed `resource_limit` result.
- Preserve the application and desktop if the worker fails.
- Never kill unrelated processes.
- Do not use system swap as a hidden extension of VRAM.

---

# 6. Frontend and UX contract

## 6.1 Product experience

The UI must feel like a professional scientific workspace integrated into the HCS design system, not a generic admin dashboard.

Recommended primary information architecture:

1. **Home / Workspace** — recent runs, current backend status, recent experiments and shortcuts.
2. **Math Studio** — expression editor, symbols/assumptions, operation selector, symbolic result and numerical evaluation.
3. **Plots** — 2D/3D plot configuration, axes, domains, sample resolution, export.
4. **ODE Lab** — differential equation, initial conditions, solver selection, tolerances, trajectory and error panel.
5. **Spintronics Lab** — macrospin model, units, material parameters, LLG/SOT terms, solver, convergence and trajectory.
6. **Market Microstructure Lab** — order-book snapshot, imbalance, weighted midpoint and optional backtest explorer.
7. **Algebraic Geometry Lab** — modules, complexes, differentials and homology/Tor examples; mark experimental scope.
8. **Proof Desk** — Lean project selection, diagnostics, goals and proof status.
9. **Experiment Notebook** — run history, parameters, input hash, notes and exports.
10. **Agent Assistant** — local model status, suggestions, actions needing approval and MCP activity.
11. **Settings** — precision defaults, resource budgets, theme, language, runtime and optional backends.
12. **About / Sources** — licenses, upstream sources, version, source revision and limitations.

Do not show menu items for unimplemented domains as if they were ready. A roadmap card may say `Planned`, but it must be visually distinct from executable functionality.

## 6.2 First vertical slice layout

For desktop:

```text
┌────────────────────────────────────────────────────────────────────┐
│ HCSEASYMATH      Workspace   Math   Simulations   Proofs   Settings │
├──────────────┬────────────────────────────────┬────────────────────┤
│ Operations   │ Expression / Equation Editor   │ Variables & Scope  │
│              │                                │                    │
│ Differentiate│       rendered formula         │ x ∈ R              │
│ Integrate    │                                │ assumptions        │
│ Solve        │                                │ precision          │
│ Evaluate     │                                │ backend            │
│ Plot         │                                │                    │
├──────────────┴────────────────────────────────┴────────────────────┤
│ Result / Plot / Error / Steps / Provenance / Run History           │
├────────────────────────────────────────────────────────────────────┤
│ CPU: ready   Vulkan: optional/unverified   Jobs: 0   Offline: yes  │
└────────────────────────────────────────────────────────────────────┘
```

Use dockable/resizable panes only if the framework supports it accessibly. The initial UI should prioritize legibility over complexity.

## 6.3 UX requirements

- HCS tokens are the source of truth; support dark and light modes.
- German, English and French UI strings.
- Clear distinction between exact, approximate, estimated, unresolved and formally verified.
- Show assumptions and units beside results.
- Show solver name, method, precision and tolerances.
- Show resource estimates before expensive jobs.
- Show progress, cancellation and failure states.
- Do not hide mathematical errors in a generic red toast.
- Copy LaTeX, copy normalized expression, export CSV/JSON/PNG and save experiment where implemented.
- Keyboard navigation, visible focus, meaningful labels and screen-reader names.
- Reduced-motion preference.
- WCAG 2.2 AA contrast targets.
- Keyboard shortcuts never conflict with Plasma/HSCL1 shortcuts; document them.
- Responsive layout at 1366×768 and 1920×1080; test at a smaller viewport as well.
- No CDN, remote font, analytics or network-hosted script.
- Every button must perform a real action; no inert controls or demo chart values.

## 6.4 Three.js / WebGPU rendering rules

Use a pinned Three.js version, bundled locally by the frontend build. Evaluate `WebGPURenderer` and TSL for visualization, but implement a tested WebGL2 fallback. Three.js documents that WebGPU initialization is asynchronous and that the WebGPU renderer can fall back to a WebGL2 backend; it also documents current renderer limitations/experimental status. Do not make WebGPU a hard requirement for the app.

Rules:

- WebGPU is for visualization and selected client-side graphics, not the trusted numeric reference.
- Plot data comes from the backend with schema validation.
- A failed WebGPU initialization switches to WebGL2 or a 2D fallback with a clear status.
- A lost graphics context must not lose the experiment/run data.
- Provide a static or 2D mode for accessibility and low-power machines.
- Limit point counts and geometry sizes. Use downsampling or level-of-detail for very large outputs.
- Use deterministic screenshots in visual tests.
- Do not animate a static mathematical surface gratuitously.

---

# 7. HSCL1 OS integration

## 7.1 Debian package

Add a new package using the current convention:

```text
packages/debian/hscl-hcseasymath/
├── DEBIAN/
│   └── control
└── usr/
    ├── bin/
    │   └── hscl-hcseasymath
    ├── share/
    │   ├── applications/
    │   │   └── hscl-hcseasymath.desktop
    │   └── hscl/
    │       └── hcseasymath/
    │           ├── runtime.conf
    │           └── requirements-cp314.txt
```

The actual portable app source stays under `apps/hcseasymath/`; package source is the small OS shell.

Package rules:

- No maintainer script starts a service, launches a server or downloads packages.
- No root service or autostart entry.
- No large weights, training stack, Lean toolchain or external CAS included.
- The app is installed/run as the current user.
- Runtime venv and databases are under XDG user directories.
- Uninstalling the Debian package must not remove user experiments or user data.
- Runtime install is an explicit user command and shows estimated download size and destination.
- Hash-pin all downloaded wheels/artifacts where possible.
- Refuse unsupported Python versions rather than silently resolving a different lock.
- Before using Python 3.14, verify the base image still provides it.
- Do not hard-depend on `python3-venv` if it is not included in the current base image; report the missing package and provide a safe user instruction.
- Free-disk checks happen before downloads.
- A failed install removes only the temporary environment it created; it never removes a pre-existing environment.
- All package paths are validated; symlink/path traversal escapes are refused.

The package `Depends` should be minimal. Inspect the existing `hscl-cqhecs` control file and the current image packages to determine whether `python3` is the only required system dependency. Do not assume the `python3-venv` module exists.

## 7.2 Launcher contract

The launcher should expose explicit subcommands such as:

```text
hscl-hcseasymath doctor [--json]
hscl-hcseasymath install-runtime [--yes]
hscl-hcseasymath run
hscl-hcseasymath status
hscl-hcseasymath uninstall-runtime [--yes]
```

The exact names may be adjusted to avoid conflict with `hscl math`.

Requirements:

- `doctor` is read-only.
- `status` reports installed/not installed, engine availability, version and data directory.
- `install-runtime` shows package sizes, sources and hash verification before download.
- `run` starts the backend only for the logged-in user, checks health, starts the frontend and owns shutdown.
- `uninstall-runtime` removes only the app-owned runtime, never experiment data unless separately requested.
- Use fixed argument vectors, no shell expansion of user-controlled values.
- Use stable exit codes and document them.
- Provide machine-readable JSON mode.

## 7.3 `hscl` CLI namespace

Add a dedicated namespace after the app service contract stabilizes:

```text
hscl math status
hscl math doctor [--full]
hscl math engines
hscl math launch
hscl math runtime install --yes
hscl math runtime remove --yes
hscl math report --output <new-path>
```

`hscl math` must be a thin adapter to the app's supported commands/JSON API. It must not implement symbolic mathematics in Rust. Keep CLI docs generated or checked by the existing documentation generator.

Avoid creating command names that imply functionality not yet present. Only add a command after implementation and tests.

## 7.4 Control Center

Add a HCSEASYMATH integration card/page to the existing Qt 6/QML Control Center:

- Runtime installed / not installed.
- Backend not running / starting / running / failed.
- CPU mathematical engine status.
- Optional HCSUDA backend status with exact verified path count or reason unavailable.
- Optional Lean/Macaulay2/Sage status.
- Storage usage for experiments.
- Launch and stop actions.
- Links to documentation and limitations.

The page must call `hscl` through the existing `CliBackend` allow-list. Extend the allow-list with exact validated command shapes. Never invoke arbitrary user strings and never start a root process.

If the backend is not installed, the card must explain installation requirements and not pretend that calculations are available.

## 7.5 Desktop entry

Create a real `.desktop` launcher. It should start the normal user-owned application launcher, not a terminal command that prints success. Verify the desktop entry in a booted VM. Do not use `Exec=` values that inject shell code or untrusted paths.

## 7.6 Handbook and system docs

Add concise, complete EN/DE/FR handbook material:

- What HCSEASYMATH is.
- What the first version can and cannot do.
- How to install the optional runtime.
- How to launch and stop the application.
- Where data is stored.
- How to export and back up experiments.
- What local AI does and does not do.
- What happens if Vulkan/WebGPU/Lean/Sage/Macaulay2 is unavailable.
- How to uninstall the app while keeping data.
- Security and privacy notes.

Translations of security or destructive-action guidance require human/natural-language review before a release claim.

---

# 8. Upstream analysis and clean-room integration

## 8.1 Reverse engineering means inspect public interfaces and compare behavior, not copy blindly

The agent must study the following upstream projects to understand their architecture, data contracts, algorithms and tests. Reuse libraries through their supported APIs and licenses. Do not copy chunks of source code without a documented license/compatibility review. Do not decompile closed products, bypass DRM, scrape private APIs or use proprietary assets.

| Project | What to inspect | How HCSEASYMATH should use it |
|---|---|---|
| SymPy | expression trees, assumptions, simplification, calculus, parsing security, code generation | Primary symbolic math engine |
| SciPy | `solve_ivp`, integration methods, tolerances, sparse/numerical tools | Primary numerical solver/reference |
| SageMath | CAS interface, polynomial rings, ideals, exact arithmetic, optional backend model | Optional larger CAS adapter, not required in the first ISO |
| Macaulay2 | rings, modules, free resolutions, Tor, Ext, Betti tables, homological algebra | Optional DAG/homological algebra engine |
| Lean 4 + Mathlib | project structure, elaboration, kernel checking, theorem imports, build caching | Formal proof adapter |
| MathLive | math-field editor behavior and accessibility | Equation input |
| KaTeX / MathJax | TeX rendering, supported syntax, accessibility | Equation display |
| Three.js | WebGPU/WebGL2 renderer, TSL, controls, render lifecycle | Interactive visualization |
| OOMMF | reference problem definitions, macrospin/micromagnetic examples, output formats | Spintronics validation/comparison |
| Spirit | LLG, spin dynamics, micromagnetic/atomistic simulation modules and APIs | Compare scope and model output; adapt only through public API |
| MuMax3 | micromagnetic GPU architecture and benchmark problem definitions | Comparison target, not a Radeon/Vulkan dependency; its CUDA-oriented code is not a drop-in HSCL1 backend |
| HCSUDA | capability probe, planner contract, self-test evidence, dtype/shape restrictions and measured reports | Optional verified accelerated kernels |
| HCS Foundry | local model management, inference supervision, model metadata, existing MCP/API surfaces | Optional assistant provider; never start a duplicate inference server |

## 8.2 Source and algorithm review procedure

For each upstream project:

1. Record the exact URL, release/tag or commit SHA and review date.
2. Read its license file, not only a GitHub license badge.
3. Read its API documentation and examples.
4. Read relevant implementation and test files.
5. Record supported data types, units, numerical conventions and failure semantics.
6. Identify the smallest relevant capability.
7. Build a minimal reference experiment.
8. Compare HCSEASYMATH results to the upstream tool on a bounded common domain.
9. Record differences and known scope mismatch.
10. Do not port code until the license and dependency path have been reviewed.

A research note should contain:

```text
Question:
Upstream source and exact version:
License:
API surface:
Algorithm / mathematics:
Input/output types:
Units / conventions:
Reference example:
Observed result:
HCSEASYMATH adapter decision:
Compatibility risk:
Tests added:
What remains unknown:
```

## 8.3 License rules

- HSCL1 currently uses GPL-3.0-or-later. The in-tree HCSEASYMATH source must follow the root project's license and notice requirements until the owner explicitly decides otherwise.
- The later standalone repo must not silently change the license. The default recommendation is to retain GPL-3.0-or-later for a simple history-preserving extraction, unless the owner approves another compatible license after legal/dependency review.
- SymPy, NumPy, SciPy, FastAPI, React, Vite, Three.js, MathLive, KaTeX, Lean/Mathlib, Macaulay2, Sage, OOMMF, Spirit and any added component must be checked from their actual license files and pinned version.
- For every dependency, record runtime/dev/optional classification and license in a generated or maintained SBOM/dependency inventory.
- Do not copy code from MuMax3 or Spirit into HSCL1 without exact license review. An API adapter is preferable to source copying.
- Do not bundle a binary from an upstream project unless the distribution, redistribution terms, build provenance and hash are recorded.

---

# 9. Research links and reading order

Use the links below as starting points, not as a substitute for pinning the exact versions used by the code. Check the current documentation/releases at the time of implementation.

## 9.1 Symbolic and numerical mathematics

- SymPy documentation: https://docs.sympy.org/latest/
- SymPy parsing documentation: https://docs.sympy.org/latest/modules/parsing.html
- SymPy core expression model: https://docs.sympy.org/latest/modules/core.html
- SciPy reference: https://docs.scipy.org/doc/scipy/
- `solve_ivp` API and method guidance: https://docs.scipy.org/doc/scipy/reference/generated/scipy.integrate.solve_ivp.html
- NumPy documentation: https://numpy.org/doc/stable/
- SageMath documentation: https://doc.sagemath.org/
- SageMath project: https://www.sagemath.org/

## 9.2 Derived algebraic geometry / homological algebra

- Macaulay2 project: https://macaulay2.com/
- Macaulay2 documentation: https://macaulay2.com/doc/Macaulay2/
- Macaulay2 free resolutions: https://www.macaulay2.com/doc/Macaulay2/share/doc/Macaulay2/Complexes/html/_free__Resolution.html
- Stacks Project (algebraic geometry, homological algebra and derived topics): https://stacks.math.columbia.edu/
- Mathlib 4: https://github.com/leanprover-community/mathlib4

## 9.3 Formal verification

- Lean getting started: https://lean-lang.org/getting-started/
- Lean language reference: https://lean-lang.org/doc/reference/latest/
- Mathlib documentation: https://leanprover-community.github.io/mathlib4_docs/
- Lean project templates and examples: https://github.com/leanprover-community/mathlib4

## 9.4 Spintronics / SOT-MRAM

- OOMMF (NIST): https://math.nist.gov/oommf/
- Spirit spin simulation: https://github.com/spirit-code/spirit
- MuMax3: https://github.com/mumax/3
- Spin-transfer and spin-orbit torques in the LLG equation (2022): https://arxiv.org/abs/2207.12071
- 2026 finite-element SOT-MRAM modeling paper: https://www.nature.com/articles/s44306-026-00162-y
- 2026 numerical analysis of LLB with spin torques: https://doi.org/10.1051/m2an/2026028

## 9.5 Market microstructure

- Stoikov, The Micro-Price: A High Frequency Estimator of Future Prices: https://ssrn.com/abstract=2970694
- Stoikov microprice sample implementation/data: https://github.com/sstoikov/microprice
- Recent empirical discussion of microprice / imbalance: https://doi.org/10.1016/J.JFINECO.2021.04.018
- 2026 order-book imbalance analysis: https://doi.org/10.1007/s00780-026-00585-9

## 9.6 Frontend and visualization

- React: https://react.dev/
- Vite: https://vite.dev/guide/
- Three.js: https://threejs.org/docs/
- Three.js WebGPU renderer guide: https://threejs.org/manual/pages/webgpurenderer.html
- MathLive: https://mathlive.io/
- KaTeX: https://katex.org/docs/
- Playwright: https://playwright.dev/docs/intro
- axe-core: https://github.com/dequelabs/axe-core

## 9.7 API / MCP / security

- FastAPI: https://fastapi.tiangolo.com/
- FastAPI WebSockets: https://fastapi.tiangolo.com/advanced/websockets/
- FastAPI CORS: https://fastapi.tiangolo.com/tutorial/cors/
- MCP specification: https://modelcontextprotocol.io/specification/
- MCP transports: https://modelcontextprotocol.io/specification/2025-06-18/basic/transports
- MCP Python SDK: https://github.com/modelcontextprotocol/python-sdk
- Pydantic: https://docs.pydantic.dev/latest/
- SQLite: https://www.sqlite.org/docs.html
- OWASP ASVS: https://owasp.org/www-project-application-security-verification-standard/
- OWASP API Security Top 10: https://owasp.org/www-project-api-security/

## 9.8 Research handling

For each paper or external claim:

- Record publication date, venue, authors, DOI/arXiv ID and exact URL.
- Separate peer-reviewed results, preprints, software documentation and vendor claims.
- State the evaluation setting and hardware.
- Do not repeat a speed-up number without reproducing or carefully qualifying it.
- Record whether the project has independently reproduced the result.
- Keep a negative-results section; failed attempts are useful evidence.

---

# 10. Tests, proof obligations and benchmark design

## 10.1 Test pyramid

The agent must build a test pyramid:

1. Pure unit tests — fast, deterministic, no network, no GPU.
2. Property-based tests — invariants over many bounded random inputs.
3. Differential tests — compare independent implementations.
4. API/MCP integration tests — real schemas and lifecycle, isolated filesystem.
5. Frontend tests — component behavior and rendering state.
6. End-to-end tests — actual UI → local API → engine → result store.
7. Package tests — build/install/remove in a disposable root.
8. VM tests — install and run in a booted HSCL1 image.
9. Performance benchmarks — only after correctness gates pass.
10. Standalone extraction tests — clean checkout of the extracted repo.

Do not let a benchmark run before correctness tests pass.

## 10.2 Core mathematical test matrix

### Expression parser

Test:

- Valid expressions.
- Invalid tokens.
- Unknown symbols.
- Unsupported function names.
- Deeply nested operations.
- Huge exponents.
- Division by zero.
- Attribute access.
- Dunder names.
- Subscripts.
- Comprehensions.
- Lambda.
- Import syntax.
- F-strings.
- Unicode confusables where identifiers are supported.
- Very long inputs and AST node limits.

All invalid/adversarial syntax must be refused without executing code or crashing the service.

### Symbolic mathematics

Test:

- Polynomial derivatives.
- Chain rule.
- Product rule.
- Quotient rule.
- Trigonometric derivatives.
- Exponential and logarithmic derivatives in valid domains.
- Rational simplification.
- Exact rational arithmetic.
- Substitution.
- Factor/expand equivalence.
- Non-integrable or unresolved expressions.

### ODE

Test:

- Closed-form exponential decay.
- Harmonic oscillator.
- Simple logistic equation.
- Stiff test problem for method selection.
- Invalid initial conditions.
- Event handling if implemented.
- Tolerance and step-size convergence.
- Cancellation and timeout.

### Microprice

Test mathematical invariants listed in §3.2 and compare to an independent Decimal implementation.

### LLG/SOT-MRAM

Test:

- Unit magnetization vector input.
- Invalid zero vector.
- Field and torque unit validation.
- Norm drift.
- Time-step convergence.
- Damping-only behavior.
- Precession behavior.
- Sign convention.
- External reference example.

### Derived algebra

Test:

- Chain complex dimensions.
- \(d^2=0\).
- The Tor example in §3.4.
- A finite complex with known homology.
- Cross-check a bounded Macaulay2 result if installed.
- Correct refusal for unsupported ring/module types.

## 10.3 Property-based tests

Use Hypothesis or an equivalent property framework. Examples:

- Differentiating a constant yields zero.
- Differentiation is linear over supported expressions.
- A polynomial evaluated symbolically then numerically matches direct numeric evaluation within tolerance.
- Rational substitution preserves exact arithmetic.
- Plot sampling returns exactly the declared number of points unless values are explicitly invalid.
- Microprice remains in the bid-ask interval.
- Multiplying both queue sizes by a positive constant does not change microprice.
- LLG solver enforces or reports magnetization norm preservation.
- Homology calculation verifies \(d^2=0\).
- Job cancellation never reports `succeeded`.
- An API path outside the allowed artifact root is refused.

Fuzz the safe parser and JSON schemas with bounded resources. Preserve regression seeds.

## 10.4 Differential tests

Use at least two independent implementations when practical:

| HCSEASYMATH result | Independent reference |
|---|---|
| SymPy derivative | Hand-derived fixture / alternate symbolic check / numerical derivative |
| ODE trajectory | Closed-form solution / second SciPy method |
| Macrospin LLG | Published case / OOMMF or Spirit on matched equations |
| Microprice | Independent Decimal implementation |
| Tor groups | Hand-computed free resolution / Macaulay2 |
| HCSUDA kernel | Existing HCSUDA CPU oracle |
| Lean theorem | Lean kernel at a pinned toolchain |

A comparison only counts if both sides use the same assumptions, units, input normalization and problem scope.

## 10.5 Benchmark protocol

Every benchmark must record:

```json
{
  "schema_version": "hcseasymath.benchmark.v1",
  "benchmark_id": "...",
  "operation": "...",
  "input_digest": "sha256:...",
  "device": {
    "cpu": "...",
    "gpu": "...",
    "driver": "...",
    "os": "...",
    "memory_budget_bytes": 0
  },
  "software": {
    "hcseasymath": "...",
    "hcsuda": "...",
    "python": "...",
    "sympy": "...",
    "scipy": "..."
  },
  "configuration": {},
  "warmup_runs": 5,
  "measured_runs": 15,
  "median_ms": 0,
  "p95_ms": 0,
  "iqr_ms": 0,
  "peak_rss_bytes": 0,
  "gpu_time_ms": null,
  "correctness_gate": "pass",
  "notes": []
}
```

Benchmark requirements:

- At least 5 warm-up iterations for short kernels and enough warm-up for GPU clock stabilization.
- At least 15 measured repetitions for performance claims, unless a specific method justifies otherwise.
- Report median, p95 and spread/IQR; do not publish one cherry-picked timing.
- Record wall-clock and GPU timestamp time separately.
- Avoid running VMs and a local LLM during a GPU benchmark.
- Record AC/battery state and power mode if measurable.
- Record whether the iGPU shares DRAM with the CPU.
- Compare same-run baselines or a balanced run order.
- A regression >5% on a stable same-machine microbenchmark requires investigation, but noisy/incomparable numbers must be marked inconclusive rather than failed/successful.
- Never compare a GPU path against an intentionally single-threaded reference and market it as beating optimized CPU BLAS.
- Keep raw JSON evidence and a short interpretation.
- No benchmark score is a proof of asymptotic complexity.

## 10.6 Benchmark suites

Initial suites:

- `expr_parse`: safe parser throughput and refusal overhead.
- `symbolic_diff`: small/medium/large expression tree latency.
- `symbolic_simplify`: controlled family with bounded expression growth.
- `numeric_eval`: scalar and vector evaluation.
- `plot_sample`: 2D and 3D grid sizes.
- `ode_decay`: fixed analytic problem.
- `ode_stiff`: fixed stiff test.
- `llg_macrospin`: fixed model and convergence configuration.
- `microprice`: fixed batch of synthetic order-book states.
- `dag_tor`: small finite presentation examples only.
- `api_roundtrip`: UI/API/local service latency.
- `mcp_tool`: handshake and tool-call latency.
- `frontend_render`: startup and plot frame metrics on the supported GPU and fallback.
- `memory_budget`: peak RSS and artifact size.

Do not add large real-world financial datasets or sensitive user data to Git. Use synthetic fixtures or public datasets whose license permits redistribution.

---

# 11. UX and visual QA gates

The UI is accepted only when:

- Every primary route loads.
- Every implemented button has an observable result.
- Empty state explains how to start.
- Loading state is visible and cancellable.
- Failure state explains the failed calculation and preserves the input.
- Exact and approximate result labels are visible.
- Assumptions and units are displayed.
- Large calculations show resource estimates and cancellation.
- Keyboard-only navigation works.
- Focus is visible and not trapped incorrectly.
- Screen-reader names are present.
- Dark and light modes are readable.
- Reduced motion is respected.
- German and French strings do not overflow.
- No external network request is made by the UI in offline mode.
- WebGPU failure falls back without losing the run.
- No chart, metric or example result is presented as a real measured output unless generated by the current run.

Visual QA matrix:

```text
Viewports:   1366x768, 1920x1080, compact 1024x768
Themes:      HCS Midnight, HCS Light
Languages:   en, de, fr
States:      first-run, ready, running, success, error, unsupported, offline
Backends:    CPU-only, HCSUDA unavailable, WebGPU unavailable, WebGL2 fallback
Pages:       Workspace, Math Studio, ODE, Spintronics, Microstructure, Proof Desk
```

Take screenshots into `artifacts/`, not the Git repository, except for a small curated set approved for docs. Fix layout defects at the shared component/token level rather than patching individual pages.

---

# 12. Self-healing and autonomous development loops

The existing HSCL1 self-healing process remains the overall authority:

```text
OBSERVE
→ CLASSIFY
→ HYPOTHESIS
→ cheapest discriminating EXPERIMENT
→ smallest FIX + regression test
→ VERIFY (targeted → subsystem → full local gates)
→ RECORD (ledger + BUILD_LOG + CLAIMS where appropriate)
→ COMMIT
→ PUSH feature branch after green batch
```

Maximum three meaningful attempts per distinct failure hypothesis. After that, mark `BLOCKED`, include the exact reproducer, logs and next cheapest experiment. Never rerun the same command blindly, extend timeouts without a reason, weaken thresholds or turn a failing test into a skip.

## 12.1 Loop A — code/build repair

1. Capture exact failing command, exit code and log path.
2. Decide whether the failure is product code, test harness, environment, dependency drift or gate bug.
3. Write one falsifiable diagnosis.
4. Add a regression test that fails before the fix.
5. Apply the smallest patch.
6. Run focused tests.
7. Run the subsystem suite.
8. Run `forge check --strict`.
9. Inspect `git diff`.
10. Record the result and commit only after checking the command exit code.

## 12.2 Loop B — mathematical correctness

1. State the theorem/identity or numerical invariant.
2. List assumptions and units.
3. Construct the smallest counterexample candidate.
4. Test the implementation against the independent reference.
5. Minimize any mismatch.
6. Fix the mathematical implementation, not the expected answer.
7. Repeat property and differential tests.
8. Record the input hash, exact engine version and tolerance.
9. If the problem is outside supported scope, return `unresolved` or `unsupported`.

## 12.3 Loop C — numerical stability

1. Capture the baseline result and tolerance.
2. Vary solver, precision or step size.
3. Check convergence or error bounds.
4. Check NaN/Inf/overflow and boundary conditions.
5. Compare an independent solver.
6. Record the numerical error and the parameter region where the result is valid.
7. Do not suppress a warning merely to make the UI appear clean.

## 12.4 Loop D — frontend and UX

1. Reproduce the UI state at a fixed viewport.
2. Save screenshot and console/network logs.
3. Classify overflow, focus, localization, responsiveness, accessibility or data binding.
4. Add/adjust a Playwright test where possible.
5. Fix the shared component.
6. Rerun unit, accessibility and E2E checks.
7. Re-capture screenshots.

## 12.5 Loop E — performance

1. Confirm correctness and determinism first.
2. Establish baseline.
3. Change only one parameter family at a time.
4. Run enough repetitions to detect variance.
5. Compare medians and spread.
6. Record hardware, driver, power state and workload.
7. Promote a path only after measured improvement and correctness.
8. If the result is noisy or not faster, keep the prior path.

## 12.6 Loop F — packaging and OS integration

1. Build the `.deb` from a clean worktree.
2. Inspect package payload and maintainer scripts.
3. Install/remove in a disposable root or VM.
4. Check permissions, paths, desktop entry and data retention.
5. Run `hscl math doctor`.
6. Verify no listener or autostart process exists when the app is not launched.
7. Include the package in a dev ISO only after the package gate passes.
8. Boot the exact image and run guest tests.
9. Do not label a package `VM-VERIFIED` based on a package-root unit test alone.

---

# 13. Local gates and CI gates

## 13.1 Initial baseline commands

Before changing code, run the currently available repository gates exactly as documented:

```bash
python -m pytest tests -q
python scripts/forge.py check --strict
cargo fmt --all -- --check
cargo clippy --all-targets -- -D warnings
cargo test --all
```

Run the HCSUDA gates if the current masterplan requires them for the active batch:

```bash
cd hcsuda
cargo fmt --all -- --check
cargo clippy --workspace --all-targets -- -D warnings
cargo test --workspace
cargo run -p hcsuda-cli -- caps --json
cargo run -p hcsuda-cli -- selftest --json
```

Use the current command's actual help output. Do not assume flags that no longer exist.

## 13.2 New HCSEASYMATH local gates to implement

Add a script or documented command wrapper only after checking repository conventions. Suggested final gate surface:

```bash
# Python
python -m pytest apps/hcseasymath/tests -q
python -m ruff check apps/hcseasymath/backend apps/hcseasymath/tests
python -m mypy apps/hcseasymath/backend/hcseasymath
python -m pip check

# Frontend
cd apps/hcseasymath/frontend
npm ci
npm run lint
npm run typecheck
npm test -- --run
npm run build

# Package and OS integration
bash -n packages/debian/hscl-hcseasymath/usr/bin/hscl-hcseasymath
shellcheck -S warning packages/debian/hscl-hcseasymath/usr/bin/hscl-hcseasymath
scripts/build-deb.sh hscl-hcseasymath
python -m pytest tests/unit/test_pkg_hcseasymath.py -q
python -m pytest tests/unit/test_hcseasymath_in_image.py -q
```

Commands above are target gates, not permission to invent missing scripts. If a tool is not installed or a command is not yet implemented, add it intentionally and document the prerequisite. Do not report a non-existent check as passed.

## 13.3 HCSEASYMATH gate matrix

| Gate | Scope | Pass criterion |
|---|---|---|
| HM0 | Baseline | Current branch, clean/known worktree and root tests recorded |
| HM1 | Safe parser | Parser unit/property/fuzz suite passes; adversarial payloads rejected |
| HM2 | Symbolic core | Exact expected results and independent checks pass |
| HM3 | Numeric/ODE | Analytic reference and convergence gates pass |
| HM4 | Domain models | Each implemented domain's model contract and units pass |
| HM5 | API/jobs | Schema, error, cancellation, limits and process-lifecycle tests pass |
| HM6 | MCP | Handshake, tools/list/call, schema rejection, stdio cleanliness and permission tests pass |
| HM7 | Frontend | Typecheck, unit, accessibility, route and browser tests pass |
| HM8 | Package | `.deb` builds, installs, removes, preserves user data and starts only on demand |
| HM9 | HSCL1 Control Center | Real status from `hscl`, fixed command allow-list, accessible page |
| HM10 | Dev ISO | Image verifier checks package, launcher, no autostart and no unexpected listener |
| HM11 | VM | Boot exact dev ISO, launch app, run symbolic smoke, stop app, rerun guest checks |
| HM12 | Offline | No CDN or cloud call; user-selected installed runtime operates offline |
| HM13 | Performance | Reproducible benchmarks, no correctness regression; metrics saved as JSON |
| HM14 | Extraction | Clean standalone checkout builds/tests and its README accurately documents verified functionality |

## 13.4 Existing CI / cloud gates

Extend existing workflows; do not create duplicate CI pipelines without a concrete reason.

Inspect `.github/workflows/ci.yml`, `fuzz.yml` and `release.yml` in the current checkout. Add jobs/steps for:

- Python dependency lock and license check.
- HCSEASYMATH unit/property/security tests.
- Frontend lint/typecheck/unit/build.
- API/MCP integration tests.
- Debian package build and payload validation.
- HCSEASYMATH image gate tests.
- Existing Rust, QML, shell, license and dependency audit checks.
- Optional Vulkan tests only on a runner that actually exposes a Vulkan implementation; otherwise report `NOT RUN` or use a real CPU/lavapipe test for the supported subset.
- E2E browser tests on a supported runner.
- A clean-checkout build of the portable application after extraction.

Cloud status is not green merely because a required job was skipped. A skipped hardware-specific job is `NOT RUN`, not `PASS`.

## 13.5 Exact-image acceptance

The package is not considered part of HSCL1 until the exact development ISO passes:

1. Image build from a clean worktree.
2. `distro/live/verify-image.sh`.
3. UEFI QEMU boot.
4. In-guest CLI checks.
5. HCSEASYMATH package status.
6. Launch HCSEASYMATH from the desktop entry.
7. Perform an exact symbolic differentiation smoke test.
8. Verify CPU fallback.
9. Verify backend exits on app shutdown.
10. Verify no unexpected listening socket remains.
11. Verify the app did not autostart.
12. Verify package removal retains user experiment data.
13. Re-run the main guest QA checks.

Installer tests must use disposable virtual disks only. Do not install or repartition a real host machine.

---

# 14. Push, PR, merge and release discipline

## 14.1 Start from the actual repository state

At the beginning:

```bash
git status --short --branch
git remote -v
git log -10 --oneline --decorate
git fetch origin --prune
git status --short --branch
git ls-remote --heads origin main
```

Inspect untracked companion files and owner changes. Do not remove them. Do not assume the remote `main` is the same as a local `main`.

## 14.2 Feature branch

Use a dedicated branch from the current, verified base, for example:

```bash
git switch -c codex/hcseasymath-hscl1-first origin/main
```

If it exists, inspect it and continue safely. Do not reset it.

## 14.3 Commit and push checkpoints

Follow the active HCSUDA masterplan's checkpoint policy:

- Commit a coherent change only after the relevant local gates pass.
- Check the exit status of every gate; a tool output containing `PASS` is not enough if the process exit code is non-zero.
- Update `docs/BUILD_LOG.md`, the HCSEASYMATH execution log and relevant `docs/CLAIMS.md` rows.
- Push feature-branch checkpoints only after local gates are green and the repo credentials/permissions are valid.
- Never force-push or rewrite shared branch history.
- Never push directly to `main`.
- Keep one integration PR open at a time unless the active repo plan explicitly allows more.
- Refresh the PR description with the exact gate results, evidence paths and remaining risks.
- A failed cloud gate blocks the merge.
- A skipped cloud gate is not a pass.

The current remote connection used for the planning audit reported read access only. The coding agent must re-check its actual credential/permission state before any push. Do not claim a push succeeded unless GitHub confirms it.

## 14.4 Merge

Merge to `main` only when:

- All required local gates for the batch pass.
- Required cloud CI is green on the pushed SHA.
- The `.deb` builds.
- Package and image checks pass for any package/image change.
- Documentation and claims match the implementation.
- No new critical/high security finding remains unresolved.
- The PR has been reviewed.
- The active masterplan permits the merge.

Do not tag or publish a release merely because HCSEASYMATH is integrated. HSCL1 is still pre-alpha and its root release gates remain independent.

## 14.5 Standalone repository publication

Only after HM14:

- Re-check `timfromhcs/hcseasymath` existence.
- Confirm repository visibility, default branch, ownership and permissions.
- Use the license already chosen for the in-tree source unless the owner makes a documented license decision.
- Ensure all source files and tests have been extracted, not OS-specific files or build artifacts.
- Ensure source links, release versions and install instructions work.
- Build on a clean Linux checkout and a clean Windows checkout if cross-platform support is claimed.
- Run dependency, license and secret scans.
- Create a feature branch and PR or use the agreed initial-repository workflow.
- Push only when remote permissions and publication authorization are confirmed.
- Do not delete the source under HSCL1 until the new repository has been verified and the HSCL1 package is pinned to a real immutable release/tag.

---

# 15. Documentation and evidence

Maintain these documents as append-only or carefully versioned artifacts:

| File | Purpose |
|---|---|
| `docs/integrations/HCSEASYMATH.md` | What HSCL1 integrates, package state, current capabilities and limitations |
| `docs/integrations/HCSEASYMATH_AGENTS_SECTION.md` | Proposed text for root `AGENTS.md`; do not insert silently |
| `docs/research/HCSEASYMATH_BASELINE.md` | Starting commit, runtime/toolchain/hardware facts |
| `docs/research/HCSEASYMATH_RESEARCH_LEDGER.md` | Links, papers, upstream versions and review results |
| `docs/research/HCSEASYMATH_DECISIONS.md` | Append-only architecture decision records |
| `docs/research/HCSEASYMATH_BLOCKERS.md` | External blockers and next cheapest experiment |
| `docs/research/HCSEASYMATH_TEST_MATRIX.md` | All test suites and evidence |
| `docs/research/HCSEASYMATH_EXECUTION_LOG.md` | Per-session work and exact command results |
| `apps/hcseasymath/docs/LIMITATIONS.md` | App-specific limitations |
| `apps/hcseasymath/docs/BENCHMARKS.md` | Benchmark methodology |
| `apps/hcseasymath/docs/MATHEMATICAL_CONTRACTS.md` | Equations, assumptions, units, exactness and proof obligations |

Use HSCL1 status vocabulary in system documents:

- `PLANNED`
- `IMPLEMENTED`
- `TESTED`
- `VM-VERIFIED`
- `HARDWARE-VERIFIED`
- `EXPERIMENTAL`
- `BLOCKED`

Use a separate proof status inside HCSEASYMATH:

- `NOT_CHECKED`
- `NUMERICALLY_CHECKED`
- `SYMBOLICALLY_CHECKED`
- `EXTERNALLY_CROSS_CHECKED`
- `FORMALLY_VERIFIED`

Never map a mathematical status to an OS status without recording both. `HARDWARE-VERIFIED` means hardware execution and measurement on a named device; it does not mean a mathematical theorem has been formally verified.

## 15.1 Proof / Simulation Card

For each important scientific result, create a card:

```text
Question:
Mathematical model:
Source of model:
Exact equation:
Assumptions:
Units and sign conventions:
Input digest:
Engine and version:
Solver / method:
Precision and tolerances:
Independent reference:
Result:
Maximum error / residual:
Convergence evidence:
Formal proof status:
Hardware details (if relevant):
Limitations:
Reproduction command:
Artifact path:
```

A user must be able to reproduce an output without asking an LLM to reconstruct the original run.

---

# 16. Release and extraction roadmap

This roadmap is dependency-ordered. Do not jump to a later milestone because the UI mockup looks complete.

| Milestone | Deliverable | Exit gate |
|---|---|---|
| M0 | HSCL1 baseline and plan reconciliation | Current root gates green/recorded; active plan understood |
| M1 | HCSEASYMATH package foundation | Safe parser + health + capabilities + one exact derivative |
| M2 | Math Studio MVP | Differentiation, evaluation, plotting, result history |
| M3 | ODE lab | Exact-reference and convergence tests |
| M4 | Microprice and macrospin prototypes | Unit contracts and independent reference tests |
| M5 | DAG/homological algebra proof of concept | Tor example, complex checks, Macaulay2 cross-check |
| M6 | API/MCP and local storage | Typed schemas, local-only operation, no arbitrary code execution |
| M7 | Frontend and Control Center | UX gates, QML card, launcher, status from real CLI |
| M8 | HCSUDA adapter | Stable API, matching capability evidence, CPU fallback |
| M9 | Debian package | Clean install/remove, data retention, no autostart |
| M10 | Development ISO integration | `verify-image`, boot, guest E2E, offline smoke |
| M11 | Release candidate integration | Required local and cloud gates green; docs/evidence complete |
| M12 | Standalone extraction | HM14 clean checkout and license audit pass |
| M13 | Standalone repo publication | Repository created/pushed only with permission; README and CI verified |

The first user-visible milestone should be M2 or M3, not M13. The project becomes real when an HSCL1 user can launch it and complete a correct, reproducible calculation.

---

# 17. First actions for the coding agent

Do the following in order:

1. Read root `AGENTS.md`.
2. Read the current active HCSUDA masterplan and latest self-heal plan.
3. Run `git status`, fetch remote and record the actual base commit.
4. Confirm HCSUDA H2d from the exact merged source and evidence; reconcile stale HCSUDA docs separately.
5. Inspect `hscl-cqhecs` package and tests.
6. Inspect `hscl` command and MCP registry.
7. Inspect the Control Center allow-list and QML page patterns.
8. Run baseline local gates and save output.
9. Add the HCSEASYMATH integration plan and research ledger.
10. Create `apps/hcseasymath/` and implement only Phase 1.
11. Add one API integration test and one UI E2E smoke test.
12. Build the package shell after the runtime contract is proven.
13. Extend the existing CI and image gates.
14. Run the exact ISO VM acceptance before claiming OS integration.
15. Continue domain modules one at a time.
16. Do not create the standalone repository until the extraction gate passes.

---

# 18. Definition of done

HCSEASYMATH is considered **integrated into HSCL1** only when:

- Its portable source is present under the agreed in-tree boundary.
- The app starts on a clean HSCL1 installation or documented supported base.
- CPU-only mode works.
- At least one exact symbolic operation is end-to-end tested.
- The UI shows actual backend results.
- The local API is loopback-only and uses safe origin/access controls.
- MCP tools are typed, limited and tested.
- No arbitrary user code is executed.
- The local storage is user-owned and removable without data loss.
- The Debian package builds and installs/removes in a disposable environment.
- The Control Center and `hscl` show truthful runtime state.
- The package appears in the dev ISO and passes image verification.
- The exact dev ISO boots in a disposable VM and the application is exercised there.
- No unapproved listener, service or autostart process exists.
- Benchmarks have raw, reproducible evidence and no unsupported performance claims.
- README, docs, evidence ledger and limitations describe only what is implemented and tested.
- Existing HSCL1 gates remain green.
- All new code, dependencies and assets pass license and secret scans.

HCSEASYMATH may be extracted to its own repository only when the above is true and:

- The app source is portable and cleanly separated from HSCL1 integration.
- A clean checkout can build and run the app without the HSCL1 tree.
- Standalone tests pass.
- Its README and AGENTS.md accurately describe the actual verified feature set.
- License and dependency compatibility are documented.
- HSCL1 package integration can pin the standalone commit/tag.
- GitHub repository permissions and publication path are confirmed.

Until then, the source of truth is the HCSEASYMATH subtree inside HSCL1.

---

# 19. Source notes and important distinctions

The following sources informed the architecture and should be re-checked when the implementation begins:

1. SymPy parsing documentation warns that `parse_expr` uses `eval` and must not receive unsanitized input: https://docs.sympy.org/latest/modules/parsing.html
2. SciPy `solve_ivp` documents solver choices and tolerances: https://docs.scipy.org/doc/scipy/reference/generated/scipy.integrate.solve_ivp.html
3. Stoikov's microprice work defines the microprice through an expected future midpoint framework; the simple queue-size-weighted midpoint is not the full estimator: https://ssrn.com/abstract=2970694
4. The 2026 LLG/LLB numerical analysis paper studies numerical schemes for spin-torque magnetization dynamics; it is a reason to state the model and discretization, not to claim the current demo is validated: https://doi.org/10.1051/m2an/2026028
5. A 2026 SOT-MRAM finite-element paper couples charge/spin drift-diffusion and LLG dynamics; this is much more detailed than a constant-field macrospin animation: https://www.nature.com/articles/s44306-026-00162-y
6. Three.js WebGPURenderer provides a WebGL2 fallback but remains subject to compatibility and renderer limitations; initialization is asynchronous: https://threejs.org/manual/pages/webgpurenderer.html
7. FastAPI CORS documentation explains explicit origin allow-lists; do not use a wildcard for a credentialed local control API: https://fastapi.tiangolo.com/tutorial/cors/
8. MCP stdio transport requires protocol messages on stdout and permits logs on stderr: https://modelcontextprotocol.io/specification/2025-06-18/basic/transports
9. Lean 4: https://lean-lang.org/getting-started/
10. Mathlib: https://github.com/leanprover-community/mathlib4
11. Macaulay2: https://macaulay2.com/
12. SageMath: https://www.sagemath.org/
13. OOMMF: https://math.nist.gov/oommf/
14. Spirit: https://github.com/spirit-code/spirit
15. MuMax3: https://github.com/mumax/3
16. MathLive: https://mathlive.io/
17. KaTeX: https://katex.org/docs/
18. Playwright: https://playwright.dev/docs/intro

The agent must add any new source it discovers to `docs/research/HCSEASYMATH_RESEARCH_LEDGER.md` with date, version, license, relevance, limits and test plan. A link alone is not evidence that a tool was installed, used or independently validated.
