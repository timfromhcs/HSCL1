"""Symbolic operations on already-validated SymPy expressions."""

from __future__ import annotations

import sympy as sp

# Sample points for the numeric derivative check: rationals, so no float noise enters before evaluation.
_POINTS = tuple(sp.Rational(a, b) for a, b in ((1, 2), (13, 10), (21, 10), (7, 10), (19, 10), (-3, 10), (-17, 10)))
_OTHER_SYMBOLS = tuple(sp.Rational(a, b) for a, b in ((7, 5), (11, 7), (13, 9), (17, 11)))
_MIN_NUMERIC_POINTS = 3
_TOLERANCE = sp.Rational(1, 10**12)


def differentiate(expr: sp.Expr, variable: sp.Symbol) -> sp.Expr:
    """Exact derivative. Constants and absent symbols differentiate to 0."""
    return sp.diff(expr, variable)


def integrate(expr: sp.Expr, variable: sp.Symbol) -> sp.Expr | None:
    """An antiderivative (constant of integration omitted), or ``None`` when SymPy found no closed form.

    SymPy signals "no closed form" by returning the integral unevaluated; that is not an answer.
    """
    result = sp.integrate(expr, variable)
    if result.has(sp.Integral):
        return None
    return result


def verify_antiderivative(antiderivative: sp.Expr, integrand: sp.Expr, variable: sp.Symbol) -> tuple[str, str]:
    """Check ``d/dx F == f`` and say how strong the check was.

    Returns ``(kind, note)`` with kind one of ``symbolic`` (difference simplifies to 0), ``numeric`` (agrees at several
    sample points to 1e-12 relative, not proven), ``unverified`` (too few usable points) or ``failed`` (a disagreement).
    """
    derivative = sp.diff(antiderivative, variable)
    if sp.simplify(derivative - integrand) == 0:
        return "symbolic", "derivative of the result equals the input symbolically"

    others = sorted((derivative.free_symbols | integrand.free_symbols) - {variable}, key=lambda s: s.name)
    fixed = {s: _OTHER_SYMBOLS[i % len(_OTHER_SYMBOLS)] for i, s in enumerate(others)}
    usable = 0
    for point in _POINTS:
        sub = {variable: point, **fixed}
        try:
            a = sp.N(derivative.subs(sub), 30)
            b = sp.N(integrand.subs(sub), 30)
        except (ZeroDivisionError, ValueError, TypeError, OverflowError):
            continue
        if not (a.is_real and b.is_real and a.is_finite is True and b.is_finite is True):
            continue  # complex, infinite or undefined here: this point says nothing
        if abs(a - b) > _TOLERANCE * (1 + abs(b)):
            return "failed", f"derivative of the result differs from the input at {variable}={point}"
        usable += 1
    if usable >= _MIN_NUMERIC_POINTS:
        return "numeric", f"derivative of the result agrees numerically with the input at {usable} sample points"
    return "unverified", f"only {usable} usable sample points"
