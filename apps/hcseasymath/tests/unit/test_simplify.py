"""Simplification: a shorter form is returned only when it is shown to be the same function."""

import math

import pytest
import sympy as sp

from hcseasymath.core import symbolic
from hcseasymath.core.engine import OPERATIONS, execute
from hcseasymath.core.results import MathResult

x = sp.Symbol("x")


def simplify(text, var="x"):
    return execute({"operation": "simplify", "expression": text, "variable": var})


def test_simplify_is_a_listed_operation():
    assert "simplify" in OPERATIONS


@pytest.mark.parametrize(
    "text, expected",
    [
        ("(x**2 - 1)/(x - 1)", x + 1),
        ("sin(x)**2 + cos(x)**2", sp.Integer(1)),
        ("(x + 1)**2 - (x**2 + 2*x + 1)", sp.Integer(0)),
        ("sqrt(8)", 2 * sp.sqrt(2)),
        ("2 + 3", sp.Integer(5)),
        ("a*x + b*x", (sp.Symbol("a") + sp.Symbol("b")) * x),
    ],
)
def test_known_simplifications_are_exact_and_verified(text, expected):
    res = simplify(text)
    assert res["status"] == "ok" and res["exactness"] == "symbolic_exact"
    assert sp.simplify(sp.sympify(res["result_expression"]) - expected) == 0
    assert any("symbolically" in c for c in res["checks"]), res["checks"]
    MathResult.model_validate(res)


def test_the_returned_form_really_agrees_with_the_input_numerically():
    """Independent of the engine's own check: evaluate both forms and compare."""
    res = simplify("(x**2 - 1)/(x - 1)")
    assert res["status"] == "ok"
    f = sp.lambdify("x", sp.sympify(res["result_expression"]), "mpmath")
    g = sp.lambdify("x", sp.sympify("(x**2 - 1)/(x - 1)"), "mpmath")
    import mpmath

    for p in (-2.5, -0.5, 0.25, 1.75, 4.0):
        assert math.isclose(float(f(p)), float(g(p)), rel_tol=1e-12, abs_tol=1e-12), p


def test_a_cancelled_denominator_is_disclosed_not_hidden():
    """(x**2-1)/(x-1) == x+1 only away from x=1; the result must say so."""
    res = simplify("(x**2 - 1)/(x - 1)")
    assert any("not restored" in a for a in res["assumptions"]), res["assumptions"]


@pytest.mark.parametrize(
    "text", ["(x**2 - 1)/(x - 1)", "sin(x)**2 + cos(x)**2", "(x + 1)**2 - (x**2 + 2*x + 1)", "x + y"]
)
def test_a_size_claim_is_only_made_when_count_ops_agrees(text):
    """The engine may report a reduction, but never one that count_ops contradicts."""
    res = simplify(text)
    claims = [c for c in res["checks"] if "operation count" in c]
    if claims:
        before = sp.count_ops(sp.sympify(text))
        after = sp.count_ops(sp.sympify(res["result_expression"]))
        assert after < before, (text, before, after)


def test_a_real_reduction_is_reported():
    res = simplify("(x**2 - 1)/(x - 1)")
    assert any("operation count" in c for c in res["checks"]), res["checks"]


def test_no_reduction_claim_when_the_expression_does_not_shrink():
    res = simplify("x + y")
    assert res["status"] == "ok" and not any("operation count" in c for c in res["checks"])


def test_an_absent_variable_is_still_a_valid_request():
    res = simplify("sin(y)**2 + cos(y)**2", "x")
    assert res["status"] == "ok" and sp.sympify(res["result_expression"]) == sp.Integer(1)


@pytest.mark.parametrize("text", ["__import__('os')", "9**9**9", "x +"])
def test_bad_input_is_a_typed_refusal(text):
    res = simplify(text)
    assert res["status"] in {"invalid_input", "resource_limit"} and res["result_expression"] is None


def test_a_missing_variable_is_a_typed_refusal():
    res = execute({"operation": "simplify", "expression": "x + 1"})
    assert res["status"] == "invalid_input" and res["result_expression"] is None


# ---- the verifier itself, with deliberately bad answers -----------------------------------------------------------


def test_the_verifier_accepts_an_identical_pair_symbolically():
    assert symbolic.verify_equivalence(sp.sin(x) ** 2 + sp.cos(x) ** 2, sp.Integer(1))[0] == "symbolic"


def test_the_verifier_rejects_a_different_function():
    assert symbolic.verify_equivalence(x + 1, x)[0] == "failed"


def test_the_verifier_rejects_an_identity_that_only_holds_on_a_subset():
    """atan(x) + atan(1/x) is +-pi/2 depending on the sign of x; it is not the same function."""
    assert symbolic.verify_equivalence(sp.atan(x) + sp.atan(1 / x), sp.pi / 2)[0] == "failed"


def test_the_verifier_reports_a_pair_it_can_only_check_numerically():
    kind, note = symbolic.verify_equivalence(sp.log(x**2), 2 * sp.log(x))
    assert kind == "numeric" and "numerically" in note, note


def test_the_verifier_reports_when_it_has_too_few_usable_points():
    kind, note = symbolic.verify_equivalence(sp.asin(x) + sp.acosh(x), sp.asin(x) + sp.acosh(x) + 1)
    assert kind == "unverified" and "usable" in note, note


# ---- grading: a failed check is never reported as a result --------------------------------------------------------


def test_a_result_that_fails_its_own_check_is_never_returned(monkeypatch):
    monkeypatch.setattr(symbolic, "verify_equivalence", lambda a, b: ("failed", "forced"))
    res = simplify("(x**2 - 1)/(x - 1)")
    assert res["status"] == "internal_error" and res["result_expression"] is None


def test_an_unverifiable_result_is_partial_not_ok(monkeypatch):
    monkeypatch.setattr(symbolic, "verify_equivalence", lambda a, b: ("unverified", "only 0 usable sample points"))
    res = simplify("(x**2 - 1)/(x - 1)")
    assert res["status"] == "partial" and res["result_expression"] is not None
    assert any("could not be verified" in w for w in res["warnings"])
    MathResult.model_validate(res)


def test_a_result_that_only_checks_numerically_says_so(monkeypatch):
    monkeypatch.setattr(symbolic, "verify_equivalence", lambda a, b: ("numeric", "agrees at 5 sample points"))
    res = simplify("x + 0")
    assert res["status"] == "ok"
    assert any("not proven symbolically" in w for w in res["warnings"])
