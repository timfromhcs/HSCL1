"""The engine turns a request dict into a typed result dict and never raises."""

import json
import math

import pytest
import sympy as sp

from hcseasymath.core.engine import execute
from hcseasymath.core.results import MathResult

REQ = {"operation": "differentiate", "expression": "x**3 - 3*x**2 + 2*x", "variable": "x"}


def test_derivative_of_the_documented_cubic_is_exact():
    res = execute(REQ)
    assert res["status"] == "ok"
    assert res["operation"] == "differentiate"
    assert res["engine"] == "sympy"
    assert res["exactness"] == "symbolic_exact"
    assert sp.sympify(res["result_expression"]) == 3 * sp.Symbol("x") ** 2 - 6 * sp.Symbol("x") + 2


@pytest.mark.parametrize(
    "text, at",
    [
        ("x**3 - 3*x**2 + 2*x", [-2.0, -0.5, 0.0, 1.0, 3.7]),
        ("sin(x)*exp(x)", [-1.0, 0.3, 2.0]),
        ("log(x) + sqrt(x)", [0.5, 1.0, 4.0]),
        ("x/(1 + x**2)", [-3.0, 0.0, 2.5]),
    ],
)
def test_derivative_agrees_with_an_independent_numeric_derivative(text, at):
    res = execute({"operation": "differentiate", "expression": text, "variable": "x"})
    assert res["status"] == "ok"
    f = sp.lambdify("x", sp.sympify(text), "math")
    fp = sp.lambdify("x", sp.sympify(res["result_expression"]), "math")
    for p in at:
        h = 1e-6
        numeric = (f(p + h) - f(p - h)) / (2 * h)
        assert math.isclose(fp(p), numeric, rel_tol=1e-5, abs_tol=1e-6), (text, p)


def test_result_matches_the_pydantic_schema_and_is_json_serialisable():
    res = execute(REQ)
    parsed = MathResult.model_validate(res)
    assert parsed.schema_version == "hcseasymath.result.v1"
    json.dumps(res)


def test_run_id_is_deterministic_and_input_dependent():
    a, b = execute(REQ), execute(REQ)
    assert a["run_id"] == b["run_id"] and a["input_digest"] == b["input_digest"]
    other = execute({**REQ, "expression": "x**2"})
    assert other["run_id"] != a["run_id"]
    assert a["input_digest"].startswith("sha256:")


def test_provenance_names_the_software_versions():
    prov = execute(REQ)["provenance"]
    assert prov["sympy"] == sp.__version__
    assert "python" in prov


@pytest.mark.parametrize(
    "request_, status",
    [
        ({"operation": "differentiate", "expression": "__import__('os')", "variable": "x"}, "invalid_input"),
        ({"operation": "differentiate", "expression": "9**9**9", "variable": "x"}, "resource_limit"),
        ({"operation": "differentiate", "expression": "x", "variable": "not a symbol"}, "invalid_input"),
        ({"operation": "differentiate", "expression": "x"}, "invalid_input"),
        ({"operation": "launch_missiles", "expression": "x", "variable": "x"}, "unsupported"),
        ({"expression": "x"}, "invalid_input"),
        ("not a dict", "invalid_input"),
    ],
)
def test_failures_are_typed_results_not_exceptions(request_, status):
    res = execute(request_)
    assert res["status"] == status
    assert res["result_expression"] is None
    assert res["warnings"] or res["error"]
    MathResult.model_validate(res)


def test_derivative_with_respect_to_an_absent_symbol_is_zero_not_an_error():
    res = execute({"operation": "differentiate", "expression": "y**2", "variable": "x"})
    assert res["status"] == "ok" and res["result_expression"] == "0"


def test_a_field_the_operation_does_not_use_is_refused_not_silently_ignored():
    res = execute({"operation": "differentiate", "expression": "x", "variable": "x", "value": "1"})
    assert res["status"] == "invalid_input" and "value" in (res["error"] or "")


def test_evaluate_keeps_the_value_field_it_uses():
    res = execute({"operation": "evaluate", "expression": "x**2", "variable": "x", "value": "3"})
    assert res["status"] == "ok" and res["result_expression"] == "9"
