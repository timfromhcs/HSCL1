# Proposed section for `AGENTS.md` - not inserted

Status: **proposal, awaiting the owner's approval.** `AGENTS.md` is the owner's contract; the HCSWaver master plan asks for a section like the one below, but nothing was added to `AGENTS.md`.

---

## HCSWaver Scientific Workstation Integration (proposed text)

- HCSWaver is a separate application with its own repository. HSCL1 integrates it as a normal unprivileged desktop application; no root service, no boot-time daemon, no network listener until the user starts a workflow, loopback only.
- Packages follow `packages/debian/` conventions and the rules of the Genesis companion file: small shells, no model weights, solvers, Lean toolchains or benchmark sets in the ISO, no network in maintainer scripts, user data under XDG, removal keeps user data.
- Shared adapters: `hscl-cqhecs` (and a future Foundry adapter) are the only way HCSWaver and Genesis reach CQ-HECS and Foundry; neither starts its own SAT stack or llama-server.
- Status vocabulary: HSCL1 documents use PLANNED / IMPLEMENTED / TESTED / VM-VERIFIED / HARDWARE-VERIFIED; HCSWaver's FORMALLY-VERIFIED applies only to proofs accepted by a named checker for a named theorem and revision.
- Acceptance for the integration: the package builds through `scripts/build-deb.sh`, installs and removes in a disposable VM, CPU-only smoke test passes, Foundry/Vulkan/Lean absence is handled honestly, no new listening socket, image gates in `verify-image.sh` pair every added package, and the exact ISO has booted before any "VM-VERIFIED" label.
- Claims about SAT results, proofs, GPU acceleration, or P vs NP are made only with the evidence the HCSWaver master plan requires; HSCL1 docs never state them on its behalf.
