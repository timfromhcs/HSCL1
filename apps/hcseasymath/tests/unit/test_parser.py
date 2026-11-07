"""The allow-list expression parser: what it accepts and what it builds."""

import pytest
import sympy as sp

from hcseasymath.core.expression_ast import ExpressionError, parse

x, y = sp.symbols("x y")


def test_cubic_polynomial_round_trips_exactly():
    assert parse("x**3 - 3*x**2 + 2*x") == x**3 - 3 * x**2 + 2 * x


def test_precedence_and_unary_minus():
    assert parse("-x**2") == -(x**2)
    assert parse("2*x + 3*y/4") == 2 * x + sp.Rational(3, 4) * y
    assert parse("(x + 1)*(x - 1)") == (x + 1) * (x - 1)


def test_decimals_are_exact_rationals_not_binary_floats():
    assert parse("0.1*x") == sp.Rational(1, 10) * x
    assert parse("0.1 + 0.2") == sp.Rational(3, 10)
    assert parse("1e-3") == sp.Rational(1, 1000)


def test_allowed_functions_and_constants():
    assert parse("sin(x) + cos(x)") == sp.sin(x) + sp.cos(x)
    assert parse("exp(x)") == sp.exp(x)
    assert parse("log(x)") == sp.log(x)
    assert parse("sqrt(x)") == sp.sqrt(x)
    assert parse("pi*x") == sp.pi * x
    assert parse("e") == sp.E


def test_symbols_are_plain_symbols_without_assumptions():
    expr = parse("x + y_2")
    assert {s.name for s in expr.free_symbols} == {"x", "y_2"}
    assert all(not s.assumptions0.get("real") for s in expr.free_symbols)


def test_caret_is_refused_with_a_helpful_message():
    with pytest.raises(ExpressionError) as err:
        parse("x^2")
    assert err.value.code == "invalid_input"
    assert "**" in str(err.value)


@pytest.mark.parametrize("text", ["", "   ", "x +", "(x", "x y"])
def test_malformed_input_is_invalid_input(text):
    with pytest.raises(ExpressionError) as err:
        parse(text)
    assert err.value.code == "invalid_input"


def test_a_function_name_cannot_be_used_as_a_bare_symbol():
    with pytest.raises(ExpressionError):
        parse("sin + 1")


def test_result_is_deterministic():
    assert srepr(parse("x**2 + 2*x + 1")) == srepr(parse("x**2 + 2*x + 1"))


def srepr(e):
    return sp.srepr(e)
