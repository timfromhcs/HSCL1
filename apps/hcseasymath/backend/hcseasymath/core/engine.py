"""Request -> typed result. ``execute`` never raises; failures are results with a status."""

from __future__ import annotations

import re
import time
from typing import Any, Callable

import sympy as sp

from . import symbolic
from .expression_ast import ExpressionError, parse
from .results import MathResult, input_digest, provenance, run_id

_VARIABLE = re.compile(r"[A-Za-z][A-Za-z0-9_]{0,15}\Z")


def _result(request: Any, operation: str, status: str, **fields: Any) -> dict[str, Any]:
    digest = input_digest(request)
    prov = provenance()
    model = MathResult(
        run_id=run_id(digest, prov),
        status=status,
        operation=operation,
        engine="sympy",
        input_digest=digest,
        provenance=prov,
        **fields,
    )
    return model.model_dump()


def _failure(request: Any, operation: str, status: str, message: str) -> dict[str, Any]:
    return _result(request, operation, status, error=message, warnings=[message])


failure_result = _failure


def _expression_and_variable(request: dict[str, Any]) -> tuple[sp.Expr, sp.Symbol]:
    text = request.get("expression")
    var = request.get("variable")
    if not isinstance(text, str):
        raise ExpressionError("invalid_input", "missing 'expression'")
    if not isinstance(var, str) or not _VARIABLE.match(var) or not var.isascii():
        raise ExpressionError("invalid_input", "missing or invalid 'variable'")
    return parse(text), sp.Symbol(var)


def _differentiate(request: dict[str, Any], started: float) -> dict[str, Any]:
    expr, var = _expression_and_variable(request)
    result = symbolic.differentiate(expr, var)
    return _result(
        request,
        "differentiate",
        "ok",
        normalized_expression=str(expr),
        result_expression=str(result),
        exactness="symbolic_exact",
        timings_ms={"total": round((time.perf_counter() - started) * 1000.0, 3)},
    )


def _integrate(request: dict[str, Any], started: float) -> dict[str, Any]:
    expr, var = _expression_and_variable(request)
    antiderivative = symbolic.integrate(expr, var)
    elapsed = {"total": round((time.perf_counter() - started) * 1000.0, 3)}
    if antiderivative is None:
        return _result(
            request,
            "integrate",
            "unresolved",
            normalized_expression=str(expr),
            error="SymPy found no closed form for this integral; no antiderivative is claimed",
            warnings=["no closed form found"],
            timings_ms=elapsed,
        )
    kind, note = symbolic.verify_antiderivative(antiderivative, expr, var)
    elapsed = {"total": round((time.perf_counter() - started) * 1000.0, 3)}
    common = {
        "normalized_expression": str(expr),
        "assumptions": ["indefinite integral; the constant of integration is omitted"],
        "timings_ms": elapsed,
    }
    if kind == "failed":
        return _result(
            request, "integrate", "internal_error",
            error=f"the computed antiderivative failed its own derivative check ({note}); it is not returned",
            warnings=[note], **common,
        )
    fields = dict(common, result_expression=str(antiderivative), exactness="symbolic_exact")
    if kind == "symbolic":
        return _result(request, "integrate", "ok", checks=[note], **fields)
    if kind == "numeric":
        return _result(
            request, "integrate", "ok", checks=[note],
            warnings=["the derivative check is numeric only (not proven symbolically)"], **fields,
        )
    return _result(
        request, "integrate", "partial", checks=[],
        warnings=[f"the antiderivative could not be verified: {note}"], **fields,
    )


def _evaluate(request: dict[str, Any], started: float) -> dict[str, Any]:
    expr, var = _expression_and_variable(request)
    text = request.get("value")
    if not isinstance(text, str):
        raise ExpressionError("invalid_input", "missing 'value'")
    value = parse(text)
    if value.free_symbols:
        raise ExpressionError("invalid_input", "'value' must not contain symbols")
    result = expr.subs(var, value)
    elapsed = {"total": round((time.perf_counter() - started) * 1000.0, 3)}
    if result.has(sp.zoo, sp.nan, sp.oo, -sp.oo):
        return _result(
            request, "evaluate", "unresolved",
            normalized_expression=str(expr),
            error="the expression is undefined or infinite at this value; no result is claimed",
            warnings=["undefined or infinite at the given value"], timings_ms=elapsed,
        )
    return _result(
        request, "evaluate", "ok",
        normalized_expression=str(expr), result_expression=str(result),
        exactness="symbolic_exact", assumptions=[f"{var} = {value}"], timings_ms=elapsed,
    )


_DOMAIN_NOTE = (
    "the simplified form is valid where both expressions are defined; points removed by the "
    "rewrite (for example a cancelled denominator) are not restored"
)


def _simplify(request: dict[str, Any], started: float) -> dict[str, Any]:
    expr, _var = _expression_and_variable(request)
    result = symbolic.simplify(expr)
    kind, note = symbolic.verify_equivalence(result, expr)
    elapsed = {"total": round((time.perf_counter() - started) * 1000.0, 3)}
    common: dict[str, Any] = {"normalized_expression": str(expr), "timings_ms": elapsed}
    if str(result) != str(expr):
        common["assumptions"] = [_DOMAIN_NOTE]
    if kind == "failed":
        return _result(
            request, "simplify", "internal_error",
            error=f"the simplified form failed its own equivalence check ({note}); it is not returned",
            warnings=[note], **common,
        )
    checks = [note]
    before, after = sp.count_ops(expr), sp.count_ops(result)
    if after < before:
        # A size claim is made only from the measured operation counts, never assumed.
        checks.append(f"operation count reduced from {before} to {after}")
    fields = dict(common, result_expression=str(result), exactness="symbolic_exact")
    if kind == "symbolic":
        return _result(request, "simplify", "ok", checks=checks, **fields)
    if kind == "numeric":
        return _result(
            request, "simplify", "ok", checks=checks,
            warnings=["the equivalence check is numeric only (not proven symbolically)"], **fields,
        )
    return _result(
        request, "simplify", "partial", checks=[],
        warnings=[f"the simplified form could not be verified: {note}"], **fields,
    )


_REAL_DOMAIN = (
    "solutions are searched in the real domain only; the equation is the expression set to zero"
)


def _solve(request: dict[str, Any], started: float) -> dict[str, Any]:
    expr, var = _expression_and_variable(request)
    try:
        solution = symbolic.solve_equation(expr, var)
    except symbolic.SolveUnsupported as exc:
        return _result(
            request, "solve", "unresolved",
            normalized_expression=str(expr),
            error=f"the solver has no method for this equation ({exc}); no roots are claimed",
            assumptions=[_REAL_DOMAIN],
            timings_ms={"total": round((time.perf_counter() - started) * 1000.0, 3)},
        )
    elapsed = {"total": round((time.perf_counter() - started) * 1000.0, 3)}
    common: dict[str, Any] = {
        "normalized_expression": str(expr),
        "assumptions": [_REAL_DOMAIN],
        "timings_ms": elapsed,
    }
    if solution in (sp.S.Reals, sp.S.Complexes):
        return _result(
            request, "solve", "unresolved",
            error="the solver reports that the equation holds on the whole domain; no list of roots is claimed",
            warnings=["every value in the domain satisfies it, so there is no finite root list"], **common,
        )
    candidates = symbolic.finite_roots(solution)
    if candidates is None:
        return _result(
            request, "solve", "unresolved",
            error=(
                f"the solution set is a {type(solution).__name__}, not a finite list of roots; "
                "no roots are claimed"
            ),
            **common,
        )

    parameters = sorted(expr.free_symbols - {var}, key=lambda s: s.name)
    if not candidates:
        if parameters:
            return _result(
                request, "solve", "unresolved",
                error=(
                    "no root was found for this variable, but the equation contains the parameter(s) "
                    + ", ".join(s.name for s in parameters)
                    + "; the answer depends on them and is not claimed"
                ),
                **common,
            )
        warnings = [
            "the solver found no real solution; the absence is not independently verified",
        ]
        complex_count = _complex_root_count(expr, var)
        if complex_count is True:
            warnings.append("the equation has infinitely many complex roots; they are not returned")
        elif complex_count:
            warnings.append(
                f"the equation has {complex_count} complex root(s), which this version does not return"
            )
        return _result(
            request, "solve", "partial",
            result_expression="EmptySet", exactness="none", warnings=warnings, **common,
        )

    kept: list[sp.Expr] = []
    kinds: list[str] = []
    dropped = 0
    unverified: list[str] = []
    for root in candidates:
        kind, note = symbolic.verify_root(root, expr, var)
        if kind == "failed":
            dropped += 1
            continue
        kept.append(root)
        kinds.append(kind)
        if kind == "unverified":
            unverified.append(note)
    if not kept:
        return _result(
            request, "solve", "internal_error",
            error="every root failed the substitution check; no solution is returned",
            warnings=["the solver's roots did not solve the equation"], **common,
        )

    fields = dict(common, result_expression=str(sp.FiniteSet(*kept)))
    fields["exactness"] = "symbolic_exact" if set(kinds) == {"symbolic"} else (
        "numeric" if set(kinds) == {"numeric"} else "none"
    )
    checks = [f"each of the {len(kept)} returned root(s) was substituted back into the equation"]
    warnings: list[str] = []
    if dropped:
        warnings.append(f"{dropped} root(s) failed the substitution check and were dropped")
    if unverified:
        warnings.append(f"{len(unverified)} root(s) could not be verified: {unverified[0]}")
    if dropped or unverified:
        return _result(request, "solve", "partial", checks=checks, warnings=warnings, **fields)
    if set(kinds) == {"numeric"}:
        warnings.append("the substitution check is numeric only (not proven symbolically)")
        return _result(request, "solve", "ok", checks=checks, warnings=warnings, **fields)
    if parameters:
        fields["assumptions"] = [
            *_REAL_DOMAIN,
            "the roots contain the parameter(s) "
            + ", ".join(s.name for s in parameters)
            + "; their membership in the real domain is not decided",
        ]
    return _result(request, "solve", "ok", checks=checks, **fields)


def _complex_root_count(expr: sp.Expr, var: sp.Symbol) -> int | bool:
    """How many roots the equation has over the complexes: a count, ``True`` for infinitely many, 0 for none."""
    try:
        solution = sp.solveset(expr, var, domain=sp.Complexes)
    except (NotImplementedError, ValueError, TypeError):
        return 0
    if solution in (sp.S.Complexes, sp.S.Reals):
        return True
    roots = symbolic.finite_roots(solution)
    if roots is None:
        return True
    return len(roots)


_HANDLERS: dict[str, Callable[[dict[str, Any], float], dict[str, Any]]] = {
    "differentiate": _differentiate,
    "integrate": _integrate,
    "evaluate": _evaluate,
    "simplify": _simplify,
    "solve": _solve,
}
OPERATIONS = tuple(_HANDLERS)


_COMMON_FIELDS = {"operation", "expression", "variable"}
#: The only extra request fields an operation may use. Anything else is a typed refusal, not a silent ignore.
_OPERATION_FIELDS: dict[str, set[str]] = {"evaluate": {"value"}}


def execute(request: Any) -> dict[str, Any]:
    if not isinstance(request, dict):
        return _failure(request, "unknown", "invalid_input", "request must be an object")
    operation = request.get("operation")
    if not isinstance(operation, str) or not operation:
        return _failure(request, "unknown", "invalid_input", "missing 'operation'")
    handler = _HANDLERS.get(operation)
    if handler is None:
        return _failure(request, operation, "unsupported", f"unknown operation '{operation}'")
    extra = set(request) - _COMMON_FIELDS - _OPERATION_FIELDS.get(operation, set())
    if extra:
        names = ", ".join(sorted(map(str, extra)))
        return _failure(request, operation, "invalid_input", f"field(s) not used by this operation: {names}")

    started = time.perf_counter()
    try:
        return handler(request, started)
    except ExpressionError as exc:
        return _failure(request, operation, exc.code, str(exc))
    except RecursionError:
        return _failure(request, operation, "resource_limit", "expression is nested too deeply")
    except MemoryError:
        return _failure(request, operation, "resource_limit", "out of memory")
    except Exception as exc:  # noqa: BLE001 - the contract is "never raise"
        return _failure(request, operation, "internal_error", f"{type(exc).__name__}")
