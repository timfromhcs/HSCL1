# HCSPNP research ledger

Companion to the owner contract `AGENTS_HCSPNP_HSCL1_LATEST.md` (German, untracked, 1205 lines) and
`docs/superpowers/plans/2026-11-08-hcspnp-plan.md`. Method as asked: **first the repositories, then web
search, then crawling of the primary sources**. Every row says what it shows and what it does not.

Review date: 2026-11-08. Repositories read through `gh api` (CQ-HECS `main` = `30c7f1484af01cf71a8843cca56ff38786eeaf92`,
2026-11-02 17:44 UTC) and the local HSCL1 tree. Web pages read through the Firecrawl MCP (search, then `scrape`
with targeted questions on the primary page or PDF).

## Stage 1 - repositories

| Question | Finding | Evidence | Limits |
|---|---|---|---|
| Does `timfromhcs/HCSPNP` exist? | No (HTTP 404), matching the contract. HCSPNP is treated as a feature set of CQ-HECS and HSCL1. | `gh api repos/timfromhcs/HCSPNP` | State of 2026-11-08. |
| What does HSCL1 ship for CQ-HECS? | A shell package only: `packages/debian/hscl-cqhecs/` with `DEBIAN/control`, `usr/bin/hscl-cqhecs`, one `.desktop`, `runtime.conf`, `requirements-cp314.txt`. No `hscl cqhecs` CLI command (no match in `cli/hscl/src/*.rs`), no Control Center card (no match in `apps/control-center`). | `find`, `grep` on the tree | Tests and image gates were listed (`tests/unit/test_pkg_cqhecs.py`, `test_cqhecs_in_image.py`, `verify-image.sh`) but not yet re-read line by line. |
| Does the desktop entry open the Studio? | **No.** `Exec=hscl-cqhecs doctor`, `Terminal=true`: it prints runtime status. The launcher offers `doctor`, `run -- <args>`, `install-runtime`, `uninstall-runtime`; the runtime is a venv built on demand from a hash-pinned file (CPython 3.14, 64.5 MB download, 1 GiB free space required). | `usr/share/applications/hscl-cqhecs.desktop`, `usr/bin/hscl-cqhecs`, `runtime.conf` | Whether `hscl-cqhecs run -- studio` works end to end on an installed system is **not tested** here. |
| Is CaDiCaL in the OS runtime? | No. The pinned set has dill, numpy, qiskit, rustworkx, scipy, stevedore, typing_extensions and the `cqhecs` 5.0.0 wheel; the `sat` extra (`python-sat`) is excluded by design. So in the OS only the `watched`, `omniwave` and `scan` engines exist. | `requirements-cp314.txt` | Roughly: portfolio runs, `cadical` reports `unavailable`. |
| Does CQ-HECS fit Python 3.14? | Yes: `requires-python >=3.11`, classifiers up to 3.14, and the wheel is pinned for 3.14. `docs/UNIFIED_SOLVER.md` still says the project "requires Python <3.14" for the CaDiCaL benchmark environment; that text is stale (the limit came from `python-sat`, see stage 2). | `pyproject.toml`, `docs/UNIFIED_SOLVER.md` | The CQ-HECS test suite was **not run** in this stage. |
| What is in CQ-HECS? | `cqhecs/sat.py` (57 KB), `sat_external.py`, `drat.py`, `unified.py` (`hcs.sat.unified.v1`, four engines), `sat_separator.py` (exact #SAT by bucket elimination), `omniwave/` (incl. `gpu.py`, `learned.py`), `studio/app.py`, `provenance.py` (`hcs.run.v2`, schema file present), `mcp_server.py`, `src/sat_solver.cpp`; about 20 SAT-related test files. Apache-2.0. | `gh api .../git/trees/main?recursive=1` | Files not yet read in full: the contract asks for that in P-M0. |
| **Is the Studio's local HTTP server guarded?** | **No.** `cqhecs/studio/app.py` is a stdlib `ThreadingHTTPServer` bound to 127.0.0.1. A search for origin, host, token, CORS and rebind handling finds none. `_read_json` ignores `Content-Type`. POST routes `/api/sat/solve`, `/api/sat/count`, `/api/sat/sweep`, `/api/omniwave/*`, `/api/reload`, `/api/simulate`, `/api/plan`, `/api/noise/compare` need no credential. The contract (section 13) requires Host/Origin checks and a per-start random token. Consequence: any web page open in the user's browser can send a cross-site "simple" POST or use DNS rebinding to start CPU-heavy solver jobs while the Studio runs. | source read at `30c7f14`, lines 945-1085 | Static reading only; no request was sent. Impact is resource exhaustion and unwanted job runs, not shown to be code execution. |

## Stage 2 - web search

| Question | Finding | Evidence | Limits |
|---|---|---|---|
| What is the ICLR 2026 "one-shot GNN guidance" paper? | "Learning from Algorithm Feedback: One-Shot SAT Solver Guidance with GNNs" (Tonshoff, Grohe; arXiv 2505.16053, 2025-05-21; ICLR 2026 proceedings). Method name RLAF. | arxiv.org/abs/2505.16053, ICLR proceedings PDF, OpenReview forum NfWrLOKnfk | See stage 3 for content. |
| What is the AAAI 2026 tensor model counting paper? | "Proof Systems for Tensor-based Model Counting" (AAAI-26, vol. 40 no. 17, published 2026-03-14). | ojs.aaai.org article 38430 | See stage 3. |
| What does the SAT Competition require? | 2023: certificates for all Main-track participants. 2025 proceedings mention VeriPB and formally verifiable certificates. | satcompetition.github.io/2023/certificates.html, TU Wien proceedings PDF | 2023 page is older than the 2025 rules; stage 3 reads the 2025 page. |
| Which exact counters lead? | Model Counting Competition 2025: Cara, D4, Ganak, gpmc, SharpSAT-TD in the exact ranking snippet; Ganak has won tracks for two years (blog). | mccompetition.org MC2025 awards, msoos.org | Snippets disagree on order; stage 3 reads the PDF. |
| Which solvers can PySAT bundle? | CaDiCaL 1.0.3, 1.5.3, 1.9.5, 3.0.0 and Kissat 4.0.4. | pysathq.github.io/docs/html/api/solvers.html | Which build is inside a given wheel is not stated on that page. |

## Stage 3 - crawl of primary sources and local resolution

| Question | Finding | Evidence | Limits |
|---|---|---|---|
| What does RLAF guide, and what does it claim? | A GNN assigns **variable weights and polarities** to all variables in one forward pass; those are injected into the branching heuristic of existing solvers. Trained with policy gradients (GRPO) using the solver's computational cost as reward. Reported: mean solve time reduced, **more than 2x in some cases**, generalising to larger and harder problems. The abstract names neither solver nor code release nor limitations. | arXiv abstract page (scraped) | Only the abstract was read, not the paper body or its tables. Use as a design reference, never as a speed claim for this project. |
| What do `T_dense` and `T_sparse` establish? | Two tensor-based proof systems for model counting. `T_sparse` p-simulates `T_dense`; MICE p-simulates `T_sparse`; exponential lower bounds for XOR-Pairs; minimal `T_dense` proof size is characterised by the treewidth of the primal graph. The paper is purely theoretical: **no implemented checker, no experiments of its own**; it cites other work for practical sparse-vs-dense gaps. | AAAI PDF (scraped, 9 pages) | Proofs are omitted or sketched in the PDF. Consequence: a tensor backend here cannot claim a proof-checked count by pointing at this paper. |
| Exact counting baselines | MC 2025 limits: 1 h and 31 GB per instance. Unweighted track, solved counts: Ganak-ApproxMC 63 (approximate, probabilistic), Ganak 60, Cara 50, D4 50, sharpSAT-TD(-CH) 47, MTMC 39, gpmc 38. At 0% error tolerance the table scores Ganak 1, then Cara and D4 at 2. Cara is described only as "a great newcomer" by Petr Illner; no method given. | MC2025 awards PDF (scraped, 33 pages) | Ranks vs solved counts are different metrics; both are reported, neither re-derived. |
| SAT Competition 2025 proof rules | All Main-track solvers must output **UNSAT proofs** to `proof.out` and SAT certificates. The proof is checked with **dpr-trim, gratgen (GRAT) or veripb**, depending on the format chosen; the page links verified LRAT/LPR checking with cake and CakePB. | satcompetition.github.io/2025/tracks.html and /output.html (scraped) | The 2025 `certificates.html` URL does not exist (404). Time limits for checking were not found. |
| Can CaDiCaL run in the OS runtime? | `pip` resolves `python-sat 1.9.dev21` as a **cp314 manylinux wheel** (4.1 MB, MIT) plus `six` 1.17.0 (MIT); also for cp312. So the "<3.14" remark in CQ-HECS docs no longer holds. | local `pip install --dry-run --only-binary=:all: --python-version 3.14 ...` report | A resolve, not an install or run. Which CaDiCaL (1.9.5 or 3.0.0) the module defaults to must be read from the installed package. A 1.9.dev line is a development release: pin by hash, do not float. |

## Negative / unresolved

- The SAT Competition 2025 `certificates.html` page does not exist; the rules were found on `output.html` instead.
- No source states how Cara counts; do not describe it.
- RLAF code release and the tables behind "more than 2x" are unread.
