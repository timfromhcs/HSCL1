# npbench: NP benchmark harness (slices 1-5a: SAT, suites/CLI, graphs, optimisation, DRAT)

Standard library only. Research and limits: `docs/research/NP_BENCHMARK_RESEARCH.md`. Plan: ledger rows 16-21.

What is here
- `npbench/cnf.py` strict DIMACS parser and writer, full-model verifier.
- `npbench/gen_sat.py` generators: random k-SAT, threshold ratio 4.26, planted, factoring circuit (known answer).
- `npbench/proof.py` independent RUP refutation checker (flat lemma list, no deletions).
- `npbench/drat.py` DRAT line reader and deletion-aware RUP checker; RAT is **not** implemented and is reported as `rat_unsupported`.
- `npbench/solvers/cdcl.py` CDCL baseline with proof log; `npbench/solvers/walksat.py` local search (SAT or UNKNOWN).
- `npbench/runner.py` runs a solver and reports only verified verdicts, flags a contradiction with a known answer, reports PAR-2.

Rules: a solver answer is never evidence. SAT needs a verified model, UNSAT a checked proof, otherwise the verdict is
`UNKNOWN`. An unavailable solver is `unavailable`; there is no silent fallback. Pure Python solvers are baselines for
correctness and small sizes, not competitors to CaDiCaL or Kissat.

- `npbench/suites.py` suites (`light`, `sweep` = heavy), instances rebuilt from specs, manifest with SHA-256; a claimed
  answer that the generator does not know is refused.
- `python -m npbench list | manifest --suite light | run --suite light --solvers cdcl,walksat --budget 5 --out FILE [--force]`
  writes an `npbench.report.v1` JSON report with per-record results and a per-solver summary (decided, PAR-2,
  disagreements, refused, unavailable). Exit 0 all fine, 1 disagreement / refused claim / error / unavailable solver,
  2 usage error, existing report without `--force`, or a heavy suite without `--allow-heavy`. A timeout is not a failure.

- `npbench/graph.py`, `gen_graph.py`, `graph_solvers.py`, `graph_runner.py`: colouring, clique and Hamiltonian cycle.
  Strict `.col` reader; generators with theorem-backed values (Mycielski, queens with gcd(n,6)=1, Turan, complete,
  generalised Petersen) and planted ones (one-sided facts only); solvers `sat` (CNF + CDCL), `dsatur`, `bk`, `backtrack`.
  A yes-answer needs a verified witness. A no-answer needs a RUP proof (colouring, Hamiltonian cycle) or, for a clique,
  a proper colouring with k-1 colours; an exhausted search alone is reported as UNKNOWN.
  `python -m npbench run --suite graphs --solvers sat,dsatur,bk,backtrack`.

- `npbench/tsp.py`, `gen_tsp.py`, `tsp_solvers.py`, `knap.py`, `gen_knap.py`, `knap_solvers.py`, `opt_runner.py`: TSP and knapsack / subset sum
  decision tasks (is there a tour of length <= bound; is there a selection reaching a profit target). A yes needs a verified
  tour or selection. A TSP no needs integer potentials whose 1-tree bound, recomputed by the verifier, exceeds the limit; a
  knapsack no needs the exact fractional bound below the target. An exact DP without such a certificate is UNKNOWN.
  `python -m npbench run --suite optimization --solvers dp,nn2opt,lagrange,greedy,ub`.

Run from `tools/npbench` (or put it on `PYTHONPATH`). Reports belong under the ignored `artifacts/npbench/`.

## Proof checking: which checker accepted (`runner.run_instance(..., proof_checker=...)`)

- `rup` (default) - `npbench/proof.py`: a flat lemma list, no deletions, reverse unit propagation per lemma.
- `drat` - `npbench/drat.py`: the **DRAT line format** (comments, `d` deletions, one `0` per line, caps before
  allocation, strict tokens) and RUP per addition against the clause database that is active at that line.
  **RAT is not implemented.** A step that is not RUP is reported `rat_unsupported` and the proof keeps the verdict
  `unknown`; an empty clause that is not RUP is `invalid_step`; a proof without the empty clause is
  `incomplete_proof`; anything unparseable is `malformed`. Only `verdict == "unsat"` is a refutation.
- The solver record says which checker ran: `certification` is `RUP_CHECKED` or `DRAT_RUP_CHECKED`. An unknown
  checker name raises `UnknownProofChecker` instead of falling back to one that exists.

Tests: `python -m pytest tests/unit/test_npbench_sat.py tests/unit/test_npbench_cli.py tests/unit/test_npbench_graph.py tests/unit/test_npbench_opt.py tests/unit/test_npbench_drat.py`
