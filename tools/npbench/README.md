# npbench: NP benchmark harness (slice 1: SAT)

Standard library only. Research and limits: `docs/research/NP_BENCHMARK_RESEARCH.md`. Plan: ledger rows 16-21.

What is here
- `npbench/cnf.py` strict DIMACS parser and writer, full-model verifier.
- `npbench/gen_sat.py` generators: random k-SAT, threshold ratio 4.26, planted, factoring circuit (known answer).
- `npbench/proof.py` independent RUP refutation checker.
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

Run from `tools/npbench` (or put it on `PYTHONPATH`). Reports belong under the ignored `artifacts/npbench/`.

Tests: `python -m pytest tests/unit/test_npbench_sat.py tests/unit/test_npbench_cli.py`
