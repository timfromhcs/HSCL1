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


_HANDLERS: dict[str, Callable[[dict[str, Any], float], dict[str, Any]]] = {
    "differentiate": _differentiate,
    "integrate": _integrate,
    "evaluate": _evaluate,
}
OPERATIONS = tuple(_HANDLERS)


def execute(request: Any) -> dict[str, Any]:
    if not isinstance(request, dict):
        return _failure(request, "unknown", "invalid_input", "request must be an object")
    operation = request.get("operation")
    if not isinstance(operation, str) or not operation:
        return _failure(request, "unknown", "invalid_input", "missing 'operation'")
    handler = _HANDLERS.get(operation)
    if handler is None:
        return _failure(request, operation, "unsupported", f"unknown operation '{operation}'")

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
