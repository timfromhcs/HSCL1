import math

import pytest

from hcseasymath.core.engine import OPERATIONS, execute


def pl(expr, lo="0", hi="1", points=5, var="x", **kw):
    req = {"operation": "plot", "expression": expr, "variable": var, "x_min": lo, "x_max": hi, "points": points}
    req.update(kw)
    return execute(req)


def test_listed():
    assert "plot" in OPERATIONS


def test_samples_match_independent_math():
    r = pl("x**2", "0", "2", 5)
    assert r["status"] == "ok" and r["exactness"] == "numeric"
    xs = [s[0] for s in r["samples"]]
    assert xs == [0.0, 0.5, 1.0, 1.5, 2.0]
    for x, y in r["samples"]:
        assert y == pytest.approx(x * x, rel=1e-12)


def test_endpoints_are_included_and_evenly_spaced():
    r = pl("sin(x)", "-1", "1", 11)
    xs = [s[0] for s in r["samples"]]
    assert xs[0] == -1.0 and xs[-1] == 1.0 and len(xs) == 11
    for x, y in r["samples"]:
        assert y == pytest.approx(math.sin(x), abs=1e-12)


def test_undefined_points_are_null_not_connected():
    r = pl("1/x", "-1", "1", 5)  # x = 0 is a sample point
    assert r["status"] == "partial"
    ys = {s[0]: s[1] for s in r["samples"]}
    assert ys[0.0] is None
    assert ys[1.0] == 1.0 and ys[-1.0] == -1.0
    assert any("1 of 5" in w and "undefined" in w for w in r["warnings"])


def test_complex_values_are_null_not_real_part():
    r = pl("sqrt(x)", "-1", "1", 3)
    ys = {s[0]: s[1] for s in r["samples"]}
    assert ys[-1.0] is None and ys[1.0] == 1.0
    assert r["status"] == "partial"


def test_all_undefined_is_unresolved_without_samples():
    r = pl("log(x)", "-2", "-1", 4)
    assert r["status"] == "unresolved" and r["samples"] is None


def test_no_image_claim_and_disclosure():
    r = pl("x", "0", "1", 3)
    assert r["result_expression"] is None
    assert any("sample" in a for a in r["assumptions"])


@pytest.mark.parametrize("points", [1, 0, -3, 1001, 10**9, 2.5, "5", True])
def test_point_count_bounds(points):
    r = pl("x", points=points)
    assert r["status"] in ("invalid_input", "resource_limit") and r["samples"] is None


@pytest.mark.parametrize("lo,hi", [("1", "0"), ("1", "1"), ("0", "1e9"), ("-1e9", "0"), ("y", "1"), ("0", "oo"), ("0", "nan")])
def test_range_refused(lo, hi):
    r = pl("x", lo, hi)
    assert r["status"] in ("invalid_input", "resource_limit") and r["samples"] is None


def test_missing_range():
    r = execute({"operation": "plot", "expression": "x", "variable": "x"})
    assert r["status"] == "invalid_input"


def test_hostile_expression_refused():
    assert pl("__import__('os')")["status"] == "invalid_input"


def test_other_operation_must_not_accept_plot_fields():
    r = execute({"operation": "differentiate", "expression": "x", "variable": "x", "x_min": "0"})
    assert r["status"] == "invalid_input"


def test_other_symbols_refused():
    r = pl("x*y")
    assert r["status"] == "invalid_input" and r["samples"] is None
