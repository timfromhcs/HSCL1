"""Hostile input corpus (decision D4). Nothing here may execute, hang or crash."""

import time

from sympy import Rational as sp_rational

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from hcseasymath.core.expression_ast import ExpressionError, parse

# Each entry must be refused with one of these codes and must not run.
CODES = {"invalid_input", "resource_limit"}

CORPUS = [
    "__import__('os').system('echo pwned')",
    "__import__('pathlib').Path('canary.txt').write_text('x')",
    "open('canary.txt', 'w')",
    "eval('1+1')",
    "exec('x=1')",
    "(lambda: 1)()",
    "[i for i in range(3)]",
    "{1: 2}",
    "x.__class__",
    "x.__class__.__mro__[1].__subclasses__()",
    "().__class__.__bases__",
    "'a' * 3",
    "f'{x}'",
    "x if 1 else 2",
    "x and y",
    "x < y",
    "x[0]",
    "x; y",
    "x = 1",
    "import os",
    "print(1)",
    "sympy.sympify('1')",
    "sin(x, y)",
    "sin(x=1)",
    "sin(*x)",
    "unknown_function(x)",
    "x" * 5000,
    "1" * 400,
    "-" * 300 + "x",
    "sin(" * 100 + "x" + ")" * 100,
    "(10**10000)**10000",
    "(10**30)**1000",
    "(3/7)**100000",
    "((10**5000)**2)**2",
    "+".join(["x"] * 5000),
    "9**9**9",
    "9**9**9**9",
    "2**100000",
    "10**10000",
    "x**100000",
    "123456789012345678901234567890123456789012345678901234567890",
    "x‮ + 1",
    "х + 1",  # Cyrillic homoglyph of x
    "x\x00 + 1",
    "x\n+ 1; import os",
]


@pytest.mark.parametrize("text", CORPUS)
def test_hostile_input_is_refused(text, tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    start = time.monotonic()
    with pytest.raises(ExpressionError) as err:
        parse(text)
    assert err.value.code in CODES
    assert time.monotonic() - start < 2.0, "refusal must be fast"
    assert not (tmp_path / "canary.txt").exists(), "input was executed"


def test_power_tower_is_refused_before_it_is_computed():
    start = time.monotonic()
    with pytest.raises(ExpressionError) as err:
        parse("9**9**9")
    assert err.value.code == "resource_limit"
    assert time.monotonic() - start < 1.0


def test_nested_parentheses_without_structure_are_harmless():
    # Parentheses add no AST nodes; this is valid and cheap, not an attack.
    from hcseasymath.core.expression_ast import parse as p
    import sympy as sp

    assert p("(" * 100 + "x" + ")" * 100) == sp.Symbol("x")


def test_large_result_power_is_refused_before_it_is_computed():
    start = time.monotonic()
    with pytest.raises(ExpressionError) as err:
        parse("(10**10000)**10000")
    assert err.value.code == "resource_limit"
    assert time.monotonic() - start < 1.0


def test_modest_powers_are_still_allowed():
    assert parse("2**10") == 1024
    assert parse("2**10000") == 2**10000  # 10001 bits, below the result cap
    assert parse("(1/3)**5") == sp_rational(1, 243)
    assert parse("x**1000").as_base_exp()[1] == 1000


@settings(max_examples=400, deadline=2000)
@given(st.text(max_size=300))
def test_arbitrary_text_never_raises_anything_but_the_typed_error(text):
    try:
        parse(text)
    except ExpressionError as e:
        assert e.code in CODES


@settings(max_examples=300, deadline=2000)
@given(
    st.text(alphabet="xy01 2+-*/()._,e^%@~!<>=[]{}'\"\\", max_size=60),
)
def test_grammar_shaped_noise_never_escapes(text):
    try:
        parse(text)
    except ExpressionError as e:
        assert e.code in CODES
