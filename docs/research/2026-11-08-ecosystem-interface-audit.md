# Ecosystem integration interfaces — source audit 2026-11-08

Status: source-inspected only; no scientific/GPU/training/runtime claim follows from this audit. Owner now authorizes related-repository updates/pushes. Current task reuses existing interfaces instead of creating duplicate trainers, daemons or products. No Qwen Mythos/cloud inference.

## Pinned source observations

- HCS Foundry main `cfea6fab4ea4bd0ffb1517dc59e98a80f830096a`: `server/pyproject.toml` version7.5.0, Python>=3.11. Existing `foundry run doctor`, models, train plan/run/doctor and MCP serve; HTTP default loopback8770 with x-foundry-token pairing. `server/foundry/mcp_server.py`, `security.py`, `gateway.py` own these interfaces. Optional Vercel teacher gateway stays off for local model work.
- HCS Discovery Studio main `fdd6ccb7a58fb63313ce2ec928f1234c022fb813`: root pyproject version3.0.1, Python>=3.12,<3.14. Existing `hcs-discovery doctor`, serve and MCP serve, read-only doctor/model-list tools; API health/ready/diagnostics/OpenAPI already exist. Loopback8787 default; non-loopback requires HCS_API_TOKEN. Source: `src/hcs_discovery/{mcp_server.py,core/config.py}`.
- LocalAI Gateway main `74c500bc64e3b3c1f61866a778c02ade9993c200`: package0.5.0, Python>=3.13, loopback8090. Existing OpenAI-compatible routes, doctor, placement/autotune and MCP transport. `src/localai_gateway/{app.py,exposure.py}` have no HTTP authentication; public binding requires an explicit override. Do not expose it as a Miner LAN receiver.
- HCS Neural Foundry main `4635ac2018a35d3f0628154038fe29eb7d906911`: package0.2.0, Python>=3.11,<3.14. Existing CLI/API/MCP service layer in `python/hcs_foundry/{services.py,api.py,mcp_server.py}`. API bearer authentication and compute/write approvals exist; API default8765 needs port coordination. Health route at this revision hard-codes0.1.0 and exposes workspace path without auth; a separate regression-backed follow-up is underway, not assumed fixed here.

## Concrete integration constraints

1. Foundry and Neural both declare Python distribution name `hcs-foundry` despite distinct import packages/CLI. They require separate pinned environments; never co-install into one venv.
2. Discovery/Neural explicitly exclude Python3.14, the Ubuntu26.04 runtime. Use a tested compatible isolated runtime; do not erase package bounds without evidence.
3. Studio/Neural/proposed Miner8765 can overlap. Set explicit endpoints and test actual bind addresses; source defaults are not a conflict-free port allocation.
4. Probe the chosen provider's existing read-only doctor/MCP contract at a pinned revision before adding HSCL1 adapters. Treat unknown/missing/error as such; source inspection cannot certify an installed service, scientific result, model compatibility or acceleration.

Sources are the named files at immutable revisions in the owner's repositories: [Foundry](https://github.com/timfromhcs/hcs-foundry/tree/cfea6fab4ea4bd0ffb1517dc59e98a80f830096a), [Discovery](https://github.com/timfromhcs/hcs-discovery-studio/tree/fdd6ccb7a58fb63313ce2ec928f1234c022fb813), [Gateway](https://github.com/timfromhcs/local-ai-backend/tree/74c500bc64e3b3c1f61866a778c02ade9993c200), [Neural](https://github.com/timfromhcs/hcs-neural-foundry/tree/4635ac2018a35d3f0628154038fe29eb7d906911).
