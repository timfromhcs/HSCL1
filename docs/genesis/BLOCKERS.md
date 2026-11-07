# Genesis blockers (append only)

| Date | Blocker | Evidence | Next experiment |
|---|---|---|---|
| 2026-11-07 | No terminal path into an installed HSCL1 system (Workshop is inert by design), so `hscl-cqhecs install-runtime` cannot be run inside an installed image | the installs in `artifacts/install-0.1.3-alpha.0/` were driven by screenshots only | run the same launcher in a QEMU guest through a deliberately enabled Workshop in a *test* image, never in the release image |
| 2026-11-07 | `python3-venv` is not in the live ISO; offline runtime install on the live ISO is impossible | pristine root: `python3-venv` not installed, no `ensurepip` | measure the size of `python3-venv` and its dependencies before deciding to add them |
| 2026-11-07 | No local clone of hcs-foundry; licence reads `NOASSERTION` on GitHub | `gh api`; the file says MIT | shallow clone exists under `C:\AI\work\hcs-foundry`; read its service, ports and MCP tools next |
| 2026-11-07 | `timfromhcs/hcswaver` does not exist; creating a public repository is the owner's decision | `gh repo view` -> 404 | none until the owner says to create it |
| 2026-11-07 | Foundry has no text-generation MCP tool or documented generation API | `mcp_server.py` tool list | read `runtime/llama_server.py` and `api/` for an internal interface; propose a narrow typed adapter or upstream tool |
| 2026-11-07 | No `lean4` package in Ubuntu 26.04; Lean toolchains need `elan` and the network | `apt-cache policy lean4` empty | treat Lean as a first-run download on explicit action, never in the ISO |
| 2026-11-07 | Inserting the HCSWaver section into `AGENTS.md` needs the owner's approval | masterplan 1.4 vs the owner's contract | proposal file written |
