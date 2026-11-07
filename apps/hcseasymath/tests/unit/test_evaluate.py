import pytest

from hcseasymath.core.engine import OPERATIONS, execute


def ev(expr, value, var="x"):
    return execute({"operation": "evaluate", "expression": expr, "variable": var, "value": value})


def test_listed():
    assert "evaluate" in OPERATIONS


def test_exact_rational():
    r = ev("x**2 + 1/3", "1/2")
    assert r["status"] == "ok" and r["result_expression"] == "7/12" and r["exactness"] == "symbolic_exact"


def test_keeps_exact_irrational():
    r = ev("sqrt(x)", "2")
    assert r["status"] == "ok" and r["result_expression"] == "sqrt(2)"


@pytest.mark.parametrize("expr,value", [("1/x", "0"), ("log(x)", "0")])
def test_undefined_is_unresolved_without_result(expr, value):
    r = ev(expr, value)
    assert r["status"] == "unresolved" and r["result_expression"] is None


@pytest.mark.parametrize("value", ["y", "__import__('os')", "9**9**9"])
def test_hostile_or_symbolic_value_refused(value):
    r = ev("x+1", value)
    assert r["status"] in ("invalid_input", "resource_limit") and r["result_expression"] is None


def test_missing_value():
    assert execute({"operation": "evaluate", "expression": "x", "variable": "x"})["status"] == "invalid_input"
