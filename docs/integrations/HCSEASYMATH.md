# HCSEASYMATH inside HSCL1

Status: **PLANNED**. No application code exists yet. This page is the boundary
description; the execution order is in
`docs/superpowers/plans/2026-11-08-hcseasymath-plan.md` and the owner contract is the
untracked `AGENTS_HCSEASYMATH_HSCL1_FIRST.md`.

## What it is

A local mathematical and scientific workbench: safe expression entry, exact symbolic
operations (SymPy), numerical evaluation and ODEs (NumPy/SciPy) with declared precision,
plots, and saved experiments with provenance. A language model may help phrase a
question; it is never the calculator and never decides whether a result is true.

## Boundary

| Owned by | Pieces |
|---|---|
| `apps/hcseasymath/` (portable) | parser, symbolic/numeric engines, domain modules, local API, frontend, schemas, tests |
| HSCL1 (OS integration) | `hscl math ...` CLI namespace, typed MCP tools in `hscl mcp`, Control Center card, `hscl-hcseasymath` Debian package, desktop entry, handbook, image gates |
| HCSUDA (optional) | verified kernels, used only through its planner when evidence matches the device; the first slice does not need it |
| HCS Foundry (optional) | local model assistance; never required |

Not in the app: its own GGUF parser or model runtime, a second MCP server, a second
theme system, a root service, a cloud call, an autostarted listener.

## Safety properties that will be tested, not asserted

1. No `eval`/`exec`/`sympify` on user text; hostile-input corpus refused (E2).
2. Every operation runs in a killable worker with time and memory limits.
3. Loopback only, `Host`/`Origin` validated, per-launch token, no wildcard CORS, no listener after exit (E5).
4. An `unresolved` or `unsupported` mathematical result is never reported as success.
5. Numerical output always names precision, solver and tolerance; symbolic output names the engine.

## Known limits (today)

Nothing is implemented. The research gaps that block later modules are listed in
`docs/research/HCSEASYMATH_BLOCKERS.md`.
