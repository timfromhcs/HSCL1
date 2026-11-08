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


def simplify(expr: sp.Expr) -> sp.Expr:
    """SymPy's general simplifier. The caller must verify that the result is the same function."""
    return sp.simplify(expr)


def verify_equivalence(candidate: sp.Expr, original: sp.Expr) -> tuple[str, str]:
    """Check that ``candidate`` and ``original`` are the same function, and say how strong the check was.

    Returns ``(kind, note)`` with kind one of ``symbolic`` (difference simplifies to 0), ``numeric``
    (agrees at several sample points to 1e-12 relative, not proven), ``unverified`` (too few usable
    points) or ``failed`` (a disagreement).

    Point identities such as ``atan(x) + atan(1/x) == pi/2`` hold only on a subset of the reals; the
    sample points include negative rationals, so such a pair is rejected instead of being accepted as
    an identity.
    """
    if sp.simplify(candidate - original) == 0:
        return "symbolic", "result equals the input symbolically"

    symbols = sorted(candidate.free_symbols | original.free_symbols, key=lambda s: s.name)
    if len(symbols) > len(_POINTS):
        # Every symbol needs its own sample value, or two symbols that happen to be equal at the
        # same point could make a wrong pair look right.
        return "unverified", f"{len(symbols)} free symbols but only {len(_POINTS)} distinct sample values"

    usable = 0
    for index in range(len(_POINTS)):
        sub = {sym: _POINTS[(index + offset) % len(_POINTS)] for offset, sym in enumerate(symbols)}
        try:
            a = sp.N(candidate.subs(sub), 30)
            b = sp.N(original.subs(sub), 30)
        except (ZeroDivisionError, ValueError, TypeError, OverflowError):
            continue
        if not (a.is_real and b.is_real and a.is_finite is True and b.is_finite is True):
            continue  # complex, infinite or undefined here: this point says nothing
        if abs(a - b) > _TOLERANCE * (1 + abs(b)):
            where = ", ".join(f"{sym}={sub[sym]}" for sym in symbols)
            return "failed", f"result differs from the input at {where}" if where else "result differs from the input"
        usable += 1
    if usable >= _MIN_NUMERIC_POINTS:
        return "numeric", f"result agrees numerically with the input at {usable} sample points"
    return "unverified", f"only {usable} usable sample points"


class SolveUnsupported(Exception):
    """``solveset`` has no method for this equation (it raises ``NotImplementedError``)."""


def solve_equation(expr: sp.Expr, variable: sp.Symbol) -> sp.Set:
    """Solutions of ``expr == 0`` in the real domain, as a SymPy set.

    ``solveset`` is used instead of ``solve``: it returns a set (so "a list of all roots" is never
    invented), it takes the domain explicitly, and it does not depend on the shape of the output.
    """
    try:
        return sp.solveset(expr, variable, domain=sp.S.Reals)
    except NotImplementedError as exc:
        raise SolveUnsupported(str(exc) or "no method for this equation") from None


def finite_roots(solution: sp.Set) -> list[sp.Expr] | None:
    """The elements of a finite solution set, or ``None`` when the set is not a finite list.

    ``EmptySet`` is a ``FiniteSet`` and yields ``[]``. A ``Union`` of finite sets is flattened. For an
    ``Intersection`` with a finite set (``solveset`` returns ``Intersection({-a}, Reals)`` when a
    parameter is present) the finite part is used; the caller must disclose that membership of the
    other sets was not decided.
    """
    if solution is sp.S.EmptySet:
        return []
    if isinstance(solution, sp.FiniteSet):
        return list(solution.args)
    if isinstance(solution, sp.Union):
        roots: list[sp.Expr] = []
        for part in solution.args:
            elements = finite_roots(part)
            if elements is None:
                return None
            roots.extend(elements)
        return roots
    if isinstance(solution, sp.Intersection):
        for part in solution.args:
            if isinstance(part, (sp.FiniteSet, sp.Union)):
                elements = finite_roots(part)
                if elements is not None:
                    return elements
        return None
    return None


def verify_root(root: sp.Expr, equation: sp.Expr, variable: sp.Symbol) -> tuple[str, str]:
    """Substitute ``root`` back into ``equation`` and say how strong the check was.

    Returns ``(kind, note)`` with kind one of ``symbolic`` (substitution gives exactly 0), ``numeric``
    (the residual is a number that is zero to 1e-12 relative, not proven), ``unverified`` (the
    residual still contains symbols) or ``failed`` (a non-zero residual).
    """
    residual = sp.simplify(equation.subs(variable, root))
    if residual == 0:
        return "symbolic", f"substituting {root} gives exactly 0"
    if not residual.free_symbols:
        try:
            value = sp.N(residual, 30)
            magnitude = abs(sp.N(root, 30))
        except (ZeroDivisionError, ValueError, TypeError, OverflowError):
            return "unverified", "the residual could not be evaluated"
        if value.is_finite is True and abs(value) <= _TOLERANCE * (1 + magnitude):
            return "numeric", f"substituting {root} leaves a residual of {value} (numerically zero)"
        return "failed", f"substituting {root} leaves the non-zero residual {value}"
    return "unverified", "the residual still contains symbols, so it cannot be checked numerically"
