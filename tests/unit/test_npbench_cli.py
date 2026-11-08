"""NP benchmark, slice 2: suites, manifest and the CLI report (ledger row 17)."""
import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools" / "npbench"))

from npbench import __main__ as cli  # noqa: E402
from npbench import cnf as C  # noqa: E402
from npbench import suites as S  # noqa: E402


def test_light_suite_has_unique_ids_and_known_answers_where_claimed():
    specs = S.suite_specs("light")
    ids = [s["id"] for s in specs]
    assert len(ids) == len(set(ids)) and len(ids) >= 10
    for s in specs:
        assert s["expected"] in (None, "SAT", "UNSAT")
    assert {"SAT", "UNSAT"} <= {s["expected"] for s in specs}, "the light suite needs known SAT and known UNSAT instances"


def test_instances_are_deterministic_and_the_manifest_binds_their_bytes():
    spec = S.suite_specs("light")[0]
    f1, e1 = S.build_instance(spec)
    f2, e2 = S.build_instance(spec)
    assert f1 == f2 and e1 == e2
    manifest = S.manifest("light")
    entry = next(m for m in manifest if m["id"] == spec["id"])
    import hashlib
    assert entry["sha256"] == hashlib.sha256(C.write_dimacs(f1).encode("ascii")).hexdigest()


def test_unknown_family_and_unknown_suite_are_refused():
    with pytest.raises(ValueError):
        S.build_instance({"id": "x", "family": "nope", "params": {}})
    with pytest.raises(ValueError):
        S.suite_specs("nope")


def test_expected_answer_in_a_spec_cannot_override_the_generator():
    spec = {"id": "f", "family": "factoring", "params": {"n": 13, "bits_p": 3, "bits_q": 3}, "expected": "SAT"}
    with pytest.raises(ValueError):
        S.build_instance(spec)  # the generator knows 13 is prime: a wrong claim is refused, not trusted


def run(tmp_path, *extra, suite="light", solvers="cdcl", budget="10"):
    out = tmp_path / "report.json"
    code = cli.main(["run", "--suite", suite, "--solvers", solvers, "--budget", budget, "--out", str(out), *extra])
    return code, out


def test_light_run_writes_a_complete_report_and_exits_zero(tmp_path):
    code, out = run(tmp_path)
    assert code == 0
    rep = json.loads(out.read_text())
    assert rep["schema"] == "npbench.report.v1" and rep["suite"] == "light"
    assert len(rep["records"]) == len(S.suite_specs("light"))
    assert len(rep["manifest"]) == len(rep["records"])
    summary = rep["summary"]["cdcl"]
    assert summary["disagreements"] == 0 and summary["decided"] == len(rep["records"]) and summary["par2"] is not None
    for rec in rep["records"]:
        assert rec["status"] in ("SAT", "UNSAT") and rec["certification"] in ("MODEL_VERIFIED", "RUP_CHECKED")
    assert "environ" not in json.dumps(rep).lower()


def test_walksat_and_cdcl_agree_on_every_instance_walksat_decides(tmp_path):
    code, out = run(tmp_path, solvers="cdcl,walksat", budget="3")
    rep = json.loads(out.read_text())
    by = {}
    for rec in rep["records"]:
        by.setdefault(rec["id"], {})[rec["solver"]] = rec["status"]
    for ident, st in by.items():
        if st["walksat"] in ("SAT", "UNSAT"):
            assert st["walksat"] == st["cdcl"], ident
    assert rep["summary"]["walksat"]["disagreements"] == 0


def test_an_unavailable_solver_is_reported_and_makes_the_exit_code_nonzero(tmp_path):
    code, out = run(tmp_path, solvers="cdcl,kissat", budget="5")
    rep = json.loads(out.read_text())
    assert code == 1
    assert rep["summary"]["kissat"]["unavailable"] == len(rep["records"]) // 2
    assert all(r["status"] == "unavailable" for r in rep["records"] if r["solver"] == "kissat")


def test_existing_report_is_not_overwritten_without_force(tmp_path):
    code, out = run(tmp_path)
    before = out.read_bytes()
    code2 = cli.main(["run", "--suite", "light", "--solvers", "cdcl", "--budget", "5", "--out", str(out)])
    assert code2 == 2 and out.read_bytes() == before
    code3 = cli.main(["run", "--suite", "light", "--solvers", "cdcl", "--budget", "5", "--out", str(out), "--force"])
    assert code3 == 0


def test_heavy_suite_needs_an_explicit_flag(tmp_path):
    out = tmp_path / "heavy.json"
    assert cli.main(["run", "--suite", "sweep", "--solvers", "cdcl", "--budget", "1", "--out", str(out)]) == 2
    assert not out.exists()
    assert S.is_heavy("sweep") and not S.is_heavy("light")


def test_bad_arguments_exit_two(tmp_path):
    assert cli.main(["run", "--suite", "nope", "--out", str(tmp_path / "x.json")]) == 2
    assert cli.main(["run", "--suite", "light", "--budget", "0", "--out", str(tmp_path / "y.json")]) == 2
    assert cli.main(["run", "--suite", "light", "--budget", "abc", "--out", str(tmp_path / "z.json")]) == 2


def test_a_solver_whose_claims_are_refused_is_counted_and_fails_the_run(tmp_path, monkeypatch):
    from npbench import runner as R
    from npbench.solvers import cdcl as K

    def liar(formula, budget_s, seed):  # claims SAT with an all-false model: no instance of the light suite accepts it
        return K.Result("SAT", {v: False for v in range(1, formula.num_vars + 1)}, None, 0)

    monkeypatch.setitem(R.SOLVERS, "liar", liar)
    code, out = run(tmp_path, solvers="liar", budget="2")
    rep = json.loads(out.read_text())
    assert code == 1
    assert rep["summary"]["liar"]["decided"] == 0
    assert rep["summary"]["liar"]["refused"] == len(rep["records"])
    assert all(r["status"] == "UNKNOWN" and "refused" in r["note"] for r in rep["records"])


def test_a_verified_verdict_against_the_recorded_answer_is_a_disagreement_and_fails_the_run(tmp_path, monkeypatch):
    real = S.build_instance

    def flipped(spec):  # simulates a buggy generator: the recorded answer is wrong, the formula is right
        formula, expected = real(spec)
        return formula, {"SAT": "UNSAT", "UNSAT": "SAT"}.get(expected, expected)

    monkeypatch.setattr(cli.S, "build_instance", flipped)
    code, out = run(tmp_path)
    rep = json.loads(out.read_text())
    known = [r for r in rep["records"] if r["expected"] is not None]
    assert code == 1 and known
    assert all(r["disagreement"] for r in known)
    assert rep["summary"]["cdcl"]["disagreements"] == len(known)


def test_list_and_manifest_commands(tmp_path, capsys):
    assert cli.main(["list"]) == 0
    listed = capsys.readouterr().out
    assert "light" in listed and "sweep" in listed and "heavy" in listed
    assert cli.main(["manifest", "--suite", "light"]) == 0
    man = json.loads(capsys.readouterr().out)
    assert len(man) == len(S.suite_specs("light")) and all("sha256" in m for m in man)
