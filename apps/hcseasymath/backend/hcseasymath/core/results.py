"""Typed result record (``hcseasymath.result.v1``) and the run-id/provenance helpers."""

from __future__ import annotations

import hashlib
import json
import platform
from typing import Any, Literal

import sympy as sp
from pydantic import BaseModel, ConfigDict

SCHEMA_VERSION = "hcseasymath.result.v1"

Status = Literal[
    "ok",
    "partial",
    "unresolved",
    "unsupported",
    "invalid_input",
    "resource_limit",
    "cancelled",
    "engine_unavailable",
    "internal_error",
]
Exactness = Literal["symbolic_exact", "numeric", "none"]


class MathResult(BaseModel):
    """What every operation returns. A non-``ok`` status never carries a result expression."""

    model_config = ConfigDict(extra="forbid")

    schema_version: Literal["hcseasymath.result.v1"] = SCHEMA_VERSION
    run_id: str
    status: Status
    operation: str
    engine: str
    input_digest: str
    normalized_expression: str | None = None
    result_expression: str | None = None
    exactness: Exactness = "none"
    assumptions: list[str] = []
    warnings: list[str] = []
    #: How the result was verified, for example "derivative of the result equals the input symbolically".
    checks: list[str] = []
    error: str | None = None
    timings_ms: dict[str, float] = {}
    provenance: dict[str, str] = {}


def input_digest(request: Any) -> str:
    """Stable digest of a request: canonical JSON, sorted keys."""
    try:
        blob = json.dumps(request, sort_keys=True, separators=(",", ":"), default=repr)
    except (TypeError, ValueError):
        blob = repr(request)
    return "sha256:" + hashlib.sha256(blob.encode("utf-8")).hexdigest()


def provenance() -> dict[str, str]:
    return {"sympy": sp.__version__, "python": platform.python_version()}


def run_id(digest: str, prov: dict[str, str]) -> str:
    """Deterministic: same input and same software give the same id."""
    material = digest + json.dumps(prov, sort_keys=True)
    return "run_" + hashlib.sha256(material.encode("utf-8")).hexdigest()[:16]
