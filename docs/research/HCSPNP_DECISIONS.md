# HCSPNP decisions, gaps and blockers

Source of each decision: `HCSPNP_RESEARCH_LEDGER.md`. Status vocabulary as in the root `AGENTS.md`.
Honesty line carried over from the contract: nothing here supports a claim about `P = NP`, a general
polynomial algorithm for NP-complete problems, or "SSD as VRAM".

## Decisions

| ID | Decision | Why | Proof (planned) | Status |
|---|---|---|---|---|
| P1 | HCSPNP is a feature family of CQ-HECS (solver logic, Studio, `hcs.run.v2`) and HSCL1 (launcher, CLI, MCP, package, image). No new repository, GUI, package, daemon, MCP server or model runtime. | Contract 0.1 and 2.3; `HCSPNP` is 404. | Review checklist per PR: "what existing file does this extend?" | IN FORCE |
| P2 | **The Studio guard comes before any launcher that starts the Studio.** The Studio's HTTP server has no Host/Origin/token check, so a desktop icon that starts it would expose unauthenticated solver endpoints to every web page the user visits. The fix belongs upstream in CQ-HECS (`cqhecs/studio/app.py`). | Ledger stage 1, source lines 945-1085 at `30c7f14`; contract section 13. | Tests in CQ-HECS: foreign Host 400, foreign Origin 403, missing token 401, `text/plain` POST refused, OPTIONS gets no CORS headers. | PLANNED (needs B-P1) |
| P3 | Until P2 ships, the desktop entry stays status-only and the docs say so. After P2 the launcher gets a `studio` subcommand (port 0, `--no-browser`, opens the printed URL with the token fragment) and `Terminal=false`. | Contract 12.1; honest current state. | `tests/unit/test_pkg_cqhecs.py` extended (argv, paths, no shell), then live and installed VM. | PLANNED |
| P4 | CaDiCaL stays optional. If wanted in the OS runtime, add `python-sat` as a **separate, hash-pinned, explicitly confirmed** step (`install-runtime --with-sat`), showing its size (4.1 MB wheel + `six`). No floating `dev` pin. | A cp314 wheel resolves (ledger stage 3), but it is a development release and the default CaDiCaL version is unread. | Read the installed module; `unified.capabilities()` shows `cadical: available`; proof still goes through `cqhecs.drat`. | PLANNED |
| P5 | Vocabulary for UNSAT: certified only when an independent checker accepted that engine's proof (`scan` tree-resolution, `omniwave` and `cadical` through `cqhecs.drat`); `watched` UNSAT is "exhaustive search, no certificate". The in-repo DRAT checker is **not** competition-grade: SAT Competition 2025 checks with dpr-trim, GRAT or VeriPB. No competition claim. External checkers may be added later as optional adapters for a second opinion. | Contract section 4; ledger stage 3. | M2 tests: no UI or API string says "certified" for an unchecked UNSAT. | PLANNED |
| P6 | Learned guidance follows the RLAF shape only: a model outputs **variable weights and polarities** for an existing solver's branching; it never decides SAT/UNSAT. Opt-in, off by default; the baseline must reproduce without a model. No speed claim from the paper (">2x in some cases", abstract only). | Ledger stage 3. | A/B on a held-out instance family with seeds and hardware recorded; negative results kept. | PLANNED (M4) |
| P7 | Tensor-based counting is research: `T_dense`/`T_sparse` are theory without a checker, so a tensor backend cannot claim "proof-checked counts". First task is a width-aware comparison against the existing separator (induced width of bucket elimination relates to treewidth). | Ledger stage 3. | M5: exact agreement with brute force and the separator on small families; refusal beyond the budget. | PLANNED (M5) |
| P8 | External exact counters (Ganak, D4, sharpSAT-TD) are references, not dependencies. Their 2025 numbers (1 h, 31 GB per instance) are not reproducible on this laptop; we compare on scaled limits and say so. | Ledger stage 3. | Benchmark protocol records solver version, limits, seeds, hardware. | PLANNED |
| P9 | **File ownership across tracks.** `cli/hscl/`, `apps/control-center/`, `distro/live/verify-image.sh`, `scripts/remaster-iso.sh`, `packages/debian/` are edited by one track at a time. The holder is written in the self-heal ledger as `LOCK: <track>`; a track that needs a locked file waits or works elsewhere. | Contract section 1.4 (parallel HCSEASYMATH work). | Ledger shows at most one LOCK per file group. | IN FORCE |
| P10 | A pull request into `timfromhcs/CQ-HECS` is an outward action in another repository. The agent prepares the change in a local clone and **does not push it** until the owner agrees. | Authorisation so far covers HSCL1. | `git remote -v` of the clone shows no push; branch exists only locally. | IN FORCE |
| P11 | The Ecosystem Master priority list P0-P14 governs the order of all work; this file's decisions keep their numbers. The live ledger is the only place that lists the order. | Master 7 and 8.5. | Ledger section 3 maps every milestone to a Master P-number. | IN FORCE |
| P12 | Merge policy: merge to `main` only when every CI check is green, as a merge commit, never forced, never a release or tag. This is read as the standing owner instruction that Master rule 17 requires. Pushes into other repositories stay forbidden without approval (P10). | Owner request ("main merge" and the standing ping text: merge only on green CI) and Master rules 16-17. | Each merge is reported with its check count. | IN FORCE |

## Gaps found (with their files)

1. Desktop entry runs `doctor` only (`packages/debian/hscl-cqhecs/usr/share/applications/hscl-cqhecs.desktop`).
2. No `hscl cqhecs` command, MCP tool or Control Center card.
3. Studio has no Host/Origin/token protection (CQ-HECS `cqhecs/studio/app.py`).
4. `python-sat` (CaDiCaL) is not in the OS runtime pin.
5. CQ-HECS `docs/UNIFIED_SOLVER.md` says "<3.14", contradicting `pyproject.toml` and the 3.14 runtime pin.
6. CQ-HECS suite never run from a clean checkout by this project.
7. The hardware bridge answers early POST rejections without draining the body (platform-dependent connection resets; fixed only in a local clone).
8. `src/sat_solver.cpp` (native) is unaudited; contract section 23.1 forbids listing it as a capability until audited.

## Blockers

| ID | Item | Type | Next step |
|---|---|---|---|
| B-P1 | Owner approval to open PRs in `timfromhcs/CQ-HECS` | owner | prepare the Studio guard patch locally; ask when it is green |
| B-P2 | CQ-HECS suite result | **answered 2026-11-08** | 2739 passed, 1 failed (real bridge defect, local fix prepared), 110 skipped; see `HCSPNP_BASELINE.md` |
| B-P3 | Which CaDiCaL `python-sat 1.9.dev21` provides | **answered 2026-11-08** | the adapter pins `SOLVER_NAME = "cadical195"` (CaDiCaL 1.9.5); `Solver(name="cadical195", with_proof=True)` returned UNSAT with a 3-line proof on Python 3.14.4 |
| B-P4 | RLAF code and benchmark tables | research gap | read the paper body before designing M4 |
| B-P5 | Does `hscl-cqhecs run -- studio` work on an installed system | unverified | VM test after P-M1; one heavy job at a time |
| B-P6 | `hcs-foundry` interfaces | not inspected | only if M4 needs a model host |
| B-P7 | Licences of optional external checkers (dpr-trim, gratgen, veripb, cake_lpr) | unread | read before any adapter |
