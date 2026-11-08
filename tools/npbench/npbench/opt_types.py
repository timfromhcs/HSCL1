"""Result type shared by the optimisation solvers (TSP, knapsack)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Optional


@dataclass
class OptResult:
    status: str  # "SAT" | "UNSAT" | "UNKNOWN"; for decision tasks "SAT" means: the bound can be met
    witness: Any  # tour (vertex order) or selection (item indices)
    cert_kind: Optional[str]  # "LOWER_BOUND" | "LP_BOUND" | None
    cert: Any
    work: int
    note: str = ""
