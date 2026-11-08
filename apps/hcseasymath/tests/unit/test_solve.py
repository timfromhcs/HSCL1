"""Equation solving: `solveset` real roots, each one substituted back before it is reported."""

import pytest
import sympy as sp

from hcseasymath.core import symbolic
from hcseasymath.core.engine import OPERATIONS, execute
from hcseasymath.core.results import MathResult

x = sp.Symbol("x")
EMPTY = {"EmptySet": sp.EmptySet}


def solve(text, var="x"):
    return execute({"operation": "solve", "expression": text, "variable": var})


def roots_of(res):
    return sp.sympify(res["result_expression"], locals=EMPTY)


def test_solve_is_a_listed_operation():
    assert "solve" in OPERATIONS


@pytest.mark.parametrize(
    "text, expected",
    [
        ("x**2 - 4", {-2, 2}),
        ("x**2 - 2", {-sp.sqrt(2), sp.sqrt(2)}),
        ("x**3 - x", {-1, 0, 1}),
        ("(x - 2)**2", {2}),
        ("exp(x) - 1", {0}),
        ("x + a", {-sp.Symbol("a")}),
    ],
)
def test_known_roots_are_exact_and_verified(text, expected):
    res = solve(text)
    assert res["status"] == "ok" and res["exactness"] == "symbolic_exact"
    assert roots_of(res) == sp.FiniteSet(*expected)
    assert any("substituted back" in c for c in res["checks"]), res["checks"]
    MathResult.model_validate(res)


def test_every_returned_root_really_solves_the_equation():
    """Independent of the engine's own check: substitute each root and evaluate."""
    res = solve("x**4 - 5*x**2 + 4")
    assert res["status"] == "ok"
    for root in roots_of(res):
        value = sp.simplify((x**4 - 5 * x**2 + 4).subs(x, root))
        assert value == 0, (root, value)


def test_no_real_root_is_reported_as_a_verified_absence_with_the_complex_count():
    res = solve("x**2 + 1")
    assert res["status"] == "partial" and res["result_expression"] == "EmptySet"
    assert any("2 complex" in w for w in res["warnings"]), res["warnings"]
    assert any("not independently verified" in w for w in res["warnings"]), res["warnings"]
    MathResult.model_validate(res)


def test_an_equation_with_no_solution_at_all_says_so_without_a_complex_note():
    res = solve("3")
    assert res["status"] == "partial" and res["result_expression"] == "EmptySet"
    assert not any("complex" in w for w in res["warnings"]), res["warnings"]


def test_an_infinite_solution_set_is_unresolved_never_a_guessed_list():
    res = solve("sin(x)")
    assert res["status"] == "unresolved" and res["result_expression"] is None
    assert res["error"] and "not a finite list of roots" in res["error"]


def test_an_equation_that_holds_everywhere_is_not_expanded():
    res = solve("0")
    assert res["status"] == "unresolved" and res["result_expression"] is None
    assert "whole domain" in (res["error"] or "")


def test_a_parameter_in_the_equation_makes_an_empty_answer_inconclusive():
    res = solve("y - 1")
    assert res["status"] == "unresolved" and res["result_expression"] is None
    assert res["error"] and "parameter" in res["error"]


def test_the_result_states_the_domain():
    res = solve("x**2 - 4")
    assert any("real" in a for a in res["assumptions"]), res["assumptions"]


@pytest.mark.parametrize("text", ["__import__('os')", "9**9**9", "x +"])
def test_bad_input_is_a_typed_refusal(text):
    res = solve(text)
    assert res["status"] in {"invalid_input", "resource_limit"} and res["result_expression"] is None


def test_a_missing_variable_is_a_typed_refusal():
    res = execute({"operation": "solve", "expression": "x + 1"})
    assert res["status"] == "invalid_input" and res["result_expression"] is None


# ---- the root verifier itself -------------------------------------------------------------------------------------


def test_the_verifier_accepts_a_correct_root():
    assert symbolic.verify_root(sp.Integer(2), x**2 - 4, x)[0] == "symbolic"


def test_the_verifier_rejects_a_wrong_root():
    assert symbolic.verify_root(sp.Integer(3), x**2 - 4, x)[0] == "failed"


def test_the_verifier_reports_a_root_it_can_only_check_numerically():
    kind, note = symbolic.verify_root(sp.Float("1.4142135623730951"), x**2 - 2, x)
    assert kind == "numeric" and "numerically zero" in note, (kind, note)


def test_the_verifier_reports_a_root_it_cannot_check():
    a, b = sp.Symbol("a"), sp.Symbol("b")
    kind, note = symbolic.verify_root(b, x**2 - a**2, x)
    assert kind == "unverified" and "symbols" in note, (kind, note)


# ---- grading: an unverified or failed root is never reported as a solution ----------------------------------------


def test_a_root_that_fails_its_check_is_dropped_and_the_rest_is_partial(monkeypatch):
    calls = {"n": 0}

    def flaky(root, equation, variable):
        calls["n"] += 1
        return ("failed", "forced") if calls["n"] == 1 else ("symbolic", "forced ok")

    monkeypatch.setattr(symbolic, "verify_root", flaky)
    res = solve("x**2 - 4")
    assert res["status"] == "partial" and res["result_expression"] is not None
    assert len(roots_of(res)) == 1
    assert any("failed the substitution check" in w for w in res["warnings"]), res["warnings"]


def test_when_every_root_fails_its_check_nothing_is_returned(monkeypatch):
    monkeypatch.setattr(symbolic, "verify_root", lambda root, equation, variable: ("failed", "forced"))
    res = solve("x**2 - 4")
    assert res["status"] == "internal_error" and res["result_expression"] is None


def test_an_unverifiable_root_is_partial_not_ok(monkeypatch):
    monkeypatch.setattr(symbolic, "verify_root", lambda root, equation, variable: ("unverified", "symbols remain"))
    res = solve("x**2 - 4")
    assert res["status"] == "partial" and res["result_expression"] is not None
    assert any("could not be verified" in w for w in res["warnings"]), res["warnings"]


def test_a_root_checked_only_numerically_says_so(monkeypatch):
    monkeypatch.setattr(symbolic, "verify_root", lambda root, equation, variable: ("numeric", "residual 1e-17"))
    res = solve("x**2 - 4")
    assert res["status"] == "ok"
    assert any("not proven symbolically" in w for w in res["warnings"]), res["warnings"]
