"""Symbolic operations on already-validated SymPy expressions."""

from __future__ import annotations

import sympy as sp


def differentiate(expr: sp.Expr, variable: sp.Symbol) -> sp.Expr:
    """Exact derivative. Constants and absent symbols differentiate to 0."""
    return sp.diff(expr, variable)
