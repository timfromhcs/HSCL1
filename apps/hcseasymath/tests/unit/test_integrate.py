"""Indefinite integration: exact when SymPy finds an antiderivative AND it checks out, `unresolved` otherwise."""

import math

import pytest
import sympy as sp

from hcseasymath.core import symbolic
from hcseasymath.core.engine import OPERATIONS, execute
from hcseasymath.core.results import MathResult

x = sp.Symbol("x")


def integrate(text, var="x"):
    return execute({"operation": "integrate", "expression": text, "variable": var})


def test_integrate_is_a_listed_operation():
    assert "integrate" in OPERATIONS and "differentiate" in OPERATIONS


@pytest.mark.parametrize(
    "text, expected",
    [
        ("x**2", x**3 / 3),
        ("sin(x)", -sp.cos(x)),
        ("1/x", sp.log(x)),
        ("5", 5 * x),
        ("log(x)", x * sp.log(x) - x),
        ("1/(1+x**2)", sp.atan(x)),
    ],
)
def test_known_antiderivatives_are_exact_and_verified(text, expected):
    res = integrate(text)
    assert res["status"] == "ok" and res["exactness"] == "symbolic_exact"
    assert sp.simplify(sp.sympify(res["result_expression"]) - expected) == 0
    assert any("symbolically" in c for c in res["checks"]), res["checks"]


@pytest.mark.parametrize("text, at", [("x*exp(x)", [-1.0, 0.4, 2.0]), ("tan(x)**3", [0.2, 0.9]), ("sin(x)/x", [0.5, 1.5])])
def test_the_returned_function_really_differentiates_back_to_the_input(text, at):
    """Independent of the engine's own check: numeric derivative of the answer against the question."""
    res = integrate(text)
    assert res["status"] == "ok"
    F = sp.lambdify("x", sp.sympify(res["result_expression"], locals={"Si": sp.Si}), "mpmath")
    f = sp.lambdify("x", sp.sympify(text), "mpmath")
    import mpmath

    for p in at:
        slope = mpmath.diff(F, p)
        assert math.isclose(float(slope), float(f(p)), rel_tol=1e-7, abs_tol=1e-9), (text, p)


def test_no_closed_form_is_unresolved_never_ok_and_never_a_made_up_primitive():
    res = integrate("exp(x**x)")
    assert res["status"] == "unresolved"
    assert res["result_expression"] is None and res["exactness"] == "none"
    assert res["error"] and "closed form" in res["error"]
    MathResult.model_validate(res)


def test_a_result_that_only_checks_numerically_says_so():
    res = integrate("sqrt(1+x**3)")  # SymPy answers with a hypergeometric function; simplify() cannot prove it
    assert res["status"] == "ok"
    assert any("numerically" in c for c in res["checks"]), res["checks"]
    assert not any("symbolically" in c for c in res["checks"])
    assert any("not proven symbolically" in w for w in res["warnings"])


def test_the_constant_of_integration_is_stated_not_hidden():
    res = integrate("x")
    assert any("constant of integration" in a for a in res["assumptions"])
    assert "C" not in res["result_expression"]


def test_a_variable_that_is_absent_integrates_as_a_constant():
    res = integrate("y**2", "x")
    assert res["status"] == "ok" and sp.simplify(sp.sympify(res["result_expression"]) - x * sp.Symbol("y") ** 2) == 0


def test_other_symbols_are_kept_symbolic():
    res = integrate("a*x", "x")
    assert res["status"] == "ok" and sp.simplify(sp.sympify(res["result_expression"]) - sp.Symbol("a") * x**2 / 2) == 0


@pytest.mark.parametrize("text", ["__import__('os')", "9**9**9", "x +"])
def test_bad_input_is_a_typed_refusal(text):
    res = integrate(text)
    assert res["status"] in {"invalid_input", "resource_limit"} and res["result_expression"] is None


# ---- the verifier itself, with a deliberately wrong answer -------------------------------------------------------

def test_the_verifier_rejects_a_wrong_antiderivative():
    assert symbolic.verify_antiderivative(x**3, x**2, x)[0] == "failed"
    assert symbolic.verify_antiderivative(x**3 / 3, x**2, x)[0] == "symbolic"


def test_the_verifier_accepts_a_correct_but_unsimplifiable_answer_numerically():
    f = sp.sqrt(1 + x**3)
    F = sp.integrate(f, x)
    kind, note = symbolic.verify_antiderivative(F, f, x)
    assert kind in {"symbolic", "numeric"}


def test_an_answer_that_fails_its_own_check_is_never_returned(monkeypatch):
    monkeypatch.setattr(symbolic, "verify_antiderivative", lambda F, f, var: ("failed", "forced"))
    res = integrate("x**2")
    assert res["status"] == "internal_error" and res["result_expression"] is None


def test_an_unverifiable_answer_is_partial_not_ok(monkeypatch):
    monkeypatch.setattr(symbolic, "verify_antiderivative", lambda F, f, var: ("unverified", "no usable sample points"))
    res = integrate("x**2")
    assert res["status"] == "partial" and res["result_expression"] is not None
    assert any("could not be verified" in w for w in res["warnings"])
