"""Request -> typed result. ``execute`` never raises; failures are results with a status."""

from __future__ import annotations

import re
import time
from typing import Any

import sympy as sp

from . import symbolic
from .expression_ast import ExpressionError, parse
from .results import MathResult, input_digest, provenance, run_id

_VARIABLE = re.compile(r"[A-Za-z][A-Za-z0-9_]{0,15}\Z")
OPERATIONS = ("differentiate",)


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


def execute(request: Any) -> dict[str, Any]:
    if not isinstance(request, dict):
        return _failure(request, "unknown", "invalid_input", "request must be an object")
    operation = request.get("operation")
    if not isinstance(operation, str) or not operation:
        return _failure(request, "unknown", "invalid_input", "missing 'operation'")
    if operation not in OPERATIONS:
        return _failure(request, operation, "unsupported", f"unknown operation '{operation}'")

    started = time.perf_counter()
    try:
        return _differentiate(request, started)
    except ExpressionError as exc:
        return _failure(request, operation, exc.code, str(exc))
    except RecursionError:
        return _failure(request, operation, "resource_limit", "expression is nested too deeply")
    except MemoryError:
        return _failure(request, operation, "resource_limit", "out of memory")
    except Exception as exc:  # noqa: BLE001 - the contract is "never raise"
        return _failure(request, operation, "internal_error", f"{type(exc).__name__}")


def _differentiate(request: dict[str, Any], started: float) -> dict[str, Any]:
    text = request.get("expression")
    var = request.get("variable")
    if not isinstance(text, str):
        raise ExpressionError("invalid_input", "missing 'expression'")
    if not isinstance(var, str) or not _VARIABLE.match(var) or not var.isascii():
        raise ExpressionError("invalid_input", "missing or invalid 'variable'")
    expr = parse(text)
    result = symbolic.differentiate(expr, sp.Symbol(var))
    elapsed = (time.perf_counter() - started) * 1000.0
    return _result(
        request,
        "differentiate",
        "ok",
        normalized_expression=str(expr),
        result_expression=str(result),
        exactness="symbolic_exact",
        timings_ms={"total": round(elapsed, 3)},
    )
