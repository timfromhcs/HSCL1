# HCSPNP inside CQ-HECS and HSCL1

Status: **PLANNED**. HCSPNP is not a product and not a repository (`timfromhcs/HCSPNP` returns 404). It is a set of
solver, proof, counting and UI improvements delivered through two existing projects. Owner contract:
`AGENTS_HCSPNP_HSCL1_LATEST.md` (untracked). Plan: `docs/superpowers/plans/2026-11-08-hcspnp-plan.md`.

## Who owns what

| Part | Owner | Today |
|---|---|---|
| SAT engines, #SAT separator, DRAT checker, portfolio (`hcs.sat.unified.v1`), Studio, `hcs.run.v2`, CQ-HECS MCP | `timfromhcs/CQ-HECS` (Apache-2.0) | exist; engines are not equally trustworthy, each result carries its proof status |
| Launcher `hscl-cqhecs`, desktop entry, runtime pin, ISO and image gates | HSCL1 `packages/debian/hscl-cqhecs/` | status launcher only; **the desktop entry does not open the Studio** |
| `hscl cqhecs ...`, typed MCP tools in `hscl mcp`, Control Center card | HSCL1 | do not exist |
| Vulkan compute | CQ-HECS has its own BCP path; HCSUDA is an optional second source, used only with evidence | no HCSUDA SAT kernel exists |

## What the results mean

| Output | Meaning | Not meant |
|---|---|---|
| `SAT` | a model, re-verified against the original CNF | - |
| `UNSAT` + certificate | the engine's proof was accepted by an independent in-repo checker | a competition-grade or formally verified proof |
| `UNSAT`, no certificate | exhaustive search by the `watched` engine | proven in a checked sense |
| exact count | produced by a complete exact algorithm within its budget | an approximation, or a partial count |
| `UNKNOWN` | budget, width or memory limit reached | "probably UNSAT" |

## Known security gap (upstream)

The Studio's local HTTP server (`cq-hecs studio`, 127.0.0.1:8765 by default) performs no Host, Origin or token check; its POST
endpoints start solver jobs. Until that is fixed upstream and the runtime pin is raised, HSCL1 does not start the Studio from a
desktop icon. See `docs/research/HCSPNP_DECISIONS.md` P2.

## Not claimed

No statement about `P = NP`. No learned model, tensor network, Vulkan kernel or amount of memory is claimed to solve NP-complete
problems in general. No "SSD as VRAM". No speed-up is claimed from a paper or a capability flag.
