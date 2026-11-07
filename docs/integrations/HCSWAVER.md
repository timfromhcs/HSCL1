# HCSWaver on HSCL1 - integration status

**Status: PLANNED. Nothing of HCSWaver is installed or shipped by HSCL1 today.** This page records what HSCL1 will own, what exists upstream, and what has been checked. It is not a feature description.

## What HCSWaver is (per its master plan)
A standalone, local-first workstation for SAT/reduction experiments with checked proofs. It is a research tool; it does not claim to settle P vs NP. Its own repository, `timfromhcs/hcswaver`, **does not exist yet** (checked 2026-11-07).

## What HSCL1 will provide
Packages, a launcher, read-only status commands, a Control Center card, handbook pages in English, German and French, and image checks. Never: root services, boot-time daemons, model weights, Lean toolchains or benchmark corpora in the image.

## What exists today that it will build on
| Piece | State on HSCL1 | Evidence |
|---|---|---|
| `hscl-cqhecs` (CQ-HECS launcher, runtime installed on demand from a SHA-256 pinned file) | in the 0.1.3-dev2 development image; install of the runtime verified once on Ubuntu 26.04 / Python 3.14 outside HSCL1 | `docs/genesis/EXECUTION_LOG.md`, `docs/BUILD_LOG.md` |
| Foundry adapter | none | `docs/genesis/BASELINE.md` |
| Control Center card, `hscl` commands for HCSWaver | none | - |

## Upstream facts checked on 2026-11-07
- CQ-HECS 5.0.0 (Apache-2.0) has SAT code (`sat.py`, `sat_external.py`, `drat.py`, an OMNIWAVE engine) and an MCP server; exact APIs not yet read.
- HCS Foundry 7.5.0 (MIT) exposes an MCP server over stdio (protocol 2025-06-18) with machine, model, dataset and training tools; it has **no text-generation MCP tool**. Generation is internal to Foundry (llama.cpp supervision), so a typed adapter or an upstream tool is needed.
- Ubuntu 26.04 archive: `kissat` 4.0.3, `cadical` 2.1.3, `drat-trim` (git 2024-04-28), `elan` 4.1.2, `libwebkit2gtk-4.1-0` 2.52.6. There is no `lean4` package: Lean toolchains are fetched by `elan` on explicit user action.

## Known limits of this page
Package names, command names and the Control Center design are open until a real `.deb` of HCSWaver exists and its conventions are read from code. See the plan `docs/superpowers/plans/2026-11-07-hcswaver-integration.md`.
