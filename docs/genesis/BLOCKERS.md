# Genesis blockers (append only)

| Date | Blocker | Evidence | Next experiment |
|---|---|---|---|
| 2026-11-07 | No terminal path into an installed HSCL1 system (Workshop is inert by design), so `hscl-cqhecs install-runtime` cannot be run inside an installed image | the installs in `artifacts/install-0.1.3-alpha.0/` were driven by screenshots only | run the same launcher in a QEMU guest through a deliberately enabled Workshop in a *test* image, never in the release image |
| 2026-11-07 | `python3-venv` is not in the live ISO; offline runtime install on the live ISO is impossible | pristine root: `python3-venv` not installed, no `ensurepip` | measure the size of `python3-venv` and its dependencies before deciding to add them |
| 2026-11-07 | No local clone of hcs-foundry; licence reads `NOASSERTION` on GitHub | `gh api`; the file says MIT | shallow clone exists under `C:\AI\work\hcs-foundry`; read its service, ports and MCP tools next |
